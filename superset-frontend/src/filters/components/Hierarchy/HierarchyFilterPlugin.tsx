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

  // The currently selected key at each depth (a path from the root).
  const [path, setPath] = useState<string[]>(
    () => (ensureIsArray(filterState?.value) as string[]) ?? [],
  );

  // Restore the UI from an externally applied value (e.g. cross-filter clear).
  const lastExternal = useRef<string>('');
  useEffect(() => {
    const external = JSON.stringify(ensureIsArray(filterState?.value) ?? []);
    if (external !== lastExternal.current) {
      lastExternal.current = external;
      setPath((ensureIsArray(filterState?.value) as string[]) ?? []);
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
    (nextPath: string[]) => {
      const selectedNodes = nextPath
        .map(key => nodeByKey.get(key))
        .filter((n): n is HierarchyNode => Boolean(n));

      // Filter by the deepest selected node AND all of its descendants
      // (so choosing a parent rolls up every child underneath it).
      const deepest = selectedNodes[selectedNodes.length - 1];
      const values = deepest ? collectSubtreeValues(deepest.key) : [];

      let extraFormData: ExtraFormData = {};
      if (deepest && effectiveTargetColumn && values.length) {
        extraFormData = {
          filters: [
            {
              col: effectiveTargetColumn,
              op: 'IN' as const,
              val: values,
            },
          ],
        };
      } else if (enableEmptyFilter && !selectedNodes.length) {
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
          value: selectedNodes.length ? nextPath : null,
          label: selectedNodes.map(n => n.label).join(' > '),
        },
      });
    },
    [
      collectSubtreeValues,
      enableEmptyFilter,
      effectiveTargetColumn,
      nodeByKey,
      setDataMask,
    ],
  );

  const onLevelChange = useCallback(
    (depth: number, value?: string) => {
      const nextPath = path.slice(0, depth);
      if (value !== undefined) {
        nextPath[depth] = value;
      }
      lastExternal.current = JSON.stringify(nextPath);
      setPath(nextPath);
      emit(nextPath);
    },
    [emit, path],
  );

  // Compute the visible levels: show a level only once its parent is chosen.
  const levels = useMemo(() => {
    const result: {
      depth: number;
      options: HierarchyNode[];
      value?: string;
    }[] = [];
    for (let depth = 0; depth < nodes.length + 1; depth += 1) {
      const options =
        depth === 0 ? roots : (childrenByParent.get(path[depth - 1]) ?? []);
      if (!options.length) break;
      const value = path[depth];
      result.push({ depth, options, value });
      if (value === undefined) break; // no selection yet -> hide deeper levels
    }
    return result;
  }, [roots, childrenByParent, nodes.length, path]);

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
            ariaLabel={t('Level %s', level.depth + 1)}
            value={level.value}
            options={level.options.map(n => ({
              label: n.label,
              value: n.key,
            }))}
            onChange={val => onLevelChange(level.depth, val as string)}
            onClear={() => onLevelChange(level.depth, undefined)}
            placeholder={t('Select…')}
          />
        </LevelWrapper>
      ))}
    </Container>
  );
}
