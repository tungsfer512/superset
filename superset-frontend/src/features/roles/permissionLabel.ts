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

import { t } from '@superset-ui/core';

/** FAB stores permission and view slugs with underscores; UI shows them as words. */
export function humanizeFabSlug(slug: string): string {
  return slug.replace(/_/g, ' ');
}

/**
 * Localized label for a permission + view pair (Roles list filters, role modals).
 * Uses full English phrase in gettext when present; otherwise translates action and resource separately.
 */
export function translatePermissionPairLabel(
  permissionName: string,
  viewMenuName: string,
): string {
  const permHuman = humanizeFabSlug(permissionName);
  const viewHuman = humanizeFabSlug(viewMenuName);

  if (permHuman === viewHuman) {
    const single = t(permHuman);
    return single !== permHuman ? single : permHuman;
  }

  const combinedEnglish = `${permHuman} ${viewHuman}`;
  const full = t(combinedEnglish);
  if (full !== combinedEnglish) {
    return full;
  }

  const pTr = t(permHuman);
  const vTr = t(viewHuman);
  if (pTr === permHuman && vTr === viewHuman) {
    return combinedEnglish;
  }
  return `${pTr} — ${vTr}`;
}
