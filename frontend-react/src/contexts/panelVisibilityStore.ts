import { createContext, useContext } from 'react';

export type PanelVisibilityContextValue = {
  visiblePanels: Record<string, boolean>;
  isPanelVisible: (panelId: string) => boolean;
  setPanelVisible: (panelId: string, visible: boolean) => void;
  resetPanels: () => void;
};

export const PanelVisibilityContext = createContext<PanelVisibilityContextValue | null>(null);

export function usePanelVisibility() {
  const value = useContext(PanelVisibilityContext);
  if (!value) throw new Error('usePanelVisibility must be used inside PanelVisibilityProvider');
  return value;
}
