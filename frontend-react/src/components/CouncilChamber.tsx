import { PanelHeader } from './PanelHeader';
import { useDashboard } from '../contexts/DashboardContext';

export function CouncilChamber() {
  const { cache } = useDashboard();
  const agents = cache?.agents || [];
  const councilAgents = agents.filter((a) => /boss|manager|council|security|engineering/i.test(a.name));
  const runningCount = councilAgents.filter((a) => ['online', 'active', 'running'].includes((a.status || '').toLowerCase())).length;
  const decisions = cache?.decisions || [];
  const topology = cache?.topology || {};
  const humanGates = cache?.human_gates || { pending: [], audit_count: 0 };
  const topologyCompanies = topology.companies?.length || 0;
  const topologyTeams = topology.teams?.length || 0;
  const topologyEdges = topology.edges?.length || 0;
  const pendingGates = humanGates.pending?.length || 0;
  const auditCount = humanGates.audit_count || 0;

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
        <div className="text-xs text-gray-500 pt-2 border-t border-jarvis-border space-y-1" data-testid="council-chamber-summary">
          <div>Decision records visible: <span className="text-cyan-300">{decisions.length}</span>.</div>
          <div>Topology: <span className="text-cyan-300">{topologyCompanies}</span> company · <span className="text-cyan-300">{topologyTeams}</span> teams · <span className="text-cyan-300">{topologyEdges}</span> edges</div>
          <div>Human gates: <span className={pendingGates ? 'text-amber-300' : 'text-emerald-300'}>{pendingGates}</span> pending · <span className="text-gray-400">{auditCount}</span> audit entries</div>
        </div>
      </div>
    </div>
  );
}
