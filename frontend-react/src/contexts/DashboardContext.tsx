import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import type { DashboardCache } from '../types/dashboard';
import { api } from '../api/client';
import { errorMessage } from '../utils/config';

interface DashboardCtx {
  cache: DashboardCache | null;
  loading: boolean;
  error: string | null;
  refresh: (project?: string) => Promise<void>;
}

const Ctx = createContext<DashboardCtx | null>(null);

// D-2026-06-09 (post-sprint cleanup): export the context object so
// tests can mount providers in arbitrary compositions (e.g.
// `<DashboardContext.Provider value={...}>`). Matches the pattern
// already used by KanbanContext.tsx and ProjectContext.tsx.
export const DashboardContext = Ctx;

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [cache, setCache] = useState<DashboardCache | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastProjectRef = useRef<string | undefined>(undefined);

  const refresh = useCallback(async (project?: string) => {
    if (project) lastProjectRef.current = project;
    const scopedProject = project || lastProjectRef.current;
    setLoading(true);
    try {
      const res = await api.cache(scopedProject);
      setCache(prev => {
        // Merge: prefer newer cache, keep existing if server returns stale
        if (!prev) return res;
        const prevTime = new Date(prev.generated_at).getTime();
        const newTime = new Date(res.generated_at).getTime();
        return newTime >= prevTime ? res : prev;
      });
      setError(null);
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll every 5s
  useEffect(() => {
    const id = setInterval(() => refresh(), 5000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <Ctx.Provider value={{ cache, loading, error, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useDashboard() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useDashboard must be inside DashboardProvider');
  return ctx;
}
