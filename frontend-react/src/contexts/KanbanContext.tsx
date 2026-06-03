import React, { createContext, useContext, useReducer, useCallback } from 'react';
import type { KanbanCard } from '../types/dashboard';
import { api } from '../api/client';

type State = {
  cards: KanbanCard[];
  loading: boolean;
  error: string | null;
};

type Action =
  | { type: 'SET'; cards: KanbanCard[] }
  | { type: 'UPDATE_CARD'; id: string; patch: Partial<KanbanCard> }
  | { type: 'LOADING' }
  | { type: 'ERROR'; msg: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET': return { ...state, cards: action.cards, loading: false, error: null };
    case 'UPDATE_CARD':
      return { ...state, cards: state.cards.map(c => c.id === action.id ? { ...c, ...action.patch } : c) };
    case 'LOADING': return { ...state, loading: true };
    case 'ERROR': return { ...state, error: action.msg, loading: false };
    default: return state;
  }
}

interface KanbanCtx {
  state: State;
  refresh: (project?: string) => Promise<void>;
  heartbeat: (taskId: string, progress: string) => Promise<void>;
  block: (taskId: string, reason?: string) => Promise<void>;
  unblock: (taskId: string) => Promise<void>;
  complete: (taskId: string) => Promise<void>;
}

const Ctx = createContext<KanbanCtx | null>(null);

export function KanbanProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { cards: [], loading: false, error: null });

  const refresh = useCallback(async (project?: string) => {
    dispatch({ type: 'LOADING' });
    try {
      const res = await api.kanban(project);
      dispatch({ type: 'SET', cards: res.tasks || [] });
    } catch (e: any) {
      dispatch({ type: 'ERROR', msg: e.message });
    }
  }, []);

  const heartbeat = useCallback(async (taskId: string, progress: string) => {
    try {
      await api.heartbeat(taskId, progress);
      dispatch({ type: 'UPDATE_CARD', id: taskId, patch: { last_heartbeat_at: new Date().toISOString() } });
    } catch (e: any) {
      dispatch({ type: 'ERROR', msg: e.message });
    }
  }, []);

  const block = useCallback(async (taskId: string, reason?: string) => {
    try {
      await api.blockTask(taskId, reason);
      dispatch({ type: 'UPDATE_CARD', id: taskId, patch: { status: 'blocked' } });
    } catch (e: any) {
      dispatch({ type: 'ERROR', msg: e.message });
    }
  }, []);

  const unblock = useCallback(async (taskId: string) => {
    try {
      await api.unblockTask(taskId);
      dispatch({ type: 'UPDATE_CARD', id: taskId, patch: { status: 'ready' } });
    } catch (e: any) {
      dispatch({ type: 'ERROR', msg: e.message });
    }
  }, []);

  const complete = useCallback(async (taskId: string) => {
    try {
      await api.completeTask(taskId);
      dispatch({ type: 'UPDATE_CARD', id: taskId, patch: { status: 'done' } });
    } catch (e: any) {
      dispatch({ type: 'ERROR', msg: e.message });
    }
  }, []);

  return (
    <Ctx.Provider value={{ state, refresh, heartbeat, block, unblock, complete }}>
      {children}
    </Ctx.Provider>
  );
}

export function useKanban() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useKanban must be inside KanbanProvider');
  return ctx;
}
