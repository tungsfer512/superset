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
  CSSProperties,
  FC,
  MouseEvent as ReactMouseEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
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

const SIZE_KEY = 'superset-ai-panel-size';
const MIN_W = 320;
const MIN_H = 380;
const DEFAULT_SIZE = { width: 400, height: 640 };

const Panel = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.colorBgContainer};
  border: 1px solid ${({ theme }) => theme.colorBorderSecondary};
  border-radius: ${({ theme }) => theme.borderRadiusLG}px;
  box-shadow: ${({ theme }) => theme.boxShadowSecondary};
  overflow: hidden;
`;

const ResizeHandle = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  width: ${({ theme }) => theme.sizeUnit * 4}px;
  height: ${({ theme }) => theme.sizeUnit * 4}px;
  cursor: nwse-resize;
  z-index: 2;
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

const clamp = (value: number, min: number, max: number) =>
  Math.max(min, Math.min(max, value));

function loadSize(): { width: number; height: number } {
  if (typeof window === 'undefined') {
    return DEFAULT_SIZE;
  }
  try {
    const raw = window.localStorage.getItem(SIZE_KEY);
    if (raw) {
      return JSON.parse(raw) as { width: number; height: number };
    }
  } catch {
    // ignore
  }
  return DEFAULT_SIZE;
}

/** The chat window body: resizable/fullscreen, header, message list and input. */
export const AskAIPanel: FC<AskAIPanelProps> = ({ onClose }) => {
  const { messages, status, error, send, reset } = useAskAi();
  const [draft, setDraft] = useState('');
  const [fullscreen, setFullscreen] = useState(false);
  const [size, setSize] = useState(loadSize);
  const bodyRef = useRef<HTMLDivElement>(null);
  const isLoading = status === 'loading';

  useEffect(() => {
    const node = bodyRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    try {
      window.localStorage.setItem(SIZE_KEY, JSON.stringify(size));
    } catch {
      // ignore
    }
  }, [size]);

  const startResize = useCallback(
    (event: ReactMouseEvent) => {
      event.preventDefault();
      const startX = event.clientX;
      const startY = event.clientY;
      const startW = size.width;
      const startH = size.height;
      const onMove = (moveEvent: MouseEvent) => {
        // Anchored bottom-right: dragging up-left grows the window.
        setSize({
          width: clamp(
            startW + (startX - moveEvent.clientX),
            MIN_W,
            window.innerWidth - 40,
          ),
          height: clamp(
            startH + (startY - moveEvent.clientY),
            MIN_H,
            window.innerHeight - 40,
          ),
        });
      };
      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    },
    [size],
  );

  const submit = () => {
    const question = draft.trim();
    if (!question || isLoading) {
      return;
    }
    setDraft('');
    send(question);
  };

  const panelStyle: CSSProperties = fullscreen
    ? {
        position: 'fixed',
        inset: 16,
        width: 'auto',
        height: 'auto',
        zIndex: 1001,
      }
    : {
        width: size.width,
        height: Math.min(size.height, window.innerHeight - 40),
      };

  return (
    <Panel
      data-test="ask-ai-panel"
      role="dialog"
      aria-label={t('Ask AI')}
      style={panelStyle}
    >
      {!fullscreen && (
        <ResizeHandle
          onMouseDown={startResize}
          data-test="ask-ai-resize"
          aria-hidden
        />
      )}
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
        <Button
          type="text"
          size="small"
          icon={
            fullscreen ? (
              <Icons.CompressOutlined style={iconButtonStyle} />
            ) : (
              <Icons.ExpandOutlined style={iconButtonStyle} />
            )
          }
          onClick={() => setFullscreen(prev => !prev)}
          aria-label={fullscreen ? t('Exit fullscreen') : t('Fullscreen')}
          title={fullscreen ? t('Exit fullscreen') : t('Fullscreen')}
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
