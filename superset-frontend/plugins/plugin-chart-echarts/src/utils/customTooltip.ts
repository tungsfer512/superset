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
 * Declarative tooltip customization.
 *
 * The chart's `tooltip.formatter` is a function, so it cannot travel through
 * `form_data`, which is JSON. Rather than accept code from the control panel --
 * which would run in every viewer's browser, embedded guests included -- this
 * accepts a validated description of the wanted tooltip and the plugins build
 * the formatter from it.
 *
 * Anything invalid is dropped rather than thrown: a typo in the config must
 * degrade to the default tooltip, never break the chart.
 */
import {
  getNumberFormatter,
  logging,
  t,
  ValueFormatter,
} from '@superset-ui/core';

/** Placeholders in `title` that stand for the tooltip's default heading. */
const TITLE_PLACEHOLDER = /\{(?:time|x)\}/g;

export type TooltipSeriesConfig = {
  /** Replaces the series name shown in the row. */
  label?: string;
  /** Prepended to the formatted value. */
  prefix?: string;
  /** Appended to the formatted value. */
  suffix?: string;
  /** d3 format string, overriding the chart's number format for this row. */
  format?: string;
  /** Drops the row entirely. */
  hidden?: boolean;
  /** Rows with a lower number come first; unordered rows keep their position. */
  order?: number;
};

export type TooltipGroupConfig = {
  /**
   * Which part of the series name to group on: a dimension name, or its
   * position among the chart's dimensions. A series with several dimensions is
   * named by joining their values with `", "`, in dimension order, so
   * `status` + `year` yields `"Shipped, 2003"`.
   */
  by: string | number;
  /** Header template; `{value}` stands for the group's value. */
  label?: string;
  /** Groups listed here come first, in this order; the rest follow as found. */
  order?: string[];
  /** Drop the group's own value from each row's label. Defaults to true. */
  stripFromLabel?: boolean;
  /** Add a subtotal to each group header. Defaults to false. */
  total?: boolean;
};

export type CustomTooltipConfig = {
  /** Heading template; `{time}` or `{x}` stands for the default heading. */
  title?: string;
  /** Keeps at most this many series rows, summarizing the rest as a count. */
  maxRows?: number;
  /** Splits the rows into sections, each under its own header. */
  group?: TooltipGroupConfig;
  series: Record<string, TooltipSeriesConfig>;
};

/** Series with several dimensions are named by joining the values with this. */
const SERIES_NAME_SEPARATOR = ', ';

/** Indents a row under its group header. Plain spaces would collapse in HTML. */
const INDENT = '\u00a0\u00a0';

const asString = (value: unknown): string | undefined =>
  typeof value === 'string' ? value : undefined;

const asBoolean = (value: unknown): boolean | undefined =>
  typeof value === 'boolean' ? value : undefined;

const asFiniteNumber = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

function parseSeriesConfig(value: unknown): TooltipSeriesConfig | undefined {
  if (!isRecord(value)) {
    return undefined;
  }
  const config: TooltipSeriesConfig = {
    label: asString(value.label),
    prefix: asString(value.prefix),
    suffix: asString(value.suffix),
    format: asString(value.format),
    hidden: asBoolean(value.hidden),
    order: asFiniteNumber(value.order),
  };
  return Object.values(config).some(entry => entry !== undefined)
    ? config
    : undefined;
}

function parseGroupConfig(value: unknown): TooltipGroupConfig | undefined {
  if (!isRecord(value)) {
    return undefined;
  }
  const by = asString(value.by) ?? asFiniteNumber(value.by);
  if (by === undefined || by === '') {
    logging.warn(
      'Ignoring tooltip group: `by` must be a dimension or an index',
    );
    return undefined;
  }
  const order = Array.isArray(value.order)
    ? value.order.filter((entry): entry is string => typeof entry === 'string')
    : undefined;
  return {
    by,
    label: asString(value.label),
    order: order?.length ? order : undefined,
    stripFromLabel: asBoolean(value.stripFromLabel),
    total: asBoolean(value.total),
  };
}

/**
 * Turn the raw control value into a config, or `undefined` if there is nothing
 * usable in it.
 */
