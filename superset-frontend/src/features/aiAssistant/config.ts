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

/**
 * Base URL of the `superset-ai` sidecar — the panel always talks to the
 * sidecar, never to Superset core.
 *
 * Resolution order:
 *  1. `window.supersetAiBaseUrl` if set (e.g. `'/superset-ai'` when Superset is
 *     served behind a reverse proxy that routes that path to the sidecar —
 *     same-origin, so the session cookie flows automatically).
 *  2. Otherwise the sidecar on the same host at its dedicated port (default
 *     8800), e.g. `http://localhost:8800`. This is a cross-origin call, so the
 *     sidecar must allow the Superset origin (SUPERSET_AI_EXTRA_CORS_ORIGINS)
 *     and the request sends credentials.
 */
const DEFAULT_SIDECAR_PORT = '8800';

type WindowWithSidecar = Window & { supersetAiBaseUrl?: string };

export function getSidecarBaseUrl(): string {
  if (typeof window === 'undefined') {
    return `:${DEFAULT_SIDECAR_PORT}`;
  }
  const override = (window as WindowWithSidecar).supersetAiBaseUrl;
  if (override) {
    return override;
  }
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:${DEFAULT_SIDECAR_PORT}`;
}
