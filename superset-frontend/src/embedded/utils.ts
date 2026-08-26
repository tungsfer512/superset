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

import { DataMaskStateWithId } from '@superset-ui/core';
import { isEmpty, isEqual } from 'lodash';
import { NATIVE_FILTER_PREFIX } from 'src/dashboard/components/nativeFilters/FiltersConfigModal/utils';

/**
 * The header carrying the viewer's time zone on every API call this page makes.
 *
 * The zone arrives as a `?timezone=` URL parameter on the embedded page, the
 * same way `lang` does, and is validated server side before being echoed back
 * in the bootstrap config. The API calls made from here carry no URL parameters
 * of their own, so it travels on as a header and the backend converts temporal
 * columns to that zone in SQL. An absent or rejected value yields no header,
 * leaving the instance default in place.
 */
export const getDisplayTimeZoneHeaders = (
  config: {
    DISPLAY_TIME_ZONE?: string;
    DISPLAY_TIME_ZONE_HEADER_NAME?: string;
  } = {},
): Record<string, string> => {
  const {
    DISPLAY_TIME_ZONE: timezone,
    DISPLAY_TIME_ZONE_HEADER_NAME: headerName,
  } = config;
  return timezone && headerName ? { [headerName]: timezone } : {};
};

export const getDataMaskChangeTrigger = (
  dataMask: DataMaskStateWithId,
  previousDataMask: DataMaskStateWithId,
) => {
  let crossFiltersChanged = false;
  let nativeFiltersChanged = false;

  if (!isEmpty(dataMask) && !isEmpty(previousDataMask)) {
    for (const key in dataMask) {
      if (
        key.startsWith(NATIVE_FILTER_PREFIX) &&
        !isEqual(dataMask[key], previousDataMask[key])
      ) {
        nativeFiltersChanged = true;
        break;
      } else if (!isEqual(dataMask[key], previousDataMask[key])) {
        crossFiltersChanged = true;
        break;
      }
    }
  }
  return { crossFiltersChanged, nativeFiltersChanged };
};
