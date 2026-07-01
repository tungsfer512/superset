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

import { FC, useEffect, useState } from 'react';
import { styled, t } from '@superset-ui/core';
import { Typography } from '@superset-ui/core/components';
import { Icons } from '@superset-ui/core/components/Icons';
import { listConversations } from '../api';
import { ConversationSummary } from '../types';

export interface ConversationHistoryProps {
  onSelect: (conversationId: string) => void;
}

const List = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.sizeUnit * 2}px;
`;

const Item = styled.button`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.sizeUnit * 2}px;
  width: 100%;
  text-align: left;
  padding: ${({ theme }) => theme.sizeUnit * 3}px;
  background: ${({ theme }) => theme.colorBgContainer};
  border: 1px solid ${({ theme }) => theme.colorBorderSecondary};
  border-radius: ${({ theme }) => theme.borderRadius}px;
  cursor: pointer;

  &:hover {
    border-color: ${({ theme }) => theme.colorPrimary};
    background: ${({ theme }) => theme.colorPrimaryBg};
  }
`;

const ItemBody = styled.div`
  flex: 1;
  min-width: 0;
`;

const Title = styled.div`
  font-weight: ${({ theme }) => theme.fontWeightStrong};
  color: ${({ theme }) => theme.colorText};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const Meta = styled.div`
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
`;

const Empty = styled.div`
  color: ${({ theme }) => theme.colorTextSecondary};
  text-align: center;
  padding: ${({ theme }) => theme.sizeUnit * 6}px 0;
`;

function formatWhen(seconds: number): string {
  try {
    return new Date(seconds * 1000).toLocaleString();
  } catch {
    return '';
  }
}

/** Lists the user's saved conversations; selecting one loads it for review. */
export const ConversationHistory: FC<ConversationHistoryProps> = ({
  onSelect,
}) => {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listConversations(controller.signal)
      .then(rows => {
        setItems(rows);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Unknown error');
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  if (loading) {
    return <Empty>{t('Loading history…')}</Empty>;
  }
  if (error) {
    return (
      <Typography.Text type="danger" data-test="ai-history-error">
        {error}
      </Typography.Text>
    );
  }
  if (items.length === 0) {
    return <Empty>{t('No saved conversations yet.')}</Empty>;
  }

  return (
    <List data-test="ai-history-list">
      {items.map(item => (
        <Item
          key={item.id}
          type="button"
          onClick={() => onSelect(item.id)}
          title={item.title ?? t('Chat')}
        >
          <Icons.CommentOutlined />
          <ItemBody>
            <Title>{item.title || t('Chat')}</Title>
            <Meta>
              {formatWhen(item.updated_at)} · {item.message_count}{' '}
              {t('messages')}
            </Meta>
          </ItemBody>
        </Item>
      ))}
    </List>
  );
};

export default ConversationHistory;
