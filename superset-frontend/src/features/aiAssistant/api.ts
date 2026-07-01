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

import { getSidecarBaseUrl } from './config';
import { AskResponse, ConversationDetail, ConversationSummary } from './types';

/**
 * Extract the sidecar's `detail` message (falling back to the status).
 */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) {
      return body.detail;
    }
  } catch {
    // non-JSON body; fall through to the generic message
  }
  return `AI request failed (${response.status})`;
}

/**
 * Call the sidecar `POST /ask`. Credentials are included so that, behind a
 * same-origin reverse proxy, Superset's session cookie is forwarded and the
 * query runs as the current user (preserving RBAC/RLS).
 */
export async function askAi(
  question: string,
  conversationId?: string,
  signal?: AbortSignal,
): Promise<AskResponse> {
  const response = await fetch(`${getSidecarBaseUrl()}/ask`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      conversation_id: conversationId ?? null,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as AskResponse;
}

/** List the current user's saved conversations (most recent first). */
export async function listConversations(
  signal?: AbortSignal,
): Promise<ConversationSummary[]> {
  const response = await fetch(`${getSidecarBaseUrl()}/conversations`, {
    method: 'GET',
    credentials: 'include',
    signal,
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as ConversationSummary[];
}

/** Load a single conversation's messages so it can be reviewed and continued. */
export async function getConversation(
  conversationId: string,
  signal?: AbortSignal,
): Promise<ConversationDetail> {
  const response = await fetch(
    `${getSidecarBaseUrl()}/conversations/${encodeURIComponent(conversationId)}`,
    { method: 'GET', credentials: 'include', signal },
  );
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as ConversationDetail;
}
