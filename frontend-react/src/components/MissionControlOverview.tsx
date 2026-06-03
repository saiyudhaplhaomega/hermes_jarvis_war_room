import { useMemo } from 'react';
import { useDashboard } from '../contexts/DashboardContext';
import { useProject } from '../contexts/ProjectContext';

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

export function MissionControlOverview() {
  const { cache, error } = useDashboard();
  const { project } = useProject();
  const agents = cache?.agents || [];
  const decisions = cache?.decisions || [];
  const memory = cache?.memory || {};
  const projectCards = useMemo(() => {
    if (!cache || !project) return [];
    return cache.kanban_by_project?.[project.slug] || [];
  }, [cache, project]);
  const runningAgents = agents.filter(agent => ['online', 'active', 'running'].includes((agent.status || '').toLowerCase())).length;
  const blockedCards = projectCards.filter(card => card.status === 'blocked' || card.blocked_by_parents).length;
  const activeProject = project?.slug || 'no-project-selected';

  return (
    <section className="premium-hero xl:col-span-4 lg:col-span-3 md:col-span-2">
      <div className="hero-orb hero-orb-violet" />
      <div className="hero-orb hero-orb-cyan" />
      <div className="relative z-10 grid grid-cols-1 xl:grid-cols-[1.1fr_1fr_1fr] gap-5">
        <div>
          <div className="mono text-[11px] text-emerald-300 tracking-[0.35em] uppercase flex items-center gap-2">
            <span className="status-dot" /> Uplink synced
          </div>
          <h2 className="text-4xl lg:text-5xl font-semibold tracking-tight mt-3">Jarvis Mission Control</h2>
          <p className="text-gray-400 mt-3 max-w-xl">
            Premium command deck for the Company OS: chat, project-scoped kanban, memory, decisions, council, Discord, and dynamic role/model overlays.
          </p>
          <div className="mt-5 flex flex-wrap gap-2 mono text-[11px] uppercase tracking-widest">
            <span className="pill-cyan">Project: {activeProject}</span>
            <span className="pill-violet">React War Room</span>
            <span className="pill-mint">Profiles read-only</span>
          </div>
        </div>
        <div className="radar-card">
          <div className="mono text-[10px] text-gray-400 uppercase tracking-widest mb-3">Agent Radar</div>
          <div className="radar-grid">
            {agents.slice(0, 10).map((agent, index) => {
              const angle = (index / Math.max(agents.length, 1)) * Math.PI * 2;
              const radius = 26 + (index % 4) * 13;
              const x = 50 + Math.cos(angle) * radius;
              const y = 50 + Math.sin(angle) * radius;
              return <span key={agent.name} className="radar-dot" title={`${agent.name} · ${agent.status}`} style={{ left: `${x}%`, top: `${y}%` }} />;
            })}
            <div className="radar-sweep" />
          </div>
          <div className="mt-3 text-xs text-gray-400">{runningAgents} running / {agents.length} configured</div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="metric-glass"><span>Agents</span><strong>{agents.length}</strong></div>
          <div className="metric-glass"><span>Running</span><strong className="text-emerald-300">{runningAgents}</strong></div>
          <div className="metric-glass"><span>Project Cards</span><strong className="text-cyan-300">{projectCards.length}</strong></div>
          <div className="metric-glass"><span>Blocked</span><strong className={blockedCards ? 'text-red-300' : 'text-emerald-300'}>{blockedCards}</strong></div>
          <div className="metric-glass"><span>Decisions</span><strong className="text-violet-300">{formatNumber(decisions.length)}</strong></div>
          <div className="metric-glass"><span>Memory</span><strong className="text-amber-300">{formatNumber(Object.keys(memory).length)}</strong></div>
        </div>
      </div>
      {error && <div className="relative z-10 mt-4 text-xs text-red-300">Dashboard cache error: {error}</div>}
    </section>
  );
}
