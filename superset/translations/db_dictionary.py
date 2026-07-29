# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""DB-backed translation dictionary.

Stores translations (UI strings + user content) in a table so they can be
edited at runtime and merged into the language pack served to the frontend.
Seeded once from the compiled ``messages.json`` files; the source files stay
the initial-load fallback, the DB becomes the live source of truth.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Iterator, Optional

import sqlalchemy as sa
from flask_appbuilder import Model

logger = logging.getLogger(__name__)

TRANSLATIONS_DIR = os.path.dirname(os.path.abspath(__file__))
DOMAIN = "superset"
_PACK_TTL_SECONDS = 15

# locale -> (expiry_epoch, merged_pack) ; short TTL so runtime edits show up fast
_pack_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def msgid_hash(msgid: str) -> str:
    """Stable hash so we can UNIQUE-index arbitrarily long msgids (markdown)."""
    return hashlib.sha256(msgid.encode("utf-8")).hexdigest()


class TranslationDictionary(Model):  # pylint: disable=too-few-public-methods
    __tablename__ = "translation_dictionary"
    __table_args__ = (
        sa.UniqueConstraint(
            "locale",
            "msgcontext",
            "msgid_hash",
            name="uq_translation_locale_ctx_hash",
        ),
        {"extend_existing": True},
    )

    id = sa.Column(sa.Integer, primary_key=True)
    locale = sa.Column(sa.String(16), nullable=False, index=True)
    msgcontext = sa.Column(sa.String(255), nullable=True)
    msgid = sa.Column(sa.Text, nullable=False)
    msgid_hash = sa.Column(sa.String(64), nullable=False)
    msgstr = sa.Column(sa.Text, nullable=False, default="")
    source = sa.Column(sa.String(8), nullable=False, default="db")  # 'po' | 'db'
    updated_on = sa.Column(sa.DateTime, nullable=True, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.locale}: {self.msgid[:40]}"


# --------------------------------------------------------------------------- #
# File <-> parsing helpers
# --------------------------------------------------------------------------- #
def _target_locales() -> Optional[set[str]]:
    """Which locales to seed/sync. None means every locale dir on disk.

    Defaults to the app's default locale + English so we don't bloat the table
    with every bundled language. Override with env TRANSLATION_DICTIONARY_LOCALES
    (comma-separated, or "all").
    """
    env = os.getenv("TRANSLATION_DICTIONARY_LOCALES", "").strip()
    if env:
        if env.lower() == "all":
            return None
        return {x.strip() for x in env.split(",") if x.strip()}
    try:
        from flask import current_app

        default = current_app.config.get("BABEL_DEFAULT_LOCALE", "en")
    except Exception:  # noqa: BLE001 - no app context
        default = "en"
    return {default, "en"}


def _load_file_pack(locale: str) -> dict[str, Any]:
    """Load a compiled messages.json as a FRESH dict (never share references)."""
    if not locale or locale == "en":
        filename = os.path.join(TRANSLATIONS_DIR, "empty_language_pack.json")
    else:
        filename = os.path.join(
            TRANSLATIONS_DIR, locale, "LC_MESSAGES", "messages.json"
        )
    try:
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {"domain": DOMAIN, "locale_data": {DOMAIN: {"": {"domain": DOMAIN}}}}


def _pack_entries(pack: dict[str, Any]) -> dict[str, Any]:
    return (pack.get("locale_data") or {}).get(DOMAIN) or {}


