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

export interface SqlColumn {
  name: string;
}

export interface SqlArtifact {
  executed_sql: string;
  columns: SqlColumn[];
  rows: Record<string, unknown>[];
  row_count: number;
}

export interface ChartArtifact {
  chart_id?: number | null;
  chart_name?: string;
  // Dashboards reuse this shape (title instead of chart_name).
  title?: string;
  url: string | null;
}

export type Artifact = SqlArtifact | ChartArtifact;

export function isChartArtifact(artifact: Artifact): artifact is ChartArtifact {
  return 'url' in artifact;
}

export interface ToolTraceEntry {
  name: string;
}

/** Response shape from the sidecar `POST /ask` endpoint. */
export interface AskResponse {
  answer: string;
  conversation_id: string;
  artifacts: Artifact[];
  tool_trace: ToolTraceEntry[];
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
  artifacts?: Artifact[];
}

export type AiStatus = 'idle' | 'loading' | 'error';

/** A row in the conversation history list (`GET /conversations`). */
export interface ConversationSummary {
  id: string;
  title: string | null;
  updated_at: number;
  message_count: number;
}

/** A stored message as returned by `GET /conversations/{id}`. */
export interface StoredMessage {
  role: ChatRole;
  text: string;
  artifacts?: Artifact[];
}

/** Full conversation detail (`GET /conversations/{id}`). */
export interface ConversationDetail {
  id: string;
  messages: StoredMessage[];
}

/** Suggested prompts for the empty chat state (`GET /suggestions`). */
export interface SuggestionsResponse {
  suggestions: string[];
  /** True when inferred from history by the LLM (vs history-derived/default). */
  generated: boolean;
}
