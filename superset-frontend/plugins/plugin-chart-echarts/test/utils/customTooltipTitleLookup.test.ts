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
import { getColumnLabel, QueryFormData } from '@superset-ui/core';
import buildTimeseriesQuery from '../../src/Timeseries/buildQuery';
import buildMixedQuery from '../../src/MixedTimeseries/buildQuery';
import {
  buildTooltipTitleLookup,
  formatCustomTooltipTitle,
  getTooltipTitleColumns,
  parseCustomTooltipConfig,
} from '../../src/utils/customTooltip';

const config = (title: string) =>
  parseCustomTooltipConfig(JSON.stringify({ title }));

describe('getTooltipTitleColumns', () => {
  it('lists the columns a title names besides the axis', () => {
    expect(
      getTooltipTitleColumns(config('{city} ({postal_code}) {x} {time}'), [
        'city',
      ]),
    ).toEqual(['postal_code']);
  });

  it('is empty without a title', () => {
    expect(getTooltipTitleColumns(undefined)).toEqual([]);
    expect(getTooltipTitleColumns(config('Ngày {x}'))).toEqual([]);
  });
});

describe('buildTooltipTitleLookup', () => {
  const title = config('Thành phố {postal_code}');

  it('looks up a one-to-one column by x value', () => {
    const lookup = buildTooltipTitleLookup(title, 'city', [
      { city: 'Lyon', postal_code: '69004' },
      { city: 'Koln', postal_code: '50739' },
    ]);
    expect(lookup?.('Lyon')).toEqual({ postal_code: '69004' });
    expect(
      formatCustomTooltipTitle('Lyon', title, 'city', lookup?.('Lyon')),
    ).toBe('Thành phố 69004');
  });

  it('throws when one x value has several values (1-N)', () => {
    expect(() =>
      buildTooltipTitleLookup(title, 'city', [
        { city: 'Lyon', postal_code: '69004' },
        { city: 'Lyon', postal_code: '69005' },
      ]),
    ).toThrow(/"Lyon" has 2 values/);
  });

  it('throws when one value spans several x values (N-1)', () => {
    expect(() =>
      buildTooltipTitleLookup(title, 'city', [
        { city: 'Lyon', postal_code: '69004' },
        { city: 'Paris', postal_code: '69004' },
      ]),
    ).toThrow(/"69004" belongs to 2/);
  });

  it('matches temporal x values by timestamp', () => {
    const lookup = buildTooltipTitleLookup(config('{quarter}'), 'order_date', [
      { order_date: 1072915200000, quarter: 'Q1' },
    ]);
    expect(lookup?.(1072915200000)).toEqual({ quarter: 'Q1' });
  });

  it('is undefined until the lookup query has run', () => {
    expect(buildTooltipTitleLookup(title, 'city', undefined)).toBeUndefined();
    // rows from a query run for an earlier title
    expect(
      buildTooltipTitleLookup(title, 'city', [{ city: 'Lyon', state: 'X' }]),
    ).toBeUndefined();
  });
});

describe('title lookup query', () => {
  const formData = {
    datasource: '5__table',
    viz_type: 'echarts_timeseries_bar',
    x_axis: 'city',
    metrics: ['SUM(sales)'],
    groupby: ['status'],
    tooltipCustomConfig: '{"title": "Thành phố {postal_code}"}',
  } as unknown as QueryFormData;

  it('is appended after the chart query', () => {
    const { queries } = buildTimeseriesQuery(formData);
    expect(queries).toHaveLength(2);
    expect(queries[1].columns?.map(getColumnLabel)).toEqual([
      'city',
      'postal_code',
    ]);
    expect(queries[1].metrics).toEqual([]);
    expect(queries[1].post_processing).toEqual([]);
  });

  it('is left out when the title names only the axis', () => {
    const { queries } = buildTimeseriesQuery({
      ...formData,
      tooltipCustomConfig: '{"title": "Thành phố {city}"}',
    });
    expect(queries).toHaveLength(1);
  });

  it('comes third on Mixed Chart', () => {
    const { queries } = buildMixedQuery({
      ...formData,
      viz_type: 'mixed_timeseries',
      metrics_b: ['COUNT(*)'],
    });
    expect(queries).toHaveLength(3);
    expect(queries[2].columns?.map(getColumnLabel)).toEqual([
      'city',
      'postal_code',
    ]);
  });
});
