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
import {
  AppSection,
  Behavior,
  ChartDataResponseResult,
  ChartProps,
  DataRecord,
  FilterState,
  QueryFormData,
} from '@superset-ui/core';
import { RefObject } from 'react';
import { FilterBarOrientation } from 'src/dashboard/types';
import { PluginFilterHooks, PluginFilterStylesProps } from '../types';

/**
 * Column ROLES are mapped to real columns of the chosen mapping dataset (the
 * names are dynamic, not hard-coded), and the "value column" doubles as the
 * chart column to filter — unless a `targetColumn` override is provided.
 */
export interface PluginFilterHierarchyCustomizeProps {
  keyColumn?: string; // id column — builds the tree (unique per node)
  parentColumn?: string; // parent id column — links child → parent
  labelColumn?: string; // display column
  levelColumn?: string; // optional numeric depth
  valueColumn?: string; // column whose value is emitted (default filter target)
  targetColumn?: string; // optional override: chart column name to filter
  enableEmptyFilter?: boolean;
  defaultValue?: string[] | null;
}

// Conventional names auto-detected when the user hasn't picked a column yet.
export const DEFAULT_COLUMN_GUESS = {
  key: ['node_key', 'id', 'group_id'],
  parent: ['parent_key', 'parent_id', 'parent'],
  label: ['node_label', 'name', 'label', 'group_name'],
  level: ['level', 'depth'],
};

export type PluginFilterHierarchyQueryFormData = QueryFormData &
  PluginFilterStylesProps &
  PluginFilterHierarchyCustomizeProps;

export interface PluginFilterHierarchyChartProps extends ChartProps {
  queriesData: ChartDataResponseResult[];
}

/** One node of the hierarchy, normalized from a mapping-table row. */
export interface HierarchyNode {
  key: string;
  label: string;
  parent: string;
  value: string; // value emitted when this node is selected
  level?: number;
}

export type PluginFilterHierarchyProps = PluginFilterStylesProps & {
  data: DataRecord[];
  behaviors: Behavior[];
  appSection: AppSection;
  formData: PluginFilterHierarchyQueryFormData;
  filterState: FilterState;
  isRefreshing: boolean;
  inputRef?: RefObject<any>;
  filterBarOrientation?: FilterBarOrientation;
  isOverflowingFilterBar?: boolean;
  clearAllTrigger?: Record<string, boolean>;
  onClearAllComplete?: (filterId: string) => void;
} & PluginFilterHooks;

export const DEFAULT_FORM_DATA: PluginFilterHierarchyCustomizeProps = {
  enableEmptyFilter: false,
  defaultValue: null,
};
