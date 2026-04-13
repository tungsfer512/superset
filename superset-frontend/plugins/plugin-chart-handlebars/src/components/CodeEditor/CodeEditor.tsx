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
import AceEditor, { IAceEditorProps } from 'react-ace';

import { config as aceConfig } from 'ace-builds';

// must go after AceEditor import
import 'ace-builds/src-min-noconflict/mode-handlebars';
import 'ace-builds/src-min-noconflict/mode-css';
import 'ace-builds/src-noconflict/theme-github';
import 'ace-builds/src-noconflict/theme-monokai';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const cssWorkerUrl = require('ace-builds/src-min-noconflict/worker-css');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const htmlWorkerUrl = require('ace-builds/src-min-noconflict/worker-html');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const javascriptWorkerUrl = require('ace-builds/src-min-noconflict/worker-javascript');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const jsonWorkerUrl = require('ace-builds/src-min-noconflict/worker-json');

const resolveWorkerUrl = (workerModule: unknown): string => {
  if (typeof workerModule === 'string') return workerModule;
  if (
    workerModule &&
    typeof workerModule === 'object' &&
    'default' in workerModule
  ) {
    const maybeDefault = (workerModule as { default?: unknown }).default;
    if (typeof maybeDefault === 'string') return maybeDefault;
  }
  return '';
};

export type CodeEditorMode = 'handlebars' | 'css';
export type CodeEditorTheme = 'light' | 'dark';

export interface CodeEditorProps extends IAceEditorProps {
  mode?: CodeEditorMode;
  theme?: CodeEditorTheme;
  name?: string;
}

export const CodeEditor: FC<CodeEditorProps> = ({
  mode,
  theme,
  name,
  width,
  height,
  value,
  ...rest
}: CodeEditorProps) => {
  // Ensure web workers resolve correctly under webpack-dev-server.
  // Without this, Ace can attempt to import a non-string URL (e.g. "[object Object]"),
  // causing runtime failures in Explore on routes like /explore/...
  aceConfig.setModuleUrl('ace/mode/css_worker', resolveWorkerUrl(cssWorkerUrl));
  aceConfig.setModuleUrl(
    'ace/mode/html_worker',
    resolveWorkerUrl(htmlWorkerUrl),
  );
  aceConfig.setModuleUrl(
    'ace/mode/javascript_worker',
    resolveWorkerUrl(javascriptWorkerUrl),
  );
  aceConfig.setModuleUrl(
    'ace/mode/json_worker',
    resolveWorkerUrl(jsonWorkerUrl),
  );

  const m_name = name || Math.random().toString(36).substring(7);
  const m_theme = theme === 'light' ? 'github' : 'monokai';
  const m_mode = mode || 'handlebars';
  const m_height = height || '300px';
  const m_width = width || '100%';

  return (
    <div className="code-editor" style={{ minHeight: height, width: m_width }}>
      <AceEditor
        mode={m_mode}
        theme={m_theme}
        name={m_name}
        height={m_height}
        width={m_width}
        fontSize={14}
        showPrintMargin
        focus
        editorProps={{ $blockScrolling: true }}
        wrapEnabled
        highlightActiveLine
        value={value}
        setOptions={{
          enableBasicAutocompletion: true,
          enableLiveAutocompletion: true,
          enableSnippets: true,
          showLineNumbers: true,
          tabSize: 2,
          showGutter: true,
          useWorker: false,
        }}
        {...rest}
      />
    </div>
  );
};
