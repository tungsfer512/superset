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

import { useCallback, useRef, useState } from 'react';
import { askAi } from '../api';
import { AiStatus, ChatMessage } from '../types';

export interface UseAskAi {
  messages: ChatMessage[];
  status: AiStatus;
  error: string | null;
  send: (question: string) => Promise<void>;
  reset: () => void;
}

/** Local conversation state for the Ask AI panel (no global Redux needed). */
export function useAskAi(): UseAskAi {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<AiStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const conversationId = useRef<string | undefined>(undefined);
  const counter = useRef(0);

  const nextId = useCallback((role: string) => {
    counter.current += 1;
    return `${role}-${counter.current}`;
  }, []);

  const send = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || status === 'loading') {
        return;
      }
      setMessages(prev => [
        ...prev,
        { id: nextId('user'), role: 'user', text: trimmed },
      ]);
      setStatus('loading');
      setError(null);
      try {
        const response = await askAi(trimmed, conversationId.current);
        conversationId.current = response.conversation_id;
        setMessages(prev => [
          ...prev,
          {
            id: nextId('assistant'),
            role: 'assistant',
            text: response.answer,
            artifacts: response.artifacts,
          },
        ]);
        setStatus('idle');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setStatus('error');
      }
    },
    [nextId, status],
  );

  const reset = useCallback(() => {
    setMessages([]);
    setStatus('idle');
    setError(null);
    conversationId.current = undefined;
  }, []);

  return { messages, status, error, send, reset };
}
