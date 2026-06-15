/**
 * usePanelState — persistent collapsed/expanded state per panel.
 *
 * D-2026-06-08-dash-1: collapses survive page reload via localStorage.
 * Replaces PanelHeader's local useState which lost state on refresh.
 *
 * Usage:
 *   const { collapsed, toggle, setCollapsed } = usePanelState("topology");
 *   <PanelHeader collapsible collapsed={collapsed} onToggle={toggle} />
 *
 * Storage key: "jarvis.dashboard.panel.<id>.collapsed"
 */
import { useCallback, useEffect, useState } from "react";

const NAMESPACE = "jarvis.dashboard.panel";
const STORAGE_KEY = (id: string) => `${NAMESPACE}.${id}.collapsed`;

function readPersisted(id: string, defaultValue: boolean): boolean {
  if (typeof window === "undefined") return defaultValue;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY(id));
    if (raw === null) return defaultValue;
    return raw === "1" || raw === "true";
  } catch {
    return defaultValue;
  }
}

function writePersisted(id: string, value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY(id), value ? "1" : "0");
  } catch {
    // localStorage might be disabled (Safari private mode etc.)
    // Silent fail — the in-memory state still works for the session.
  }
}

export interface PanelState {
  /** True when the panel body is hidden. */
  collapsed: boolean;
  /** Flip the state. */
  toggle: () => void;
  /** Set the state explicitly. */
  setCollapsed: (value: boolean) => void;
  /** True if this panel's state is persisted in localStorage. */
  persisted: boolean;
}

export function usePanelState(panelId: string, defaultCollapsed = false): PanelState {
  // Initialize from localStorage on first render (SSR-safe).
  const [collapsed, setCollapsedState] = useState<boolean>(() =>
    readPersisted(panelId, defaultCollapsed)
  );
  // Track whether we've read from localStorage yet (so we don't
  // write the default back on mount, which would clobber the saved
  // value if storage was modified between render and effect).
  const [persisted] = useState<boolean>(() =>
    typeof window !== "undefined"
  );

  useEffect(() => {
    writePersisted(panelId, collapsed);
  }, [panelId, collapsed]);

  const toggle = useCallback(() => {
    setCollapsedState((v) => !v);
  }, []);

  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value);
  }, []);

  return { collapsed, toggle, setCollapsed, persisted };
}