def iter_file_translations(
    locales: Optional[set[str]] = None,
) -> Iterator[tuple[str, str, str]]:
    """Yield (locale, msgid, msgstr) from every compiled messages.json on disk."""
    if not os.path.isdir(TRANSLATIONS_DIR):
        return
    for locale in sorted(os.listdir(TRANSLATIONS_DIR)):
        if locales is not None and locale not in locales:
            continue
        path = os.path.join(TRANSLATIONS_DIR, locale, "LC_MESSAGES", "messages.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:  # noqa: BLE001
            continue
        for msgid, val in _pack_entries(data).items():
            if not msgid:  # skip the "" metadata entry
                continue
            if isinstance(val, list):
                msgstr = val[0] if val else ""
            elif isinstance(val, str):
                msgstr = val
            else:
                msgstr = ""
            if msgstr and msgstr != msgid:
                yield locale, msgid, msgstr


# --------------------------------------------------------------------------- #
# Import (seed / sync-from-file)
# --------------------------------------------------------------------------- #
def import_from_files(only_missing: bool = True) -> int:
    """Insert file translations into the DB.

    Merge semantics: only add (locale, msgid) rows that are NOT already in the
    DB -- never overwrite an existing entry. Returns the number added.
    """
    from superset import db

    session = db.session
    locales = _target_locales()
    existing: set[tuple[str, str]] = set()
    if only_missing:
        for loc, h in session.query(
            TranslationDictionary.locale, TranslationDictionary.msgid_hash
        ).all():
            existing.add((loc, h))

    added = 0
    for locale, msgid, msgstr in iter_file_translations(locales):
        h = msgid_hash(msgid)
        key = (locale, h)
        if key in existing:
            continue
        existing.add(key)
        session.add(
            TranslationDictionary(
                locale=locale,
                msgcontext=None,
                msgid=msgid,
                msgid_hash=h,
                msgstr=msgstr,
                source="po",
                updated_on=datetime.utcnow(),
            )
        )
        added += 1
    try:
        session.commit()
    except Exception:  # noqa: BLE001 - another worker seeded concurrently
        session.rollback()
        raise
    invalidate_cache()
    return added


def seed_if_empty() -> int:
    """Initial load from files, ONLY when the table has no rows yet."""
    from superset import db

    session = db.session
    try:
        count = session.query(sa.func.count(TranslationDictionary.id)).scalar() or 0
    except Exception:  # noqa: BLE001 - table not created yet
        return 0
    if count > 0:
        return 0
    try:
        added = import_from_files(only_missing=True)
        logger.info("Seeded translation_dictionary with %s entries", added)
        return added
    except Exception:  # noqa: BLE001 - concurrent seed race
        session.rollback()
        return 0


# --------------------------------------------------------------------------- #
# Export (DB -> mo / po / json)
# --------------------------------------------------------------------------- #
def _read_meta(locale: str) -> dict[str, Any]:
    meta = _pack_entries(_load_file_pack(locale)).get("")
    if isinstance(meta, dict) and meta:
        return meta
    return {
        "domain": DOMAIN,
        "plural_forms": "nplurals=2; plural=(n != 1);",
        "lang": locale,
    }


def export_to_files() -> list[str]:
    """Write every locale in the DB back out to messages.{json,po,mo}."""
    from babel.messages.catalog import Catalog
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import write_po

    from superset import db

    session = db.session
    locales = [
        row[0]
        for row in session.query(TranslationDictionary.locale).distinct().all()
    ]
    written: list[str] = []
    for locale in locales:
        rows = (
            session.query(TranslationDictionary)
            .filter(TranslationDictionary.locale == locale)
            .all()
        )
        lc_dir = os.path.join(TRANSLATIONS_DIR, locale, "LC_MESSAGES")
        os.makedirs(lc_dir, exist_ok=True)

        # messages.json (Jed) -- what the language_pack endpoint reads as fallback
        entries: dict[str, Any] = {"": _read_meta(locale)}
        for row in rows:
            entries[row.msgid] = [row.msgstr]
        jed = {"domain": DOMAIN, "locale_data": {DOMAIN: entries}}
        with open(os.path.join(lc_dir, "messages.json"), "w", encoding="utf-8") as f:
            json.dump(jed, f, ensure_ascii=False)

        # messages.po + messages.mo (gettext)
        catalog = Catalog(locale=locale, domain=DOMAIN)
        for row in rows:
            if row.msgstr:
                catalog.add(
                    row.msgid,
                    string=row.msgstr,
                    context=row.msgcontext or None,
                )
        with open(os.path.join(lc_dir, "messages.po"), "wb") as f:
            write_po(f, catalog)
        with open(os.path.join(lc_dir, "messages.mo"), "wb") as f:
            write_mo(f, catalog)
        written.append(locale)
    return written


# --------------------------------------------------------------------------- #
# Merged language pack (file + DB) served to the frontend
# --------------------------------------------------------------------------- #
def invalidate_cache() -> None:
    _pack_cache.clear()


def get_merged_pack(locale: str) -> dict[str, Any]:
    """File pack with DB entries merged on top (DB wins). Cached briefly."""
    now = time.time()
    cached = _pack_cache.get(locale)
    if cached and cached[0] > now:
        return cached[1]

    pack = _load_file_pack(locale)
    try:
        from superset import db

        rows = (
            db.session.query(
                TranslationDictionary.msgid, TranslationDictionary.msgstr
            )
            .filter(TranslationDictionary.locale == locale)
            .all()
        )
        entries = pack.setdefault("locale_data", {}).setdefault(DOMAIN, {})
        for msgid, msgstr in rows:
            if msgstr:
                entries[msgid] = [msgstr]
    except Exception:  # noqa: BLE001 - fall back to the file pack
        logger.warning("Could not merge DB translations for %s", locale)

    _pack_cache[locale] = (now + _PACK_TTL_SECONDS, pack)
    return pack
