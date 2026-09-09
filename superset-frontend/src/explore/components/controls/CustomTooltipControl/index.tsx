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
import { useEffect, useMemo, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { css, ensureIsArray, styled, t } from '@superset-ui/core';
import {
  Button,
  Icons,
  Input,
  InputNumber,
  Select,
  Switch,
} from '@superset-ui/core/components';
import { getChartKey } from 'src/explore/exploreUtils';
import ControlHeader from '../../ControlHeader';
import {
  type CustomTooltipSettings,
  type TooltipSeriesOverride,
  deriveGroupValues,
  isParseableJson,
  parseSettings,
  serializeSettings,
} from './utils';

export interface CustomTooltipControlProps {
  /** The stored JSON; the chart reads this exact string. */
  value?: string;
  onChange?: (value: string) => void;
  name?: string;
  label?: string;
  description?: string;
  renderTrigger?: boolean;
  hovered?: boolean;
}

const Field = styled.div`
  ${({ theme }) => css`
    margin-bottom: ${theme.sizeUnit * 2}px;
  `}
`;

const FieldLabel = styled.div`
  ${({ theme }) => css`
    font-size: ${theme.fontSizeSM}px;
    color: ${theme.colorTextSecondary};
    margin-bottom: ${theme.sizeUnit}px;
  `}
`;

const InlineField = styled.div`
  ${({ theme }) => css`
    display: flex;
    align-items: center;
    gap: ${theme.sizeUnit * 2}px;
    margin-bottom: ${theme.sizeUnit * 2}px;
    font-size: ${theme.fontSizeSM}px;
  `}
`;

/**
 * The series and its label sit on two lines rather than side by side.
 *
 * The panel is narrow and series names get long -- and worse, two of them often
 * differ only at the end ("…, Chưa hoàn thành" vs "…, Đã hoàn thành"), so a
 * squeezed dropdown truncates them to the same prefix and the rows become
 * indistinguishable. `minmax(0, …)` lets the dropdown shrink at all: a plain
 * `1fr` floors at the content's width and crushes whatever shares the row.
 */
const LabelRow = styled.div`
  ${({ theme }) => css`
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'series remove'
      'label label';
    align-items: center;
    gap: ${theme.sizeUnit}px;
    margin-bottom: ${theme.sizeUnit * 3}px;

    > *:nth-child(1) {
      grid-area: series;
      min-width: 0;
    }
    > *:nth-child(2) {
      grid-area: remove;
    }
    > *:nth-child(3) {
      grid-area: label;
      min-width: 0;
    }
  `}
`;

const RowNote = styled.div`
  ${({ theme }) => css`
    font-size: ${theme.fontSizeSM}px;
    color: ${theme.colorTextTertiary};
    margin: -${theme.sizeUnit / 2}px 0 ${theme.sizeUnit}px 0;
  `}
`;

const Footer = styled.div`
  ${({ theme }) => css`
    display: flex;
    justify-content: flex-end;
    margin-top: ${theme.sizeUnit * 2}px;
  `}
`;

const Invalid = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorError};
    font-size: ${theme.fontSizeSM}px;
    margin-top: ${theme.sizeUnit}px;
  `}
`;

const toName = (entry: any): string =>
  typeof entry === 'string'
    ? entry
    : (entry?.label ?? entry?.column_name ?? '');

/**
 * Builds the custom tooltip config through a form, keeping the JSON the chart
 * reads as the stored value. A raw editor is one click away for anything the
 * form does not cover, and the form takes over again as long as the JSON still
 * parses.
 */