export function parseCustomTooltipConfig(
  raw?: string | null,
): CustomTooltipConfig | undefined {
  if (typeof raw !== 'string' || !raw.trim()) {
    return undefined;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    logging.warn('Ignoring unparseable custom tooltip config', error);
    return undefined;
  }

  if (!isRecord(parsed)) {
    logging.warn('Ignoring custom tooltip config: expected an object');
    return undefined;
  }

  const series: Record<string, TooltipSeriesConfig> = {};
  if (isRecord(parsed.series)) {
    Object.entries(parsed.series).forEach(([name, value]) => {
      const seriesConfig = parseSeriesConfig(value);
      if (seriesConfig) {
        series[name] = seriesConfig;
      }
    });
  }

  const maxRows = asFiniteNumber(parsed.maxRows);
  const config: CustomTooltipConfig = {
    title: asString(parsed.title),
    maxRows:
      maxRows !== undefined && maxRows > 0 ? Math.floor(maxRows) : undefined,
    group: parseGroupConfig(parsed.group),
    series,
  };

  return config.title === undefined &&
    config.maxRows === undefined &&
    config.group === undefined &&
    Object.keys(series).length === 0
    ? undefined
    : config;
}

/**
 * Drop hidden series and apply the configured order.
 *
 * Rows carrying an `order` come first, ascending; everything else keeps the
 * order the chart already chose.
 */
export function orderTooltipKeys(
  keys: string[],
  config?: CustomTooltipConfig,
): string[] {
  if (!config) {
    return keys;
  }
  return keys
    .filter(key => !config.series[key]?.hidden)
    .map((key, index) => ({ key, index }))
    .sort((a, b) => {
      const orderA = config.series[a.key]?.order ?? Infinity;
      const orderB = config.series[b.key]?.order ?? Infinity;
      return orderA === orderB ? a.index - b.index : orderA - orderB;
    })
    .map(({ key }) => key);
}

/**
 * Resolve `group.by` to a position in the series name.
 *
 * A name is the dimension values joined in dimension order, so a dimension's
 * name maps to its index in `dimensions`. Returns undefined when it cannot be
 * resolved, which turns grouping off rather than grouping on the wrong part.
 */
export function resolveGroupIndex(
  config?: CustomTooltipConfig,
  /**
   * The chart's dimensions, in order. A dimension is either a column name or an
   * ad-hoc column, which contributes its label to the series name; both are
   * accepted so a `by` naming either one resolves.
   */
  dimensions: readonly (string | { label?: string })[] = [],
  /**
   * How many parts precede the dimensions in the series name. Mixed Chart puts
   * the metric first ("SUM(sales), Shipped, 2003"), so its dimensions start one
   * place further along than on a plain time-series chart.
   */
  offset = 0,
): number | undefined {
  const by = config?.group?.by;
  if (by === undefined) {
    return undefined;
  }
  if (typeof by === 'number') {
    return by >= 0 ? by + offset : undefined;
  }
  const names = dimensions.map(dimension =>
    typeof dimension === 'string' ? dimension : (dimension?.label ?? ''),
  );
  const index = names.indexOf(by);
  if (index === -1) {
    logging.warn(
      `Ignoring tooltip group: no dimension named "${by}" on this chart`,
    );
    return undefined;
  }
  return index + offset;
}

/** The group a series belongs to, or undefined when it has no such part. */
export function getTooltipGroupValue(
  key: string,
  groupIndex?: number,
): string | undefined {
  if (groupIndex === undefined) {
    return undefined;
  }
  const parts = key.split(SERIES_NAME_SEPARATOR);
  return groupIndex < parts.length ? parts[groupIndex] : undefined;
}

export function getTooltipSeriesLabel(
  key: string,
  config?: CustomTooltipConfig,
  groupIndex?: number,
): string {
  const explicit = config?.series[key]?.label;
  if (explicit !== undefined) {
    return explicit;
  }
  const groupValue = getTooltipGroupValue(key, groupIndex);
  if (groupValue === undefined) {
    return key;
  }
  // the header already states the group, so drop it from the row
  const label =
    config?.group?.stripFromLabel === false
      ? key
      : key
          .split(SERIES_NAME_SEPARATOR)
          .filter((_, index) => index !== groupIndex)
          .join(SERIES_NAME_SEPARATOR) || key;
  return `${INDENT}${label}`;
}

/**
 * The number formatter for one row: the series' own format if it declared one,
 * otherwise whatever the chart already resolved.
 */
export function getTooltipValueFormatter(
  fallback: ValueFormatter,
  key: string,
  config?: CustomTooltipConfig,
): ValueFormatter {
  const format = config?.series[key]?.format;
  return format ? getNumberFormatter(format) : fallback;
}

/**
 * Wrap an already formatted value in the series' prefix and suffix.
 *
 * Applied to the rendered string rather than the number so that composite
 * forecast values ("20, y = 30 (10, 40)") keep their shape.
 */
