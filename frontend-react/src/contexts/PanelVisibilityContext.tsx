import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { COMMAND_PANEL_LINKS } from '../components/commandMenuLinks';
import { PanelVisibilityContext } from './panelVisibilityStore';

const STORAGE_KEY = 'jarvis.dashboard.visiblePanels.v1';

function defaultVisibility(): Record<string, boolean> {
  return Object.fromEntries(COMMAND_PANEL_LINKS.map(panel => [panel.id, true]));
}

function readStoredVisibility(): Record<string, boolean> {
  const defaults = defaultVisibility();
  if (typeof window === 'undefined') return defaults;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return Object.fromEntries(
      COMMAND_PANEL_LINKS.map(panel => [panel.id, typeof parsed[panel.id] === 'boolean' ? Boolean(parsed[panel.id]) : true]),
    );
  } catch {
    return defaults;
  }
}

export function PanelVisibilityProvider({ children }: { children: ReactNode }) {
  const [visiblePanels, setVisiblePanels] = useState<Record<string, boolean>>(() => readStoredVisibility());

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(visiblePanels));
    } catch {
      // Visibility preference persistence is best-effort only.
    }
  }, [visiblePanels]);

  const setPanelVisible = useCallback((panelId: string, visible: boolean) => {
    setVisiblePanels(current => ({ ...current, [panelId]: visible }));
  }, []);

  const isPanelVisible = useCallback((panelId: string) => visiblePanels[panelId] !== false, [visiblePanels]);
  const resetPanels = useCallback(() => setVisiblePanels(defaultVisibility()), []);

  const value = useMemo(() => ({ visiblePanels, isPanelVisible, setPanelVisible, resetPanels }), [visiblePanels, isPanelVisible, setPanelVisible, resetPanels]);

  return <PanelVisibilityContext.Provider value={value}>{children}</PanelVisibilityContext.Provider>;
}
