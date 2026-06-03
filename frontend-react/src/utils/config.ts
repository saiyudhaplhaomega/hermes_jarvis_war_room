export interface RuntimeConfig {
  API_BASE: string;
  TOKEN: string;
  WS_URL: string;
}

function getConfig(): RuntimeConfig {
  // spa_server.py can inject window.__CONFIG__ before the bundle
  const injected = (window as any).__CONFIG__;
  if (injected) return injected;
  // Fallback: read from meta tags or env (dev only)
  return {
    API_BASE: import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1',
    TOKEN: import.meta.env.VITE_TOKEN || '',
    WS_URL: import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/ws',
  };
}

export const CONFIG = getConfig();