export function decorateTooltipValue(
  value: string,
  key: string,
  config?: CustomTooltipConfig,
): string {
  const seriesConfig = config?.series[key];
  if (!seriesConfig || !value) {
    return value;
  }
  return `${seriesConfig.prefix ?? ''}${value}${seriesConfig.suffix ?? ''}`;
}

export function formatCustomTooltipTitle(
  defaultTitle: string,
  config?: CustomTooltipConfig,
  /**
   * The x-axis column. Accepted as a placeholder as well, because writing
   * `{city}` for an axis named `city` is the natural guess and silently
   * printing it verbatim is no help.
   */
  xAxisName?: string,
): string {
  const template = config?.title;
  if (!template) {
    return defaultTitle;
  }
  const substituted = template.replace(TITLE_PLACEHOLDER, defaultTitle);
  return xAxisName
    ? substituted.split(`{${xAxisName}}`).join(defaultTitle)
    : substituted;
}

/**
 * Fill in a section header template.
 *
 * `{value}` is the group's value. The grouping dimension's own name works too
 * -- `{year}` when grouping by `year` -- because that is the natural guess, and
 * silently printing it verbatim helps nobody. Substituted by splitting rather
 * than with a regular expression, so a column named `a.b(c)` is not read as a
 * pattern.
 */
export function formatGroupHeader(
  template: string,
  value: string,
  byName?: string,
): string {
  const filled = template.split('{value}').join(value);
  return typeof byName === 'string' && byName
    ? filled.split(`{${byName}}`).join(value)
    : filled;
}

export type TooltipEntry = {
  /** The original series name, before any relabelling. */
  key: string;
  /** The rendered row: label, value, and optionally a percentage. */
  row: string[];
  /** The numeric observation, for group subtotals. */
  value?: number;
};

/**
 * Lay the rows out in sections, one per group, each under its own header.
 *
 * Groups appear in `group.order` first and then in the order the chart already
 * chose. A series with no such part in its name is left ungrouped, above the
 * sections, rather than forced under a header that would misdescribe it.
 */
export function groupTooltipRows(
  entries: TooltipEntry[],
  config: CustomTooltipConfig,
  groupIndex: number,
  formatter?: ValueFormatter,
): { rows: string[][]; headerRows: number[]; keyRows: Map<string, number> } {
  const groups = new Map<string, TooltipEntry[]>();
  const ungrouped: TooltipEntry[] = [];
  entries.forEach(entry => {
    const value = getTooltipGroupValue(entry.key, groupIndex);
    if (value === undefined) {
      ungrouped.push(entry);
      return;
    }
    const bucket = groups.get(value);
    if (bucket) {
      bucket.push(entry);
    } else {
      groups.set(value, [entry]);
    }
  });

  const wanted = config.group?.order ?? [];
  const names = [
    ...wanted.filter(name => groups.has(name)),
    ...[...groups.keys()].filter(name => !wanted.includes(name)),
  ];

  const rows: string[][] = [];
  const headerRows: number[] = [];
  const keyRows = new Map<string, number>();
  const push = (entry: TooltipEntry) => {
    keyRows.set(entry.key, rows.length);
    rows.push(entry.row);
  };

  ungrouped.forEach(push);
  names.forEach(name => {
    const bucket = groups.get(name) ?? [];
    const label = formatGroupHeader(
      config.group?.label ?? '{value}',
      name,
      typeof config.group?.by === 'string' ? config.group.by : undefined,
    );
    const header = [label];
    if (config.group?.total && formatter) {
      const total = bucket.reduce((sum, entry) => sum + (entry.value ?? 0), 0);
      header.push(formatter.format(total));
    }
    headerRows.push(rows.length);
    rows.push(header);
    bucket.forEach(push);
  });

  return { rows, headerRows, keyRows };
}

/**
 * Keep at most `maxRows` rows, replacing the remainder with a count.
 *
 * `focusedRow` is re-pointed, or dropped when the focused row got trimmed away,
 * so the bolded row never lands on the wrong series.
 */
export function limitTooltipRows(
  rows: string[][],
  focusedRow: number | undefined,
  config?: CustomTooltipConfig,
): { rows: string[][]; focusedRow: number | undefined } {
  const maxRows = config?.maxRows;
  // `group` wins: trimming a grouped list would strand headers over nothing,
  // and the count row could not say which section it summarized.
  if (config?.group || maxRows === undefined || rows.length <= maxRows) {
    return { rows, focusedRow };
  }
  const kept = rows.slice(0, maxRows);
  const hidden = rows.length - maxRows;
  kept.push([t('%s more…', hidden), '']);
  return {
    rows: kept,
    focusedRow:
      focusedRow !== undefined && focusedRow < maxRows ? focusedRow : undefined,
  };
}
