import { PanelHeader } from './PanelHeader';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DiscordThread } from '../types/dashboard';

export function DiscordNexus() {
  const [threads, setThreads] = useState<DiscordThread[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    api.discordThreads()
      .then((res) => { if (alive) setThreads(res.threads || []); })
      .catch((e) => { if (alive) setError(e.message || 'Discord bridge unavailable'); });
    return () => { alive = false; };
  }, []);

  return (
    <div className="card">
      <PanelHeader title="Discord Nexus" badge={`${threads.length} threads`} collapsible />
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {threads.map((thread) => (
          <div key={thread.thread_id || `${thread.channel_id}-${thread.thread_name}`} className="text-xs p-2 rounded bg-[#0f172a] border border-jarvis-border">
            <div className="font-semibold text-gray-300 truncate">{thread.thread_name || 'Unnamed thread'}</div>
            <div className="text-gray-500 truncate">#{thread.channel_id} · thread {thread.thread_id || 'n/a'}</div>
            <div className="text-gray-500 truncate">Bots: {(thread.participant_bots || []).join(', ') || 'none reported'}</div>
            {thread.last_message_ts && <div className="text-gray-600 mt-1">Last: {new Date(thread.last_message_ts).toLocaleString()}</div>}
          </div>
        ))}
        {!threads.length && !error && (
          <div className="text-xs text-gray-500 text-center py-8">Discord bridge online. No active threads received yet.</div>
        )}
        {error && <div className="text-xs text-red-400 text-center py-8">{error}</div>}
      </div>
    </div>
  );
}
