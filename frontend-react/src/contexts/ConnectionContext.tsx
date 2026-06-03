import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { CONFIG } from '../utils/config';

interface ConnCtx {
  status: 'connecting' | 'open' | 'closed' | 'polling';
  ws: WebSocket | null;
  send: (msg: any) => void;
}

const Ctx = createContext<ConnCtx | null>(null);

export function ConnectionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<ConnCtx['status']>('connecting');
  const [ws, setWs] = useState<WebSocket | null>(null);

  const connect = useCallback(() => {
    const socket = new WebSocket(CONFIG.WS_URL);
    socket.onopen = () => setStatus('open');
    socket.onclose = () => {
      setStatus('polling');
      setTimeout(connect, 3000);
    };
    socket.onerror = () => setStatus('closed');
    setWs(socket);
  }, []);

  useEffect(() => { connect(); }, [connect]);

  const send = useCallback((msg: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
  }, [ws]);

  return (
    <Ctx.Provider value={{ status, ws, send }}>
      {children}
    </Ctx.Provider>
  );
}

export function useConnection() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useConnection must be inside ConnectionProvider');
  return ctx;
}
