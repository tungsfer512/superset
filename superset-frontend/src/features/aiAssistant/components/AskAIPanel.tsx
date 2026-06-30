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

import { FC, useState } from 'react';
import { t } from '@superset-ui/core';
import {
  Button,
  Drawer,
  Flex,
  Input,
  Typography,
} from '@superset-ui/core/components';
import { useAskAi } from '../hooks/useAskAi';
import ChatMessage from './ChatMessage';
import SuggestedPrompts from './SuggestedPrompts';

export interface AskAIPanelProps {
  open: boolean;
  onClose: () => void;
}

const DEFAULT_PROMPTS = [
  t('Có những dataset nào tôi xem được?'),
  t('Tổng số dòng trong dataset đầu tiên là bao nhiêu?'),
  t('Liệt kê 5 bản ghi mới nhất.'),
];

/** Slide-out chat panel that talks to the superset-ai sidecar. */
export const AskAIPanel: FC<AskAIPanelProps> = ({ open, onClose }) => {
  const { messages, status, error, send } = useAskAi();
  const [draft, setDraft] = useState('');
  const isLoading = status === 'loading';

  const submit = () => {
    const question = draft.trim();
    if (!question || isLoading) {
      return;
    }
    setDraft('');
    send(question);
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={t('Ask AI')}
      width={480}
      data-test="ask-ai-panel"
    >
      <Flex vertical gap="middle" style={{ height: '100%' }}>
        <Flex vertical gap="middle" style={{ flex: 1, overflowY: 'auto' }}>
          {messages.length === 0 ? (
            <SuggestedPrompts prompts={DEFAULT_PROMPTS} onSelect={send} />
          ) : (
            messages.map(message => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          {isLoading && (
            <Typography.Text type="secondary">
              {t('Assistant is thinking…')}
            </Typography.Text>
          )}
          {error && (
            <Typography.Text type="danger" data-test="ai-error">
              {error}
            </Typography.Text>
          )}
        </Flex>
        <Flex gap="small">
          <Input.TextArea
            value={draft}
            onChange={event => setDraft(event.target.value)}
            onPressEnter={event => {
              if (!event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder={t('Ask a question about your data…')}
            autoSize={{ minRows: 1, maxRows: 4 }}
            aria-label={t('Ask a question about your data…')}
            disabled={isLoading}
          />
          <Button
            type="primary"
            onClick={submit}
            loading={isLoading}
            disabled={!draft.trim()}
          >
            {t('Send')}
          </Button>
        </Flex>
      </Flex>
    </Drawer>
  );
};

export default AskAIPanel;
