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

import { useCallback, useEffect, useRef, useState } from 'react';
import { askAi, getConversation } from '../api';
import { AiStatus, ChatMessage } from '../types';

export interface UseAskAi {
  messages: ChatMessage[];
  status: AiStatus;
  error: string | null;
  send: (question: string) => Promise<void>;
  reset: () => void;
  /** Load a past conversation by id so it can be reviewed and continued. */
  openConversation: (conversationId: string) => Promise<void>;
}

const STORAGE_KEY = 'superset-ai-conversation';

interface StoredConversation {
  conversationId?: string;
  messages: ChatMessage[];
}

function loadStored(): StoredConversation {
  if (typeof window === 'undefined') {
    return { messages: [] };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw) as StoredConversation;
    }
  } catch {
    // ignore corrupt/unavailable storage
  }
  return { messages: [] };
}

/**
 * Local conversation state for the Ask AI panel. Persists the current
 * conversation to localStorage so it survives reloads (review recent chat).
 */
export function useAskAi(): UseAskAi {
  const initial = useRef<StoredConversation>(loadStored());
  const [messages, setMessages] = useState<ChatMessage[]>(
    initial.current.messages,
  );
  const [status, setStatus] = useState<AiStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const conversationId = useRef<string | undefined>(
    initial.current.conversationId,
  );
  const counter = useRef(initial.current.messages.length);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          conversationId: conversationId.current,
          messages,
        }),
      );
    } catch {
      // storage full/unavailable — non-fatal
    }
  }, [messages]);

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
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch {
        // ignore
      }
    }
  }, []);

  const openConversation = useCallback(
    async (id: string) => {
      setStatus('loading');
      setError(null);
      try {
        const detail = await getConversation(id);
        counter.current = 0;
        const loaded = detail.messages.map(message => ({
          id: nextId(message.role),
          role: message.role,
          text: message.text,
          artifacts: message.artifacts,
        }));
        conversationId.current = detail.id;
        setMessages(loaded);
        setStatus('idle');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setStatus('error');
      }
    },
    [nextId],
  );

  return { messages, status, error, send, reset, openConversation };
}
