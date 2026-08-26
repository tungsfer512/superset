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

import { useEffect, useMemo, useState } from 'react';
import { SupersetClient, t } from '@superset-ui/core';
import { Select } from '@superset-ui/core/components';

export const INSTANCE_DEFAULT = '';

interface TimeZone {
  name: string;
  offset: string;
}

export interface DisplayTimeZoneSelectProps {
  value?: string;
  onChange?: (value: string) => void;
}

/**
 * Picks the IANA timezone the user's temporal data is rendered in.
 *
 * The options come from `/api/v1/me/timezones/` rather than from the browser's
 * `Intl.supportedValuesOf('timeZone')`: the two disagree on which name in an
 * alias pair is canonical, so a browser-built list offers values the API
 * rejects (`Asia/Saigon` vs `Asia/Ho_Chi_Minh`). Zones sharing a UTC offset are
 * also kept distinct, unlike in `TimezoneSelector`, because the exact name is
 * what reaches the generated SQL.
 */
export default function DisplayTimeZoneSelect({
  value,
  onChange,
}: DisplayTimeZoneSelectProps) {
  const [zones, setZones] = useState<TimeZone[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let stale = false;
    SupersetClient.get({ endpoint: '/api/v1/me/timezones/' })
      .then(({ json }) => {
        if (!stale) {
          setZones(json.result);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!stale) {
          setLoading(false);
        }
      });
    return () => {
      stale = true;
    };
  }, []);

  const options = useMemo(
    () => [
      { label: t('Instance default'), value: INSTANCE_DEFAULT },
      ...zones.map(({ name, offset }) => ({
        label: `${name} (UTC${offset})`,
        value: name,
      })),
    ],
    [zones],
  );

  return (
    <Select
      ariaLabel={t('Display timezone')}
      options={options}
      value={value ?? INSTANCE_DEFAULT}
      onChange={selected =>
        onChange?.((selected as string) ?? INSTANCE_DEFAULT)
      }
      placeholder={t('Instance default')}
      loading={loading}
      showSearch
    />
  );
}
