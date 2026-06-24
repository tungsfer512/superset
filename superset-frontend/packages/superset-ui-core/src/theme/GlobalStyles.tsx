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
import { css, useTheme, Global } from '@emotion/react';

export const GlobalStyles = () => {
  const theme = useTheme();
  return (
    <Global
      key={`global-${theme.colorLink}`}
      styles={css`
        // SPA
        html,
        body,
        #app {
          height: 100%;
        }

        body {
          background-color: ${theme.colorBgBase};
          color: ${theme.colorText};
          -webkit-font-smoothing: antialiased;
          margin: 0;
          font-family: ${theme.fontFamily};
        }

        a {
          color: ${theme.colorLink};
        }

        h1,
        h2,
        h3,
        h4,
        h5,
        h6,
        strong,
        th {
          font-weight: ${theme.fontWeightStrong};
        }

        .echarts-tooltip[style*='visibility: hidden'] {
          display: none !important;
        }

        .no-wrap {
          white-space: nowrap;
        }

        .column-config-popover {
          & .ant-input-number {
            width: 100%;
          }
          && .btn-group svg {
            line-height: 0;
            top: 0;
          }
          & .btn-group > .btn {
            padding: 5px 10px 6px;
          }
        }

        // Overriding bootstrap styles
        #app {
          flex: 1 1 auto;
          position: relative;
          display: flex;
          flex-direction: column;
          height: 100%;
        }
        [role='button'] {
          cursor: pointer;
        }

        /* --- Brand polish (custom theme refinements) --- */
        ::selection {
          background: ${theme.colorPrimaryBg};
          color: ${theme.colorText};
        }

        * {
          scrollbar-width: thin;
          scrollbar-color: ${theme.colorBorder} transparent;
        }
        *::-webkit-scrollbar {
          width: 10px;
          height: 10px;
        }
        *::-webkit-scrollbar-track {
          background: transparent;
        }
        *::-webkit-scrollbar-thumb {
          background: ${theme.colorBorder};
          border-radius: 999px;
          border: 2px solid ${theme.colorBgContainer};
        }
        *::-webkit-scrollbar-thumb:hover {
          background: ${theme.colorPrimary};
        }

        a {
          transition: color 0.15s ease;
        }
        .ant-btn {
          transition:
            background-color 0.15s ease,
            border-color 0.15s ease,
            color 0.15s ease,
            box-shadow 0.15s ease;
        }

        :focus-visible {
          outline: 2px solid ${theme.colorPrimary};
          outline-offset: 2px;
        }

        /* ===== Structural polish (color-agnostic) ===== */
        /* Cards lift on hover */
        .ant-card {
          transition:
            box-shadow 0.2s ease,
            transform 0.2s ease,
            border-color 0.2s ease;
        }
        .ant-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 16px 36px -18px rgba(10, 32, 30, 0.32) !important;
        }

        /* Smoother, rounded tables */
        .ant-table-wrapper .ant-table {
          background: transparent;
          border-radius: 14px;
        }
        .ant-table-wrapper .ant-table-container {
          border: 1px solid ${theme.colorBorderSecondary};
          border-radius: 14px;
          overflow: hidden;
        }
        /* remove the vertical header divider for a cleaner look */
        .ant-table-thead > tr > th::before {
          width: 0 !important;
        }
        /* keep cells square so the rounded container clips them cleanly
           (cell radius larger than the container radius leaves a corner gap) */
        .ant-table-thead > tr > th,
        .ant-table-tbody > tr > td {
          border-radius: 0 !important;
        }
        .ant-table-thead > tr > th {
          border-bottom: 1px solid ${theme.colorBorderSecondary} !important;
          font-weight: 700;
        }
        .ant-table-tbody > tr > td {
          border-bottom: 1px solid ${theme.colorBorderSecondary} !important;
        }
        .ant-table-tbody > tr:last-child > td {
          border-bottom: none !important;
        }
        .ant-table-tbody > tr {
          transition: background 0.12s ease;
        }
        /* ag-grid (SQL Lab results) rounded */
        .ag-root-wrapper {
          border-radius: 12px !important;
          overflow: hidden;
        }

        /* Dropdowns / popovers: always solid background, rounded, elevated
           (prevents transparent menus where text shows through) */
        .ant-dropdown-menu,
        .ant-select-dropdown,
        .ant-cascader-dropdown .ant-cascader-menu,
        .ant-picker-dropdown .ant-picker-panel-container,
        .ant-menu-submenu-popup > .ant-menu,
        .ant-popover-inner {
          background-color: ${theme.colorBgElevated} !important;
          border-radius: 12px !important;
          box-shadow:
            0 6px 16px -6px rgba(10, 32, 30, 0.2),
            0 12px 32px -10px rgba(10, 32, 30, 0.24) !important;
          border: 1px solid ${theme.colorBorderSecondary};
        }
        .ant-dropdown-menu-item,
        .ant-dropdown-menu-submenu-title,
        .ant-select-item {
          border-radius: 8px !important;
        }
        /* never inherit the white navbar text inside popups */
        .ant-menu-submenu-popup .ant-menu-item,
        .ant-menu-submenu-popup .ant-menu-item a,
        .ant-menu-submenu-popup .ant-menu-item-group-title,
        .ant-dropdown-menu-item,
        .ant-dropdown-menu-item a {
          color: ${theme.colorText} !important;
        }

        /* Multi-select options: let the label shrink/ellipsis and keep the
           selected check pushed to the right with a gap (no overlap) */
        .ant-select-item {
          white-space: normal !important;
        }
        .ant-select-item-option {
          display: flex !important;
          align-items: flex-start !important;
        }
        .ant-select-item-option-content {
          flex: 1 1 auto !important;
          min-width: 0 !important;
          white-space: normal !important;
          overflow-wrap: anywhere !important;
          word-break: break-word !important;
          padding-right: 10px !important;
        }
        .ant-select-item-option-content .ant-space,
        .ant-select-item-option-content .ant-space-item {
          white-space: normal !important;
          min-width: 0 !important;
        }
        .ant-select-item-option-state {
          flex: 0 0 auto !important;
          margin-inline-start: auto !important;
          margin-top: 3px;
        }

      `}
    />
  );
};
