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

import { FC } from 'react';
import { styled, t } from '@superset-ui/core';
import { Flex, SafeMarkdown, Typography } from '@superset-ui/core/components';
import { ChatMessage as ChatMessageType, isChartArtifact } from '../types';
import SqlResultBlock from './SqlResultBlock';
import TableResultBlock from './TableResultBlock';

export interface ChatMessageProps {
  message: ChatMessageType;
}

const Row = styled.div<{ isUser: boolean }>`
  display: flex;
  justify-content: ${({ isUser }) => (isUser ? 'flex-end' : 'flex-start')};
`;

const Bubble = styled.div<{ isUser: boolean }>`
  max-width: 90%;
  padding: ${({ theme }) => theme.sizeUnit * 2}px
    ${({ theme }) => theme.sizeUnit * 3}px;
  border-radius: ${({ theme }) => theme.borderRadiusLG}px;
  background: ${({ theme, isUser }) =>
    isUser ? theme.colorPrimary : theme.colorBgContainer};
  color: ${({ theme, isUser }) =>
    isUser ? theme.colorTextLightSolid : theme.colorText};
  border: 1px solid
    ${({ theme, isUser }) =>
      isUser ? theme.colorPrimary : theme.colorBorderSecondary};
  word-break: break-word;
`;

const PlainText = styled.div`
  white-space: pre-wrap;
`;

/** Renders assistant markdown with tidy spacing inside the bubble. */
const Markdown = styled.div`
  font-size: ${({ theme }) => theme.fontSize}px;

  & > *:first-of-type {
    margin-top: 0;
  }
  & > *:last-child {
    margin-bottom: 0;
  }
  p {
    margin: 0 0 ${({ theme }) => theme.sizeUnit * 2}px;
  }
  ul,
  ol {
    margin: 0 0 ${({ theme }) => theme.sizeUnit * 2}px;
    padding-left: ${({ theme }) => theme.sizeUnit * 5}px;
  }
  code {
    background: ${({ theme }) => theme.colorFillSecondary};
    padding: 0 ${({ theme }) => theme.sizeUnit}px;
    border-radius: ${({ theme }) => theme.borderRadiusSM}px;
    font-size: ${({ theme }) => theme.fontSizeSM}px;
  }
  pre {
    overflow-x: auto;
  }
  a {
    color: ${({ theme }) => theme.colorPrimary};
  }
`;

/** One chat bubble: text (markdown for assistant) plus any artifacts. */
export const ChatMessage: FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  return (
    <Flex vertical gap={4} data-test="ai-chat-message">
      <Typography.Text
        type="secondary"
        style={{ fontSize: 11, alignSelf: isUser ? 'flex-end' : 'flex-start' }}
      >
        {isUser ? t('You') : t('Assistant')}
      </Typography.Text>
      <Row isUser={isUser}>
        <Bubble isUser={isUser}>
          {isUser ? (
            <PlainText>{message.text}</PlainText>
          ) : (
            <Markdown>
              <SafeMarkdown source={message.text} />
            </Markdown>
          )}
          {message.artifacts?.map((artifact, index) => (
            <Flex
              // eslint-disable-next-line react/no-array-index-key
              key={index}
              vertical
              gap="middle"
              style={{ marginTop: 12 }}
            >
              {isChartArtifact(artifact) ? (
                artifact.url && (
                  <Typography.Link href={artifact.url} target="_blank">
                    {t('Open: %s', artifact.chart_name ?? artifact.title ?? '')}
                  </Typography.Link>
                )
              ) : (
                <>
                  {artifact.executed_sql && (
                    <SqlResultBlock sql={artifact.executed_sql} />
                  )}
                  {(artifact.rows?.length ?? 0) > 0 && (
                    <TableResultBlock artifact={artifact} />
                  )}
                </>
              )}
            </Flex>
          ))}
        </Bubble>
      </Row>
    </Flex>
  );
};

export default ChatMessage;
