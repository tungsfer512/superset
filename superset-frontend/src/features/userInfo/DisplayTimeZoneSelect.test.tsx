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

import fetchMock from 'fetch-mock';
import { render, screen, userEvent } from 'spec/helpers/testing-library';
import DisplayTimeZoneSelect from './DisplayTimeZoneSelect';

const TZ = 'Asia/Ho_Chi_Minh';
const ENDPOINT = 'glob:*/api/v1/me/timezones/';

beforeEach(() => {
  fetchMock.get(ENDPOINT, {
    result: [
      { name: 'UTC', offset: '+00:00' },
      // an alias pair the browser and the server disagree about
      { name: TZ, offset: '+07:00' },
      { name: 'Asia/Bangkok', offset: '+07:00' },
    ],
  });
});

afterEach(() => {
  fetchMock.reset();
});

const open = async () => {
  await userEvent.click(screen.getByRole('combobox'));
};

test('shows the selected zone', async () => {
  render(<DisplayTimeZoneSelect value={TZ} />);
  expect(await screen.findByText(new RegExp(TZ))).toBeInTheDocument();
});

test('falls back to the instance default when no value is set', () => {
  render(<DisplayTimeZoneSelect />);
  expect(screen.getByText('Instance default')).toBeInTheDocument();
});

test('offers the zones the server accepts, not the browser list', async () => {
  render(<DisplayTimeZoneSelect value="" />);
  await open();

  // `Intl.supportedValuesOf` reports `Asia/Saigon` for this zone, which the
  // API would reject, so the option must come from the server verbatim
  expect(
    await screen.findByRole('option', { name: `${TZ} (UTC+07:00)` }),
  ).toBeInTheDocument();
  // zones sharing an offset stay distinct: the name reaches the SQL
  expect(
    await screen.findByRole('option', { name: 'Asia/Bangkok (UTC+07:00)' }),
  ).toBeInTheDocument();
});

test('reports the picked zone', async () => {
  const onChange = jest.fn();
  render(<DisplayTimeZoneSelect value="" onChange={onChange} />);
  await open();

  await userEvent.click(
    await screen.findByRole('option', { name: `${TZ} (UTC+07:00)` }),
  );

  expect(onChange).toHaveBeenCalledWith(TZ);
});

test('still renders the default option when the request fails', async () => {
  fetchMock.reset();
  fetchMock.get(ENDPOINT, 500);

  render(<DisplayTimeZoneSelect value="" />);
  await open();

  expect(
    await screen.findByRole('option', { name: 'Instance default' }),
  ).toBeInTheDocument();
});
