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
      <h4>{t('Hướng dẫn cấu hình bộ lọc phân cấp')}</h4>
      <ol>
        <li>
          {t(
            'Tạo bảng/khung nhìn "mapping" gồm: 1 cột id (khóa), 1 cột id cha, ' +
              '1 cột tên hiển thị (và cột level tùy chọn). Tên cột tùy ý. ' +
              'Bấm nút bên dưới để lấy SQL đệ quy / CSV mẫu.',
          )}
        </li>
        <li>
          {t('Vào Datasets → + Dataset, đăng ký kết quả đó thành một dataset.')}
        </li>
        <li>
          {t(
            'Ở bộ lọc này: chọn dataset mapping đó, rồi ở panel bên phải gán ' +
              'các cột theo vai trò (id / id cha / hiển thị / level) và chọn ' +
              '"Lọc theo (cột giá trị)".',
          )}
        </li>
        <li>
          {t(
            'Lưu lại. Trên dashboard: chọn một node ở cấp cha → hệ thống tự sinh ' +
              'cấp con; biểu đồ được lọc theo node sâu nhất bạn đã chọn.',
          )}
        </li>
      </ol>

      <div className="section-title">{t('Vai trò các cột')}</div>
      <ul>
        <li>
          {t(
            'Cột id (khóa): id duy nhất — dùng để dựng cây (tránh gộp nhầm ' +
              'node trùng tên).',
          )}
        </li>
        <li>
          {t(
            'Cột id cha: id của node cha; để trống / 0 / không khớp id nào = ' +
              'node gốc.',
          )}
        </li>
        <li>{t('Cột hiển thị: tên hiện cho người dùng.')}</li>
        <li>
          {t(
            'Lọc theo (cột giá trị): chọn cột nào thì lấy giá trị cột đó làm ' +
              'điều kiện lọc, VÀ lọc trên cột cùng tên bên biểu đồ. Nếu biểu ' +
              'đồ đặt tên cột khác, điền "Cột lọc trên biểu đồ" để ghi đè.',
          )}
        </li>
      </ul>

      <div className="section-title">{t('Ví dụ bảng mapping')}</div>
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
          {copied === 'sql' ? t('Đã sao chép SQL ✓') : t('Sao chép SQL mẫu')}
        </Button>
        <Button
          buttonStyle="secondary"
          buttonSize="small"
          onClick={() => copy('csv')}
        >
          {copied === 'csv' ? t('Đã sao chép CSV ✓') : t('Sao chép CSV mẫu')}
        </Button>
      </ButtonRow>
    </Guide>
  );
}
