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
import { t } from '../translation';
import { sanitizeHtml } from './html';

const TRUNCATION_STYLE = `
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export function tooltipHtml(
  data: string[][],
  title?: string,
  focusedRow?: number,
  /**
   * Indices of rows that head a section rather than carrying a series. They are
   * rendered at full weight and opacity so the grouping reads as a hierarchy.
   */
  headerRows?: number[],
) {
  const headers = new Set(headerRows);
  const titleRow = title
    ? `<span style="font-weight: 700;${TRUNCATION_STYLE}">${title}</span>`
    : '';
  return sanitizeHtml(`
    <div>
      ${titleRow}
      <table>
          ${data.length === 0 ? `<tr><td>${t('No data')}</td></tr>` : ''}
          ${data
            .map((row, i) => {
              const rowStyle =
                i === focusedRow || headers.has(i)
                  ? 'font-weight: 700;'
                  : 'opacity: 0.8;';
              const cells = row.map((cell, j) => {
                const cellStyle = `
                  text-align: ${j > 0 ? 'right' : 'left'};
                  padding-left: ${j === 0 ? 0 : 16}px;
                  ${TRUNCATION_STYLE}
                `;
                return `<td style="${cellStyle}">${cell}</td>`;
              });
              return `<tr style="${rowStyle}">${cells.join('')}</tr>`;
            })
            .join('')}
      </table>
    </div>`);
}
