import { useEffect, useState } from 'react';
import { useProject } from '../contexts/ProjectContext';
import { api } from '../api/client';
import type { Decision } from '../types/dashboard';
import { PanelHeader } from './PanelHeader';
import { errorMessage } from '../utils/config';

export function DecisionLog() {
  const { project } = useProject();
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [error, setError] = useState('');
  const projectSlug = project?.slug || '';

  useEffect(() => {
    let alive = true;
    api.decisions(projectSlug || undefined)
      .then((res) => { if (alive) setDecisions(res || []); })
      .catch((e: unknown) => { if (alive) setError(errorMessage(e, 'Decision log unavailable')); });
    return () => { alive = false; };
  }, [projectSlug]);

  return (
    <div className="card">
      <PanelHeader title="Decision Log" badge={`${projectSlug || 'all'} · ${decisions.length} decisions`} collapsible />
      <div className="text-[10px] text-gray-500 mb-2 truncate">
        Scope: {projectSlug || 'global'}
      </div>
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {decisions.map(d => (
          <div key={d.id} className="text-xs p-2 rounded bg-[#0f172a] border border-jarvis-border">
            <div className="flex justify-between gap-2">
              <span className="font-semibold text-gray-300 truncate">{d.title || d.id}</span>
              {d.tier !== undefined && <span className="tier-badge tier-0 shrink-0">Tier {d.tier}</span>}
            </div>
            {d.project && <div className="text-blue-400 mt-1">Project: {d.project}</div>}
            <div className="text-gray-500 mt-1 truncate">{d.source}</div>
            <div className="text-gray-500 mt-1">{d.created_at ? new Date(d.created_at).toLocaleString() : 'Unknown date'}</div>
          </div>
        ))}
        {decisions.length === 0 && !error && (
          <div className="text-xs text-gray-500 text-center py-4">No scoped decisions yet.</div>
        )}
        {error && <div className="text-xs text-red-400 text-center py-4">{error}</div>}
      </div>
    </div>
  );
}
