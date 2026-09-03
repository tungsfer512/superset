# Kế hoạch triển khai i18n nội dung (Content i18n) — Production

> **Mục tiêu**: dịch **nhãn dữ liệu theo từng dataset** (tên cột/metric → text thân thiện, đa ngôn
> ngữ) **và** nội dung do người dùng tạo (**tên chart, tiêu đề dashboard, tab, markdown, header, tên
> filter, tên dataset/folder**) theo **từng thực thể riêng biệt**, thay cho từ điển toàn cục theo
> chuỗi đang chạy. Áp dụng đồng nhất cho **Explore, dashboard thường, dashboard nhúng (guest)** và
> **export (CSV/XLSX)**. Thiết kế cho production, không dừng ở MVP.
>
> Phiên bản plan: **v2** (viết lại sau khi khảo sát code thực tế của fork — xem §1).

---

## MỤC LỤC

| § | Nội dung |
|---|---|
| 0 | TL;DR — các quyết định kiến trúc đã chốt |
| 1 | Hiện trạng codebase (khảo sát thực tế, có anchor file:line) |
| 2 | Vấn đề cụ thể của cơ chế toàn cục hiện tại |
| 3 | Nguyên tắc thiết kế dài hạn |
| 4 | Kiến trúc tổng thể |
| 5 | Mô hình dữ liệu + DDL + migration |
| 6 | Đặc tả khoá (key spec) — registry loại thực thể/trường |
| 7 | Backend: package, service, resolver, locale, cache, version |
| 8 | Backend: các điểm cắm (integration points) |
| 9 | REST API — đặc tả đầy đủ |
| 10 | Frontend: registry + `translateEntity` + di trú 75 call-site |
| 11 | Frontend: UI biên tập + trang quản trị |
| 12 | Per-dashboard-per-chart override (Mức B) |
| 13 | Di trú dữ liệu từ `translation_dictionary` toàn cục |
| 14 | Bảo mật, RBAC, embed |
| 15 | Hiệu năng & caching |
| 16 | Kiểm thử |
| 17 | Lộ trình phase + acceptance criteria + ước lượng |
| 18 | Runbook triển khai & rollback |
| 19 | Rủi ro & giảm thiểu |
| 20 | Bản đồ thay đổi theo file |
| 21 | Cấu hình |
| 22 | Phụ lục: schema JSON, ví dụ payload, quyết định mặc định |

---

## 0. TL;DR — quyết định kiến trúc đã chốt

1. **Một store chuẩn hoá `object_translations`** khoá theo `(object_type, object_id, field, locale)`
   — không dùng cột JSON, không dùng bảng riêng cho từng loại. Thêm loại thực thể mới **không cần
   migration**.
2. **Nhãn dữ liệu (cột/metric) resolve ở backend**, cắm vào `verbose_map`/`data` của datasource →
   tự động đúng ở Explore, dashboard, embed, chart data, CSV/XLSX export, không phụ thuộc client.
3. **Nội dung render ở client (tên chart/dashboard/tab/markdown/filter) dùng bundle theo phạm vi**
   (scoped bundle) tải qua endpoint riêng, và frontend tra cứu **theo khoá thực thể**
   (`translateEntity(type, id, field, fallback)`) thay cho tra theo chuỗi toàn cục.
4. **Mức B (override tên chart theo từng dashboard) BẬT ngay** — đúng yêu cầu "từng chart, từng
   dashboard có bản dịch riêng biệt". Thứ tự resolve: override-trong-dashboard → bản dịch của chart →
   giá trị gốc.
5. **Locale** theo thứ tự: `?lang=` → header `X-Superset-Locale` → claim `locale` trong guest token →
   session/babel (user đăng nhập) → `Accept-Language` → default config.
6. **Mọi cache key liên quan phải kèm `locale` + `content_i18n_version`**; version là counter lưu
   trong `key_value`, bump mỗi lần ghi bản dịch → cache cũ tự chết.
7. **Dual-read trong thời gian di trú**: thiếu bản dịch per-entity → fallback về từ điển toàn cục
   hiện có (`translation_dictionary`). Bật/tắt bằng config. Sau khi seed + QA xong thì tắt.
8. **Từ điển toàn cục KHÔNG bị xoá** — nó tiếp tục phục vụ **chuỗi UI** (`t()`); chỉ phần **nội
   dung** được bóc ra khỏi nó.

---

## 1. Hiện trạng codebase (khảo sát thực tế)

### 1.1. Đã có một từ điển DB **toàn cục** (khác với giả định ban đầu)

Fork này đã triển khai i18n DB-backed toàn cục qua 3 commit `e35186387d`, `6189d24008`, `ef5cca3b66`:

