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
import {
  deriveGroupValues,
  isParseableJson,
  parseSettings,
  serializeSettings,
} from 'src/explore/components/controls/CustomTooltipControl/utils';

describe('parseSettings', () => {
  it('reads an empty or broken value as empty settings', () => {
    expect(parseSettings(undefined)).toEqual({});
    expect(parseSettings('')).toEqual({});
    expect(parseSettings('   ')).toEqual({});
    expect(parseSettings('{not json')).toEqual({});
    expect(parseSettings('[1,2]')).toEqual({});
  });

  it('reads a full config', () => {
    const settings = parseSettings(
      JSON.stringify({
        title: 'Madrid',
        maxRows: 5,
        group: {
          by: 'year',
          label: 'Năm {value}',
          order: ['2005', '2004'],
          total: true,
        },
        series: { 'Shipped, 2003': { label: 'Đã giao', suffix: ' ₫' } },
      }),
    );
    expect(settings.title).toBe('Madrid');
    expect(settings.maxRows).toBe(5);
    expect(settings.group).toMatchObject({
      by: 'year',
      label: 'Năm {value}',
      order: ['2005', '2004'],
      total: true,
    });
    expect(settings.series?.['Shipped, 2003']).toMatchObject({
      label: 'Đã giao',
      suffix: ' ₫',
    });
  });

  it('accepts a numeric group index, which the form edits as text', () => {
    expect(parseSettings('{"group":{"by":1}}').group?.by).toBe('1');
  });
});

describe('serializeSettings', () => {
  it('writes nothing when nothing is configured', () => {
    expect(serializeSettings({})).toBe('');
    expect(serializeSettings({ title: '' })).toBe('');
    expect(serializeSettings({ series: {} })).toBe('');
    // an added-but-untouched series contributes no keys
    expect(serializeSettings({ series: { a: {} } })).toBe('');
  });

  it('drops a group with no dimension chosen', () => {
    expect(serializeSettings({ group: { label: 'x', total: true } })).toBe('');
  });

  it('omits the defaults rather than writing dead keys', () => {
    const json = JSON.parse(
      serializeSettings({
        group: { by: 'year', stripFromLabel: true, total: false },
      }),
    );
    expect(json.group).toEqual({ by: 'year' });
  });

  it('writes stripFromLabel only when turned off', () => {
    const json = JSON.parse(
      serializeSettings({ group: { by: 'year', stripFromLabel: false } }),
    );
    expect(json.group).toEqual({ by: 'year', stripFromLabel: false });
  });

  it('leaves out maxRows while grouping, which the chart would ignore', () => {
    const json = JSON.parse(
      serializeSettings({ maxRows: 5, group: { by: 'year' } }),
    );
    expect(json.maxRows).toBeUndefined();
    expect(JSON.parse(serializeSettings({ maxRows: 5 })).maxRows).toBe(5);
  });

  it('round-trips through the form without drift', () => {
    const original = serializeSettings({
      title: 'Madrid',
      group: { by: 'year', label: 'Năm {value}', order: ['2005'], total: true },
      series: { 'Shipped, 2003': { label: 'Đã giao', hidden: true } },
    });
    expect(serializeSettings(parseSettings(original))).toBe(original);
  });
});

describe('isParseableJson', () => {
  it('accepts an object or an empty value, rejects the rest', () => {
    expect(isParseableJson('')).toBe(true);
    expect(isParseableJson('{"title":"x"}')).toBe(true);
    expect(isParseableJson('{oops')).toBe(false);
    expect(isParseableJson('[1,2]')).toBe(false);
    expect(isParseableJson('42')).toBe(false);
  });
});

describe('deriveGroupValues', () => {
  // A time-series query comes back pivoted: the breakdown is in the column
  // names, not in a column of its own, so the values have to be read off the
  // series names rather than the rows.
  const seriesNames = [
    'Shipped, 2003',
    'Shipped, 2004',
    'Cancelled, 2003',
    'Disputed, 2005',
  ];
  const dimensions = ['status', 'year'];

  it('reads the values of the chosen dimension', () => {
    expect(deriveGroupValues(seriesNames, dimensions, 'year')).toEqual([
      '2003',
      '2004',
      '2005',
    ]);
    expect(deriveGroupValues(seriesNames, dimensions, 'status')).toEqual([
      'Shipped',
      'Cancelled',
      'Disputed',
    ]);
  });

  it('returns nothing when there is no dimension to read', () => {
    expect(deriveGroupValues(seriesNames, dimensions, undefined)).toEqual([]);
    expect(deriveGroupValues(seriesNames, dimensions, 'nope')).toEqual([]);
    expect(deriveGroupValues([], dimensions, 'year')).toEqual([]);
  });

  it('skips a series that has no such part', () => {
    expect(
      deriveGroupValues(['SUM(sales)', 'Shipped, 2003'], dimensions, 'year'),
    ).toEqual(['2003']);
  });
});
