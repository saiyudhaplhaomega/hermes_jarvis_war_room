import { useCallback, useEffect, useRef, useState } from 'react';
import { CommandMenu } from './CommandMenu';
import { COMMAND_PANEL_LINKS, type DashboardViewName } from './commandMenuLinks';
import { useDashboard } from '../contexts/DashboardContext';
import { useView } from '../contexts/ViewContext';
import { useProject } from '../contexts/ProjectContext';

function clockText(date: Date): string {
  return date.toLocaleTimeString('en-GB', { hour12: false });
}

export function DashboardHeader() {
  const { cache } = useDashboard();
  const { view, setView } = useView();
  const { project } = useProject();
  const metrics = cache?.metrics || {};
  const [now, setNow] = useState(() => new Date());
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);

  const scrollToPanel = useCallback((panelId: string) => {
    const panelIds = new Set(COMMAND_PANEL_LINKS.map((panel) => panel.id));
    if (!panelIds.has(panelId)) return;

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        const target = document.getElementById(panelId);
        if (!target) return;
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
        window.history.replaceState(null, '', `#${panelId}`);
      });
    });
  }, []);

  const handleNavigate = useCallback((nextView: DashboardViewName, panelId?: string) => {
    setView(nextView);
    if (panelId) {
      scrollToPanel(panelId);
    }
  }, [scrollToPanel, setView]);

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <header className="premium-nav">
      <div className="flex items-center gap-3 min-w-0">
        <div className="brand-orb"><span /></div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight">Hermes</h1>
            <span className="mono text-[10px] text-gray-400 tracking-[0.25em]">/ JARVIS WAR ROOM</span>
            <span className="version-badge">v1.3</span>
          </div>
          <div className="mono text-[10px] text-gray-500 truncate">{project ? `PROJECT ${project.slug}` : 'NO PROJECT SELECTED'} · PROFILE-SAFE CONTROL PLANE</div>
        </div>
      </div>
      <div className="nav-pill">
        <button
          onClick={() => setView('chat')}
          className={view === 'chat' ? 'active' : ''}
        >
          Chat
        </button>
        <button
          onClick={() => setView('dashboard')}
          className={view === 'dashboard' ? 'active' : ''}
        >
          Dashboard
        </button>
      </div>
      <div className="flex items-center gap-3 text-xs mono">
        <span className="status-pill"><span className="status-dot" /> Backend linked</span>
        <span className="hidden md:inline text-gray-500">Tokens: {metrics.tokens ?? 0}</span>
        <span className="hidden md:inline text-gray-500">Cost: ${(metrics.cost ?? 0).toFixed(2)}</span>
        <span className="clock-pill">{clockText(now)}</span>
        <button
          ref={menuButtonRef}
          type="button"
          className={`hamburger-btn ${menuOpen ? 'open' : ''}`}
          aria-label={menuOpen ? 'Close dashboard command menu' : 'Open dashboard command menu'}
          aria-expanded={menuOpen}
          aria-controls="dashboard-command-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>
      </div>
      <CommandMenu
        open={menuOpen}
        currentView={view}
        onClose={() => setMenuOpen(false)}
        onNavigate={handleNavigate}
        returnFocusRef={menuButtonRef}
      />
    </header>
  );
}
