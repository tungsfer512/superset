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
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AppSection,
  DataRecord,
  ExtraFormData,
  ensureIsArray,
  styled,
  t,
} from '@superset-ui/core';
import { Select } from '@superset-ui/core/components';
import {
  Clauses,
  ExpressionTypes,
} from 'src/explore/components/controls/FilterControl/types';
import { FilterBarOrientation } from 'src/dashboard/types';
import { HierarchyNode, PluginFilterHierarchyProps } from './types';

const Container = styled.div<{ horizontal: boolean }>`
  ${({ horizontal, theme }) => `
    display: flex;
    flex-direction: ${horizontal ? 'row' : 'column'};
    gap: ${theme.sizeUnit * 2}px;
    ${horizontal ? 'align-items: center;' : ''}
    width: 100%;
  `}
`;

const LevelWrapper = styled.div<{ horizontal: boolean }>`
  ${({ horizontal, theme }) => `
    ${horizontal ? `min-width: ${theme.sizeUnit * 40}px;` : 'width: 100%;'}
  `}
`;

const asString = (value: unknown): string =>
  value === undefined || value === null ? '' : String(value);

// Normalize the stored filterState into per-level selections (string[][]).
// Accepts the new shape (array of arrays) and the legacy single-path (string[]).
function normalizeSelections(value: unknown): string[][] {
  const arr = ensureIsArray(value);
  if (arr.length === 0) {
    return [];
  }
  if (Array.isArray(arr[0])) {
    return arr as string[][];
  }
  return (arr as string[]).map(key => [key]);
}

interface ColumnRoles {
  keyColumn?: string;
  parentColumn?: string;
  labelColumn?: string;
  levelColumn?: string;
  valueColumn?: string;
}

/** Build the normalized node list from rows, using the mapped role columns. */
function buildNodes(data: DataRecord[], cols: ColumnRoles): HierarchyNode[] {
  const { keyColumn, parentColumn, labelColumn, levelColumn, valueColumn } =
    cols;
  if (!keyColumn || !parentColumn) {
    return [];
  }
  const labelCol = labelColumn || keyColumn;
  const valueCol = valueColumn || keyColumn;
  return data.map(row => {
    const key = asString(row[keyColumn]);
    return {
      key,
      label: asString(row[labelCol]) || key,
      parent: asString(row[parentColumn]),
      value: asString(row[valueCol]),
      level:
        levelColumn && row[levelColumn] != null
          ? Number(row[levelColumn])
          : undefined,
    };
  });
}