export default function CustomTooltipControl({
  value,
  onChange,
  ...headerProps
}: CustomTooltipControlProps) {
  const settings = useMemo(() => parseSettings(value), [value]);
  const [rawMode, setRawMode] = useState(false);
  const [draft, setDraft] = useState(value ?? '');
  // The rename rows on screen. Kept here rather than derived from the value: a
  // row with no series chosen yet, or one whose label was just cleared, has
  // nothing to store, and an empty override is pruned out of the JSON -- so it
  // would vanish the moment it appeared.
  const [labelRows, setLabelRows] = useState<{ id: number; key: string }[]>(
    () =>
      Object.keys(parseSettings(value).series ?? {}).map((key, index) => ({
        id: index,
        key,
      })),
  );
  const nextRowId = useRef(labelRows.length);

  // The chart's dimensions name the groups; its series names are what a
  // per-series override keys on. Both come from the last query response, the
  // same way the series colour control reads them.
  const { dimensions, seriesNames, xAxisName } = useSelector((state: any) => {
    const explore = state?.explore ?? {};
    const formData = explore.form_data ?? {};
    const response =
      state?.charts?.[getChartKey(explore)]?.queriesResponse?.[0] ?? {};
    const rows: any[] = ensureIsArray(response.data);
    const dims = [
      ...ensureIsArray(formData.groupby),
      ...ensureIsArray(formData.dimensions),
    ]
      .map(toName)
      .filter(Boolean);
    const xCol = toName(formData.x_axis);
    const exclude = new Set([xCol, ...dims, '__timestamp'].filter(Boolean));
    const names = new Set<string>();
    ensureIsArray(response.colnames)
      .filter(col => !exclude.has(String(col)))
      .forEach(col => names.add(String(col)));
    if (dims.length && rows.length) {
      rows.forEach(row => {
        const combo = dims
          .map(dim => row?.[dim])
          .filter(entry => entry !== undefined && entry !== null)
          .join(', ');
        if (combo) {
          names.add(combo);
        }
      });
    }
    return {
      dimensions: dims,
      seriesNames: Array.from(names),
      xAxisName: xCol,
    };
  });

  const groupValues = useMemo(
    () => deriveGroupValues(seriesNames, dimensions, settings.group?.by),
    [seriesNames, dimensions, settings.group?.by],
  );

  const commit = (next: CustomTooltipSettings) => {
    const serialized = serializeSettings(next);
    setDraft(serialized);
    onChange?.(serialized);
  };

  const setGroup = (
    patch: Partial<NonNullable<CustomTooltipSettings['group']>>,
  ) => commit({ ...settings, group: { ...settings.group, ...patch } });

  /** Merge, never replace: options set through the JSON editor stay applied. */
  const setSeries = (name: string, patch: Partial<TooltipSeriesOverride>) =>
    commit({
      ...settings,
      series: {
        ...settings.series,
        [name]: { ...settings.series?.[name], ...patch },
      },
    });

  const dropSeries = (next: CustomTooltipSettings, name?: string) => {
    if (!name) {
      return next;
    }
    const series = { ...next.series };
    delete series[name];
    return { ...next, series };
  };

  const addRow = () => {
    const id = nextRowId.current;
    nextRowId.current += 1;
    setLabelRows(rows => [...rows, { id, key: '' }]);
  };

  const removeRow = (id: number) => {
    const row = labelRows.find(entry => entry.id === id);
    setLabelRows(rows => rows.filter(entry => entry.id !== id));
    commit(dropSeries(settings, row?.key));
  };

  /** Point a row at a different series, carrying its options across. */
  const setRowKey = (id: number, key: string) => {
    const row = labelRows.find(entry => entry.id === id);
    setLabelRows(rows =>
      rows.map(entry => (entry.id === id ? { ...entry, key } : entry)),
    );
    if (!key || key === row?.key) {
      return;
    }
    const carried = row?.key ? settings.series?.[row.key] : undefined;
    const without = dropSeries(settings, row?.key);
    commit({
      ...without,
      series: { ...without.series, [key]: { ...carried } },
    });
  };

  // A JSON edit can introduce series the rows do not show yet. Only ever add:
  // a row whose label was cleared has no stored override any more, and pulling
  // it out from under the cursor would be hostile.
  useEffect(() => {
    const configured = Object.keys(settings.series ?? {});
    const missing = configured.filter(
      key => !labelRows.some(row => row.key === key),
    );
    if (missing.length) {
      setLabelRows(rows => [
        ...rows,
        ...missing.map(key => {
          const id = nextRowId.current;
          nextRowId.current += 1;
          return { id, key };
        }),
      ]);
    }
  }, [settings.series, labelRows]);

  if (rawMode) {
    const valid = isParseableJson(draft);
    return (
      <div>
        <ControlHeader {...headerProps} />
        <Input.TextArea
          value={draft}
          rows={12}
          spellCheck={false}
          placeholder='{ "group": { "by": "year" } }'
          onChange={event => {
            const next = event.target.value;
            setDraft(next);
            if (isParseableJson(next)) {
              onChange?.(next.trim() ? next : '');
            }
          }}
        />
        {!valid && (
          <Invalid>{t('Not valid JSON; changes are not saved.')}</Invalid>
        )}
        <Footer>
          <Button
            buttonSize="small"
            buttonStyle="link"
            disabled={!valid}
            onClick={() => setRawMode(false)}
          >
            {t('Back to the form')}
          </Button>
        </Footer>
      </div>
    );
  }

  return (
    <div>
      <ControlHeader {...headerProps} />

      <Field>
        <FieldLabel>
          {xAxisName
            ? t('Heading — {x} or {%(axis)s} stands for the hovered value', {
                axis: xAxisName,
              })
            : t('Heading — {x} stands for the hovered value')}
        </FieldLabel>
        <Input
          value={settings.title ?? ''}
          placeholder={
            xAxisName
              ? t('e.g. Thành phố {%(axis)s}', { axis: xAxisName })
              : t('e.g. Ngày {x}')
          }
          onChange={event => commit({ ...settings, title: event.target.value })}
        />
      </Field>

      <Field>
        <FieldLabel>{t('Group rows by')}</FieldLabel>
        <Select
          ariaLabel={t('Group rows by')}
          allowClear
          allowNewOptions
          placeholder={t('No grouping')}
          value={settings.group?.by ?? undefined}
          options={dimensions.map(name => ({ value: name, label: name }))}
          onChange={next =>
            setGroup({
              by: (typeof next === 'object' ? (next as any)?.value : next) as
                | string
                | undefined,
            })
          }
        />
      </Field>

      {settings.group?.by && (
        <>
          <Field>
            <FieldLabel>
              {t(
                'Section header — {value} or {%(dimension)s} stands for the section',
                { dimension: settings.group.by },
              )}
            </FieldLabel>
            <Input
              value={settings.group.label ?? ''}
              placeholder={t('e.g. Năm {%(dimension)s}', {
                dimension: settings.group.by,
              })}
              onChange={event => setGroup({ label: event.target.value })}
            />
          </Field>
          <Field>
            <FieldLabel>{t('Section order')}</FieldLabel>
            <Select
              ariaLabel={t('Section order')}
              mode="multiple"
              allowClear
              allowNewOptions
              placeholder={t('As the chart orders them')}
              value={settings.group.order ?? []}
              options={groupValues.map(name => ({ value: name, label: name }))}
              onChange={next =>
                setGroup({
                  order: ensureIsArray(next).map(entry =>
                    String(
                      typeof entry === 'object' ? (entry as any)?.value : entry,
                    ),
                  ),
                })
              }
            />
          </Field>
          <InlineField>
            <Switch
              checked={Boolean(settings.group.total)}
              onChange={checked => setGroup({ total: checked })}
              aria-label={t('Subtotal per section')}
            />
            {t('Subtotal per section')}
          </InlineField>
          <InlineField>
            <Switch
              checked={settings.group.stripFromLabel === false}
              onChange={checked => setGroup({ stripFromLabel: !checked })}
              aria-label={t('Keep the full series name in rows')}
            />
            {t('Keep the full series name in rows')}
          </InlineField>
        </>
      )}

      {!settings.group?.by && (
        <Field>
          <FieldLabel>{t('Most rows to list')}</FieldLabel>
          <InputNumber
            min={1}
            value={settings.maxRows}
            placeholder={t('All of them')}
            onChange={next =>
              commit({
                ...settings,
                maxRows: typeof next === 'number' ? next : undefined,
              })
            }
          />
        </Field>
      )}

      <Field>
        <FieldLabel>{t('Rename series')}</FieldLabel>
        {labelRows.map(row => {
          const override = row.key ? settings.series?.[row.key] : undefined;
          // Anything set through the JSON editor stays applied; say so, so the
          // form does not read as the whole story for this series.
          const otherKeys = Object.entries(override ?? {}).filter(
            ([key, entry]) => key !== 'label' && entry !== undefined,
          );
          return (
            <div key={row.id}>
              <LabelRow>
                <Select
                  ariaLabel={t('Series')}
                  allowNewOptions
                  placeholder={t('Series')}
                  value={row.key || undefined}
                  options={seriesNames
                    .filter(
                      name =>
                        name === row.key ||
                        !labelRows.some(other => other.key === name),
                    )
                    .map(name => ({ value: name, label: name }))}
                  onChange={next =>
                    setRowKey(
                      row.id,
                      String(
                        (typeof next === 'object'
                          ? (next as any)?.value
                          : next) ?? '',
                      ),
                    )
                  }
                />
                <Button
                  buttonSize="xsmall"
                  buttonStyle="link"
                  onClick={() => removeRow(row.id)}
                  aria-label={t('Remove')}
                >
                  <Icons.DeleteOutlined iconSize="s" />
                </Button>
                <Input
                  value={override?.label ?? ''}
                  disabled={!row.key}
                  placeholder={t('Label to show')}
                  onChange={event =>
                    row.key && setSeries(row.key, { label: event.target.value })
                  }
                />
              </LabelRow>
              {otherKeys.length > 0 && (
                <RowNote>
                  {t('Also set in JSON: %(keys)s', {
                    keys: otherKeys.map(([key]) => key).join(', '),
                  })}
                </RowNote>
              )}
            </div>
          );
        })}
        <Button
          buttonSize="small"
          buttonStyle="link"
          onClick={addRow}
          aria-label={t('Add a series')}
        >
          <Icons.PlusOutlined iconSize="s" /> {t('Add a series')}
        </Button>
      </Field>

      <Footer>
        <Button
          buttonSize="small"
          buttonStyle="link"
          onClick={() => {
            setDraft(value ?? '');
            setRawMode(true);
          }}
        >
          {t('Edit as JSON')}
        </Button>
      </Footer>
    </div>
  );
}