| Thành phần | Vị trí | Ghi chú |
|---|---|---|
| Model `TranslationDictionary` | [db_dictionary.py](superset/translations/db_dictionary.py) | `(locale, msgcontext, msgid_hash)` UNIQUE; `msgid_hash` = sha256 để index msgid dài (markdown) |
| Seed từ file `.json` | `import_from_files()`, `seed_if_empty()` | chỉ thêm khi thiếu, không ghi đè |
| Export ngược ra `.json/.po/.mo` | `export_to_files()` | |
| Merge pack phục vụ FE | `get_merged_pack()` (TTL 15s, cache in-process) | DB thắng file |
| Endpoint language pack | [superset/views/core.py:907+](superset/views/core.py#L907) | trả pack đã merge, `Cache-Control: no-store` |
| REST API + seed lúc boot | [docker/pythonpath_dev/superset_config.py](docker/pythonpath_dev/superset_config.py) (~L910+) | `TranslationDictionaryRestApi`, `class_permission_name="TranslationDictionary"`, có `sync_from_file`/`export_to_file` |
| Trang quản trị | [src/pages/TranslationDictionaryList/index.tsx](superset-frontend/src/pages/TranslationDictionaryList/index.tsx) + route `/translation-dictionary/` ([routes.tsx:370](superset-frontend/src/views/routes.tsx#L370)) | |
| Search theo bản dịch | `translated_name_matches()` dùng ở [charts/filters.py](superset/charts/filters.py), [dashboards/filters.py](superset/dashboards/filters.py), [datasets/filters.py](superset/datasets/filters.py) | subquery `msgstr ILIKE %v%` → `IN (msgid)` |

### 1.2. Frontend dịch nội dung bằng tra chuỗi toàn cục

- `Translator.translateContent()` ([Translator.ts](superset-frontend/packages/superset-ui-core/src/translation/Translator.ts)) —
  gọi thẳng `i18n.gettext(text)`, **không sprintf** (đúng, vì nội dung có thể chứa `%`).
- Export qua [TranslatorSingleton.ts](superset-frontend/packages/superset-ui-core/src/translation/TranslatorSingleton.ts).
- **75 call-site trên 15 file** (đếm thực tế). Danh sách đầy đủ ở §10.3.

### 1.3. Nhãn cột/metric

- `TableColumn.verbose_name` ([models.py:769](superset/connectors/sqla/models.py#L769)),
  `SqlMetric.verbose_name` ([models.py:1001](superset/connectors/sqla/models.py#L1001)).
- Gom vào `verbose_map` ([models.py:352](superset/connectors/sqla/models.py#L352)), nhúng vào
  `data` ([models.py:366](superset/connectors/sqla/models.py#L366)), lọc bớt ở
  `data_for_slices` ([models.py:402](superset/connectors/sqla/models.py#L402)).
- CSV/XLSX dùng lại `verbose_map` khi đổi tên cột DataFrame
  ([query_context_processor.py:996-998](superset/common/query_context_processor.py#L996)).
- **Hiện chỉ có 1 giá trị duy nhất — không đa ngôn ngữ.**

### 1.4. Embed & locale

- [superset/embedded/view.py](superset/embedded/view.py) đã hỗ trợ `?lang=` nhưng **chỉ ghi đè
  `common.locale` trong bootstrap HTML** (ảnh hưởng language pack FE tải về). Các **request API sau
  đó** (`/api/v1/dashboard/...`, `/api/v1/chart/data`) **không mang locale** → backend dùng
  session/`Accept-Language`, cross-origin iframe thường không có cookie ⇒ **locale backend sai**.
- Locale user đăng nhập: `session["locale"]` set qua
  [`patch_flask_locale`](superset/initialization/__init__.py#L856).
- Guest token ([superset/security/guest_token.py](superset/security/guest_token.py)) có `user`,
  `resources`, `rls_rules` — **chưa có `locale`**.

### 1.5. Luồng nạp dữ liệu dashboard (quan trọng cho thiết kế bundle)

Dashboard **không** dùng bootstrap server-render cho nội dung; SPA gọi REST:
- `/api/v1/dashboard/<idOrSlug>` — metadata + `position_json`
- `/api/v1/dashboard/<idOrSlug>/charts` — danh sách slice
- `/api/v1/dashboard/<idOrSlug>/datasets` — datasource (chứa `verbose_map`)

(xem [hooks/apiResources/dashboards.ts](superset-frontend/src/hooks/apiResources/dashboards.ts),
[DashboardPage.tsx:133-140](superset-frontend/src/dashboard/containers/DashboardPage.tsx#L133))

Explore: `/api/v1/explore/` ([explore/api.py:56](superset/explore/api.py#L56)) trả gói
`form_data + slice + dataset`.

⇒ **Bundle dịch phải đi qua REST**, không nhét vào `common` bootstrap (vốn được memoize toàn cục 60s
theo `(user_id, locale)` tại [views/base.py:369](superset/views/base.py#L369)).

---

## 2. Vấn đề cụ thể của cơ chế toàn cục hiện tại

| # | Vấn đề | Hệ quả thực tế |
|---|---|---|
| V1 | Khoá theo **chuỗi**, không theo thực thể | 2 chart cùng tên "Doanh thu" ở 2 dashboard khác nhau **buộc** phải cùng bản dịch |
| V2 | Trùng chuỗi UI ↔ nội dung | Chart tên "Dashboards" sẽ ăn bản dịch của menu "Dashboards" |
| V3 | Không dịch được cột/metric theo dataset | Cột `rev` ở 2 dataset khác nghĩa vẫn ra 1 nhãn |
| V4 | Dịch xảy ra **hoàn toàn ở client** | Export CSV/XLSX, ảnh báo cáo (screenshot/report), chart data → **không dịch** |
| V5 | Bảng phình theo mọi msgid UI (~vài nghìn dòng) và trộn chung 2 mục đích | Đội dịch nội dung phải lội qua chuỗi UI |
| V6 | `translated_name_matches` fan-out theo chuỗi | Search "doanh thu" khớp cả object không liên quan trùng tên |
| V7 | Embed: locale không tới backend | Nhãn cột/metric trong iframe sai ngôn ngữ (khi backend resolve) |
| V8 | Không có version → cache lệch | `get_merged_pack` TTL 15s chỉ vá tạm; các cache khác (query, datasource) không biết bản dịch đổi |

Thiết kế mới giải quyết trọn V1–V8.

---

## 3. Nguyên tắc thiết kế dài hạn

1. **Một nguồn sự thật**: mọi bản dịch nội dung nằm ở một bảng, một resolver, một API.
2. **Khoá thực thể tổng quát**: `(object_type, object_id, field, locale)` — mở rộng loại mới không
   đổi schema.
3. **Resolve gần dữ liệu nhất**: nhãn dữ liệu → backend (phủ cả export/report/embed); nội dung render
   → bundle scoped ở client (tránh N+1 và tránh phá cấu trúc payload hiện có).
4. **Fallback tầng, không bao giờ rỗng**: `vi-VN` → `vi` → default locale → `verbose_name`/giá trị gốc.
5. **Không phá vỡ hiện tại**: dual-read về từ điển toàn cục trong suốt giai đoạn di trú; mọi thay đổi
   ẩn sau `CONTENT_I18N_ENABLED`.
6. **Hiệu năng là ràng buộc cứng**: batch 1 query/trang, cache 2 tầng (request-scope + Redis), version
   trong mọi cache key.
7. **An toàn embed**: guest chỉ nhận bundle của dashboard được cấp trong token.
8. **Quản trị được**: RBAC riêng, báo cáo độ phủ, import/export CSV/XLSX/PO, dọn orphan.

---

## 4. Kiến trúc tổng thể

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      object_translations  (metadata DB)                     │
│           (object_type, object_id, field, locale)  →  value                 │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                ┌──────────────▼───────────────┐        ┌────────────────────┐
                │  TranslationResolver          │◄──────►│ cache 2 tầng       │
                │  resolve / bulk_resolve       │        │ g._ct_cache (req)  │
                │  scope_bundle / upsert        │        │ Redis (locale+ver) │
                └───────┬──────────────┬────────┘        └────────────────────┘
                        │              │
     ── nhãn dữ liệu ───┘              └─── nội dung render client ───
     ┌──────────────────────────┐        ┌──────────────────────────────────┐
     │ BaseDatasource.verbose_map│       │ GET/POST /api/v1/content_i18n/    │
     │ .data / .data_for_slices  │       │           bundle                  │
     │ query_context get_data    │       │ scope=dashboard:12 | refs=[...]   │
     └────────────┬──────────────┘       └────────────────┬─────────────────┘
                  │                                        │
   Explore controls · chart render · CSV/XLSX      registerContentTranslations()
   · report screenshot · embed                     translateEntity(type,id,field)
                                                   (SliceHeader, Tab, Markdown,
                                                    Header, FilterControl, cards…)

Locale resolver  (?lang → X-Superset-Locale → guest claim → session → AL → default)
      tham gia CẢ HAI nhánh và nằm trong MỌI cache key.
```

---

## 5. Mô hình dữ liệu

### 5.1. Bảng `object_translations`

```sql
CREATE TABLE object_translations (
    id             BIGSERIAL PRIMARY KEY,
    object_type    VARCHAR(64)   NOT NULL,   -- xem §6
    object_id      VARCHAR(191)  NOT NULL,   -- id số dạng chuỗi, hoặc uuid
    field          VARCHAR(191)  NOT NULL,   -- 'verbose_name' | 'slice_name' | 'component.<id>.text' | …
    locale         VARCHAR(16)   NOT NULL,   -- đã normalize: 'vi', 'en'
    value          TEXT          NOT NULL,
    -- vận hành
    is_auto        BOOLEAN       NOT NULL DEFAULT FALSE,  -- do máy/seed sinh, chờ duyệt
    source         VARCHAR(16)   NOT NULL DEFAULT 'manual', -- manual|seed|import|auto
    source_hash    VARCHAR(64),                            -- sha256(giá trị gốc lúc dịch) → phát hiện stale
    -- audit
    created_on     TIMESTAMP,
    changed_on     TIMESTAMP,
    created_by_fk  INTEGER REFERENCES ab_user(id),
    changed_by_fk  INTEGER REFERENCES ab_user(id),
    CONSTRAINT uq_object_translation
        UNIQUE (object_type, object_id, field, locale)
);

CREATE INDEX ix_object_translations_lookup
    ON object_translations (object_type, object_id, locale);
CREATE INDEX ix_object_translations_scope
    ON object_translations (object_type, locale);
CREATE INDEX ix_object_translations_changed_on
    ON object_translations (changed_on);
```

**Ghi chú kỹ thuật**

- `VARCHAR(191)`: giới hạn an toàn cho MySQL `utf8mb4` + index (191×4 = 764 byte < 767).
- `source_hash`: lưu sha256 của **giá trị gốc** tại thời điểm dịch. Khi tên chart gốc đổi mà bản dịch
  chưa cập nhật → UI đánh dấu **"stale"**. Đây là tính năng production thật sự cần (không có nó, bản
  dịch cũ âm thầm hiển thị sai).
- `is_auto` + `source`: phân biệt bản dịch seed/máy với bản dịch người duyệt → cho phép workflow
  "review hàng loạt".
- Không tạo FK tới `slices`/`dashboards`/`table_columns`: `object_id` là polymorphic. Dọn orphan bằng
  job định kỳ (§7.8) — đánh đổi có chủ ý để giữ schema mở rộng được.

### 5.2. Bảng `translation_locales` (P3, tuỳ chọn)

```sql
CREATE TABLE translation_locales (
    code           VARCHAR(16) PRIMARY KEY,   -- 'vi'
    label          VARCHAR(64) NOT NULL,      -- 'Tiếng Việt'
    fallback_code  VARCHAR(16),               -- 'en'
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    is_default     BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order     INTEGER NOT NULL DEFAULT 0
);
```

P1–P2 dùng hằng config (`CONTENT_I18N_LOCALES`). Chuyển sang bảng ở P3 mà không đổi API (service đọc
bảng nếu tồn tại, ngược lại đọc config).

### 5.3. Version counter

Không dùng `SELECT max(changed_on)` mỗi request (thêm 1 query/req). Dùng:

- **Nguồn bền vững**: `key_value` store có sẵn của Superset (resource `content_i18n`, key `version`),
  giá trị = integer counter.
- **Cache nóng**: Redis key `content_i18n:version` (TTL 300s), đọc trước; miss → đọc `key_value`.
- Mọi thao tác ghi (upsert/delete/import/seed) gọi `bump_version()` → tăng counter, set Redis.

### 5.4. Alembic migration

`superset/migrations/versions/2026-XX-XX_HH-MM_<rev>_add_object_translations.py`

- Dùng helper trong `superset.migrations.shared.utils` (`create_table`, `create_index`,
  `drop_table`…) để tương thích đa dialect.
- `upgrade()`: tạo bảng + 3 index.
- `downgrade()`: drop index + drop table.
- **Không** seed dữ liệu trong migration (seed là CLI riêng, idempotent, chạy được lại — xem §13).
- Kiểm thử migration trên SQLite + Postgres + MySQL (fork đang chạy Postgres, nhưng giữ tương thích).

---

## 6. Đặc tả khoá (key spec)

### 6.1. Registry loại thực thể

| object_type | object_id | field | Nguồn giá trị gốc | Phase |
|---|---|---|---|---|
| `dataset_column` | `TableColumn.id` | `verbose_name` | `verbose_name or column_name` | P1 |
| `dataset_column` | `TableColumn.id` | `description` | `description` | P1 |
| `dataset_metric` | `SqlMetric.id` | `verbose_name` | `verbose_name or metric_name` | P1 |
| `dataset_metric` | `SqlMetric.id` | `description` | `description` | P1 |
| `dataset` | `SqlaTable.id` | `table_name` | `table_name` | P2 |
| `dataset` | `SqlaTable.id` | `description` | `description` | P2 |
| `dataset_folder` | `SqlaTable.id` | `folder.<folderUuid>.name` | `folders[].name` (JSON) | P2 |
| `chart` | `Slice.id` | `slice_name` | `slice_name` | P2 |
| `chart` | `Slice.id` | `description` | `description` | P2 |
| `dashboard` | `Dashboard.id` | `dashboard_title` | `dashboard_title` | P2 |
| `dashboard` | `Dashboard.id` | `description` | metadata | P2 |
| `dashboard_component` | `Dashboard.id` | `component.<componentId>.text` | `position_json[componentId].meta.text` | P2 |
| `dashboard_component` | `Dashboard.id` | `component.<chartComponentId>.sliceNameOverride` | override tên chart trong dashboard này (Mức B) | P2 |
| `native_filter` | `Dashboard.id` | `filter.<filterId>.name` | `json_metadata.native_filter_configuration[].name` | P2 |
| `native_filter` | `Dashboard.id` | `filter.<filterId>.description` | | P5 |
| `saved_query` / `annotation_layer` / `tag` | id | `label`/`name` | | P5 |
| `form_data` | `Slice.id` | `formData.<path>` (vd `x_axis_label`) | tiêu đề trục người dùng gõ | P5 |

**Quy tắc chung**
- `object_type`: snake_case, ≤64 ký tự, khai báo trong enum `ObjectType` — **API từ chối type lạ**.
- `field`: hoặc là tên cột thật, hoặc dạng có tiền tố `component.` / `filter.` / `folder.` /
  `formData.` + định danh + hậu tố. Regex hợp lệ:
  `^[a-zA-Z_][a-zA-Z0-9_]*(\.[A-Za-z0-9_\-]+)*$`, ≤191 ký tự.
- Khoá phẳng dùng ở bundle/FE: `"<object_type>:<object_id>:<field>"`.

### 6.2. Vì sao `dashboard_component` gắn vào `dashboard_id`

Tab/markdown/header/filter nằm trong `position_json`/`json_metadata`, **không có bản ghi DB riêng**.
`componentId` (vd `TAB-a1b2`, `MARKDOWN-x9`) do FE sinh và **ổn định qua các lần lưu** (chỉ đổi khi
xoá/tạo lại component). Ràng buộc này được ghi nhận là rủi ro R6 (§19) và xử lý bằng:
- job dọn orphan (component đã bị xoá khỏi layout),
- panel biên tập luôn liệt kê component **đang tồn tại** + cảnh báo bản dịch mồ côi.

---

## 7. Backend — package, service, resolver

### 7.1. Cấu trúc package

```
superset/content_i18n/
├── __init__.py
├── models.py          # ObjectTranslation, ObjectType enum
├── keys.py            # TranslationKey, parse/format khoá phẳng, validate
├── locale.py          # get_content_locale(), normalize_locale(), supported_locales()
├── service.py         # resolver: resolve/bulk_resolve/scope_bundle/upsert/delete/coverage
├── version.py         # get_version(), bump_version()
├── scopes.py          # builder: dashboard_scope(), explore_scope(), list_scope()
├── api.py             # ContentTranslationRestApi + BundleApi
├── schemas.py         # marshmallow schemas
├── commands/
│   ├── seed.py        # seed từ translation_dictionary toàn cục
│   ├── import_export.py
│   └── cleanup.py     # dọn orphan
└── cli.py             # superset content-i18n {seed,import,export,coverage,cleanup}
```

### 7.2. `locale.py`

```python
def normalize_locale(raw: str | None) -> str:
    """'vi-VN'/'vi_VN' → 'vi'; không hợp lệ/không hỗ trợ → default."""

def supported_locales() -> list[str]:
    """translation_locales (nếu có) → CONTENT_I18N_LOCALES → [BABEL_DEFAULT_LOCALE]."""

def get_content_locale() -> str:
    """Thứ tự ưu tiên (dừng ở nguồn đầu tiên hợp lệ):
      1. request.args['lang']                 — iframe embed, permalink, report
      2. header 'X-Superset-Locale'           — SupersetClient của embedded SDK gắn
      3. guest token claim 'locale'           — host app phát token
      4. flask_babel.get_locale()             — user đăng nhập (session)
      5. request.accept_languages.best_match(supported_locales())
      6. CONTENT_I18N_DEFAULT_LOCALE
    Kết quả cache trong flask.g._content_locale (1 lần / request).
    """
```

> **Không** dùng `Accept-Language` làm nguồn chính: fetch/XHR không cho JS ghi header này, và
> proxy hay ghi đè.

### 7.3. `service.py` — API nội bộ

```python
Key = tuple[str, str, str]          # (object_type, object_id, field)

def resolve(key: Key, locale: str | None = None, default: str = "") -> str
def bulk_resolve(keys: Iterable[Key], locale: str | None = None) -> dict[Key, str]
def scope_bundle(keys: Iterable[Key], locale: str | None = None) -> dict[str, str]
    # trả {"chart:12:slice_name": "Doanh thu", ...} — CHỈ chứa key có bản dịch

def upsert(rows: list[TranslationRow], user_id: int | None) -> int
def delete(keys: Iterable[Key], locale: str | None = None) -> int
def list_for(object_type: str, object_id: str) -> list[ObjectTranslation]
def coverage(object_type: str | None = None) -> list[CoverageRow]
def mark_stale(object_type: str, object_id: str, field: str, new_source: str) -> None
```

**Thuật toán `bulk_resolve`** (1 query cho cả trang):

```
1. locale = normalize(locale or get_content_locale())
2. tách keys thành hit/miss theo cache request-scope  g._ct_cache[(locale, key)]
3. miss → thử Redis: key = f"ci18n:{version}:{locale}:{sha1(sorted(miss))}"
4. vẫn miss → 1 query:
     SELECT object_type, object_id, field, locale, value
     FROM object_translations
     WHERE locale IN (locale, fallback_locale)
       AND (object_type, object_id) IN (...)      -- tuple IN, chunk 500
5. ưu tiên locale chính > fallback_locale
6. ghi Redis (TTL CONTENT_I18N_CACHE_TTL) + ghi g._ct_cache
7. key không có bản dịch → KHÔNG có trong dict trả về (caller tự fallback về giá trị gốc)
```

Chunk `IN (...)` theo 500 tuple để tránh vỡ giới hạn tham số của driver.

### 7.4. Fallback chain (chốt)

```
value(locale)            ví dụ 'vi'
 → value(fallback_locale) 'en'      (nếu CONTENT_I18N_FALLBACK_CHAIN bật)
 → dual-read từ translation_dictionary theo giá trị gốc  (trong giai đoạn di trú)
 → giá trị gốc (verbose_name / slice_name / …)
 → tên kỹ thuật (column_name / metric_name)
```

### 7.5. Precedence nhãn dữ liệu (chốt)

```
label do user tự đặt trong form_data (adhoc metric label, AS alias)
  >  object_translations[dataset_metric|dataset_column].verbose_name[locale]
  >  verbose_name (cột DB)
  >  metric_name / column_name
```

Nguyên tắc: **bản dịch không bao giờ đè lên thứ người dùng gõ tay trong chart**.

### 7.6. Caching & invalidation

| Cache | Key hiện tại | Bổ sung |
|---|---|---|
| `cached_common_bootstrap_data` | `(user_id, locale)` | giữ nguyên (không nhét bundle vào đây) |
| Bundle Redis | — | `ci18n:bundle:{version}:{locale}:{scope_hash}` |
| `bulk_resolve` Redis | — | `ci18n:{version}:{locale}:{keys_hash}` |
| Datasource `data`/`verbose_map` | @property, không cache | thêm memo theo `(id, locale, version)` trong `flask.g` |
| Chart data query cache ([query_cache_key](superset/common/query_context_processor.py#L248)) | `datasource.uid`, `changed_on`, rls… | **thêm** `content_locale`, `content_i18n_version` |
| Dataset list/dashboard API response cache (`@cache` của FAB) | user/perm | thêm locale + version vào key builder |
| `get_merged_pack` (UI strings) | TTL 15s | giữ nguyên |

**Vì sao phải thêm vào `query_cache_key`**: `get_data()` đổi tên cột DataFrame theo `verbose_map`
trước khi sinh CSV/XLSX ([:996](superset/common/query_context_processor.py#L996)). Nếu kết quả
table-like được cache mà key không kèm locale ⇒ user `en` có thể nhận file cột tiếng Việt. Đây là bug
im lặng, bắt buộc chặn ngay từ P1.

### 7.7. Request-scope memo (bắt buộc)

`verbose_map` là `@property` và `data_for_slices` gọi nó **trong vòng lặp qua từng slice**
([models.py:402+](superset/connectors/sqla/models.py#L402)). Nếu resolver query mỗi lần gọi → N+1
nghiêm trọng trên dashboard 30 chart. Giải pháp:

```python
# superset/connectors/sqla/models.py (BaseDatasource)
@property
def verbose_map(self) -> dict[str, str]:
    locale = get_content_locale()
    memo = g.setdefault("_verbose_map_memo", {})
    ck = (self.type, self.id, locale, content_i18n_version())
    if ck not in memo:
        memo[ck] = self._build_verbose_map(locale)   # 1 bulk_resolve
    return memo[ck]
```

### 7.8. Job dọn dẹp

`superset content-i18n cleanup [--dry-run]`:
- Xoá row trỏ tới `chart`/`dashboard`/`dataset_column`/`dataset_metric` **không còn tồn tại**.
- Xoá row `dashboard_component`/`native_filter` mà componentId/filterId không còn trong
  `position_json`/`json_metadata`.
- Đánh dấu `stale` khi `source_hash` ≠ hash(giá trị gốc hiện tại).
- Chạy được qua Celery beat (khuyến nghị hằng ngày).

---

## 8. Backend — các điểm cắm

| # | File:anchor | Thay đổi | Phase |
|---|---|---|---|
| B1 | [connectors/sqla/models.py:352](superset/connectors/sqla/models.py#L352) `verbose_map` | build theo locale qua `bulk_resolve` + memo `g` | P1 |
| B2 | [connectors/sqla/models.py:366](superset/connectors/sqla/models.py#L366) `data` | `columns`/`metrics` con: `verbose_name`, `description` đã localize | P1 |
| B3 | [connectors/sqla/models.py:402](superset/connectors/sqla/models.py#L402) `data_for_slices` | dùng lại memo, không tự query | P1 |
| B4 | [query_context_processor.py:248](superset/common/query_context_processor.py#L248) `query_cache_key` | thêm `content_locale` + `content_i18n_version` | P1 |
| B5 | [query_context_processor.py:996](superset/common/query_context_processor.py#L996) `get_data` | không đổi logic (đã ăn theo `verbose_map`), thêm test | P1 |
| B6 | `superset/content_i18n/api.py` | endpoint bundle + CRUD | P1/P2 |
| B7 | [dashboards/api.py] `get` / `get_charts` | (tuỳ chọn) đính `content_translations` inline khi `CONTENT_I18N_INLINE_BUNDLE=True` | P2 |
| B8 | [explore/api.py:56](superset/explore/api.py#L56) | đính bundle scope explore (chart + dataset folder) | P2 |
| B9 | [embedded/view.py:90](superset/embedded/view.py#L90) | ngoài `common.locale`, thêm `bootstrap_data["content_i18n"] = {"locale":…, "version":…}` để FE gắn header | P2 |
| B10 | [security/guest_token.py](superset/security/guest_token.py) + [manager.py:2673](superset/security/manager.py#L2673) | thêm claim `locale` (optional) vào `GuestToken`; đọc trong `get_content_locale()` | P2 |
| B11 | [charts/filters.py](superset/charts/filters.py), [dashboards/filters.py](superset/dashboards/filters.py), [datasets/filters.py](superset/datasets/filters.py) | thay `translated_name_matches` bằng `EXISTS` join `object_translations` theo id thực thể | P2 |
| B12 | [views/core.py:907](superset/views/core.py#L907) | giữ nguyên (UI strings) | — |
| B13 | `superset/reports/` (screenshot/CSV report) | truyền locale của owner/report vào ngữ cảnh render | P4 |
| B14 | `superset/commands/dashboard/export`, `chart/export` | (tuỳ chọn) xuất kèm `translations.yaml` | P5 |

### 8.1. Ví dụ B11 — search theo bản dịch, đúng thực thể

```python
# superset/charts/filters.py
def apply(self, query: Query, value: Any) -> Query:
    ilike_value = f"%{value}%"
    locale = get_content_locale()
    translated = (
        select(ObjectTranslation.object_id)
        .where(
            ObjectTranslation.object_type == ObjectType.CHART,
            ObjectTranslation.field == "slice_name",
            ObjectTranslation.locale == locale,
            ObjectTranslation.value.ilike(ilike_value),
        )
    )
    return query.filter(
        or_(
            Slice.slice_name.ilike(ilike_value),
            Slice.description.ilike(ilike_value),
            cast(Slice.id, String).in_(translated),   # khớp ĐÚNG chart, không fan-out
        )
    )
```

---

## 9. REST API — đặc tả

Base: `/api/v1/content_translation/`. Class permission: `ContentTranslation`.

### 9.1. Bundle (đọc — nóng nhất)

```
GET /api/v1/content_translation/bundle?scope=dashboard:12&locale=vi
GET /api/v1/content_translation/bundle?scope=explore:slice:34
GET /api/v1/content_translation/bundle?scope=dataset:9
```

Response `200`:
```json
{
  "locale": "vi",
  "version": 271,
  "scope": "dashboard:12",
  "entries": {
    "dashboard:12:dashboard_title": "Tổng quan kinh doanh",
    "chart:34:slice_name": "Doanh thu theo tháng",
    "dashboard_component:12:component.TAB-a1b2.text": "Tổng quan",
    "dashboard_component:12:component.CHART-x9.sliceNameOverride": "Doanh thu (Q4)",
    "native_filter:12:filter.NATIVE_FILTER-1.name": "Khu vực"
  }
}
```

- Header `ETag: W/"ci18n-271-vi-<scope_hash>"`, `Cache-Control: private, max-age=60`.
- Client gửi `If-None-Match` → `304` khi version không đổi (rẻ hơn nhiều so với gửi lại bundle).
- **Chỉ trả entry có bản dịch** (không nhồi giá trị gốc) → bundle nhỏ.
- Guest token: chỉ chấp nhận `scope=dashboard:<id>` với `<id>` nằm trong `resources` của token; sai →
  `403`.

```
POST /api/v1/content_translation/bundle
{ "locale": "vi", "refs": [["chart", "1", "slice_name"], ["chart", "2", "slice_name"]] }
```
→ dùng cho các trang danh sách (ChartList/DashboardList/DatasetList/Home) khi tập id là động.
Giới hạn `CONTENT_I18N_MAX_REFS_PER_REQUEST` (mặc định 500).

### 9.2. CRUD & quản trị

| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| `GET` | `/` | list, filter `object_type`, `object_id`, `locale`, `is_auto`, `q` (ilike value), phân trang | `can_read` |
| `POST` | `/` | tạo 1 row | `can_write` |
| `PUT` | `/<pk>` | sửa | `can_write` |
| `DELETE` | `/<pk>` | xoá | `can_write` |
| `POST` | `/bulk_upsert` | mảng row, upsert theo unique key, transaction | `can_write` |
| `POST` | `/bulk_delete` | xoá theo mảng key hoặc id | `can_write` |
| `GET` | `/for/<object_type>/<object_id>` | mọi field × locale của 1 thực thể + **giá trị gốc** để đối chiếu | `can_read` |
| `GET` | `/coverage?object_type=&locale=` | `{type, locale, total, translated, pct, stale}` | `can_read` |
| `GET` | `/missing?object_type=&locale=&page=` | danh sách thực thể **chưa có** bản dịch (để đội dịch làm việc theo hàng đợi) | `can_read` |
| `GET` | `/export?format=csv\|xlsx\|po&object_type=&locale=` | file song ngữ (source, target, key) | `can_read` |
| `POST` | `/import` | upload CSV/XLSX/PO, `mode=merge\|overwrite`, có `dry_run=true` trả diff | `can_write` |
| `POST` | `/seed_from_dictionary` | chạy §13 (idempotent, hỗ trợ `dry_run`) | `can_write` |
| `POST` | `/cleanup` | dọn orphan / đánh dấu stale | `can_write` |

**Định dạng CSV export** (cột cố định, đội dịch làm việc trên Excel):

```csv
object_type,object_id,field,source_value,locale,value,is_auto,stale
chart,34,slice_name,"Monthly revenue",vi,"Doanh thu theo tháng",false,false
```

**Chống lạm dụng**: `POST /bundle` và `GET /bundle` bật rate-limit theo `Limiter` sẵn có.

---

## 10. Frontend — registry + `translateEntity`

### 10.1. Module mới trong `@superset-ui/core`

`packages/superset-ui-core/src/translation/ContentTranslations.ts`

```ts
export type ContentBundle = Record<string, string>;   // "chart:12:slice_name" -> "…"

export function registerContentTranslations(
  bundle: ContentBundle,
  opts?: { locale?: string; version?: number; replace?: boolean },
): void;

export function clearContentTranslations(): void;

/** Tra cứu theo thực thể; miss → dual-read (nếu bật) → fallback. */
export function translateEntity(
  objectType: string,
  objectId: string | number | null | undefined,
  field: string,
  fallback?: string | null,
): string;

/** Tên chart trong ngữ cảnh dashboard: override → chart → gốc (Mức B). */
export function translateSliceName(
  sliceId: number,
  fallback: string,
  ctx?: { dashboardId?: number; componentId?: string },
): string;

export function getContentTranslationsVersion(): number;
```

- Export thêm từ `TranslatorSingleton.ts` và `translation/index.ts`.
- `translateContent()` **giữ nguyên**, đánh dấu `@deprecated`, và là đường fallback của
  `translateEntity` khi `CONTENT_I18N_DUAL_READ = true`.
- Store là module-level `Map` + `useSyncExternalStore` để component re-render khi bundle nạp xong.

### 10.2. Hook & nạp bundle

`superset-frontend/src/hooks/apiResources/contentTranslations.ts`

```ts
useContentTranslationBundle(scope: string)          // GET  /bundle?scope=
useContentTranslationRefs(refs: ContentRef[])       // POST /bundle
```

Điểm nạp:

| Nơi | Scope | Ghi chú |
|---|---|---|
| `DashboardPage.tsx` | `dashboard:<id>` | fetch **song song** với `useDashboard/Charts/Datasets`; chặn render tới khi xong (tránh nháy chữ) |
| Explore (`ExploreViewContainer`) | `explore:slice:<id>` hoặc `dataset:<id>` | |
| ChartList / DashboardList / DatasetList / Home | `POST /bundle` với id của trang hiện tại | chạy sau khi có kết quả list, cập nhật tại chỗ |
| Embedded (`src/embedded/index.tsx`) | `dashboard:<id>` | đọc `bootstrap_data.content_i18n.locale`, **gắn header `X-Superset-Locale` mặc định cho SupersetClient** → mọi API sau đó (kể cả `/chart/data`) đúng locale |

**Cache FE**: bundle lưu theo `(scope, locale)` trong RTK-Query/`useApiV1Resource` + `ETag` từ server.

### 10.3. Di trú 75 call-site `translateContent` (bảng đầy đủ)

| File | Dòng | Hiện tại | Sau khi đổi |
|---|---|---|---|
| `dashboard/components/SliceHeader/index.tsx` | 223, 267 | `translateContent(sliceName)` | `translateSliceName(sliceId, sliceName, {dashboardId, componentId})` |
| `dashboard/components/Header/index.jsx` | 607 | `translateContent(dashboardTitle)` | `translateEntity('dashboard', id, 'dashboard_title', dashboardTitle)` |
| `dashboard/containers/DashboardPage.tsx` | 244 | `document.title` | như trên |
| `dashboard/components/gridComponents/Tab/Tab.jsx` | 395 | `component.meta.text` | `translateEntity('dashboard_component', dashboardId, \`component.${component.id}.text\`, text)` |
| `dashboard/components/gridComponents/Header/Header.jsx` | 254 | idem | idem |
| `dashboard/components/gridComponents/Markdown/Markdown.jsx` | 320 | idem | idem (dịch **toàn bộ** markdown source) |
| `dashboard/components/AddSliceCard/AddSliceCard.tsx` | 274 | `sliceName` | `translateEntity('chart', sliceId, 'slice_name', …)` |
| `dashboard/.../FilterBar/FilterControls/FilterControl.tsx` | 332 | `filter.name` | `translateEntity('native_filter', dashboardId, \`filter.${filterId}.name\`, name)` |
| `dashboard/.../FilterBar/CrossFilters/CrossFilter.tsx` | 77 | idem | idem |
| `dashboard/.../FilterCard/NameRow.tsx` | 70, 73 | idem | idem |
| `explore/components/ExploreChartHeader/index.jsx` | 251 | `sliceName` | `translateEntity('chart', sliceId, 'slice_name', …)` |
| `explore/components/ExploreViewContainer/index.jsx` | 277 | `document.title` | idem |
| `explore/components/controls/DatasourceControl/index.jsx` | 431 | `getDatasourceTitle(datasource)` | `translateEntity('dataset', datasource.id, 'table_name', …)` |
| `explore/components/DatasourcePanel/DatasourcePanelItem.tsx` | 157, 203 | `folder.name` | `translateEntity('dataset_folder', datasetId, \`folder.${folder.uuid}.name\`, …)` |
| `explore/components/useExploreAdditionalActionsMenu/DashboardsSubMenu.tsx` | 89 | `dashboard_title` | `translateEntity('dashboard', d.id, 'dashboard_title', …)` |
| `features/charts/ChartCard.tsx` | 133, 179, 195 | `slice_name`, `datasource_name_text` | chart + dataset |
| `features/dashboards/DashboardCard.tsx` | 164 | `dashboard_title` | dashboard |
| `features/home/ActivityTable.tsx`, `DashboardTable.tsx` | — | tên chart/dashboard | theo id trong item |
| `pages/ChartList`, `DashboardList`, `DatasetList`, `SavedQueryList`, `AlertReportList`, `AnnotationLayerList` | — | tên các loại | theo id; loại chưa hỗ trợ (saved query, alert, annotation) **giữ `translateContent`** tới P5 |
| `components/ColumnOption.tsx`, `components/MetricOption.tsx` | — | nhãn cột/metric | **XOÁ** `translateContent` — backend đã localize `verbose_name` (B1/B2) |
| `components/ListView/types.ts` | — | flag hỗ trợ | giữ, đổi sang nhận `translateKey` |

> Nguyên tắc di trú: mỗi call-site đều có sẵn id thực thể trong props/redux. Nếu chỗ nào **không có
> id** (hiếm — như `datasource_name_text` trong một số card), tạm giữ `translateContent` và ghi vào
> danh sách nợ kỹ thuật trong PR mô tả.

### 10.4. Chế độ soạn thảo

Khi `editMode = true` (Dashboard/Explore), **luôn hiển thị giá trị gốc**, không dịch — giữ đúng hành
vi hiện tại (`editMode ? dashboardTitle : translateContent(...)` ở Header/index.jsx:607) để người sửa
không vô tình lưu bản dịch đè lên tên gốc. Bổ sung badge nhỏ "🌐 vi" cạnh field có bản dịch, click →
mở modal biên tập (§11).

---

## 11. UI biên tập & trang quản trị

### 11.1. Component dùng chung

`src/features/contentTranslations/`
- `TranslationsModal.tsx` — nhận `{objectType, objectId, fields:[{field,label,sourceValue,multiline}]}`,
  render form theo tab locale, lưu bằng `POST /bulk_upsert`, hiện cảnh báo **stale**.
- `TranslationBadge.tsx` — chip nhỏ "🌐 2/2" hiển thị độ phủ của thực thể, click mở modal.
- `useTranslationsFor(objectType, objectId)` — hook đọc `GET /for/...`.

### 11.2. Điểm cắm UI

| Nơi | Cách vào | Trường dịch |
|---|---|---|
| Dataset editor → tab **Columns** | nút 🌐 mỗi dòng + nút "Dịch hàng loạt" trên header bảng | `verbose_name`, `description` |
| Dataset editor → tab **Metrics** | idem | `verbose_name`, `description` |
| Dataset editor → tab **Settings** | trường tên dataset | `table_name`, `description` |
| Explore → menu "..." của chart | mục **Bản dịch** | `slice_name`, `description` |
| Chart list → dropdown mỗi dòng | mục **Bản dịch** | idem |
| Dashboard (edit mode) → panel phải, tab **Bản dịch** | cây component | `dashboard_title`, `component.*.text`, `filter.*.name`, **`component.*.sliceNameOverride`** |
| Dashboard list → dropdown | **Bản dịch** | `dashboard_title` |

### 11.3. Trang quản trị tập trung

Đổi `/translation-dictionary/` thành trang 2 tab (giữ URL cũ + thêm `/content-translations/`):

- **Tab "Chuỗi giao diện"** = trang `TranslationDictionaryList` hiện tại (không đổi).
- **Tab "Nội dung"** (mới) — `src/pages/ContentTranslationList/`:
  - Bộ lọc: loại thực thể, locale, trạng thái (`đã dịch` / `thiếu` / `stale` / `tự động`), tìm kiếm.
  - Bảng: `Loại | Thực thể (link) | Trường | Gốc | Bản dịch (inline edit) | Trạng thái | Sửa lần cuối`.
  - Thanh trên cùng: **thanh độ phủ** theo locale (`/coverage`).
  - Nút: **Nhập CSV/XLSX** (có xem trước diff khi `dry_run`), **Xuất**, **Seed từ từ điển cũ**,
    **Dọn dẹp**.
  - Hàng đợi dịch: chế độ "Chỉ hiện thiếu" (`/missing`) + phím tắt lưu-và-xuống-dòng.

---

## 12. Per-dashboard-per-chart override (Mức B) — BẬT

Thuật toán resolve tên chart hiển thị:

```
translateSliceName(sliceId, fallback, {dashboardId, componentId}):
  1. bundle["dashboard_component:<dashboardId>:component.<componentId>.sliceNameOverride"]
  2. bundle["chart:<sliceId>:slice_name"]
  3. (dual-read) translateContent(fallback)
  4. fallback  (slice_name gốc, hoặc sliceNameOverride người dùng đã đặt trong dashboard)
```

- Tương tác với `sliceNameOverride` **có sẵn** của Superset (đổi tên chart trong dashboard, không dịch):
  nếu người dùng đã đặt override tiếng gốc, `fallback` truyền vào chính là override đó → bản dịch
  theo componentId vẫn thắng khi có.
- Backend không cần biết gì thêm — override chỉ là một `field` khác trong cùng bảng.
- UI: trong panel Bản dịch của dashboard, mỗi chart có 2 dòng: *"Dùng bản dịch chung của chart"*
  (readonly, hiện giá trị) và *"Ghi đè trong dashboard này"* (input).

---

## 13. Di trú dữ liệu từ từ điển toàn cục

### 13.1. Lệnh

```
superset content-i18n seed \
    --from dictionary \
    --locales vi,en \
    --types chart,dashboard,dashboard_component,native_filter,dataset,dataset_column,dataset_metric \
    [--dry-run] [--report /tmp/seed-report.csv] [--overwrite]
```

### 13.2. Thuật toán

```
for locale in locales:
    dict_map = {msgid: msgstr}  từ translation_dictionary (locale)
    # chart
    for slice in Slice.query:
        if slice.slice_name in dict_map and dict_map[...] != slice.slice_name:
            upsert(chart, slice.id, slice_name, locale, value,
                   source='seed', is_auto=True,
                   source_hash=sha256(slice.slice_name))
    # dashboard_title, dataset table_name, column/metric verbose_name…
    # dashboard_component: duyệt position_json → mọi node có meta.text
    # native_filter: duyệt json_metadata.native_filter_configuration
```

- **Idempotent**: mặc định `INSERT ... ON CONFLICT DO NOTHING` (chỉ `--overwrite` mới ghi đè).
- **Báo cáo mơ hồ**: msgid xuất hiện ở ≥2 thực thể khác nhau → ghi vào report với cột
  `ambiguous=true`, để người duyệt xác nhận. Đây chính là các case mà cơ chế toàn cục đang **sai âm
  thầm** (V1).
- **Báo cáo va chạm UI**: msgid vừa là chuỗi UI vừa là tên thực thể (V2) → cờ `ui_collision=true`.
- Kết quả `--dry-run` in bảng tổng hợp: `loại | tổng | sẽ tạo | bỏ qua | mơ hồ | va chạm UI`.

### 13.3. Sau seed

1. QA đối chiếu bằng trang quản trị (lọc `is_auto=true`) → duyệt/sửa → `is_auto=false`.
2. Tắt dual-read (`CONTENT_I18N_DUAL_READ = False`) ở môi trường staging, chạy hồi quy.
3. Dọn khỏi `translation_dictionary` các msgid **chỉ** phục vụ nội dung:
   `superset content-i18n prune-dictionary --dry-run` → xoá row có `source='db'` và msgid khớp tên
   thực thể đã có bản dịch per-entity. Chuỗi UI **giữ nguyên**.
4. Giữ backup dump bảng `translation_dictionary` trước khi prune.

---

## 14. Bảo mật, RBAC, embed

- **Permission mới**: `can_read`/`can_write on ContentTranslation`.
  - `Admin`: đủ quyền (tự động).
  - Role đề xuất **`Translator`**: `can_read/can_write on ContentTranslation` + `can_read on Chart /
    Dashboard / Dataset` (để nhìn thấy giá trị gốc), **không** có quyền sửa chart/dashboard.
  - Đăng ký role mẫu trong `superset_config.py` hoặc CLI `superset content-i18n init-roles`.
- **Đọc bundle**:
  - User đăng nhập: kiểm tra quyền xem thực thể trong scope (dùng lại `security_manager` cho
    dashboard/chart) — nếu không có quyền, trả `403` (không rò tên đã dịch).
  - Guest token: scope phải khớp `resources` trong token; chỉ cho `scope=dashboard:<id>`.
  - Dashboard public/anonymous: cho phép đọc bundle của dashboard đó.
- **Validate ghi**: `object_type` ∈ enum; `field` khớp regex; `locale` ∈ `supported_locales()`;
  `len(value) ≤ CONTENT_I18N_MAX_VALUE_LEN` (mặc định 8000).
- **XSS**: `value` được render đúng như giá trị gốc — Markdown vẫn đi qua sanitizer hiện có của
  `Markdown.jsx`; tên chart/tab render dạng text. **Không** thêm đường dẫn render mới.
- **Audit**: `created_by_fk/changed_by_fk` + log action qua `event_logger` cho bulk_upsert/import.

---

## 15. Hiệu năng

**Ngân sách mục tiêu**

| Kịch bản | Mục tiêu |
|---|---|
| Dashboard 30 chart, 5 tab, 10 filter | +1 request bundle (~5–15 KB), +≤1 query DB, p95 < 30 ms |
| `verbose_map` cho dataset 200 cột | +0 query khi cache nóng, +1 query khi lạnh |
| Explore mở chart | +1 request bundle nhỏ (< 2 KB) |
| Danh sách 25 dòng | +1 POST bundle |

**Biện pháp**
1. `bulk_resolve` gộp theo `(object_type, object_id)` — **1 query/trang**.
2. Memo request-scope trong `flask.g` (chặn N+1 tại `data_for_slices`).
3. Redis cache bundle theo `(version, locale, scope_hash)`; version bump = invalidate toàn bộ.
4. ETag/304 cho bundle → tải lại dashboard hầu như không tốn băng thông.
5. Bảng nhỏ: ước lượng `(#chart + #dashboard×(1+#component) + #cột + #metric) × #locale`. Với 500
   chart, 50 dashboard, 100 dataset × 30 cột ⇒ ~10–15k dòng/locale — không đáng kể.
6. Tránh nhồi bundle vào `cached_common_bootstrap_data` (memoize toàn cục 60s) — sẽ phình theo
   scope × locale và bẩn cache của mọi trang.

---

## 16. Kiểm thử

### 16.1. Unit (pytest) — `tests/unit_tests/content_i18n/`

| File | Nội dung |
|---|---|
| `test_locale.py` | thứ tự ưu tiên 6 nguồn; `normalize_locale` (`vi_VN`,`vi-VN`,`VI`,`xx`); locale không hỗ trợ → default |
| `test_keys.py` | parse/format khoá phẳng; regex `field`; từ chối `object_type` lạ; ký tự `:` trong id |
| `test_service.py` | `bulk_resolve` 1 query (đếm bằng `sqlalchemy` event); chuỗi fallback; chunk >500 key; dual-read |
| `test_version.py` | bump khi upsert/delete/import; đọc từ Redis/key_value |
| `test_precedence.py` | adhoc label > i18n > verbose_name > raw |
| `test_cache_key.py` | `query_cache_key` đổi khi locale/version đổi, giữ nguyên khi không đổi |

### 16.2. Integration (pytest) — `tests/integration_tests/content_i18n/`

- `verbose_map`/`data` trả nhãn theo locale; đổi bản dịch → lần gọi sau đổi theo.
- `/api/v1/chart/data` `result_format=csv` → header cột đúng ngôn ngữ; `?lang=en` vs `?lang=vi` cho 2
  file khác nhau (chặn bug cache V8).
- `/api/v1/content_translation/bundle` scope dashboard: đúng tập entry, không lộ chart ngoài dashboard.
- Guest token: scope sai → 403; scope đúng → 200.
- Search list API: tìm theo bản dịch chỉ khớp đúng thực thể (không fan-out như V6).
- `bulk_upsert` transaction: 1 dòng lỗi → rollback toàn bộ.
- Seed idempotent: chạy 2 lần → số dòng không đổi.

### 16.3. Frontend (Jest + RTL)

- `ContentTranslations.test.ts`: register/clear, `translateEntity` fallback 4 tầng,
  `translateSliceName` với override.
- `SliceHeader`, `Tab`, `Markdown`, `Header`, `FilterControl`: render đúng bản dịch; `editMode` hiện
  giá trị gốc.
- `TranslationsModal`: lưu gọi `bulk_upsert` đúng payload; hiển thị cảnh báo stale.
- Đổi locale → bundle mới → component re-render (qua `useSyncExternalStore`).

### 16.4. E2E tối thiểu (Cypress — chỉ 2 case)

- Embed `?lang=vi` và `?lang=en`: tiêu đề dashboard, tên chart, nhãn cột **và** file CSV tải về khác
  nhau.
- Sửa bản dịch trong trang quản trị → reload dashboard thấy đổi (kiểm tra invalidation thật).

---

## 17. Lộ trình

Mỗi phase **ship được độc lập**, sau mỗi phase hệ thống vẫn chạy đúng nếu dừng lại.

### P0 — Chuẩn bị (0.5 ngày)
- Chốt §22 (quyết định mặc định), tạo branch `content-i18n`, bật `CONTENT_I18N_ENABLED=False` ở prod.

### P1 — Nền tảng + nhãn cột/metric (3–4 ngày)
| Task | Đầu ra |
|---|---|
| P1.1 | Migration `object_translations` + 3 index |
| P1.2 | `content_i18n/{models,keys,locale,version,service}.py` |
| P1.3 | Cắm B1/B2/B3 (`verbose_map`, `data`, `data_for_slices`) + memo `g` |
| P1.4 | Cắm B4 (`query_cache_key` + locale/version) |
| P1.5 | CRUD API + `bulk_upsert` + RBAC |
| P1.6 | CLI `content-i18n coverage` |
| P1.7 | Test §16.1 + phần dataset của §16.2 |

**Acceptance**: đặt bản dịch cột `revenue`→`Doanh thu` cho dataset A; Explore/dashboard/embed/CSV đều
hiển thị đúng theo locale; dataset B có cột `revenue` **không** bị ảnh hưởng; bật/tắt
`CONTENT_I18N_ENABLED` không đổi hành vi cũ.

### P2 — Nội dung theo thực thể (4–5 ngày)
| Task | Đầu ra |
|---|---|
| P2.1 | Endpoint `bundle` (GET scope + POST refs) + ETag + guest scoping |
| P2.2 | `scopes.py`: dashboard/explore/list scope builder |
| P2.3 | FE: `ContentTranslations.ts` + hook + nạp bundle ở Dashboard/Explore/list/embedded |
| P2.4 | Di trú 75 call-site theo bảng §10.3 (giữ dual-read) |
| P2.5 | Mức B — `translateSliceName` + field `sliceNameOverride` |
| P2.6 | B9/B10: `X-Superset-Locale` cho embedded SDK + claim `locale` trong guest token |
| P2.7 | B11: viết lại 3 filter search theo thực thể |
| P2.8 | Test §16.3 + phần bundle/embed của §16.2 |

**Acceptance**: 2 chart trùng tên ở 2 dashboard có bản dịch khác nhau; iframe `?lang=en` đúng ngôn
ngữ ở **cả** tên chart lẫn nhãn cột; tìm kiếm theo tên đã dịch trả đúng thực thể.

### P3 — UI biên tập & quản trị (4–5 ngày)
- `TranslationsModal` + badge; cắm vào Dataset editor (Columns/Metrics/Settings), Explore menu, Chart
  list, Dashboard edit panel, Dashboard list.
- Trang `ContentTranslationList` 2 tab + coverage + hàng đợi `missing` + inline edit.
- Import/Export CSV/XLSX/PO + `dry_run` diff.

**Acceptance**: đội dịch phi kỹ thuật dịch trọn 1 dashboard mà không cần vào DB/CLI.

### P4 — Di trú & dọn dẹp (2–3 ngày)
- `seed --from dictionary` + report mơ hồ/va chạm; QA duyệt `is_auto`.
- Tắt dual-read ở staging → hồi quy → tắt ở prod.
- `prune-dictionary` cho phần nội dung; job `cleanup` định kỳ (Celery beat).
- B13: report/screenshot dùng locale của owner.

**Acceptance**: `CONTENT_I18N_DUAL_READ=False` mà không mất bản dịch nào đang hiển thị.

### P5 — Nâng cao (tuỳ chọn, 3–5 ngày)
- Bảng `translation_locales` + UI quản ngôn ngữ.
- Dịch `form_data` (nhãn trục, tiêu đề tuỳ chỉnh), saved query/annotation/tag.
- Export/import dashboard kèm `translations.yaml`.
- Gợi ý dịch tự động (điền `is_auto=true`, bắt buộc duyệt).
- Sắp xếp danh sách theo tên đã dịch (cần join khi order_by).

**Tổng ước lượng P1–P4: ~14–17 ngày công** (1 người full-stack).

---

## 18. Runbook triển khai & rollback

**Triển khai**
1. Deploy code với `CONTENT_I18N_ENABLED=False` → chạy `superset db upgrade` (chỉ tạo bảng rỗng, zero
   downtime, không khoá bảng nghiệp vụ).
2. Bật `CONTENT_I18N_ENABLED=True` + `CONTENT_I18N_DUAL_READ=True` trên 1 worker (canary) → theo dõi
   p95 latency dashboard, số query/req.
3. Chạy `content-i18n seed --dry-run` → review report → chạy thật.
4. Mở trang quản trị cho đội dịch; QA theo dashboard trọng điểm.
5. Sau ≥2 tuần ổn định: `CONTENT_I18N_DUAL_READ=False`, rồi `prune-dictionary`.

**Rollback**
- Mức 1: `CONTENT_I18N_ENABLED=False` → hệ thống quay về hành vi hiện tại 100% (bảng vẫn còn dữ liệu).
- Mức 2: revert deploy; bảng `object_translations` để lại vô hại.
- Mức 3 (chỉ khi bỏ hẳn): `superset db downgrade` 1 revision.
- **Điều kiện an toàn**: không xoá `translation_dictionary` trước bước 5; luôn có dump trước prune.

**Giám sát**
- Statsd/log: số query của resolver mỗi request, tỉ lệ hit Redis bundle, tỉ lệ `304`, số key miss
  (→ danh sách cần dịch), p95 endpoint `/bundle`.

---

## 19. Rủi ro & giảm thiểu

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | Cache phục vụ nhầm ngôn ngữ (CSV/chart data) | **Cao** | locale + version trong `query_cache_key` (P1.4) + test §16.2 |
| R2 | N+1 query ở `data_for_slices` | **Cao** | memo `flask.g` + test đếm query |
| R3 | Seed fan-out sai (V1/V2) | Trung bình | dry-run + cột `ambiguous`/`ui_collision` + `is_auto` chờ duyệt |
| R4 | Vỡ 75 call-site khi di trú | Trung bình | dual-read + đổi từng nhóm file + snapshot test |
| R5 | Embed vẫn sai locale ở API | Trung bình | header `X-Superset-Locale` + claim guest token + E2E |
| R6 | `componentId` đổi khi sửa layout → mất bản dịch | Trung bình | job cleanup + cảnh báo orphan trong panel + export trước khi sửa lớn |
| R7 | Bản dịch cũ hiển thị khi tên gốc đã đổi | Trung bình | `source_hash` → cờ **stale** + bộ lọc trong trang quản trị |
| R8 | Bundle lớn với dashboard khổng lồ | Thấp | chỉ trả entry có bản dịch + gzip + ETag |
| R9 | Xung đột với `sliceNameOverride` sẵn có | Thấp | thứ tự resolve §12 + test |
| R10 | Quyền: người dịch sửa được nội dung gốc | Thấp | role `Translator` tách bạch, không có `can_write on Chart/Dashboard` |

---

## 20. Bản đồ thay đổi theo file

**Backend — mới**
```
superset/content_i18n/{__init__,models,keys,locale,service,version,scopes,api,schemas,cli}.py
superset/content_i18n/commands/{seed,import_export,cleanup}.py
superset/migrations/versions/<ts>_add_object_translations.py
tests/unit_tests/content_i18n/*  ·  tests/integration_tests/content_i18n/*
```

**Backend — sửa**
```
superset/connectors/sqla/models.py            # L352 verbose_map, L366 data, L402 data_for_slices
superset/common/query_context_processor.py    # L248 query_cache_key (+ test cho L996 get_data)
superset/charts/filters.py                    # bỏ translated_name_matches → EXISTS theo id
superset/dashboards/filters.py                # idem
superset/datasets/filters.py                  # idem
superset/dashboards/api.py                    # (tuỳ chọn) inline bundle
superset/explore/api.py                       # đính bundle scope explore
superset/embedded/view.py                     # L90+ thêm bootstrap content_i18n
superset/security/guest_token.py              # claim locale (optional)
superset/security/manager.py                  # L2673 create_guest_access_token
superset/initialization/__init__.py           # đăng ký ContentTranslationRestApi (hoặc qua config)
docker/pythonpath_dev/superset_config.py      # hằng CONTENT_I18N_*, đăng ký API/role
```

**Frontend — mới**
```
packages/superset-ui-core/src/translation/ContentTranslations.ts (+ test)
src/hooks/apiResources/contentTranslations.ts
src/features/contentTranslations/{TranslationsModal,TranslationBadge,useTranslationsFor}.tsx
src/pages/ContentTranslationList/index.tsx
```

**Frontend — sửa** (15 file `translateContent` ở §10.3, cộng)
```
packages/superset-ui-core/src/translation/{TranslatorSingleton.ts,index.ts}
src/views/routes.tsx                          # route /content-translations/
src/embedded/index.tsx                        # header X-Superset-Locale + nạp bundle
src/dashboard/containers/DashboardPage.tsx    # prefetch bundle
src/explore/components/ExploreViewContainer/index.jsx
src/features/datasets/...                     # nút 🌐 ở Columns/Metrics
```

---

## 21. Cấu hình

```python
# superset_config.py
CONTENT_I18N_ENABLED = True             # cờ tổng, tắt = hành vi cũ 100%
CONTENT_I18N_LOCALES = ["vi", "en"]     # locale hỗ trợ dịch nội dung
CONTENT_I18N_DEFAULT_LOCALE = "vi"
CONTENT_I18N_FALLBACK_CHAIN = True      # thiếu vi → thử en trước khi về gốc
CONTENT_I18N_DUAL_READ = True           # miss per-entity → tra translation_dictionary (giai đoạn di trú)
CONTENT_I18N_LANG_QUERY_PARAM = "lang"
CONTENT_I18N_LOCALE_HEADER = "X-Superset-Locale"
CONTENT_I18N_CACHE_TTL = 300            # giây, cache Redis cho bundle/bulk_resolve
CONTENT_I18N_MAX_REFS_PER_REQUEST = 500
CONTENT_I18N_MAX_VALUE_LEN = 8000
CONTENT_I18N_INLINE_BUNDLE = False      # True = nhét bundle vào /api/v1/dashboard/<id> (giảm 1 RTT)
CONTENT_I18N_OVERRIDE_PER_DASHBOARD = True   # Mức B
```

---

## 22. Phụ lục

### 22.1. Các quyết định mặc định (đã chốt, có thể đảo)

| # | Câu hỏi mở trong plan v1 | Quyết định | Lý do | Đảo được? |
|---|---|---|---|---|
| 1 | Mức B (override theo dashboard) | **Bật ngay ở P2** | yêu cầu nêu rõ "từng chart, từng dashboard riêng biệt" | Có — tắt bằng `CONTENT_I18N_OVERRIDE_PER_DASHBOARD` |
| 2 | Danh sách ngôn ngữ | **`["vi","en"]` bằng config ở P1–P2**, bảng `translation_locales` ở P3 | tránh over-engineering sớm; API không đổi | Có |
| 3 | Trường được dịch | theo bảng §6.1 (bao trọn 75 call-site hiện có + cột/metric) | để **retire được** dịch nội dung toàn cục, phải phủ hết chỗ đang dùng | Có — thêm loại không cần migration |
| 4 | Nguồn locale embed | `?lang=` + header `X-Superset-Locale` + claim guest token | `?lang=` một mình không tới được các API sau bootstrap | Có |
| 5 | Di trú | **Có seed** từ `translation_dictionary`, dry-run + duyệt `is_auto` | tránh mất công dịch đã bỏ ra | Có — bỏ qua seed thì bắt đầu sạch |

### 22.2. Schema JSON của `bulk_upsert`

```json
{
  "rows": [
    {
      "object_type": "chart",
      "object_id": "34",
      "field": "slice_name",
      "locale": "vi",
      "value": "Doanh thu theo tháng",
      "source_value": "Monthly revenue"
    }
  ],
  "delete_empty": true
}
```
`source_value` (tuỳ chọn) → server tính `source_hash`. `delete_empty=true`: value rỗng ⇒ xoá row
(để UI "xoá bản dịch" không cần API riêng).

### 22.3. Ví dụ luồng dashboard nhúng, `?lang=en`

```
1. GET /embedded/<uuid>?lang=en
   → bootstrap: common.locale='en', content_i18n={locale:'en', version:271}
2. FE gắn SupersetClient header X-Superset-Locale: en
3. GET /api/v1/content_translation/bundle?scope=dashboard:12   (guest token, scope hợp lệ)
   → entries (en)
4. GET /api/v1/dashboard/12/datasets
   → verbose_map đã resolve theo 'en'  (backend, B1/B2)
5. POST /api/v1/chart/data
   → cache key kèm ('en', 271); CSV export cột tiếng Anh
6. Render: translateEntity/translateSliceName đọc bundle bước 3
```

### 22.4. Bảng đối chiếu "vấn đề → nơi được giải quyết"

| Vấn đề (§2) | Giải quyết ở |
|---|---|
| V1 khoá theo chuỗi | §5.1 + §6 + §10 |
| V2 trùng UI ↔ nội dung | tách store (§5) + prune (§13.3) |
| V3 cột/metric theo dataset | §8 B1/B2 |
| V4 export/report không dịch | §8 B4/B5/B13 |
| V5 bảng phình, trộn mục đích | 2 bảng, 2 tab quản trị (§11.3) |
| V6 search fan-out | §8 B11 |
| V7 embed sai locale | §7.2 + §8 B9/B10 |
| V8 cache lệch | §5.3 version + §7.6 |
