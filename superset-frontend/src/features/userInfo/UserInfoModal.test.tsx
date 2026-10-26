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
import { UserInfoEditModal } from './UserInfoModal';

const user = {
  firstName: 'Ada',
  lastName: 'Lovelace',
  username: 'ada',
  isActive: true,
  isAnonymous: false,
};

beforeEach(() => {
  fetchMock.get('glob:*/api/v1/me/timezones/', {
    result: [{ name: 'Asia/Ho_Chi_Minh', offset: '+07:00' }],
  });
});

afterEach(() => {
  fetchMock.reset();
});

test('opens the timezone popup outside the scrolling modal body', async () => {
  render(
    <UserInfoEditModal
      show
      onHide={jest.fn()}
      onSave={jest.fn()}
      user={user}
    />,
    { useRedux: true },
  );

  await userEvent.click(
    screen.getByRole('combobox', { name: /Display timezone/ }),
  );
  const option = await screen.findByRole('option', {
    name: 'Asia/Ho_Chi_Minh (UTC+07:00)',
  });

  // inside the body it is clipped when it flips above this last field
  expect(option.closest('.ant-modal-body')).toBeNull();
  expect(option.closest('.ant-modal-content')).not.toBeNull();
});

test('starts on the default when the user has no preference', () => {
  render(
    <UserInfoEditModal
      show
      onHide={jest.fn()}
      onSave={jest.fn()}
      user={user}
    />,
    { useRedux: true },
  );

  expect(screen.getByText('Default (no conversion)')).toBeInTheDocument();
});
