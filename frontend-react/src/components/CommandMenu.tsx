import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';
import { COMMAND_PANEL_LINKS, type DashboardViewName } from './commandMenuLinks';
import { usePanelVisibility } from '../contexts/panelVisibilityStore';

interface CommandMenuProps {
  open: boolean;
  currentView: DashboardViewName;
  onClose: () => void;
  onNavigate: (view: DashboardViewName, panelId?: string) => void;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
}

function focusableElements(root: HTMLElement): HTMLElement[] {
  return Array.from(
    root.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => !el.hasAttribute('aria-hidden'));
}

export function CommandMenu({ open, currentView, onClose, onNavigate, returnFocusRef }: CommandMenuProps) {
  const drawerRef = useRef<HTMLElement | null>(null);
  const { visiblePanels, setPanelVisible, resetPanels } = usePanelVisibility();

  useEffect(() => {
    if (!open) return;

    const previousActive = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const timer = window.setTimeout(() => {
      const first = drawerRef.current ? focusableElements(drawerRef.current)[0] : null;
      first?.focus();
    }, 0);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        returnFocusRef.current?.focus();
        return;
      }

      if (event.key !== 'Tab' || !drawerRef.current) return;
      const nodes = focusableElements(drawerRef.current);
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('keydown', onKeyDown);
      if (previousActive && document.body.contains(previousActive)) {
        previousActive.focus();
      }
    };
  }, [open, onClose, returnFocusRef]);

  const navigate = (view: DashboardViewName, panelId?: string) => {
    onNavigate(view, panelId);
    onClose();
    returnFocusRef.current?.focus();
  };

  return (
    <>
      <div
        className={`command-menu-backdrop ${open ? 'open' : ''}`}
        aria-hidden="true"
        onClick={() => {
          onClose();
          returnFocusRef.current?.focus();
        }}
      />
      <aside
        id="dashboard-command-menu"
        ref={drawerRef}
        className={`command-menu-drawer ${open ? 'open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Dashboard command menu"
        aria-hidden={!open}
      >
        <div className="command-menu-header">
          <div>
            <p className="command-menu-kicker">Command Menu</p>
            <h2>Navigate War Room</h2>
          </div>
          <button className="command-menu-close" type="button" onClick={onClose} aria-label="Close command menu">
            ×
          </button>
        </div>

        <section className="command-menu-section" aria-label="Views">
          <p className="command-menu-section-title">Views</p>
          <div className="command-menu-toggle">
            <button type="button" className={currentView === 'chat' ? 'active' : ''} onClick={() => navigate('chat')}>
              Chat
            </button>
            <button type="button" className={currentView === 'dashboard' ? 'active' : ''} onClick={() => navigate('dashboard')}>
              Dashboard
            </button>
          </div>
        </section>

        <section className="command-menu-section" aria-label="Visible panels">
          <div className="flex items-center justify-between gap-2">
            <p className="command-menu-section-title">Visible Panels</p>
            <button type="button" className="command-menu-mini-button" onClick={resetPanels}>Show all</button>
          </div>
          <div className="command-menu-checkbox-list">
            {COMMAND_PANEL_LINKS.map((panel) => (
              <label key={`visible:${panel.id}`} className="command-menu-checkbox-row">
                <input
                  type="checkbox"
                  checked={visiblePanels[panel.id] !== false}
                  onChange={event => setPanelVisible(panel.id, event.target.checked)}
                />
                <span className="panel-icon" aria-hidden="true">{panel.icon}</span>
                <span className="panel-copy">
                  <strong>{panel.label}</strong>
                  <small>{visiblePanels[panel.id] === false ? 'Hidden from dashboard' : 'Visible on dashboard'}</small>
                </span>
              </label>
            ))}
          </div>
        </section>

        <section className="command-menu-section" aria-label="Dashboard panels">
          <p className="command-menu-section-title">Jump to Panel</p>
          <div className="command-menu-panel-list" role="menu">
            {COMMAND_PANEL_LINKS.map((panel) => (
              <button
                key={panel.id}
                type="button"
                className="command-menu-panel-link"
                role="menuitem"
                onClick={() => navigate('dashboard', panel.id)}
              >
                <span className="panel-icon" aria-hidden="true">{panel.icon}</span>
                <span className="panel-copy">
                  <strong>{panel.label}</strong>
                  <small>{panel.description}</small>
                </span>
              </button>
            ))}
          </div>
        </section>
      </aside>
    </>
  );
}
