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
import { FC } from 'react';
import { styled, t } from '@superset-ui/core';
import { FormItem, Input, Select } from '@superset-ui/core/components';
import { DEFAULT_COLUMN_GUESS } from './types';

export interface HierarchyConfigFieldsProps {
  filterId: string;
  columns: string[];
  initial?: {
    keyColumn?: string;
    parentColumn?: string;
    labelColumn?: string;
    levelColumn?: string;
    valueColumn?: string;
    targetColumn?: string;
  };
  onChange: () => void;
}

const Fields = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.sizeUnit}px;
`;

const Label = styled.span`
  ${({ theme }) => `
    font-size: ${theme.fontSizeSM}px;
    color: ${theme.colorTextSecondary};
  `}
`;

// First column whose name matches one of the guesses (case-insensitive),
// otherwise the fallback (by position) if present.
const guess = (columns: string[], names: string[], fallbackIndex?: number) => {
  const lower = columns.map(c => c.toLowerCase());
  const hit = names.map(n => n.toLowerCase()).find(n => lower.includes(n));
  if (hit) {
    return columns[lower.indexOf(hit)];
  }
  return fallbackIndex !== undefined ? columns[fallbackIndex] : undefined;
};

/** Role → column mapping controls for the hierarchical filter, rendered inside
 *  the native-filter config form. Column options come from the mapping dataset,
 *  so names stay dynamic (nothing is hard-coded). */
const HierarchyConfigFields: FC<HierarchyConfigFieldsProps> = ({
  filterId,
  columns,
  initial,
  onChange,
}) => {
  const options = columns.map(c => ({ value: c, label: c }));
  const keyGuess = guess(columns, DEFAULT_COLUMN_GUESS.key, 1);
  const parentGuess = guess(columns, DEFAULT_COLUMN_GUESS.parent, 3);
  const labelGuess = guess(columns, DEFAULT_COLUMN_GUESS.label, 2);
  const levelGuess = guess(columns, DEFAULT_COLUMN_GUESS.level, 0);

  const name = (field: string) => ['filters', filterId, 'controlValues', field];

  const columnSelect = (
    field: string,
    label: string,
    initialValue?: string,
    allowClear = false,
  ) => (
    <FormItem
      name={name(field)}
      initialValue={initialValue}
      label={<Label>{label}</Label>}
    >
      <Select
        allowClear={allowClear}
        options={options}
        onChange={onChange}
        placeholder={t('Select a column…')}
        ariaLabel={label}
      />
    </FormItem>
  );

  return (
    <Fields>
      {columnSelect(
        'keyColumn',
        t('Id column (builds the tree)'),
        initial?.keyColumn ?? keyGuess,
      )}
      {columnSelect(
        'parentColumn',
        t('Parent id column'),
        initial?.parentColumn ?? parentGuess,
      )}
      {columnSelect(
        'labelColumn',
        t('Display column (label)'),
        initial?.labelColumn ?? labelGuess,
      )}
      {columnSelect(
        'levelColumn',
        t('Level column (optional)'),
        initial?.levelColumn ?? levelGuess,
        true,
      )}
      {columnSelect(
        'valueColumn',
        t('Filter by (value column)'),
        initial?.valueColumn ?? keyGuess,
      )}
      <FormItem
        name={name('targetColumn')}
        initialValue={initial?.targetColumn}
        label={
          <Label>
            {t("Chart column to filter — empty = use the value column's name")}
          </Label>
        }
      >
        <Input
          allowClear
          placeholder={t(
            'e.g. group_id (if the chart names the column differently)',
          )}
          onChange={onChange}
        />
      </FormItem>
    </Fields>
  );
};

export default HierarchyConfigFields;
