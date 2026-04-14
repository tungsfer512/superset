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
import { useEffect, useReducer } from 'react';
import { LANGUAGE_PACK_LOADED_EVENT } from 'src/constants';

/**
 * Returns a monotonically increasing value that changes whenever the async
 * language pack finishes loading.  Drop it into `useMemo` / `useCallback`
 * dependency arrays so that translated strings (`t()`) are recomputed after
 * the Jed catalogue becomes available.
 *
 * @example
 *   const locale = useI18nReady();
 *   const columns = useMemo(() => [{ Header: t('Name') }], [locale]);
 */
export default function useI18nReady(): number {
  const [revision, bump] = useReducer((n: number) => n + 1, 0);

  useEffect(() => {
    window.addEventListener(LANGUAGE_PACK_LOADED_EVENT, bump);
    return () => window.removeEventListener(LANGUAGE_PACK_LOADED_EVENT, bump);
  }, []);

  return revision;
}
