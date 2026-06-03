import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { ArmyRun, ArmyWorker } from '../types/dashboard';

const STATUS_STYLE: Record<string, string> = {
  queued: 'text-slate-300 border-slate-500/40 bg-slate-500/10',
  running: 'text-cyan-200 border-cyan-400/40 bg-cyan-400/10',
  completed: 'text-emerald-200 border-emerald-400/40 bg-emerald-400/10',
  needs_review: 'text-amber-200 border-amber-400/40 bg-amber-400/10',
  approved: 'text-green-200 border-green-400/40 bg-green-400/10',
  rejected: 'text-red-200 border-red-400/40 bg-red-400/10',
  failed: 'text-rose-200 border-rose-400/40 bg-rose-400/10',
};

function fmtDate(value?: string) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export function ArmyOperations() {
  const [workers, setWorkers] = useState<ArmyWorker[]>([]);
  const [runs, setRuns] = useState<ArmyRun[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [task, setTask] = useState('Create a harmless status note for the Army Operations smoke test.');
  const [worker, setWorker] = useState('claude');
  const [repo, setRepo] = useState('');
  const [dryRun, setDryRun] = useState(true);
  const [logs, setLogs] = useState('');
  const [diff, setDiff] = useState('');
  const [rejectReason, setRejectReason] = useState('Needs clearer smoke test evidence.');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const selected = useMemo(() => runs.find((run) => run.run_id === selectedId) || runs[0], [runs, selectedId]);

  async function refresh() {
    setError('');
    const [workerPayload, runPayload] = await Promise.all([api.armyWorkers(), api.armyRuns()]);
    setWorkers(workerPayload.workers);
    setRuns(runPayload.runs);
    if (!selectedId && runPayload.runs[0]) setSelectedId(runPayload.runs[0].run_id);
  }

  async function loadRunDetail(runId: string) {
    if (!runId) return;
    const [logPayload, diffPayload] = await Promise.all([api.armyLogs(runId), api.armyDiff(runId)]);
    setLogs(logPayload.logs || '');
    setDiff(diffPayload.diff || '');
  }

  useEffect(() => {
    refresh().catch((err) => setError(String(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selected?.run_id) loadRunDetail(selected.run_id).catch((err) => setError(String(err)));
  }, [selected?.run_id]);

  async function withBusy(fn: () => Promise<void>) {
    setBusy(true);
    setError('');
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const availableWorkerIds = workers.filter((item) => item.available || dryRun).map((item) => item.id);

  return (
    <div className="panel-card army-operations">
      <div className="panel-header-row">
        <div>
          <p className="panel-kicker">CONDUCTOR DECK</p>
          <h2 className="panel-title">Army Operations</h2>
          <p className="panel-subtitle">Dashboard-local CLI worker runs with logs, diffs, approval gates, and no profile mutation.</p>
        </div>
        <button className="btn-secondary" onClick={() => withBusy(refresh)} disabled={busy}>Refresh</button>
      </div>

      {error && <div className="rounded border border-red-400/40 bg-red-500/10 p-2 text-sm text-red-100">{error}</div>}

      <div className="grid gap-3 md:grid-cols-3">
        {workers.map((item) => (
          <div key={item.id} className="rounded-lg border border-white/10 bg-black/20 p-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-jarvis-text">{item.label}</h3>
              <span className={`rounded-full border px-2 py-0.5 text-xs ${item.available ? 'border-emerald-400/40 text-emerald-200' : 'border-slate-500/40 text-slate-300'}`}>
                {item.available ? 'available' : 'standby'}
              </span>
            </div>
            <p className="mt-2 text-xs text-jarvis-muted">{item.notes}</p>
            <p className="mt-2 truncate text-[11px] text-slate-500">{item.path || item.kind}</p>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-cyan-400/20 bg-cyan-950/10 p-3">
        <div className="grid gap-3 md:grid-cols-[160px_1fr]">
          <label className="text-xs uppercase tracking-wider text-jarvis-muted">Worker</label>
          <select className="control-input" value={worker} onChange={(event) => setWorker(event.target.value)}>
            {workers.map((item) => <option key={item.id} value={item.id} disabled={!availableWorkerIds.includes(item.id)}>{item.label}</option>)}
          </select>
          <label className="text-xs uppercase tracking-wider text-jarvis-muted">Repo / scope</label>
          <input className="control-input" value={repo} onChange={(event) => setRepo(event.target.value)} placeholder="optional path or project scope" />
          <label className="text-xs uppercase tracking-wider text-jarvis-muted">Task</label>
          <textarea className="control-input min-h-[92px]" value={task} onChange={(event) => setTask(event.target.value)} />
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-jarvis-muted">
            <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
            Dry run / dashboard-local only
          </label>
          <button
            className="btn-primary"
            disabled={busy || !task.trim()}
            onClick={() => withBusy(async () => {
              const created = await api.spawnArmyRun({ worker, task, repo, dry_run: dryRun });
              setSelectedId(created.run.run_id);
            })}
          >
            Spawn Mission Run
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.9fr)_minmax(420px,1.1fr)]">
        <div className="rounded-lg border border-white/10 bg-black/20 p-3">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-jarvis-muted">Mission Run Board</h3>
          <div className="space-y-2 max-h-[520px] overflow-auto pr-1">
            {runs.length === 0 && <p className="text-sm text-jarvis-muted">No runs yet. Spawn a dry run to start.</p>}
            {runs.map((run) => (
              <button
                key={run.run_id}
                className={`w-full rounded border p-3 text-left transition ${selected?.run_id === run.run_id ? 'border-cyan-400/60 bg-cyan-400/10' : 'border-white/10 bg-slate-950/30 hover:border-white/30'}`}
                onClick={() => setSelectedId(run.run_id)}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-cyan-100">{run.run_id}</span>
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] ${STATUS_STYLE[run.status] || STATUS_STYLE.queued}`}>{run.status}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-jarvis-text">{run.task}</p>
                <p className="mt-2 text-[11px] text-jarvis-muted">{run.worker} • {fmtDate(run.updated_at)}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-black/20 p-3">
          {selected ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-mono text-sm text-cyan-100">{selected.run_id}</h3>
                  <p className="text-xs text-jarvis-muted">{selected.worker} • {fmtDate(selected.created_at)} • writes_profile_configs=false</p>
                </div>
                <span className={`rounded-full border px-2 py-0.5 text-xs ${STATUS_STYLE[selected.status] || STATUS_STYLE.queued}`}>{selected.status}</span>
              </div>
              <p className="mt-3 whitespace-pre-wrap rounded bg-slate-950/60 p-2 text-sm text-jarvis-text">{selected.task}</p>

              <div className="mt-3 flex flex-wrap gap-2">
                <button className="btn-secondary" disabled={busy} onClick={() => selected && withBusy(async () => { await api.rerunArmyRun(selected.run_id); })}>Rerun</button>
                <button className="btn-secondary" disabled={busy} onClick={() => selected && withBusy(async () => { await api.approveArmyRun(selected.run_id); })}>Approve state</button>
                <input className="control-input max-w-sm" value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} />
                <button className="btn-danger" disabled={busy || !rejectReason.trim()} onClick={() => selected && withBusy(async () => { await api.rejectArmyRun(selected.run_id, rejectReason); })}>Reject</button>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-jarvis-muted">Live Ops Log</h4>
                  <pre className="max-h-[360px] overflow-auto rounded border border-white/10 bg-black/50 p-3 text-xs text-slate-200">{logs || 'No logs captured.'}</pre>
                </div>
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-jarvis-muted">Diff Review Chamber</h4>
                  <pre className="max-h-[360px] overflow-auto rounded border border-white/10 bg-black/50 p-3 text-xs text-emerald-100">{diff || 'No workspace diff captured.'}</pre>
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-jarvis-muted">Select a run to inspect logs and diffs.</p>
          )}
        </div>
      </div>
    </div>
  );
}
