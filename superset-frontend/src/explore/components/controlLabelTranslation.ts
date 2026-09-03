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

/**
 * Re-translating control choice labels at render time.
 *
 * Shared control configs call `t()` when the module loads, which is before the
 * language pack has arrived, so the labels come through in English and have to
 * be translated again here.
 *
 * That sweep must not touch names the dataset defines. A column called `year`
 * or `status` would otherwise pick up the translation of that word and stop
 * matching what the user sees everywhere else, so those are passed through as
 * the dataset spells them.
 */
import { t } from '@superset-ui/core';

/**
 * Datasource sort choices use labels like `year [asc]` from the API. Jed only has msgids
 * `[asc]` / `[desc]` (see Python __("[asc]")), so translate the suffix here.
 */
export function translateChoiceDisplayLabel(
  lbl: string,
  /**
   * Names that belong to the dataset. Left exactly as the dataset spells them:
   * a column called `year` or `status` must not turn into its Vietnamese word
   * just because the translation pack happens to carry that msgid.
   */
  datasetNames?: Set<string>,
): string {
  if (lbl.endsWith(' [asc]')) {
    const stem = lbl.slice(0, -' [asc]'.length);
    return `${stem} ${t('[asc]')}`;
  }
  if (lbl.endsWith(' [desc]')) {
    const stem = lbl.slice(0, -' [desc]'.length);
    return `${stem} ${t('[desc]')}`;
  }
  return datasetNames?.has(lbl) ? lbl : t(lbl);
}

/** Re-apply gettext: shared control configs often call t() at module load (before language pack). */
export function translateControlTupleLabels(
  rows: unknown,
  datasetNames?: Set<string>,
): unknown {
  if (!Array.isArray(rows)) return rows;
  return rows.map(row => {
    if (Array.isArray(row) && row.length >= 2) {
      const [value, lbl] = row;
      if (typeof lbl === 'string') {
        return [value, translateChoiceDisplayLabel(lbl, datasetNames)];
      }
    }
    return row;
  });
}

/** SelectControl `options` as { label, value, description }[] (e.g. partition time_series_option). */
function translateControlObjectOptions(
  options: Record<string, unknown>[],
  datasetNames?: Set<string>,
): Record<string, unknown>[] {
  return options.map(item => ({
    ...item,
    ...(typeof item.label === 'string' && {
      label: translateChoiceDisplayLabel(item.label, datasetNames),
    }),
    ...(typeof item.description === 'string' && {
      description: t(item.description),
    }),
  }));
}

export function translateControlOptions(
  options: unknown,
  datasetNames?: Set<string>,
): unknown {
  if (!Array.isArray(options) || options.length === 0) {
    return options;
  }
  const head = options[0];
  const isObjectStyle =
    head !== null &&
    typeof head === 'object' &&
    !Array.isArray(head) &&
    'label' in (head as object);
  if (isObjectStyle) {
    return translateControlObjectOptions(
      options as Record<string, unknown>[],
      datasetNames,
    );
  }
  return translateControlTupleLabels(options, datasetNames);
}
