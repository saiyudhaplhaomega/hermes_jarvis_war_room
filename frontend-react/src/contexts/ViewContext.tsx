import React, { createContext, useContext, useState } from 'react';

interface ViewCtx {
  view: 'chat' | 'dashboard';
  setView: (v: 'chat' | 'dashboard') => void;
}

const Ctx = createContext<ViewCtx | null>(null);

export function ViewProvider({ children }: { children: React.ReactNode }) {
  const [view, setView] = useState<'chat' | 'dashboard'>('chat');
  return <Ctx.Provider value={{ view, setView }}>{children}</Ctx.Provider>;
}

export function useView(): ViewCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useView must be inside ViewProvider');
  return c;
}
