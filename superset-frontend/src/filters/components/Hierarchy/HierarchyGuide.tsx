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
import { useState } from 'react';
import { styled, t } from '@superset-ui/core';
import { Button } from '@superset-ui/core/components';
import copyTextToClipboard from 'src/utils/copy';

const Guide = styled.div`
  ${({ theme }) => `
    font-size: ${theme.fontSizeSM}px;
    color: ${theme.colorText};
    line-height: 1.6;

    h4 {
      font-size: ${theme.fontSize}px;
      font-weight: ${theme.fontWeightStrong};
      margin: 0 0 ${theme.sizeUnit}px 0;
    }
    ol,
    ul {
      margin: ${theme.sizeUnit}px 0;
      padding-left: ${theme.sizeUnit * 5}px;
    }
    li {
      margin-bottom: ${theme.sizeUnit}px;
    }
    code {
      background: ${theme.colorBgLayout};
      padding: 0 ${theme.sizeUnit / 2}px;
      border-radius: ${theme.borderRadiusSM}px;
      font-family: ${theme.fontFamilyCode};
    }
    .section-title {
      font-weight: ${theme.fontWeightStrong};
      margin-top: ${theme.sizeUnit * 3}px;
    }
  `}
`;

const TableScroll = styled.div`
  overflow-x: auto;
  margin-top: ${({ theme }) => theme.sizeUnit * 2}px;
`;

const ExampleTable = styled.table`
  ${({ theme }) => `
    border-collapse: collapse;
    font-size: ${theme.fontSizeSM}px;
    th, td {
      border: 1px solid ${theme.colorBorderSecondary};
      padding: ${theme.sizeUnit / 2}px ${theme.sizeUnit * 2}px;
      text-align: left;
      white-space: nowrap;
    }
    th {
      background: ${theme.colorBgLayout};
      font-weight: ${theme.fontWeightStrong};
    }
  `}
`;

const ButtonRow = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.sizeUnit * 2}px;
  margin-top: ${({ theme }) => theme.sizeUnit * 3}px;
  flex-wrap: wrap;
`;

const EXAMPLE_HEADERS = ['level', 'node_key', 'node_label', 'parent_key'];

const EXAMPLE_ROWS = [
  ['0', '1479', 'Scots English', '0'],
  ['1', '1480', 'Khối Hội Sở', '1479'],
  ['1', '1481', 'Khối Trung Tâm', '1479'],
  ['2', '1485', 'Vùng 1', '1481'],
  ['3', '1486', 'Scots English Linh Đàm', '1485'],
];

// MySQL recursive CTE turning a self-referential table (id, name, parent_id)
// into the mapping. Register the result as a (virtual) dataset.
const SAMPLE_SQL = `WITH RECURSIVE tree AS (
  SELECT id, name, parent_id, 0 AS level
  FROM your_group_table
  WHERE parent_id = 0            -- gốc: sửa cho đúng cách bạn đánh dấu gốc
  UNION ALL
  SELECT c.id, c.name, c.parent_id, t.level + 1
  FROM your_group_table c
  JOIN tree t ON c.parent_id = t.id
)
SELECT
  level,
  id         AS node_key,      -- id: dựng cây (tránh trùng tên)
  name       AS node_label,    -- tên hiển thị
  parent_id  AS parent_key     -- id cha (0/NULL = gốc)
FROM tree
ORDER BY level, node_key;`;

const SAMPLE_CSV = `level,node_key,node_label,parent_key
0,1479,Scots English,0
1,1480,Khối Hội Sở,1479
1,1481,Khối Trung Tâm,1479
2,1485,Vùng 1,1481
3,1486,Scots English Linh Đàm,1485`;

/** Config-time guidance: how to build the mapping dataset for this filter. */
export default function HierarchyGuide() {
  const [copied, setCopied] = useState<'sql' | 'csv' | null>(null);

  const copy = (kind: 'sql' | 'csv') => {
    const text = kind === 'sql' ? SAMPLE_SQL : SAMPLE_CSV;
    copyTextToClipboard(() => Promise.resolve(text))
      .then(() => setCopied(kind))
      .catch(() => setCopied(null));
  };

  return (
    <Guide className="hierarchy-filter-guide">
      <h4>{t('How to set up the hierarchical filter')}</h4>
      <ol>
        <li>
          {t(
            'Create a mapping table/view with: an id (key) column, a parent-id ' +
              'column, a display-name column (and an optional level column). ' +
              'Column names are up to you. Use the buttons below to copy sample ' +
              'recursive SQL / CSV.',
          )}
        </li>
        <li>
          {t(
            'Go to Datasets → + Dataset and register that result as a dataset.',
          )}
        </li>
        <li>
          {t(
            'In this filter: pick that mapping dataset, then map the role ' +
              'columns on the right (id / parent id / label / level) and choose ' +
              '"Filter by (value column)".',
          )}
        </li>
        <li>
          {t(
            'Save. On the dashboard: pick a node at a parent level → child ' +
              'levels are generated automatically; charts are filtered by the ' +
              'selected node and all of its descendants.',
          )}
        </li>
      </ol>

      <div className="section-title">{t('Column roles')}</div>
      <ul>
        <li>
          {t(
            'Id (key) column: a unique id — used to build the tree, so ' +
              'duplicate labels never merge.',
          )}
        </li>
        <li>
          {t(
            'Parent id column: the parent node id; empty / 0 / an id matching ' +
              'nothing means a root node.',
          )}
        </li>
        <li>{t('Display column: the name shown to users.')}</li>
        <li>
          {t(
            'Filter by (value column): the column whose value becomes the ' +
              'filter condition, applied to the same-named column on the charts. ' +
              'If a chart names the column differently, fill "Chart column to ' +
              'filter" to override.',
          )}
        </li>
      </ul>

      <div className="section-title">{t('Example mapping table')}</div>
      <TableScroll>
        <ExampleTable>
          <thead>
            <tr>
              {EXAMPLE_HEADERS.map(h => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {EXAMPLE_ROWS.map((row, rowIndex) => (
              // eslint-disable-next-line react/no-array-index-key
              <tr key={rowIndex}>
                {row.map((cell, i) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <td key={i}>{cell || '—'}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </ExampleTable>
      </TableScroll>

      <ButtonRow>
        <Button
          buttonStyle="primary"
          buttonSize="small"
          onClick={() => copy('sql')}
        >
          {copied === 'sql' ? t('Copied SQL ✓') : t('Copy sample SQL')}
        </Button>
        <Button
          buttonStyle="secondary"
          buttonSize="small"
          onClick={() => copy('csv')}
        >
          {copied === 'csv' ? t('Copied CSV ✓') : t('Copy sample CSV')}
        </Button>
      </ButtonRow>
    </Guide>
  );
}
