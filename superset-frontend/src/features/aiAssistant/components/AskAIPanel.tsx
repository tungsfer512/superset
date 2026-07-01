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

import { FC, useEffect, useRef, useState } from 'react';
import { styled, t } from '@superset-ui/core';
import { Button, Input, Typography } from '@superset-ui/core/components';
import { Icons } from '@superset-ui/core/components/Icons';
import { useAskAi } from '../hooks/useAskAi';
import ChatMessage from './ChatMessage';
import SuggestedPrompts from './SuggestedPrompts';

export interface AskAIPanelProps {
  onClose?: () => void;
}

const DEFAULT_PROMPTS = [
  t('Có những dataset nào tôi xem được?'),
  t('Đếm số dòng trong dataset đầu tiên.'),
  t('Vẽ biểu đồ cột từ một dataset và đưa link.'),
];

const Panel = styled.div`
  display: flex;
  flex-direction: column;
  width: 400px;
  max-width: calc(100vw - ${({ theme }) => theme.sizeUnit * 8}px);
  height: min(640px, 78vh);
  background: ${({ theme }) => theme.colorBgContainer};
  border: 1px solid ${({ theme }) => theme.colorBorderSecondary};
  border-radius: ${({ theme }) => theme.borderRadiusLG}px;
  box-shadow: ${({ theme }) => theme.boxShadowSecondary};
  overflow: hidden;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.sizeUnit * 2}px;
  padding: ${({ theme }) => theme.sizeUnit * 3}px;
  background: ${({ theme }) => theme.colorPrimary};
  color: ${({ theme }) => theme.colorTextLightSolid};
`;

const HeaderTitle = styled.div`
  flex: 1;
  font-weight: ${({ theme }) => theme.fontWeightStrong};
  font-size: ${({ theme }) => theme.fontSizeLG}px;
  line-height: 1.2;
`;

const Avatar = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: ${({ theme }) => theme.sizeUnit * 8}px;
  height: ${({ theme }) => theme.sizeUnit * 8}px;
  border-radius: 50%;
  background: ${({ theme }) => theme.colorPrimaryHover};
`;

const Body = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${({ theme }) => theme.sizeUnit * 4}px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.sizeUnit * 3}px;
  background: ${({ theme }) => theme.colorBgLayout};
`;

const Footer = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.sizeUnit * 2}px;
  padding: ${({ theme }) => theme.sizeUnit * 3}px;
  border-top: 1px solid ${({ theme }) => theme.colorBorderSecondary};
  background: ${({ theme }) => theme.colorBgContainer};
`;

const Typing = styled.div`
  align-self: flex-start;
  color: ${({ theme }) => theme.colorTextSecondary};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  font-style: italic;
`;

const iconButtonStyle = { color: 'inherit' } as const;

/** The chat window body: header, scrolling message list and input. */
export const AskAIPanel: FC<AskAIPanelProps> = ({ onClose }) => {
  const { messages, status, error, send, reset } = useAskAi();
  const [draft, setDraft] = useState('');
  const bodyRef = useRef<HTMLDivElement>(null);
  const isLoading = status === 'loading';

  useEffect(() => {
    // Auto-scroll to the latest message.
    const node = bodyRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages, isLoading]);

  const submit = () => {
    const question = draft.trim();
    if (!question || isLoading) {
      return;
    }
    setDraft('');
    send(question);
  };

  return (
    <Panel data-test="ask-ai-panel" role="dialog" aria-label={t('Ask AI')}>
      <Header>
        <Avatar>
          <Icons.CommentOutlined />
        </Avatar>
        <HeaderTitle>{t('Ask AI')}</HeaderTitle>
        <Button
          type="text"
          size="small"
          icon={<Icons.PlusOutlined style={iconButtonStyle} />}
          onClick={reset}
          aria-label={t('New chat')}
          title={t('New chat')}
          style={iconButtonStyle}
        />
        {onClose && (
          <Button
            type="text"
            size="small"
            icon={<Icons.CloseOutlined style={iconButtonStyle} />}
            onClick={onClose}
            aria-label={t('Close')}
            title={t('Close')}
            style={iconButtonStyle}
          />
        )}
      </Header>

      <Body ref={bodyRef}>
        {messages.length === 0 ? (
          <SuggestedPrompts prompts={DEFAULT_PROMPTS} onSelect={send} />
        ) : (
          messages.map(message => (
            <ChatMessage key={message.id} message={message} />
          ))
        )}
        {isLoading && <Typing>{t('Assistant is thinking…')}</Typing>}
        {error && (
          <Typography.Text type="danger" data-test="ai-error">
            {error}
          </Typography.Text>
        )}
      </Body>

      <Footer>
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
          icon={<Icons.ArrowRightOutlined />}
          aria-label={t('Send')}
        >
          {t('Send')}
        </Button>
      </Footer>
    </Panel>
  );
};

export default AskAIPanel;
