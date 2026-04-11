/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import { t } from '@superset-ui/core';
import { QueryEditor } from '../types';

/** Canonical English prefix (persisted tabs / tests / legacy state). */
const UNTITLED_QUERY_ENGLISH = 'Untitled Query';

function escapeRegExp(text: string) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Localized default SQL Lab tab title, e.g. "Untitled Query 3". */
export function formatUntitledQueryTabName(n: number): string {
  return t('Untitled Query %s', String(n));
}

function parseUntitledTabNumber(
  name: string | undefined,
  localizedBase: string,
): number | null {
  if (!name) return null;
  const englishMatch = name.match(
    new RegExp(`^${escapeRegExp(UNTITLED_QUERY_ENGLISH)} (\\d+)$`),
  );
  if (englishMatch) {
    return parseInt(englishMatch[1], 10);
  }
  if (localizedBase !== UNTITLED_QUERY_ENGLISH) {
    const localizedMatch = name.match(
      new RegExp(`^${escapeRegExp(localizedBase)} (\\d+)$`),
    );
    if (localizedMatch) {
      return parseInt(localizedMatch[1], 10);
    }
  }
  return null;
}

export const newQueryTabName = (
  queryEditors: QueryEditor[],
  initialTitle?: string,
): string => {
  const localizedBase = t('Untitled Query');
  const defaultTitle = formatUntitledQueryTabName(1);

  if (queryEditors.length > 0) {
    const numbers = queryEditors
      .map(qe => parseUntitledTabNumber(qe.name, localizedBase))
      .filter((n): n is number => n !== null);
    if (numbers.length > 0) {
      return formatUntitledQueryTabName(Math.max(...numbers) + 1);
    }
  }

  if (initialTitle !== undefined) {
    return t(initialTitle);
  }
  return defaultTitle;
};
