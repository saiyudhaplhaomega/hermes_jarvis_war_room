import React, { createContext, useContext, useReducer, useCallback, useRef } from 'react';
import type { ChatMessage } from '../types/dashboard';
import { api } from '../api/client';

type State = {
  messages: ChatMessage[];
  mode: string;
  agent: string;
  modes: { slug: string; label: string; description: string; tier: number }[];
  sending: boolean;
  error: string | null;
  cost: string;
  tier: number;
  pendingExec: string | null;
};

type Action =
  | { type: 'SET_MODE'; payload: string }
  | { type: 'SET_AGENT'; payload: string }
  | { type: 'SET_MODES'; payload: State['modes'] }
  | { type: 'ADD_MSG'; payload: ChatMessage }
  | { type: 'UPDATE_MSG'; payload: { id: string; updates: Partial<ChatMessage> } }
  | { type: 'SET_SENDING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR' };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_MODE':
      return { ...state, mode: action.payload };
    case 'SET_AGENT':
      return { ...state, agent: action.payload };
    case 'SET_MODES':
      return { ...state, modes: action.payload };
    case 'ADD_MSG':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'UPDATE_MSG':
      return {
        ...state,
        messages: state.messages.map(m =>
          (m.id || m.ts) === action.payload.id ? { ...m, ...action.payload.updates } : m
        ),
      };
    case 'SET_SENDING':
      return { ...state, sending: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'CLEAR':
      return { ...state, messages: [], error: null };
    default:
      return state;
  }
}

const defaultModes = [
  { slug: 'standard', label: '⚒ Standard', description: 'General purpose', tier: 0 },
  { slug: 'grill', label: '🔥 Grill Mode', description: 'Challenge ideas', tier: 1 },
  { slug: 'council', label: '⚖ Council', description: 'Multi-agent review', tier: 2 },
  { slug: 'boss', label: '👁 Boss', description: 'Final approval', tier: 3 },
];

interface ChatCtx {
  state: State;
  setMode: (m: string) => void;
  setAgent: (a: string) => void;
  sendMessage: (msg: string, projectSlug?: string, agentSlug?: string) => Promise<void>;
  confirmExec: (msgId: string) => void;
  cancelExec: (msgId: string) => void;
  clear: () => void;
}

const Ctx = createContext<ChatCtx | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {
    messages: [],
    mode: 'standard',
    agent: 'jarvis',
    modes: defaultModes,
    sending: false,
    error: null,
    cost: '$0.00',
    tier: 0,
    pendingExec: null,
  });

  const nonceRef = useRef(0);

  const setMode = useCallback((m: string) => dispatch({ type: 'SET_MODE', payload: m }), []);
  const setAgent = useCallback((a: string) => dispatch({ type: 'SET_AGENT', payload: a || 'jarvis' }), []);

  const sendMessage = useCallback(async (msg: string, projectSlug?: string, agentSlug?: string) => {
    const selectedAgent = agentSlug || state.agent || 'jarvis';
    const id = `msg_${Date.now()}_${nonceRef.current++}`;
    const userMsg: ChatMessage = {
      id,
      role: 'user',
      content: msg,
      ts: Date.now(),
      mode: state.mode,
      tier: 0,
    };
    dispatch({ type: 'ADD_MSG', payload: userMsg });
    dispatch({ type: 'SET_SENDING', payload: true });

    try {
      const res = await api.chat(msg, state.mode, projectSlug, selectedAgent);
      const assistantMsg: ChatMessage = {
        id: `resp_${Date.now()}`,
        role: 'assistant',
        content: res.response || res.message || JSON.stringify(res) || 'No response',
        ts: Date.now(),
        agent: res.agent || selectedAgent,
        mode: res.mode || state.mode,
        tier: res.tier ?? 1,
        cost: res.cost,
        exec: res.exec,
      };
      dispatch({ type: 'ADD_MSG', payload: assistantMsg });
    } catch (e: any) {
      console.error('[ChatContext] chat error:', e);
      dispatch({ type: 'SET_ERROR', payload: e.message || 'Failed to send' });
    } finally {
      dispatch({ type: 'SET_SENDING', payload: false });
    }
  }, [state.mode, state.agent]);

  const confirmExec = useCallback((msgId: string) => {
    dispatch({ type: 'UPDATE_MSG', payload: { id: msgId, updates: { exec: 'confirmed' } } });
  }, []);

  const cancelExec = useCallback((msgId: string) => {
    dispatch({ type: 'UPDATE_MSG', payload: { id: msgId, updates: { exec: 'cancelled' } } });
  }, []);

  const clear = useCallback(() => dispatch({ type: 'CLEAR' }), []);

  return (
    <Ctx.Provider value={{ state, setMode, setAgent, sendMessage, confirmExec, cancelExec, clear }}>
      {children}
    </Ctx.Provider>
  );
}

export function useChat(): ChatCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useChat must be inside ChatProvider');
  return c;
}
