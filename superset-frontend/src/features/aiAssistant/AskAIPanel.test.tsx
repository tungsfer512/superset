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
import {
  askAi,
  getConversation,
  getSuggestions,
  listConversations,
} from './api';
import { AskResponse } from './types';

jest.mock('./api');

const mockedAskAi = askAi as jest.MockedFunction<typeof askAi>;
const mockedList = listConversations as jest.MockedFunction<
  typeof listConversations
>;
const mockedGet = getConversation as jest.MockedFunction<
  typeof getConversation
>;
const mockedSuggestions = getSuggestions as jest.MockedFunction<
  typeof getSuggestions
>;

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
  mockedList.mockReset();
  mockedGet.mockReset();
  mockedSuggestions.mockReset();
  window.localStorage.clear();
  // Defaults: no history -> fresh chat; suggestions fall back to local defaults.
  mockedList.mockResolvedValue([]);
  mockedSuggestions.mockResolvedValue({ suggestions: [], generated: false });
});

test('shows suggested prompts when empty', async () => {
  render(<AskAIPanel onClose={jest.fn()} />);
  expect(await screen.findByText('Gợi ý câu hỏi')).toBeInTheDocument();
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

  await userEvent.click(
    await screen.findByText('Có những dataset nào tôi xem được?'),
  );

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

test('resumes the last conversation on open without fetching suggestions', async () => {
  mockedList.mockResolvedValue([
    { id: 'c1', title: 'Cũ', updated_at: 1, message_count: 2 },
  ]);
  mockedGet.mockResolvedValue({
    id: 'c1',
    messages: [{ role: 'assistant', text: 'Trả lời cũ' }],
  });
  mockedSuggestions.mockResolvedValue({
    suggestions: ['Doanh thu theo quý?', 'Top sản phẩm bán chạy?'],
    generated: true,
  });
  render(<AskAIPanel onClose={jest.fn()} />);

  // The last session is restored automatically...
  expect(await screen.findByText('Trả lời cũ')).toBeInTheDocument();
  // ...and no (paid) suggestions call was made on open.
  expect(mockedSuggestions).not.toHaveBeenCalled();

  // Only "New chat" fetches history-based suggestions.
  await userEvent.click(screen.getByRole('button', { name: 'New chat' }));
  expect(await screen.findByText('Doanh thu theo quý?')).toBeInTheDocument();
  expect(mockedSuggestions).toHaveBeenCalledTimes(1);
});

test('opens history and loads a past conversation', async () => {
  mockedList.mockResolvedValue([
    { id: 'c1', title: 'Doanh thu 2024', updated_at: 1, message_count: 2 },
  ]);
  mockedGet.mockResolvedValue({
    id: 'c1',
    messages: [
      { role: 'user', text: 'Xem doanh thu' },
      { role: 'assistant', text: 'Tổng doanh thu là 1 tỷ.' },
    ],
  });
  render(<AskAIPanel onClose={jest.fn()} />);

  await userEvent.click(screen.getByRole('button', { name: 'History' }));
  const entry = await screen.findByText('Doanh thu 2024');
  await userEvent.click(entry);

  expect(
    await screen.findByText('Tổng doanh thu là 1 tỷ.'),
  ).toBeInTheDocument();
  // Continuing the loaded conversation sends its id back to the API.
  mockedAskAi.mockResolvedValue(buildResponse('Còn tăng trưởng 10%.'));
  await userEvent.type(
    screen.getByLabelText('Ask a question about your data…'),
    'Tăng trưởng?',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Send' }));
  await waitFor(() =>
    expect(mockedAskAi).toHaveBeenCalledWith('Tăng trưởng?', 'c1'),
  );
});
