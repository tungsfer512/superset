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
import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import {
  css,
  ensureIsArray,
  GenericDataType,
  getTimeFormatter,
  styled,
  t,
} from '@superset-ui/core';
import {
  ColorPicker,
  type ColorValue,
  Select,
} from '@superset-ui/core/components';
import { getChartKey } from 'src/explore/exploreUtils';
import ControlHeader from '../../ControlHeader';

export interface SeriesColorsControlProps {
  value?: Record<string, string>;
  onChange?: (value: Record<string, string>) => void;
  /** 'series' colors a whole series; 'category' colors a single bar/point */
  colorMode?: 'series' | 'category';
  name?: string;
  label?: string;
  description?: string;
  renderTrigger?: boolean;
  hovered?: boolean;
}

const Row = styled.div`
  ${({ theme }) => css`
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: ${theme.sizeUnit * 2}px;
    padding: ${theme.sizeUnit}px 0;
  `}
`;

const Name = styled.span`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 auto;
  min-width: 0;
  font-size: ${({ theme }) => theme.fontSizeSM}px;
`;

const Field = styled.div`
  margin-bottom: ${({ theme }) => theme.sizeUnit * 2}px;
`;

const toName = (g: any): string =>
  typeof g === 'string' ? g : (g?.label ?? g?.column_name ?? '');

export default function SeriesColorsControl({
  value = {},
  onChange,
  colorMode = 'series',
  ...headerProps
}: SeriesColorsControlProps) {
  // Read the current chart's query response + form data from the store
  // (control mapStateToProps doesn't receive it here).
  const { seriesOptions, categoryOptions, categoryIsTemporal, timeFormat } =
    useSelector((state: any) => {
      const explore = state?.explore ?? {};
      const fd = explore.form_data ?? {};
      const key = getChartKey(explore);
      const resp = state?.charts?.[key]?.queriesResponse?.[0] ?? {};
      const colnames: any[] = ensureIsArray(resp.colnames);
      const coltypes: any[] = ensureIsArray(resp.coltypes);
      const data: any[] = ensureIsArray(resp.data);
      const dims = [
        ...ensureIsArray(fd.groupby),
        ...ensureIsArray(fd.dimensions),
      ]
        .map(toName)
        .filter(Boolean);
      const xCol = toName(fd.x_axis);
      const exclude = new Set(
        [xCol, ...dims, '__timestamp', 'time', 'timestamp'].filter(Boolean),
      );
      const cats = new Set<string>();
      if (xCol && data.length) {
        data.forEach(r => {
          const v = r?.[xCol];
          if (v !== undefined && v !== null) cats.add(String(v));
        });
      }
      // Detect a date/datetime x-axis so we can show readable times in the
      // dropdown instead of raw epoch milliseconds. Prefer the column type
      // reported by the query; fall back to a heuristic on the values.
      const xIdx = colnames.indexOf(xCol);
      let temporal = xIdx >= 0 && coltypes[xIdx] === GenericDataType.Temporal;
      if (!temporal && cats.size) {
        temporal = Array.from(cats).every(
          v => /^\d{12,}$/.test(v) && Number.isFinite(Number(v)),
        );
      }
      const ser = new Set<string>();
      colnames.filter(c => !exclude.has(c)).forEach(c => ser.add(String(c)));
      if (dims.length && data.length) {
        data.forEach(r => {
          const combo = dims
            .map(d => r?.[d])
            .filter(v => v !== undefined && v !== null)
            .join(', ');
          if (combo) ser.add(combo);
        });
      }
      // Pick an UNAMBIGUOUS, fixed format for the dropdown (the chart's default
      // `smart_date` is adaptive and drops the year, e.g. shows just "April").
      // Use the finest granularity present so every value stays distinct.
      let timeFmt = '%Y-%m-%d';
      if (temporal) {
        const nums = Array.from(cats)
          .map(Number)
          .filter(n => Number.isFinite(n));
        const hasSub = (mod: number) => nums.some(n => n % mod !== 0);
        if (hasSub(60 * 1000)) timeFmt = '%Y-%m-%d %H:%M:%S';
        else if (hasSub(60 * 60 * 1000)) timeFmt = '%Y-%m-%d %H:%M';
        else if (hasSub(24 * 60 * 60 * 1000)) timeFmt = '%Y-%m-%d %H:00';
      }
      return {
        seriesOptions: Array.from(ser),
        categoryOptions: Array.from(cats),
        categoryIsTemporal: temporal,
        timeFormat: timeFmt,
      };
    });

  // For temporal categories, render labels as formatted dates while keeping the
  // stored key as the raw epoch value (so it still matches the chart data).
  const formatLabel = useMemo(() => {
    if (colorMode !== 'category' || !categoryIsTemporal)
      return (s: string) => s;
    const fmt = getTimeFormatter(timeFormat);
    return (s: string) => {
      const n = Number(s);
      return Number.isFinite(n) ? fmt(n) : s;
    };
  }, [colorMode, categoryIsTemporal, timeFormat]);

  const setColor = (label: string, hex?: string) => {
    const next = { ...value };
    if (hex) next[label] = hex;
    else delete next[label];
    onChange?.(next);
  };

  const available = colorMode === 'category' ? categoryOptions : seriesOptions;
  const selectOptions = useMemo(
    () =>
      available
        .filter(label => !(label in value))
        .map(label => ({ value: label, label: formatLabel(label) })),
    [available, value, formatLabel],
  );

  return (
    <div>
      <ControlHeader {...headerProps} />
      <Field>
        <Select
          ariaLabel={
            colorMode === 'category'
              ? t('Add column value')
              : t('Add series')
          }
          allowNewOptions
          placeholder={
            colorMode === 'category'
              ? t('Select a column value to color…')
              : t('Select a series to color…')
          }
          options={selectOptions}
          value={null}
          onChange={(v: any) => {
            const label = typeof v === 'object' ? v?.value : v;
            if (label && !(label in value)) setColor(String(label), '#1FA8C9');
          }}
        />
      </Field>
      {Object.keys(value).map(label => (
        <Row key={label}>
          <Name title={formatLabel(label)}>{formatLabel(label)}</Name>
          <ColorPicker
            value={value[label]}
            allowClear
            onChangeComplete={(color: ColorValue) =>
              setColor(label, color.toHexString())
            }
            onClear={() => setColor(label)}
          />
        </Row>
      ))}
    </div>
  );
}
