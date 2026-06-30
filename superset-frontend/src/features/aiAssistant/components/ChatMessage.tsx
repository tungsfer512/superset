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
import { t } from '@superset-ui/core';
import { Card, Flex, Typography } from '@superset-ui/core/components';
import { ChatMessage as ChatMessageType } from '../types';
import SqlResultBlock from './SqlResultBlock';
import TableResultBlock from './TableResultBlock';

export interface ChatMessageProps {
  message: ChatMessageType;
}

/** One chat bubble: the text plus any SQL/table artifacts for assistant turns. */
export const ChatMessage: FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  return (
    <Flex
      vertical
      gap="small"
      style={{ alignItems: isUser ? 'flex-end' : 'flex-start' }}
      data-test="ai-chat-message"
    >
      <Typography.Text type="secondary">
        {isUser ? t('You') : t('Assistant')}
      </Typography.Text>
      <Card size="small" style={{ maxWidth: '100%' }}>
        <Typography.Paragraph
          style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}
        >
          {message.text}
        </Typography.Paragraph>
        {message.artifacts?.map((artifact, index) => (
          <Flex
            // eslint-disable-next-line react/no-array-index-key
            key={index}
            vertical
            gap="middle"
            style={{ marginTop: 12 }}
          >
            <SqlResultBlock sql={artifact.executed_sql} />
            {artifact.rows.length > 0 && (
              <TableResultBlock artifact={artifact} />
            )}
          </Flex>
        ))}
      </Card>
    </Flex>
  );
};

export default ChatMessage;
