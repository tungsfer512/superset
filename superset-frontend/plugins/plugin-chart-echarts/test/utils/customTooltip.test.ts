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
import { getNumberFormatter } from '@superset-ui/core';
import {
  decorateTooltipValue,
  formatCustomTooltipTitle,
  getTooltipSeriesLabel,
  getTooltipValueFormatter,
  limitTooltipRows,
  orderTooltipKeys,
  parseCustomTooltipConfig,
} from '../../src/utils/customTooltip';

describe('parseCustomTooltipConfig', () => {
  it('returns undefined for an empty value', () => {
    expect(parseCustomTooltipConfig(undefined)).toBeUndefined();
    expect(parseCustomTooltipConfig(null)).toBeUndefined();
    expect(parseCustomTooltipConfig('')).toBeUndefined();
    expect(parseCustomTooltipConfig('   ')).toBeUndefined();
  });

  it('returns undefined for invalid JSON rather than throwing', () => {
    expect(parseCustomTooltipConfig('{not json')).toBeUndefined();
  });

  it('returns undefined for JSON that is not an object', () => {
    expect(parseCustomTooltipConfig('[1, 2]')).toBeUndefined();
    expect(parseCustomTooltipConfig('"a string"')).toBeUndefined();
    expect(parseCustomTooltipConfig('42')).toBeUndefined();
  });

  it('returns undefined when nothing usable is configured', () => {
    expect(parseCustomTooltipConfig('{}')).toBeUndefined();
    expect(parseCustomTooltipConfig('{"unknownKey": 1}')).toBeUndefined();
    // a series entry with no recognized field contributes nothing
    expect(
      parseCustomTooltipConfig('{"series": {"a": {"nope": 1}}}'),
    ).toBeUndefined();
  });

  it('parses a full config', () => {
    expect(
      parseCustomTooltipConfig(
        JSON.stringify({
          title: 'Ngày {time}',
          maxRows: 3,
          series: {
            'SUM(revenue)': {
              label: 'Doanh thu',
              prefix: '~',
              suffix: ' ₫',
              format: ',.0f',
              order: 1,
            },
            secret: { hidden: true },
          },
        }),
      ),
    ).toEqual({
      title: 'Ngày {time}',
      maxRows: 3,
      series: {
        'SUM(revenue)': {
          label: 'Doanh thu',
          prefix: '~',
          suffix: ' ₫',
          format: ',.0f',
          hidden: undefined,
          order: 1,
        },
        secret: {
          label: undefined,
          prefix: undefined,
          suffix: undefined,
          format: undefined,
          hidden: true,
          order: undefined,
        },
      },
    });
  });

  it('drops fields of the wrong type', () => {
    const config = parseCustomTooltipConfig(
      JSON.stringify({
        title: 42,
        series: { a: { label: 1, hidden: 'yes', order: 'first', suffix: '!' } },
      }),
    );
    expect(config?.title).toBeUndefined();
    expect(config?.series.a).toEqual({
      label: undefined,
      prefix: undefined,
      suffix: '!',
      format: undefined,
      hidden: undefined,
      order: undefined,
    });
  });

  it('ignores a non-positive or fractional maxRows', () => {
    expect(parseCustomTooltipConfig('{"maxRows": 0}')).toBeUndefined();
    expect(parseCustomTooltipConfig('{"maxRows": -5}')).toBeUndefined();
    expect(parseCustomTooltipConfig('{"maxRows": 2.7}')?.maxRows).toBe(2);
  });

  it('ignores a series entry that is not an object', () => {
    expect(
      parseCustomTooltipConfig('{"series": {"a": "label", "b": {"order": 1}}}')
        ?.series,
    ).toEqual({
      b: {
        label: undefined,
        prefix: undefined,
        suffix: undefined,
        format: undefined,
        hidden: undefined,
        order: 1,
      },
    });
  });
});

describe('orderTooltipKeys', () => {
  it('passes the keys through with no config', () => {
    expect(orderTooltipKeys(['a', 'b'], undefined)).toEqual(['a', 'b']);
  });

  it('drops hidden series', () => {
    const config = parseCustomTooltipConfig(
      '{"series": {"b": {"hidden": true}}}',
    );
    expect(orderTooltipKeys(['a', 'b', 'c'], config)).toEqual(['a', 'c']);
  });

  it('puts ordered series first and keeps the rest in place', () => {
    const config = parseCustomTooltipConfig(
      '{"series": {"c": {"order": 1}, "a": {"order": 2}}}',
    );
    expect(orderTooltipKeys(['a', 'b', 'c', 'd'], config)).toEqual([
      'c',
      'a',
      'b',
      'd',
    ]);
  });

  it('is stable for series sharing an order', () => {
    const config = parseCustomTooltipConfig(
      '{"series": {"b": {"order": 1}, "a": {"order": 1}}}',
    );
    expect(orderTooltipKeys(['a', 'b'], config)).toEqual(['a', 'b']);
  });
});

