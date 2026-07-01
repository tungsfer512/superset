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

import {
  render,
  screen,
  userEvent,
  waitFor,
} from 'spec/helpers/testing-library';
import AskAIPanel from './components/AskAIPanel';
import { askAi } from './api';
import { AskResponse } from './types';

jest.mock('./api');

const mockedAskAi = askAi as jest.MockedFunction<typeof askAi>;

const buildResponse = (answer: string): AskResponse => ({
  answer,
  conversation_id: 'conv-1',
  artifacts: [
    {
      executed_sql: 'SELECT COUNT(*) FROM orders LIMIT 1000',
      columns: [{ name: 'n' }],
      rows: [{ n: 1 }],
      row_count: 1,
    },
  ],
  tool_trace: [{ name: 'run_select_sql' }],
});

beforeEach(() => {
  mockedAskAi.mockReset();
  window.localStorage.clear();
});

test('shows suggested prompts when empty', () => {
  render(<AskAIPanel onClose={jest.fn()} />);
  expect(screen.getByText('Gợi ý câu hỏi')).toBeInTheDocument();
});

test('sends a question and renders the answer with SQL', async () => {
  mockedAskAi.mockResolvedValue(buildResponse('Có 1 đơn hàng.'));
  render(<AskAIPanel onClose={jest.fn()} />);

  await userEvent.type(
    screen.getByLabelText('Ask a question about your data…'),
    'Có bao nhiêu đơn hàng?',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Send' }));

  expect(await screen.findByText('Có 1 đơn hàng.')).toBeInTheDocument();
  expect(
    screen.getByText('SELECT COUNT(*) FROM orders LIMIT 1000'),
  ).toBeInTheDocument();
  expect(mockedAskAi).toHaveBeenCalledWith('Có bao nhiêu đơn hàng?', undefined);
});

test('clicking a suggested prompt triggers a request', async () => {
  mockedAskAi.mockResolvedValue(buildResponse('Đây là kết quả.'));
  render(<AskAIPanel onClose={jest.fn()} />);

  await userEvent.click(screen.getByText('Có những dataset nào tôi xem được?'));

  await waitFor(() => expect(mockedAskAi).toHaveBeenCalledTimes(1));
  expect(await screen.findByText('Đây là kết quả.')).toBeInTheDocument();
});

test('shows an error message when the request fails', async () => {
  mockedAskAi.mockRejectedValue(new Error('AI request failed (503)'));
  render(<AskAIPanel onClose={jest.fn()} />);

  await userEvent.type(
    screen.getByLabelText('Ask a question about your data…'),
    'hi',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Send' }));

  expect(
    await screen.findByText('AI request failed (503)'),
  ).toBeInTheDocument();
});
