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
 * Reading and writing the custom tooltip config the form edits.
 *
 * The control stores the same JSON string the chart already understands, so the
 * form and the raw editor are two views of one value and switching between them
 * loses nothing. See `plugin-chart-echarts/src/utils/customTooltip.ts` for how
 * the chart consumes it.
 */

export type TooltipSeriesOverride = {
  label?: string;
  prefix?: string;
  suffix?: string;
  format?: string;
  hidden?: boolean;
  order?: number;
};

export type TooltipGroupSettings = {
  by?: string;
  label?: string;
  order?: string[];
  stripFromLabel?: boolean;
  total?: boolean;
};

export type CustomTooltipSettings = {
  title?: string;
  maxRows?: number;
  group?: TooltipGroupSettings;
  series?: Record<string, TooltipSeriesOverride>;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const str = (value: unknown): string | undefined =>
  typeof value === 'string' && value !== '' ? value : undefined;

const bool = (value: unknown): boolean | undefined =>
  typeof value === 'boolean' ? value : undefined;

const num = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined;

/**
 * Read the stored value into settings the form can bind to.
 *
 * Never throws: a value hand-edited into something unparseable comes back as
 * empty settings, so the form still opens instead of breaking the panel.
 */
export function parseSettings(raw?: string | null): CustomTooltipSettings {
  if (typeof raw !== 'string' || !raw.trim()) {
    return {};
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return {};
  }
  if (!isRecord(parsed)) {
    return {};
  }

  const series: Record<string, TooltipSeriesOverride> = {};
  if (isRecord(parsed.series)) {
    Object.entries(parsed.series).forEach(([name, value]) => {
      if (isRecord(value)) {
        series[name] = {
          label: str(value.label),
          prefix: str(value.prefix),
          suffix: str(value.suffix),
          format: str(value.format),
          hidden: bool(value.hidden),
          order: num(value.order),
        };
      }
    });
  }

  const rawGroup = isRecord(parsed.group) ? parsed.group : undefined;
  const group: TooltipGroupSettings | undefined = rawGroup
    ? {
        by: str(rawGroup.by) ?? (num(rawGroup.by)?.toString() || undefined),
        label: str(rawGroup.label),
        order: Array.isArray(rawGroup.order)
          ? rawGroup.order.filter((e): e is string => typeof e === 'string')
          : undefined,
        stripFromLabel: bool(rawGroup.stripFromLabel),
        total: bool(rawGroup.total),
      }
    : undefined;

  return {
    title: str(parsed.title),
    maxRows: num(parsed.maxRows),
    group,
    series: Object.keys(series).length ? series : undefined,
  };
}

/** Drop keys the chart would ignore, so the JSON stays readable. */
function pruned<T extends Record<string, unknown>>(
  value: T,
): Partial<T> | undefined {
  const entries = Object.entries(value).filter(
    ([, entry]) =>
      entry !== undefined &&
      entry !== '' &&
      !(Array.isArray(entry) && entry.length === 0),
  );
  return entries.length
    ? (Object.fromEntries(entries) as Partial<T>)
    : undefined;
}

/**
 * Write the settings back out.
 *
 * Returns an empty string when nothing is configured, which is what the chart
 * reads as "use the default tooltip".
 */
export function serializeSettings(settings: CustomTooltipSettings): string {
  const series: Record<string, Partial<TooltipSeriesOverride>> = {};
  Object.entries(settings.series ?? {}).forEach(([name, override]) => {
    const kept = pruned({ ...override });
    if (kept) {
      series[name] = kept;
    }
  });

  const group = settings.group?.by
    ? pruned({
        by: settings.group.by,
        label: settings.group.label,
        order: settings.group.order,
        // only worth writing when it differs from the chart's default
        stripFromLabel:
          settings.group.stripFromLabel === false ? false : undefined,
        total: settings.group.total ? true : undefined,
      })
    : undefined;

  const config = pruned({
    title: settings.title,
    // the chart ignores maxRows while grouping, so do not write a dead key
    maxRows: group ? undefined : settings.maxRows,
    group,
    series: Object.keys(series).length ? series : undefined,
  });

  return config ? JSON.stringify(config, null, 2) : '';
}

/** Series with several dimensions are named by joining the values with this. */
const SERIES_NAME_SEPARATOR = ', ';

/**
 * The distinct values of one dimension, read off the series names.
 *
 * A time-series query comes back pivoted: each row is an x-axis value and the
 * breakdown lives in the column names, so the dimension is not a column of its
 * own to read. The names join the dimension values in dimension order, which is
 * how the chart itself locates the group.
 */
export function deriveGroupValues(
  seriesNames: string[],
  dimensions: string[],
  by?: string,
): string[] {
  if (!by) {
    return [];
  }
  const index = dimensions.indexOf(by);
  if (index === -1) {
    return [];
  }
  const values = new Set<string>();
  seriesNames.forEach(name => {
    const parts = name.split(SERIES_NAME_SEPARATOR);
    if (index < parts.length) {
      values.add(parts[index]);
    }
  });
  return Array.from(values);
}

/** Whether a hand-edited value is valid JSON the form can take over again. */
export function isParseableJson(raw: string): boolean {
  if (!raw.trim()) {
    return true;
  }
  try {
    const parsed = JSON.parse(raw);
    return isRecord(parsed);
  } catch {
    return false;
  }
}
