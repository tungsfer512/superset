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
import { addTranslation } from '@superset-ui/core';
import {
  translateChoiceDisplayLabel,
  translateControlOptions,
  translateControlTupleLabels,
} from 'src/explore/components/controlLabelTranslation';

beforeAll(() => {
  // Words that are both real UI strings and plausible column names: exactly
  // the collision this guards against.
  addTranslation('year', ['năm']);
  addTranslation('status', ['trạng thái']);
  addTranslation('Sort ascending', ['Sắp xếp tăng dần']);
});

describe('translateChoiceDisplayLabel', () => {
  it('translates a UI label', () => {
    expect(translateChoiceDisplayLabel('Sort ascending')).toBe(
      'Sắp xếp tăng dần',
    );
  });

  it('leaves a dataset name exactly as the dataset spells it', () => {
    const datasetNames = new Set(['year', 'status']);
    expect(translateChoiceDisplayLabel('year', datasetNames)).toBe('year');
    expect(translateChoiceDisplayLabel('status', datasetNames)).toBe('status');
  });

  it('still translates a UI label when a dataset list is given', () => {
    expect(
      translateChoiceDisplayLabel('Sort ascending', new Set(['year'])),
    ).toBe('Sắp xếp tăng dần');
  });

  it('translates only the sort suffix, never the column it applies to', () => {
    expect(translateChoiceDisplayLabel('year [asc]')).toBe(
      `year ${translateChoiceDisplayLabel('[asc]')}`,
    );
    expect(translateChoiceDisplayLabel('status [desc]')).toContain('status ');
  });
});

describe('translateControlTupleLabels', () => {
  it('translates the label of each [value, label] pair', () => {
    expect(translateControlTupleLabels([['asc', 'Sort ascending']])).toEqual([
      ['asc', 'Sắp xếp tăng dần'],
    ]);
  });

  it('leaves dataset-derived choices alone', () => {
    // `stackDimension` and friends build their choices from the chart's
    // columns, so both halves of the pair are the column name.
    expect(
      translateControlTupleLabels(
        [
          ['year', 'year'],
          ['status', 'status'],
        ],
        new Set(['year', 'status']),
      ),
    ).toEqual([
      ['year', 'year'],
      ['status', 'status'],
    ]);
  });

  it('passes through anything that is not a pair', () => {
    expect(translateControlTupleLabels(undefined)).toBeUndefined();
    expect(translateControlTupleLabels(['year'])).toEqual(['year']);
  });
});

describe('translateControlOptions', () => {
  it('translates object-style options', () => {
    expect(
      translateControlOptions([{ value: 'asc', label: 'Sort ascending' }]),
    ).toEqual([{ value: 'asc', label: 'Sắp xếp tăng dần' }]);
  });

  it('leaves a dataset name in object-style options', () => {
    expect(
      translateControlOptions(
        [{ value: 'year', label: 'year' }],
        new Set(['year']),
      ),
    ).toEqual([{ value: 'year', label: 'year' }]);
  });

  it('handles an empty list', () => {
    expect(translateControlOptions([])).toEqual([]);
  });
});
