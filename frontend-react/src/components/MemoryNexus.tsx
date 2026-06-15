import { useEffect, useState } from 'react';
import { useProject } from '../contexts/ProjectContext';
import { useDashboard } from '../contexts/DashboardContext';
import { api } from '../api/client';
import type { MemoryItem, ResearchItem, DepartmentInfo } from '../types/dashboard';
import { PanelHeader } from './PanelHeader';
import { errorMessage } from '../utils/config';

type Tab = 'memory' | 'research' | 'departments';

export function MemoryNexus() {
  const { project } = useProject();
  const { cache } = useDashboard();
  const [memory, setMemory] = useState<Record<string, MemoryItem>>({});
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('memory');
  const entries = Object.entries(memory);
  const research: ResearchItem[] = (cache?.research as ResearchItem[]) || [];
  const departments: Record<string, DepartmentInfo> = (cache?.departments as Record<string, DepartmentInfo>) || {};
  const projectSlug = project?.slug || '';

  useEffect(() => {
    let alive = true;
    api.memory(projectSlug || undefined)
      .then((res) => { if (alive) setMemory(res || {}); })
      .catch((e: unknown) => { if (alive) setError(errorMessage(e, 'Memory unavailable')); });
    return () => { alive = false; };
  }, [projectSlug]);

  return (
    <div className="card">
      <PanelHeader title="Memory Nexus" badge={`${projectSlug || 'all'} · ${entries.length + research.length + Object.keys(departments).length} items`} collapsible />
      <div className="text-[10px] text-gray-500 mb-2 truncate">
        Scope: {projectSlug || 'global'}
      </div>
      <div className="flex gap-1 mb-2 text-[10px] uppercase tracking-wider" data-testid="memory-tabs">
        {([
          ['memory', `Memory (${entries.length})`],
          ['research', `Research (${research.length})`],
          ['departments', `Departments (${Object.keys(departments).length})`],
        ] as Array<[Tab, string]>).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`px-2 py-1 rounded border ${tab === key ? 'border-cyan-400 text-cyan-300' : 'border-jarvis-border text-gray-500 hover:text-gray-300'}`}
            data-testid={`memory-tab-${key}`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {tab === 'memory' && entries.map(([key, item]) => (
          <div key={key} className="text-xs p-2 rounded bg-[#0f172a] border border-jarvis-border">
            <div className="font-semibold text-gray-300 truncate">{item.title || key}</div>
            <div className="text-gray-500 truncate">{item.kind ? `${item.kind} · ` : ''}{item.source}</div>
            {item.project && <div className="text-blue-400 mt-1">Project: {item.project}</div>}
            {item.updated_at && <div className="text-gray-600 mt-1">{new Date(item.updated_at).toLocaleString()}</div>}
          </div>
        ))}
        {tab === 'memory' && entries.length === 0 && !error && (
          <div className="text-xs text-gray-500 text-center py-4">No scoped memory entries yet.</div>
        )}
        {tab === 'research' && research.slice(0, 50).map((r) => (
          <div key={r.id} className="text-xs p-2 rounded bg-[#0f172a] border border-jarvis-border" data-testid={`memory-research-${r.round_id || r.id}`}>
            <div className="font-semibold text-gray-300 truncate">
              {r.round_id && <span className="text-cyan-400 mr-1">[{r.round_id}]</span>}
              {r.title}
            </div>
            <div className="text-gray-500 truncate">{r.kind} · {r.source}</div>
            {r.project && <div className="text-blue-400 mt-1">Project: {r.project}</div>}
            {r.size_bytes != null && <div className="text-gray-600 mt-1">{Math.round(r.size_bytes / 1024)} KB</div>}
          </div>
        ))}
        {tab === 'research' && research.length === 0 && (
          <div className="text-xs text-gray-500 text-center py-4">No research artifacts yet. Run the aggregator to populate.</div>
        )}
        {tab === 'departments' && Object.entries(departments).map(([name, d]) => (
          <div key={name} className="text-xs p-2 rounded bg-[#0f172a] border border-jarvis-border" data-testid={`memory-dept-${name}`}>
            <div className="font-semibold text-violet-300 truncate">{d.title || name}</div>
            <div className="text-gray-500">{d.file_count} files</div>
            <div className="text-gray-400 mt-1 truncate">
              {d.files.slice(0, 3).map(f => f.title).join(' · ')}
              {d.files.length > 3 && ` · +${d.files.length - 3} more`}
            </div>
          </div>
        ))}
        {tab === 'departments' && Object.keys(departments).length === 0 && (
          <div className="text-xs text-gray-500 text-center py-4">No department docs found.</div>
        )}
        {error && <div className="text-xs text-red-400 text-center py-4">{error}</div>}
      </div>
    </div>
  );
}
