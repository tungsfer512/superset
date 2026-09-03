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

const TIMESTAMP = 599616000000;

const baseFormData: SqlaFormData = {
  colorScheme: 'bnbColors',
  datasource: '3__table',
  granularity_sqla: 'ds',
  metric: 'sum__num',
  groupby: [],
  viz_type: 'echarts_timeseries_line',
  richTooltip: true,
  showTooltipTotal: false,
};

const queriesData = [
  {
    data: [{ Revenue: 1234.5, Cost: 200, Internal: 7, __timestamp: TIMESTAMP }],
  },
];

/** The rendered tooltip HTML for a hover over every series at one point. */
function renderTooltip(tooltipCustomConfig?: string): string {
  const chartProps = new ChartProps({
    formData: { ...baseFormData, tooltipCustomConfig },
    width: 800,
    height: 600,
    queriesData,
    theme: supersetTheme,
  });
  const { echartOptions } = transformProps(
    chartProps as EchartsTimeseriesChartProps,
  );
  const { formatter } = echartOptions.tooltip as {
    formatter: (params: unknown) => string;
  };
  return formatter(
    ['Revenue', 'Cost', 'Internal'].map((seriesName, index) => ({
      seriesName,
      seriesId: seriesName,
      value: [TIMESTAMP, [1234.5, 200, 7][index]],
      marker: '',
    })),
  );
}

describe('Timeseries custom tooltip', () => {
  it('renders every series by default', () => {
    const html = renderTooltip();
    expect(html).toContain('Revenue');
    expect(html).toContain('Cost');
    expect(html).toContain('Internal');
  });

  it('is unaffected by an invalid config', () => {
    expect(renderTooltip('{not json')).toBe(renderTooltip());
    expect(renderTooltip('')).toBe(renderTooltip());
  });

  it('relabels series', () => {
    const html = renderTooltip(
      JSON.stringify({ series: { Revenue: { label: 'Doanh thu' } } }),
    );
    expect(html).toContain('Doanh thu');
    expect(html).not.toContain('Revenue');
  });

  it('hides series', () => {
    const html = renderTooltip(
      JSON.stringify({ series: { Internal: { hidden: true } } }),
    );
    expect(html).toContain('Revenue');
    expect(html).not.toContain('Internal');
  });

  it('reorders series', () => {
    const html = renderTooltip(
      JSON.stringify({
        series: { Internal: { order: 1 }, Revenue: { order: 2 } },
      }),
    );
    expect(html.indexOf('Internal')).toBeLessThan(html.indexOf('Revenue'));
    expect(html.indexOf('Revenue')).toBeLessThan(html.indexOf('Cost'));
  });

  it('applies a prefix, suffix and per-series number format', () => {
    const html = renderTooltip(
      JSON.stringify({
        series: {
          Revenue: { prefix: '≈ ', suffix: ' ₫', format: ',.0f' },
        },
      }),
    );
    expect(html).toContain('≈ 1,235 ₫');
  });

  it('templates the heading', () => {
    expect(renderTooltip(JSON.stringify({ title: 'Ngày {time}' }))).toContain(
      'Ngày ',
    );
  });

  it('caps the number of rows', () => {
    const html = renderTooltip(JSON.stringify({ maxRows: 2 }));
    expect(html).toContain('Revenue');
    expect(html).toContain('Cost');
    expect(html).not.toContain('Internal');
    // the remainder is summarized rather than silently dropped
    expect(html).toContain('1');
  });

  it('keeps the total row when rows are capped', () => {
    const chartProps = new ChartProps({
      formData: {
        ...baseFormData,
        metrics: ['a', 'b'],
        showTooltipTotal: true,
        tooltipCustomConfig: JSON.stringify({ maxRows: 1 }),
      },
      width: 800,
      height: 600,
      queriesData,
      theme: supersetTheme,
    });
    const { echartOptions } = transformProps(
      chartProps as EchartsTimeseriesChartProps,
    );
    const { formatter } = echartOptions.tooltip as {
      formatter: (params: unknown) => string;
    };
    const html = formatter(
      ['Revenue', 'Cost', 'Internal'].map((seriesName, index) => ({
        seriesName,
        seriesId: seriesName,
        value: [TIMESTAMP, [1234.5, 200, 7][index]],
        marker: '',
      })),
    );
    expect(html).toContain('Total');
  });
});
