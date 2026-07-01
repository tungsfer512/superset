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
import { t } from '@superset-ui/core';
import { Flex, Typography } from '@superset-ui/core/components';
import { Table, TableSize } from '@superset-ui/core/components/Table';
import { SqlArtifact } from '../types';

export interface TableResultBlockProps {
  artifact: SqlArtifact;
  maxRows?: number;
}

const renderCell = (value: unknown): string =>
  value === null || value === undefined ? '' : String(value);

/** Renders the rows returned by a query as a compact, scrollable table. */
export const TableResultBlock: FC<TableResultBlockProps> = ({
  artifact,
  maxRows = 50,
}) => {
  const columns = (artifact.columns ?? []).map(col => ({
    title: col.name,
    dataIndex: col.name,
    key: col.name,
    render: (value: unknown) => renderCell(value),
  }));

  const data = (artifact.rows ?? []).slice(0, maxRows).map((row, index) => ({
    key: index,
    ...row,
  }));

  return (
    <Flex vertical gap="small">
      <Typography.Text type="secondary">
        {t('%s row(s)', artifact.row_count)}
      </Typography.Text>
      <Table
        size={TableSize.Small}
        columns={columns}
        data={data}
        pagination={false}
      />
    </Flex>
  );
};

export default TableResultBlock;
