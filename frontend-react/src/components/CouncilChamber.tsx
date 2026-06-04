import { PanelHeader } from './PanelHeader';
import { useDashboard } from '../contexts/DashboardContext';

export function CouncilChamber() {
  const { cache } = useDashboard();
  const agents = cache?.agents || [];
  const councilAgents = agents.filter((a) => /boss|manager|council|security|engineering/i.test(a.name));
  const runningCount = councilAgents.filter((a) => ['online', 'active', 'running'].includes((a.status || '').toLowerCase())).length;
  const decisions = cache?.decisions || [];

  return (
    <div className="card">
      <PanelHeader title="Council Chamber" badge={`${runningCount}/${councilAgents.length} online`} collapsible />
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {councilAgents.map((agent) => {
          const alive = ['online', 'active', 'running'].includes((agent.status || '').toLowerCase());
          return (
            <div key={agent.name} className="text-xs p-2 rounded bg-[#0f172a] border border-jarvis-border flex items-center justify-between gap-2">
              <div>
                <div className="font-semibold text-gray-300">{agent.name}</div>
                <div className="text-gray-500 truncate">{agent.model || agent.provider || 'agent'}</div>
              </div>
              <span className={alive ? 'text-green-400' : 'text-gray-500'}>{agent.status}</span>
            </div>
          );
        })}
        <div className="text-xs text-gray-500 pt-2 border-t border-jarvis-border">
          Decision records visible: {decisions.length}. Live escalation queue: not yet connected.
        </div>
      </div>
    </div>
  );
}
