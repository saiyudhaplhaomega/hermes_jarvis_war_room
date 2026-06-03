import { useEffect, useState } from 'react';
import { useProject } from '../contexts/ProjectContext';
import { api } from '../api/client';
import type { MemoryItem } from '../types/dashboard';
import { PanelHeader } from './PanelHeader';

export function MemoryNexus() {
  const { project } = useProject();
  const [memory, setMemory] = useState<Record<string, MemoryItem>>({});
  const [error, setError] = useState('');
  const entries = Object.entries(memory);
  const projectSlug = project?.slug || '';

  useEffect(() => {
    let alive = true;
    setError('');
    api.memory(projectSlug || undefined)
      .then((res) => { if (alive) setMemory(res || {}); })
      .catch((e) => { if (alive) setError(e.message || 'Memory unavailable'); });
    return () => { alive = false; };
  }, [projectSlug]);

  return (
    <div className="card">
      <PanelHeader title="Memory Nexus" badge={`${projectSlug || 'all'} · ${entries.length} entries`} />
      <div className="text-[10px] text-gray-500 mb-2 truncate">
        Scope: {projectSlug || 'global'}
      </div>
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {entries.map(([key, item]) => (
          <div key={key} className="text-xs p-2 rounded bg-[#0f172a] border border-jarvis-border">
            <div className="font-semibold text-gray-300 truncate">{item.title || key}</div>
            <div className="text-gray-500 truncate">{item.kind ? `${item.kind} · ` : ''}{item.source}</div>
            {item.project && <div className="text-blue-400 mt-1">Project: {item.project}</div>}
            {item.updated_at && <div className="text-gray-600 mt-1">{new Date(item.updated_at).toLocaleString()}</div>}
          </div>
        ))}
        {entries.length === 0 && !error && (
          <div className="text-xs text-gray-500 text-center py-4">No scoped memory entries yet.</div>
        )}
        {error && <div className="text-xs text-red-400 text-center py-4">{error}</div>}
      </div>
    </div>
  );
}