describe('getTooltipSeriesLabel', () => {
  it('falls back to the series name', () => {
    expect(getTooltipSeriesLabel('a', undefined)).toBe('a');
    expect(
      getTooltipSeriesLabel('a', parseCustomTooltipConfig('{"maxRows": 1}')),
    ).toBe('a');
  });

  it('uses the configured label', () => {
    const config = parseCustomTooltipConfig(
      '{"series": {"a": {"label": "Doanh thu"}}}',
    );
    expect(getTooltipSeriesLabel('a', config)).toBe('Doanh thu');
  });
});

describe('getTooltipValueFormatter', () => {
  const fallback = getNumberFormatter(',.2f');

  it('keeps the chart formatter when no format is configured', () => {
    expect(getTooltipValueFormatter(fallback, 'a', undefined)).toBe(fallback);
  });

  it('uses the per-series format', () => {
    const config = parseCustomTooltipConfig(
      '{"series": {"a": {"format": ",.0f"}}}',
    );
    const formatter = getTooltipValueFormatter(fallback, 'a', config);
    expect(formatter(1234.56)).toBe('1,235');
    // other series are untouched
    expect(getTooltipValueFormatter(fallback, 'b', config)).toBe(fallback);
  });
});

describe('decorateTooltipValue', () => {
  const config = parseCustomTooltipConfig(
    '{"series": {"a": {"prefix": "≈ ", "suffix": " ₫"}}}',
  );

  it('wraps the value in the prefix and suffix', () => {
    expect(decorateTooltipValue('1,235', 'a', config)).toBe('≈ 1,235 ₫');
  });

  it('leaves other series and empty values alone', () => {
    expect(decorateTooltipValue('1,235', 'b', config)).toBe('1,235');
    expect(decorateTooltipValue('', 'a', config)).toBe('');
    expect(decorateTooltipValue('1,235', 'a', undefined)).toBe('1,235');
  });
});

describe('formatCustomTooltipTitle', () => {
  it('returns the default heading with no template', () => {
    expect(formatCustomTooltipTitle('2026-08-25', undefined)).toBe(
      '2026-08-25',
    );
    expect(
      formatCustomTooltipTitle(
        '2026-08-25',
        parseCustomTooltipConfig('{"maxRows": 2}'),
      ),
    ).toBe('2026-08-25');
  });

  it('substitutes {time} and {x}', () => {
    expect(
      formatCustomTooltipTitle(
        '2026-08-25',
        parseCustomTooltipConfig('{"title": "Ngày {time}"}'),
      ),
    ).toBe('Ngày 2026-08-25');
    expect(
      formatCustomTooltipTitle(
        'Hà Nội',
        parseCustomTooltipConfig('{"title": "Khu vực: {x}"}'),
      ),
    ).toBe('Khu vực: Hà Nội');
  });

  it('substitutes every occurrence', () => {
    expect(
      formatCustomTooltipTitle(
        '5',
        parseCustomTooltipConfig('{"title": "{time} / {x}"}'),
      ),
    ).toBe('5 / 5');
  });
});

describe('limitTooltipRows', () => {
  const rows = [
    ['a', '1'],
    ['b', '2'],
    ['c', '3'],
    ['d', '4'],
  ];

  it('is a no-op with no config or under the cap', () => {
    expect(limitTooltipRows(rows, 1, undefined)).toEqual({
      rows,
      focusedRow: 1,
    });
    expect(
      limitTooltipRows(rows, 1, parseCustomTooltipConfig('{"maxRows": 4}')),
    ).toEqual({ rows, focusedRow: 1 });
  });

  it('trims to the cap and summarizes the remainder', () => {
    const config = parseCustomTooltipConfig('{"maxRows": 2}');
    const result = limitTooltipRows(rows, 0, config);
    expect(result.rows).toHaveLength(3);
    expect(result.rows.slice(0, 2)).toEqual([
      ['a', '1'],
      ['b', '2'],
    ]);
    expect(result.rows[2][0]).toContain('2');
    expect(result.focusedRow).toBe(0);
  });

  it('drops a focused row that was trimmed away', () => {
    const config = parseCustomTooltipConfig('{"maxRows": 2}');
    expect(limitTooltipRows(rows, 3, config).focusedRow).toBeUndefined();
  });
});
