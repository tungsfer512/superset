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

export interface SuggestedPromptsProps {
  prompts: string[];
  onSelect: (prompt: string) => void;
}

const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.sizeUnit * 3}px;
`;

const Greeting = styled.div`
  padding: ${({ theme }) => theme.sizeUnit * 2}px 0;
  color: ${({ theme }) => theme.colorText};
  font-size: ${({ theme }) => theme.fontSizeLG}px;
  font-weight: ${({ theme }) => theme.fontWeightStrong};
`;

const Hint = styled.div`
  color: ${({ theme }) => theme.colorTextSecondary};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  margin-bottom: ${({ theme }) => theme.sizeUnit}px;
`;

const PromptCard = styled.button`
  display: flex;
  align-items: center;
  width: 100%;
  text-align: left;
  padding: ${({ theme }) => theme.sizeUnit * 3}px
    ${({ theme }) => theme.sizeUnit * 4}px;
  border: 1px solid ${({ theme }) => theme.colorBorder};
  border-radius: ${({ theme }) => theme.borderRadiusLG}px;
  background: ${({ theme }) => theme.colorBgContainer};
  color: ${({ theme }) => theme.colorText};
  font-size: ${({ theme }) => theme.fontSize}px;
  line-height: 1.4;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;

  &:hover {
    border-color: ${({ theme }) => theme.colorPrimary};
    background: ${({ theme }) => theme.colorPrimaryBg};
  }
`;

/** Friendly empty-state with clickable starter questions. */
export const SuggestedPrompts: FC<SuggestedPromptsProps> = ({
  prompts,
  onSelect,
}) => (
  <Wrap>
    <Greeting>{t('👋 Xin chào! Tôi có thể giúp gì cho bạn?')}</Greeting>
    <Hint>{t('Gợi ý câu hỏi')}</Hint>
    {prompts.map(prompt => (
      <PromptCard key={prompt} type="button" onClick={() => onSelect(prompt)}>
        {prompt}
      </PromptCard>
    ))}
  </Wrap>
);

export default SuggestedPrompts;
