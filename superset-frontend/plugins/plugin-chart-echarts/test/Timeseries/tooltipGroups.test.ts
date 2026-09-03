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
import { ChartProps, SqlaFormData, supersetTheme } from '@superset-ui/core';
import { EchartsTimeseriesChartProps } from '../../src/types';
import transformProps from '../../src/Timeseries/transformProps';

/** A bar chart of SUM(sales) by city, broken down by status and year. */
const SERIES = [
  'Shipped, 2003',
  'Shipped, 2004',
  'Shipped, 2005',
  'Cancelled, 2003',
  'Cancelled, 2004',
  'Disputed, 2005',
];
const VALUES = [306000, 400000, 206000, 120000, 50000, 31800];

function render(tooltipCustomConfig?: string): {
  rows: string[];
  bold: string[];
} {
  const chartProps = new ChartProps({
    formData: {
      colorScheme: 'bnbColors',
      datasource: '3__table',
      viz_type: 'echarts_timeseries_bar',
      metrics: ['SUM(sales)'],
      groupby: ['status', 'year'],
      richTooltip: true,
      showTooltipTotal: true,
      tooltipCustomConfig,
    } as SqlaFormData,
    width: 800,
    height: 600,
    queriesData: [
      {
        data: [
          SERIES.reduce((row, name, i) => ({ ...row, [name]: VALUES[i] }), {
            __timestamp: 0,
          } as Record<string, unknown>),
        ],
      },
    ],
    theme: supersetTheme,
  });
  const { echartOptions } = transformProps(
    chartProps as EchartsTimeseriesChartProps,
  );
  const { formatter } = echartOptions.tooltip as {
    formatter: (params: unknown) => string;
  };
  const html = formatter(
    SERIES.map((seriesName, i) => ({
      seriesName,
      seriesId: seriesName,
      value: [0, VALUES[i]],
      marker: '',
    })),
  );
  const trs: string[] = html.match(/<tr[^>]*>[\s\S]*?<\/tr>/g) ?? [];
  const text = (tr: string) =>
    tr
      .replace(/<[^>]+>/g, '\t')
      .replace(/\t+/g, '\t')
      .replace(/\u00a0/g, '')
      .trim();
  return {
    rows: trs.map(text),
    bold: trs.filter(tr => tr.includes('font-weight: 700')).map(text),
  };
}

describe('tooltip grouping', () => {
  it('is flat without a group config', () => {
    expect(render().rows).toEqual([
      'Shipped, 2003\t306k',
      'Shipped, 2004\t400k',
      'Shipped, 2005\t206k',
      'Cancelled, 2003\t120k',
      'Cancelled, 2004\t50k',
      'Disputed, 2005\t31.8k',
      'Total\t1.11M',
    ]);
  });

  it('groups by a dimension name, newest first, dropping the year from rows', () => {
    const { rows, bold } = render(
      JSON.stringify({
        group: {
          by: 'year',
          label: '{value}',
          order: ['2005', '2004', '2003'],
        },
      }),
    );
    expect(rows).toEqual([
      '2005',
      'Shipped\t206k',
      'Disputed\t31.8k',
      '2004',
      'Shipped\t400k',
      'Cancelled\t50k',
      '2003',
      'Shipped\t306k',
      'Cancelled\t120k',
      'Total\t1.11M',
    ]);
    // the section headers are the emphasized rows
    expect(bold).toEqual(['2005', '2004', '2003']);
  });

  it('accepts a dimension position instead of a name', () => {
    expect(
      render(JSON.stringify({ group: { by: 1 } })).rows.slice(0, 3),
    ).toEqual(['2003', 'Shipped\t306k', 'Cancelled\t120k']);
  });

  it('can group by the other dimension just as well', () => {
    expect(render(JSON.stringify({ group: { by: 'status' } })).rows).toEqual([
      'Shipped',
      '2003\t306k',
      '2004\t400k',
      '2005\t206k',
      'Cancelled',
      '2003\t120k',
      '2004\t50k',
      'Disputed',
      '2005\t31.8k',
      'Total\t1.11M',
    ]);
  });

  it('adds a subtotal per group when asked', () => {
    const { rows } = render(
      JSON.stringify({
        group: { by: 'year', label: 'Năm {value}', total: true },
      }),
    );
    expect(rows[0]).toBe('Năm 2003\t426k');
    expect(rows).toContain('Năm 2004\t450k');
    expect(rows).toContain('Năm 2005\t238k');
  });

  it('keeps the full label when stripFromLabel is off', () => {
    expect(
      render(
        JSON.stringify({ group: { by: 'year', stripFromLabel: false } }),
      ).rows.slice(0, 2),
    ).toEqual(['2003', 'Shipped, 2003\t306k']);
  });

  it('still honors a per-series label inside a group', () => {
    expect(
      render(
        JSON.stringify({
          group: { by: 'year' },
          series: { 'Shipped, 2003': { label: 'Đã giao' } },
        }),
      ).rows.slice(0, 2),
    ).toEqual(['2003', 'Đã giao\t306k']);
  });

  it('ignores an unknown dimension rather than grouping on the wrong part', () => {
    expect(render(JSON.stringify({ group: { by: 'nope' } })).rows).toEqual(
      render().rows,
    );
  });

  it('ignores maxRows while grouping, so no header is left stranded', () => {
    const { rows } = render(
      JSON.stringify({ group: { by: 'year' }, maxRows: 2 }),
    );
    expect(rows).toHaveLength(10);
  });
});
