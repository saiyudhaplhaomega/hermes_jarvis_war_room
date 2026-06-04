import { useDashboard } from '../contexts/DashboardContext';
import { PanelHeader } from './PanelHeader';

export function AgentConstellation() {
  const { cache } = useDashboard();
  const agents = cache?.agents || [];
  const isAlive = (status: string) => ['online', 'active', 'running'].includes((status || '').toLowerCase());
  const alive = agents.filter(a => isAlive(a.status)).length;

  return (
    <div className="card">
      <PanelHeader title="Agent Constellation" badge={`${alive} alive`} collapsible />
      <div className="grid grid-cols-2 gap-2">
        {agents.map(agent => (
          <div key={agent.name} className="flex items-center gap-2 p-2 rounded bg-[#0f172a]">
            <div className={`w-2 h-2 rounded-full ${isAlive(agent.status) ? 'bg-green-500' : 'bg-gray-600'}`} title={agent.status} />
            <div className="text-xs">
              <div className="font-semibold text-gray-200">{agent.name}</div>
              <div className="text-gray-500">{agent.model || agent.role || 'agent'}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
