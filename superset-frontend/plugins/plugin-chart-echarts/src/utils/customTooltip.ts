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

export type CustomTooltipConfig = {
  /** Heading template; `{time}` or `{x}` stands for the default heading. */
  title?: string;
  /** Keeps at most this many series rows, summarizing the rest as a count. */
  maxRows?: number;
  series: Record<string, TooltipSeriesConfig>;
};

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
    series,
  };

  return config.title === undefined &&
    config.maxRows === undefined &&
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

export function getTooltipSeriesLabel(
  key: string,
  config?: CustomTooltipConfig,
): string {
  return config?.series[key]?.label ?? key;
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
): string {
  const template = config?.title;
  if (!template) {
    return defaultTitle;
  }
  return template.replace(TITLE_PLACEHOLDER, defaultTitle);
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
  if (maxRows === undefined || rows.length <= maxRows) {
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
