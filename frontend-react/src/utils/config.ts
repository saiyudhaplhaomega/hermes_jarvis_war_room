/**
 * Shared, dependency-free helpers used across the React contexts.
 *
 * Kept tiny on purpose: these are imported into context providers, hooks,
 * and tests, so any added dependency or behavior risks cascading regressions.
 */

/**
 * Extract a human-readable message from an unknown thrown value.
 *
 * React `catch (e: any)` anti-pattern leaks `any` types into context APIs.
 * `e.message` blows up if `e` is a string or a plain object. This helper
 * keeps the context error path a single string and narrows the catch
 * parameter to `unknown` at the call site.
 */
export function errorMessage(error: unknown, fallback = 'Unknown error'): string {
  if (error instanceof Error) return error.message || fallback;
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object' && 'message' in error) {
    const m = (error as { message?: unknown }).message;
    if (typeof m === 'string' && m.length > 0) return m;
  }
  try {
    return JSON.stringify(error);
  } catch {
    return fallback;
  }
}

/** Read a string from `window.__CONFIG__` (injected by `spa_server.py`). */
function readInjectedConfig(): RuntimeConfig | null {
  const w = (typeof window === 'undefined' ? null : (window as unknown as { __CONFIG__?: RuntimeConfig | undefined }));
  if (w && w.__CONFIG__ && typeof w.__CONFIG__.API_BASE === 'string') {
    return w.__CONFIG__;
  }
  return null;
}

export interface RuntimeConfig {
  API_BASE: string;
  TOKEN: string;
  WS_URL: string;
}

export function getConfig(): RuntimeConfig {
  const injected = readInjectedConfig();
  if (injected) return injected;
  const env = (typeof import.meta !== 'undefined' && (import.meta as { env?: Record<string, string> }).env) || {};
  return {
    API_BASE: env.VITE_API_BASE || 'http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1',
    TOKEN: env.VITE_TOKEN || '',
    WS_URL: env.VITE_WS_URL || 'ws://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/ws',
  };
}

export const CONFIG: RuntimeConfig = getConfig();
