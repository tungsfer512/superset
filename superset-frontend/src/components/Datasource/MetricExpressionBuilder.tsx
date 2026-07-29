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
import { useMemo, useState } from 'react';
import { t, css, useTheme } from '@superset-ui/core';
import { Select } from '@superset-ui/core/components';
import { Radio } from '@superset-ui/core/components/Radio';
import TextAreaControlOrig from 'src/explore/components/controls/TextAreaControl';

// TextAreaControl is a PropTypes-based control; loosen typing for JSX usage.
const TextAreaControl: any = TextAreaControlOrig;

// Aggregate functions offered in the guided (basic) mode.
// COUNT_STAR maps to COUNT(*); COUNT_DISTINCT maps to COUNT(DISTINCT col).
const AGGREGATE_OPTIONS = [
  { value: 'SUM', label: `SUM · ${t('Sum')}` },
  { value: 'AVG', label: `AVG · ${t('Average')}` },
  { value: 'MIN', label: `MIN · ${t('Minimum')}` },
  { value: 'MAX', label: `MAX · ${t('Maximum')}` },
  { value: 'COUNT', label: `COUNT · ${t('Count')}` },
  { value: 'COUNT_DISTINCT', label: `COUNT DISTINCT · ${t('Count distinct')}` },
  { value: 'COUNT_STAR', label: `COUNT(*) · ${t('Count all rows')}` },
];

const AGGREGATE_VALUES = AGGREGATE_OPTIONS.map(o => o.value);

type SimpleParts = { aggregate: string; column?: string };

// Strip surrounding quotes/backticks/brackets from an identifier.
const stripQuotes = (raw: string): string =>
  raw.replace(/^[`"[]/, '').replace(/[`"\]]$/, '');

// Try to parse a SQL expression back into {aggregate, column} so an existing
// metric opens in basic mode. Returns null when it is not a plain aggregate.
export function parseSimpleExpression(expr?: string): SimpleParts | null {
  if (!expr) return null;
  const s = expr.trim();
  if (/^COUNT\s*\(\s*\*\s*\)$/i.test(s)) {
    return { aggregate: 'COUNT_STAR' };
  }
  const distinct = s.match(
    /^COUNT\s*\(\s*DISTINCT\s+([`"[]?[\w.]+[`"\]]?)\s*\)$/i,
  );
  if (distinct) {
    return { aggregate: 'COUNT_DISTINCT', column: stripQuotes(distinct[1]) };
  }
  const m = s.match(
    /^(SUM|AVG|MIN|MAX|COUNT)\s*\(\s*([`"[]?[\w.]+[`"\]]?)\s*\)$/i,
  );
  if (m) {
    return { aggregate: m[1].toUpperCase(), column: stripQuotes(m[2]) };
  }
  return null;
}

// Build the SQL expression from the guided selections.
export function buildSimpleExpression(
  aggregate: string,
  column?: string,
): string {
  if (aggregate === 'COUNT_STAR') return 'COUNT(*)';
  if (!aggregate || !column) return '';
  if (aggregate === 'COUNT_DISTINCT') return `COUNT(DISTINCT ${column})`;
  return `${aggregate}(${column})`;
}

interface ColumnLike {
  column_name: string;
  verbose_name?: string | null;
}

interface Props {
  value: string;
  onChange: (sql: string) => void;
  columns: ColumnLike[];
}

// Render the dropdown into the modal (not the table cell, which clips it).
const popupContainer = (triggerNode: HTMLElement): HTMLElement =>
  (triggerNode.closest('.ant-modal-content') as HTMLElement) || document.body;

export default function MetricExpressionBuilder({
  value,
  onChange,
  columns,
}: Props) {
  const theme = useTheme();
  // Parse only on mount (like an uncontrolled initialValue); ignore later value churn.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const initialParsed = useMemo(() => parseSimpleExpression(value), []);
  // New (empty) metrics default to basic; unparseable ones open in SQL mode.
  const [mode, setMode] = useState<'basic' | 'sql'>(
    !value || initialParsed ? 'basic' : 'sql',
  );
  const [aggregate, setAggregate] = useState<string | undefined>(
    initialParsed?.aggregate,
  );
  const [column, setColumn] = useState<string | undefined>(
    initialParsed?.column,
  );

  const columnOptions = useMemo(
    () =>
      (columns || []).map(c => ({
        value: c.column_name,
        label: c.verbose_name || c.column_name,
      })),
    [columns],
  );

  const needsColumn = aggregate && aggregate !== 'COUNT_STAR';

  const emit = (nextAgg?: string, nextCol?: string) => {
    onChange(buildSimpleExpression(nextAgg || '', nextCol));
  };

  const handleAggregate = (val: string) => {
    setAggregate(val);
    const nextCol = val === 'COUNT_STAR' ? undefined : column;
    if (val === 'COUNT_STAR') setColumn(undefined);
    emit(val, nextCol);
  };

  const handleColumn = (val: string) => {
    setColumn(val);
    emit(aggregate, val);
  };

  const switchMode = (nextMode: 'basic' | 'sql') => {
    if (nextMode === 'basic') {
      // Re-parse whatever SQL is there so the pickers stay in sync.
      const parsed = parseSimpleExpression(value);
      setAggregate(parsed?.aggregate);
      setColumn(parsed?.column);
    }
    setMode(nextMode);
  };

  return (
    <div
      css={css`
        display: flex;
        flex-direction: column;
        gap: ${theme.sizeUnit * 2}px;
        min-width: 240px;
      `}
    >
      <Radio.Group
        size="small"
        value={mode}
        onChange={e => switchMode(e.target.value)}
        options={[
          { value: 'basic', label: t('Basic') },
          { value: 'sql', label: t('Custom SQL') },
        ]}
        optionType="button"
        buttonStyle="solid"
      />

      {mode === 'basic' ? (
        <>
          <Select
            ariaLabel={t('Aggregate function')}
            placeholder={t('Select aggregate function')}
            options={AGGREGATE_OPTIONS}
            value={
              aggregate && AGGREGATE_VALUES.includes(aggregate)
                ? aggregate
                : undefined
            }
            onChange={val => handleAggregate(val as string)}
            getPopupContainer={popupContainer}
          />
          {needsColumn && (
            <Select
              ariaLabel={t('Column')}
              placeholder={t('Select a column')}
              options={columnOptions}
              value={column}
              onChange={val => handleColumn(val as string)}
              showSearch
              getPopupContainer={popupContainer}
            />
          )}
          <div
            css={css`
              font-family: ${theme.fontFamilyCode};
              font-size: ${theme.fontSizeSM}px;
              color: ${theme.colorTextTertiary};
              background: ${theme.colorBgLayout};
              border-radius: ${theme.borderRadius}px;
              padding: ${theme.sizeUnit}px ${theme.sizeUnit * 2}px;
              word-break: break-all;
            `}
          >
            {value || t('SQL will appear here')}
          </div>
        </>
      ) : (
        <TextAreaControl
          canEdit
          initialValue={value}
          onChange={onChange}
          extraClasses={['datasource-sql-expression']}
          language="sql"
          offerEditInModal={false}
          minLines={5}
          textAreaStyles={{ minWidth: '200px', maxWidth: '450px' }}
          resize="both"
        />
      )}
    </div>
  );
}