export default function HierarchyFilterPlugin(
  props: PluginFilterHierarchyProps,
) {
  const {
    data,
    formData,
    filterState,
    setDataMask,
    setFocusedFilter,
    unsetFocusedFilter,
    filterBarOrientation,
    appSection,
  } = props;
  const {
    enableEmptyFilter,
    keyColumn,
    parentColumn,
    labelColumn,
    levelColumn,
    valueColumn,
    targetColumn,
  } = formData;
  const horizontal = filterBarOrientation === FilterBarOrientation.Horizontal;

  // The chart column to filter: explicit override, else the value column.
  const effectiveTargetColumn =
    (targetColumn && targetColumn.trim()) || valueColumn;

  const nodes = useMemo(
    () =>
      buildNodes(data, {
        keyColumn,
        parentColumn,
        labelColumn,
        levelColumn,
        valueColumn,
      }),
    [data, keyColumn, parentColumn, labelColumn, levelColumn, valueColumn],
  );

  const nodeByKey = useMemo(() => {
    const map = new Map<string, HierarchyNode>();
    nodes.forEach(n => map.set(n.key, n));
    return map;
  }, [nodes]);

  const childrenByParent = useMemo(() => {
    const map = new Map<string, HierarchyNode[]>();
    nodes.forEach(n => {
      const bucket = map.get(n.parent) ?? [];
      bucket.push(n);
      map.set(n.parent, bucket);
    });
    return map;
  }, [nodes]);

  // Root = a node whose parent is empty OR points to a key that doesn't exist
  // (covers parent_key = "" / null / 0 and any orphan marker).
  const roots = useMemo(
    () => nodes.filter(n => !n.parent || !nodeByKey.has(n.parent)),
    [nodes, nodeByKey],
  );

  // Selected keys per level (multi-select). selections[d] = keys chosen at
  // depth d; the next level shows the union of those nodes' children.
  const [selections, setSelections] = useState<string[][]>(() =>
    normalizeSelections(filterState?.value),
  );

  // Union of children of several parent keys (deduped), for the next level.
  const childrenOf = useCallback(
    (parentKeys: string[]) => {
      const seen = new Set<string>();
      const out: HierarchyNode[] = [];
      parentKeys.forEach(k =>
        (childrenByParent.get(k) ?? []).forEach(child => {
          if (!seen.has(child.key)) {
            seen.add(child.key);
            out.push(child);
          }
        }),
      );
      return out;
    },
    [childrenByParent],
  );

  // Restore the UI from an externally applied value (e.g. cross-filter clear).
  const lastExternal = useRef<string>('');
  useEffect(() => {
    const external = JSON.stringify(normalizeSelections(filterState?.value));
    if (external !== lastExternal.current) {
      lastExternal.current = external;
      setSelections(normalizeSelections(filterState?.value));
    }
  }, [filterState?.value]);

  // Values of a node plus every descendant (roll-up): selecting a parent
  // filters by the whole subtree, not just the parent's own value.
  const collectSubtreeValues = useCallback(
    (startKey: string) => {
      const values: string[] = [];
      const seen = new Set<string>();
      const stack = [startKey];
      while (stack.length) {
        const k = stack.pop() as string;
        if (seen.has(k)) {
          // eslint-disable-next-line no-continue
          continue;
        }
        seen.add(k);
        const node = nodeByKey.get(k);
        if (node && node.value !== '') {
          values.push(node.value);
        }
        (childrenByParent.get(k) ?? []).forEach(child => stack.push(child.key));
      }
      return Array.from(new Set(values));
    },
    [nodeByKey, childrenByParent],
  );

  const emit = useCallback(
    (nextSelections: string[][]) => {
      const selectedKeys = new Set<string>();
      nextSelections.forEach(level =>
        level.forEach(key => selectedKeys.add(key)),
      );

      // "Frontier" = selected nodes that have no selected descendant. These are
      // the most specific choices; each rolls up its whole subtree. So choosing
      // a parent (and stopping) filters by all its children/grandchildren.
      const hasSelectedDescendant = (key: string): boolean =>
        (childrenByParent.get(key) ?? []).some(
          child =>
            selectedKeys.has(child.key) || hasSelectedDescendant(child.key),
        );
      const frontier = [...selectedKeys].filter(
        key => !hasSelectedDescendant(key),
      );
      const values = Array.from(
        new Set(frontier.flatMap(key => collectSubtreeValues(key))),
      );
      const frontierNodes = frontier
        .map(key => nodeByKey.get(key))
        .filter((n): n is HierarchyNode => Boolean(n));

      let extraFormData: ExtraFormData = {};
      if (effectiveTargetColumn && values.length) {
        extraFormData = {
          filters: [
            { col: effectiveTargetColumn, op: 'IN' as const, val: values },
          ],
        };
      } else if (enableEmptyFilter && selectedKeys.size === 0) {
        extraFormData = {
          adhoc_filters: [
            {
              expressionType: ExpressionTypes.Sql,
              clause: Clauses.Where,
              sqlExpression: '1 = 0',
            },
          ],
        };
      }

      setDataMask({
        extraFormData,
        filterState: {
          value: selectedKeys.size ? nextSelections : null,
          label: frontierNodes.map(n => n.label).join(', '),
        },
      });
    },
    [
      childrenByParent,
      collectSubtreeValues,
      enableEmptyFilter,
      effectiveTargetColumn,
      nodeByKey,
      setDataMask,
    ],
  );

  const onLevelChange = useCallback(
    (depth: number, levelValues: string[]) => {
      // Changing a level invalidates deeper levels (their parents changed).
      const next = selections.slice(0, depth);
      next[depth] = levelValues;
      lastExternal.current = JSON.stringify(next);
      setSelections(next);
      emit(next);
    },
    [emit, selections],
  );

  // Visible levels: level 0 = roots; each deeper level = children of the nodes
  // selected above. A level shows only once the level above has a selection.
  const levels = useMemo(() => {
    const result: {
      depth: number;
      options: HierarchyNode[];
      values: string[];
    }[] = [];
    for (let depth = 0; depth < nodes.length + 1; depth += 1) {
      const options =
        depth === 0 ? roots : childrenOf(selections[depth - 1] ?? []);
      if (!options.length) break;
      const values = selections[depth] ?? [];
      result.push({ depth, options, values });
      if (!values.length) break; // nothing chosen here -> hide deeper levels
    }
    return result;
  }, [roots, childrenOf, nodes.length, selections]);

  if (!nodes.length) {
    // The full how-to lives in the control panel (always visible while
    // configuring); here we only show a short hint.
    return (
      <div>
        {appSection === AppSection.FilterConfigModal
          ? t('Map the six columns on the right to see the filter here.')
          : t('No hierarchy data. Check the filter configuration.')}
      </div>
    );
  }

  return (
    <Container
      horizontal={horizontal}
      onFocus={setFocusedFilter}
      onBlur={unsetFocusedFilter}
    >
      {levels.map(level => (
        <LevelWrapper key={level.depth} horizontal={horizontal}>
          <Select
            allowClear
            mode="multiple"
            ariaLabel={t('Level %s', level.depth + 1)}
            value={level.values}
            options={level.options.map(n => ({
              label: n.label,
              value: n.key,
            }))}
            onChange={val =>
              onLevelChange(level.depth, (val as string[]) ?? [])
            }
            onClear={() => onLevelChange(level.depth, [])}
            placeholder={t('Select…')}
          />
        </LevelWrapper>
      ))}
    </Container>
  );
}
