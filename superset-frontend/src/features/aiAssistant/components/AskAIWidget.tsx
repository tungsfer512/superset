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
import { styled, t } from '@superset-ui/core';
import { Icons } from '@superset-ui/core/components/Icons';
import AskAIPanel from './AskAIPanel';

const Root = styled.div`
  position: fixed;
  right: ${({ theme }) => theme.sizeUnit * 6}px;
  bottom: ${({ theme }) => theme.sizeUnit * 6}px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: ${({ theme }) => theme.sizeUnit * 3}px;
`;

const Fab = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: ${({ theme }) => theme.sizeUnit * 14}px;
  height: ${({ theme }) => theme.sizeUnit * 14}px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: ${({ theme }) => theme.colorTextLightSolid};
  background: ${({ theme }) => theme.colorPrimary};
  box-shadow: ${({ theme }) => theme.boxShadowSecondary};
  font-size: ${({ theme }) => theme.fontSizeXL}px;
  transition:
    transform 0.15s ease,
    background 0.15s ease;

  &:hover {
    background: ${({ theme }) => theme.colorPrimaryHover};
    transform: scale(1.05);
  }
`;

/** Floating chat bubble (bottom-right) that toggles the Ask AI window. */
export const AskAIWidget: FC = () => {
  const [open, setOpen] = useState(false);
  return (
    <Root>
      {open && <AskAIPanel onClose={() => setOpen(false)} />}
      <Fab
        type="button"
        onClick={() => setOpen(prev => !prev)}
        aria-label={open ? t('Close') : t('Ask AI')}
        title={t('Ask AI')}
        data-test="ask-ai-fab"
      >
        {open ? <Icons.CloseOutlined /> : <Icons.CommentOutlined />}
      </Fab>
    </Root>
  );
};

export default AskAIWidget;
