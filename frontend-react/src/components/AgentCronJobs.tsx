import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { useProject } from '../contexts/ProjectContext';
import { PanelHeader } from './PanelHeader';
import {
  PROJECT_SCOPES,
  SCOPE_DEFINITIONS,
  scopeColor,
  scopeLabel,
} from '../utils/projectScopes';

// D-2026-06-14 (Agent Cron Jobs):
// Lets the user create / list / edit / delete scheduled jobs that
// invoke an agent with a prompt. Three schedule types:
//   - cron       (5-field POSIX expression, e.g. "*/5 * * * *")
//   - interval   (every N seconds, 1-2592000 = up to 30 days)
//   - one_shot   (run once at an ISO 8601 UTC timestamp, then auto-disable)
//
// D-2026-06-14 (3-level scopes):
// Every job is scoped to one of three project levels:
//   1. global-hermes     - top-level Hermes folder. Applies to the
//                          whole installation. New GitHub repo
//                          imports land here by default.
//   2. jarvis-war-room   - the War Room workspace itself (dashboard,
//                          launcher, council, research).
//   3. <active-project>  - the chat-active user project (e.g.
//                          hello-world). Whatever the user picked
//                          in the chat project picker.
//
// The toolbar at the top has a "Scope" segmented control so the
// user can filter to All / Global Hermes / Jarvis War Room / the
// current project. The form's "Project" field is a select with
// the 3 fixed options + a "Custom…" escape hatch.
//
// Jobs persist in `agent_cron_jobs.json` (dashboard-local). The SPA's
// scheduler loop (in `useCronScheduler`) checks every 10s which jobs
// are due and POSTs to /chat with the agent+prompt.

interface CronJob {
  id: string;
  name: string;
  agent: string;
  prompt: string;
  schedule_type: 'cron' | 'interval' | 'one_shot';
  cron_expression: string;
  interval_seconds: number;
  run_at: string;
  project: string;
  enabled: boolean;
  notes: string;
  created_at: string;
  created_by: string;
  updated_at: string;
  last_run_at: string;
  last_run_status: string;
  last_error: string;
  run_count: number;
}

const SCHEDULE_TYPES: Array<{ value: CronJob['schedule_type']; label: string; hint: string }> = [
  { value: 'cron', label: 'Cron', hint: '5-field POSIX (min hr dom mon dow) — e.g. */5 * * * *' },
  { value: 'interval', label: 'Interval', hint: 'Run every N seconds' },
  { value: 'one_shot', label: 'One-shot', hint: 'Run once at a specific ISO 8601 UTC timestamp' },
];

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function describeSchedule(j: CronJob): string {
  if (j.schedule_type === 'cron') return `cron: ${j.cron_expression || '(unset)'}`;
  if (j.schedule_type === 'interval') {
    const s = Number(j.interval_seconds) || 0;
    if (s < 60) return `every ${s}s`;
    if (s < 3600) return `every ${Math.round(s / 60)}m`;
    if (s < 86400) return `every ${Math.round(s / 3600)}h`;
    return `every ${Math.round(s / 86400)}d`;
  }
  if (j.schedule_type === 'one_shot') return `at ${j.run_at || '(unset)'}`;
  return '?';
}

function sortAgents(agents: string[]): string[] {
  const score = (a: string) => {
    const l = a.toLowerCase();
    if (l.includes('orchestrator')) return 0;
    if (l.includes('boss')) return 1;
    if (l.includes('manager')) return 2;
    return 3;
  };
  return [...agents].sort((a, b) => {
    const sa = score(a), sb = score(b);
    if (sa !== sb) return sa - sb;
    return a.localeCompare(b);
  });
}

function emptyDraft(projectSlug: string = PROJECT_SCOPES.DEFAULT): Partial<CronJob> {
  return {
    name: '',
    agent: '',
    prompt: '',
    schedule_type: 'interval',
    cron_expression: '*/15 * * * *',
    interval_seconds: 900,
    run_at: new Date(Date.now() + 60_000).toISOString().slice(0, 19) + 'Z',
    // D-2026-06-14: caller passes the active project slug. The form's
    // project select then lets the user switch to global-hermes or
    // jarvis-war-room (or a custom slug).
    project: projectSlug,
    enabled: true,
    notes: '',
  };
}

export function AgentCronJobs() {
  const { project } = useProject();
  const activeProject = project?.slug || PROJECT_SCOPES.DEFAULT;

  const [jobs, setJobs] = useState<CronJob[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Partial<CronJob>>(emptyDraft(activeProject));
  const [status, setStatus] = useState<string>('');
  const [showForm, setShowForm] = useState(false);
  // D-2026-06-14: scope filter (All / Global Hermes / Jarvis War Room / active project)
  const [scopeFilter, setScopeFilter] = useState<string>('all');
  // "Custom project" input (when the form's project select is on "custom…")
  const [customProject, setCustomProject] = useState<string>('');

  // ── Load jobs + agent list ────────────────────────────────────
  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const [list, cacheData] = await Promise.all([
        api.listCronJobs(),
        api.cache(activeProject || undefined).catch(() => null),
      ]);
      setJobs(list.jobs || []);
      if (cacheData) {
        const list = (cacheData.agents || []).map((a: any) => a.name).filter(Boolean);
        setAgents(sortAgents(list));
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  // ── Form handlers ─────────────────────────────────────────────
  function startCreate() {
    setEditingId(null);
    setDraft({ ...emptyDraft(activeProject), agent: agents[0] || '' });
    setShowForm(true);
    setStatus('');
  }

  function startEdit(j: CronJob) {
    setEditingId(j.id);
    setDraft({ ...j });
    setShowForm(true);
    setStatus('');
  }

  function cancelForm() {
    setShowForm(false);
    setEditingId(null);
    setDraft(emptyDraft(activeProject));
    setStatus('');
  }

  async function saveDraft() {
    setError('');
    setStatus('saving…');
    try {
      if (!draft.name?.trim() || !draft.agent?.trim() || !draft.prompt?.trim()) {
        setStatus('name, agent, and prompt are required');
        return;
      }
      if (editingId) {
        const updates: any = {
          name: draft.name,
          agent: draft.agent,
          prompt: draft.prompt,
          schedule_type: draft.schedule_type,
          project: draft.project,
          enabled: draft.enabled,
          notes: draft.notes,
        };
        if (draft.schedule_type === 'cron') updates.cron_expression = draft.cron_expression;
        if (draft.schedule_type === 'interval') updates.interval_seconds = Number(draft.interval_seconds) || 0;
        if (draft.schedule_type === 'one_shot') updates.run_at = draft.run_at;
        await api.updateCronJob(editingId, updates);
        setStatus(`updated "${draft.name}"`);
      } else {
        const create: any = {
          name: draft.name,
          agent: draft.agent,
          prompt: draft.prompt,
          schedule_type: draft.schedule_type,
          project: draft.project,
          enabled: draft.enabled ?? true,
          notes: draft.notes || '',
        };
        if (draft.schedule_type === 'cron') create.cron_expression = draft.cron_expression;
        if (draft.schedule_type === 'interval') create.interval_seconds = Number(draft.interval_seconds) || 0;
        if (draft.schedule_type === 'one_shot') create.run_at = draft.run_at;
        await api.createCronJob(create);
        setStatus(`created "${draft.name}"`);
      }
      await refresh();
      cancelForm();
    } catch (e) {
      setStatus(`save failed: ${errorMessage(e)}`);
    }
  }

  async function toggleEnabled(j: CronJob) {
    try {
      await api.updateCronJob(j.id, { enabled: !j.enabled });
      await refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function deleteJob(j: CronJob) {
    if (!confirm(`Delete cron job "${j.name}"? This cannot be undone.`)) return;
    try {
      await api.deleteCronJob(j.id);
      await refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function runNow(j: CronJob) {
    setStatus(`dispatching ${j.name}…`);
    try {
      const result = await api.runCronJobNow(j.id);
      setStatus(`dispatched "${j.name}" → ${result.agent} (run #${result.job?.run_count ?? '?'})`);
      await refresh();
    } catch (e) {
      setStatus(`run-now failed: ${errorMessage(e)}`);
    }
  }

  // ── Derived: next-fire preview (very rough) ───────────────────
  const upcoming = useMemo(() => {
    return jobs
      .filter((j) => j.enabled)
      .slice(0, 5);
  }, [jobs]);

  // ── Derived: scope counts + filtered jobs (D-2026-06-14) ──────
  const scopeCounts = useMemo(() => {
    const counts: Record<string, number> = { all: jobs.length };
    counts[PROJECT_SCOPES.GLOBAL_HERMES] = jobs.filter((j) => (j.project || '') === PROJECT_SCOPES.GLOBAL_HERMES).length;
    counts[PROJECT_SCOPES.JARVIS_WAR_ROOM] = jobs.filter((j) => (j.project || '') === PROJECT_SCOPES.JARVIS_WAR_ROOM).length;
    counts[activeProject] = jobs.filter((j) => (j.project || '') === activeProject).length;
    return counts;
  }, [jobs, activeProject]);

  const filteredJobs = useMemo(() => {
    if (scopeFilter === 'all') return jobs;
    return jobs.filter((j) => (j.project || '') === scopeFilter);
  }, [jobs, scopeFilter]);

  return (
    <div className="dashboard-card agent-cron-jobs" data-testid="agent-cron-jobs">
      <PanelHeader
        title="Agent Cron Jobs"
        subtitle={`${jobs.length} job${jobs.length === 1 ? '' : 's'} · ${jobs.filter((j) => j.enabled).length} enabled · schedules run in the dashboard session`}
        accent="amber"
      />

      {/* D-2026-06-14: 3-level scope filter.
          - "All"            → show every job regardless of project
          - 🌍 "Global Hermes"→ top-level Hermes folder (war-room-wide + install-wide)
          - ⚔ "Jarvis War Room" → war-room itself
          - 📁 activeProject  → only jobs for the current chat project
          Each button shows a live count badge. */}
      <div className="cron-scope-filter" data-testid="cron-scope-filter" role="tablist" aria-label="Filter jobs by project scope">
        <button
          type="button"
          role="tab"
          aria-selected={scopeFilter === 'all'}
          className={`cron-scope-pill ${scopeFilter === 'all' ? 'cron-scope-pill--on' : ''}`}
          onClick={() => setScopeFilter('all')}
          data-testid="cron-scope-all"
        >
          <span>All</span>
          <span className="cron-scope-pill-count">{scopeCounts.all}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={scopeFilter === PROJECT_SCOPES.GLOBAL_HERMES}
          className={`cron-scope-pill ${scopeFilter === PROJECT_SCOPES.GLOBAL_HERMES ? 'cron-scope-pill--on cron-scope-pill--amber' : ''}`}
          onClick={() => setScopeFilter(PROJECT_SCOPES.GLOBAL_HERMES)}
          data-testid="cron-scope-global"
          title={SCOPE_DEFINITIONS[0].description}
        >
          <span>🌍 Global Hermes</span>
          <span className="cron-scope-pill-count">{scopeCounts[PROJECT_SCOPES.GLOBAL_HERMES]}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={scopeFilter === PROJECT_SCOPES.JARVIS_WAR_ROOM}
          className={`cron-scope-pill ${scopeFilter === PROJECT_SCOPES.JARVIS_WAR_ROOM ? 'cron-scope-pill--on cron-scope-pill--cyan' : ''}`}
          onClick={() => setScopeFilter(PROJECT_SCOPES.JARVIS_WAR_ROOM)}
          data-testid="cron-scope-warroom"
          title={SCOPE_DEFINITIONS[1].description}
        >
          <span>⚔ Jarvis War Room</span>
          <span className="cron-scope-pill-count">{scopeCounts[PROJECT_SCOPES.JARVIS_WAR_ROOM]}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={scopeFilter === activeProject}
          className={`cron-scope-pill ${scopeFilter === activeProject ? 'cron-scope-pill--on cron-scope-pill--violet' : ''}`}
          onClick={() => setScopeFilter(activeProject)}
          data-testid="cron-scope-active-project"
          title={`Only jobs for the current chat project (${activeProject})`}
        >
          <span>📁 {activeProject}</span>
          <span className="cron-scope-pill-count">{scopeCounts[activeProject] ?? 0}</span>
        </button>
      </div>

      <div className="cron-jobs-toolbar">
        <button
          type="button"
          className="pill pill-emerald"
          onClick={startCreate}
          data-testid="cron-jobs-new"
        >
          + New job
        </button>
        <button
          type="button"
          className="pill pill-default"
          onClick={refresh}
          data-testid="cron-jobs-refresh"
        >
          ↻ Refresh
        </button>
        <span className="cron-jobs-meta" data-testid="cron-jobs-count">
          {loading
            ? 'loading…'
            : scopeFilter === 'all'
              ? `${jobs.length} job${jobs.length === 1 ? '' : 's'}`
              : `${filteredJobs.length} of ${jobs.length} in this scope`}
        </span>
      </div>

      {/* ── FORM ──────────────────────────────────────────────── */}
      {showForm && (
        <div className="cron-form" data-testid="cron-jobs-form">
          <h4 className="cron-form-title">
            {editingId ? 'Edit job' : 'New job'}
          </h4>
          <div className="cron-form-grid">
            <label className="cron-field">
              <span>Name <span className="cron-req">*</span></span>
              <input
                type="text"
                placeholder="nightly-research-sweep"
                value={draft.name || ''}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                data-testid="cron-form-name"
              />
            </label>
            <label className="cron-field">
              <span>Agent <span className="cron-req">*</span></span>
              <select
                value={draft.agent || ''}
                onChange={(e) => setDraft({ ...draft, agent: e.target.value })}
                data-testid="cron-form-agent"
              >
                <option value="">(pick an agent)</option>
                {agents.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </label>
            <label className="cron-field cron-field--wide">
              <span>Prompt <span className="cron-req">*</span></span>
              <textarea
                rows={3}
                placeholder="What to send to the agent on each run — e.g. 'sweep the inbox and summarize any unhandled council tickets'"
                value={draft.prompt || ''}
                onChange={(e) => setDraft({ ...draft, prompt: e.target.value })}
                data-testid="cron-form-prompt"
              />
            </label>
            <label className="cron-field">
              <span>Schedule type <span className="cron-req">*</span></span>
              <select
                value={draft.schedule_type || 'interval'}
                onChange={(e) => setDraft({ ...draft, schedule_type: e.target.value as any })}
                data-testid="cron-form-schedule-type"
              >
                {SCHEDULE_TYPES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              <span className="cron-field-hint">
                {SCHEDULE_TYPES.find((s) => s.value === draft.schedule_type)?.hint}
              </span>
            </label>
            {draft.schedule_type === 'cron' && (
              <label className="cron-field">
                <span>Cron expression <span className="cron-req">*</span></span>
                <input
                  type="text"
                  placeholder="*/15 * * * *"
                  value={draft.cron_expression || ''}
                  onChange={(e) => setDraft({ ...draft, cron_expression: e.target.value })}
                  data-testid="cron-form-cron"
                />
                <span className="cron-field-hint">
                  5 fields: minute hour day-of-month month day-of-week. Try <code>*/5 * * * *</code> for every 5 min, or <code>0 9 * * 1-5</code> for 9am weekdays.
                </span>
              </label>
            )}
            {draft.schedule_type === 'interval' && (
              <label className="cron-field">
                <span>Every N seconds <span className="cron-req">*</span></span>
                <input
                  type="number"
                  min="1"
                  max="2592000"
                  value={draft.interval_seconds ?? 900}
                  onChange={(e) => setDraft({ ...draft, interval_seconds: Number(e.target.value) })}
                  data-testid="cron-form-interval"
                />
                <span className="cron-field-hint">
                  1-2592000 (up to 30 days). 900 = 15 min, 3600 = 1h, 86400 = 1d.
                </span>
              </label>
            )}
            {draft.schedule_type === 'one_shot' && (
              <label className="cron-field">
                <span>Run at (ISO 8601 UTC) <span className="cron-req">*</span></span>
                <input
                  type="text"
                  placeholder="2026-06-15T09:00:00Z"
                  value={draft.run_at || ''}
                  onChange={(e) => setDraft({ ...draft, run_at: e.target.value })}
                  data-testid="cron-form-run-at"
                />
                <span className="cron-field-hint">
                  ISO 8601 UTC. After firing, the job is auto-disabled.
                </span>
              </label>
            )}
            <label className="cron-field">
              <span>Project scope <span className="cron-req">*</span></span>
              {/* D-2026-06-14: select with the 3 fixed levels + custom.
                  Default is the active chat project. Switching to
                  global-hermes or jarvis-war-room routes the job to
                  that scope regardless of what the chat project is. */}
              <select
                value={
                  draft.project === PROJECT_SCOPES.GLOBAL_HERMES
                  || draft.project === PROJECT_SCOPES.JARVIS_WAR_ROOM
                  || (draft.project && scopeCounts[draft.project] !== undefined && draft.project === activeProject)
                    ? draft.project
                    : '__custom__'
                }
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === '__custom__') {
                    setDraft({ ...draft, project: customProject || '' });
                  } else {
                    setDraft({ ...draft, project: v });
                  }
                }}
                data-testid="cron-form-project"
              >
                <option value={activeProject}>📁 {activeProject} (active project)</option>
                <option value={PROJECT_SCOPES.JARVIS_WAR_ROOM}>⚔ Jarvis War Room (war-room-wide)</option>
                <option value={PROJECT_SCOPES.GLOBAL_HERMES}>🌍 Global Hermes (installation-wide)</option>
                <option value="__custom__">Custom…</option>
              </select>
              {!(
                draft.project === PROJECT_SCOPES.GLOBAL_HERMES
                || draft.project === PROJECT_SCOPES.JARVIS_WAR_ROOM
                || draft.project === activeProject
              ) && (
                <input
                  type="text"
                  placeholder="custom project slug"
                  value={customProject || draft.project || ''}
                  onChange={(e) => {
                    setCustomProject(e.target.value);
                    setDraft({ ...draft, project: e.target.value });
                  }}
                  data-testid="cron-form-project-custom"
                />
              )}
              <span className="cron-field-hint">
                {draft.project === PROJECT_SCOPES.GLOBAL_HERMES
                  ? '🌍 Installs at the Hermes top level. Applies to the whole Hermes instance, not any one project.'
                  : draft.project === PROJECT_SCOPES.JARVIS_WAR_ROOM
                    ? '⚔ Scoped to the Jarvis War Room workspace itself (dashboard, launcher, council, research).'
                    : draft.project === activeProject
                      ? `📁 Scoped to the current chat project: ${activeProject}.`
                      : 'Custom project slug (free-form).'}
              </span>
            </label>
            <label className="cron-field cron-field--checkbox">
              <input
                type="checkbox"
                checked={draft.enabled ?? true}
                onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
                data-testid="cron-form-enabled"
              />
              <span>Enabled (fires on schedule)</span>
            </label>
            <label className="cron-field cron-field--wide">
              <span>Notes (optional)</span>
              <input
                type="text"
                placeholder="Why this job exists, what it produces, etc."
                value={draft.notes || ''}
                onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
                data-testid="cron-form-notes"
              />
            </label>
          </div>
          <div className="cron-form-actions">
            <button
              type="button"
              className="pill pill-emerald"
              onClick={saveDraft}
              data-testid="cron-form-save"
            >
              {editingId ? 'Save changes' : 'Create job'}
            </button>
            <button
              type="button"
              className="pill pill-default"
              onClick={cancelForm}
              data-testid="cron-form-cancel"
            >
              Cancel
            </button>
            {status && (
              <span className="cron-form-status" data-testid="cron-form-status">{status}</span>
            )}
          </div>
        </div>
      )}

      {error && (
        <div className="cron-error" data-testid="cron-jobs-error">{error}</div>
      )}

      {/* ── JOB LIST (D-2026-06-14: scoped via filteredJobs) ────── */}
      <div className="cron-list" data-testid="cron-jobs-list">
        {jobs.length === 0 && !loading && (
          <div className="cron-empty" data-testid="cron-jobs-empty">
            No cron jobs yet. Click <b>+ New job</b> to schedule an agent.
          </div>
        )}
        {jobs.length > 0 && filteredJobs.length === 0 && !loading && (
          <div className="cron-empty" data-testid="cron-scope-empty">
            No jobs in this scope ({scopeFilter}). Switch to <b>All</b> to see all {jobs.length} job{jobs.length === 1 ? '' : 's'}.
          </div>
        )}
        {filteredJobs.map((j) => {
          const color = scopeColor(j.project || '');
          const scopeClass = `cron-scope-badge cron-scope-badge--${color}`;
          return (
          <div
            key={j.id}
            className={`cron-row ${j.enabled ? '' : 'cron-row--disabled'}`}
            data-testid={`cron-row-${j.name}`}
          >
            <div className="cron-row-head">
              <span className="cron-row-name">{j.name}</span>
              <span className="pill pill-cyan" data-testid={`cron-row-type-${j.name}`}>
                {j.schedule_type}
              </span>
              <span className="pill pill-default">{j.agent}</span>
              {/* D-2026-06-14: color-coded scope badge */}
              {j.project && (
                <span
                  className={scopeClass}
                  data-testid={`cron-row-scope-${j.name}`}
                  title={SCOPE_DEFINITIONS.find((d) => d.slug === j.project)?.description || `Project: ${j.project}`}
                >
                  {j.project === PROJECT_SCOPES.GLOBAL_HERMES && '🌍 '}
                  {j.project === PROJECT_SCOPES.JARVIS_WAR_ROOM && '⚔ '}
                  {j.project && j.project !== PROJECT_SCOPES.GLOBAL_HERMES && j.project !== PROJECT_SCOPES.JARVIS_WAR_ROOM && '📁 '}
                  {scopeLabel(j.project)}
                </span>
              )}
              <span className="cron-row-sched">{describeSchedule(j)}</span>
            </div>
            <div className="cron-row-prompt" data-testid={`cron-row-prompt-${j.name}`}>
              {j.prompt}
            </div>
            <div className="cron-row-foot">
              <label className="cron-row-toggle">
                <input
                  type="checkbox"
                  checked={j.enabled}
                  onChange={() => toggleEnabled(j)}
                  data-testid={`cron-row-toggle-${j.name}`}
                />
                <span>{j.enabled ? 'enabled' : 'disabled'}</span>
              </label>
              <span className="cron-row-meta">
                {j.run_count > 0 ? `ran ${j.run_count}×` : 'never ran'}
                {j.last_run_at && ` · last: ${new Date(j.last_run_at).toLocaleString()}`}
                {j.last_run_status && ` · ${j.last_run_status}`}
              </span>
              <div className="cron-row-actions">
                <button
                  type="button"
                  className="pill pill-violet"
                  onClick={() => runNow(j)}
                  data-testid={`cron-row-runnow-${j.name}`}
                  disabled={!j.enabled}
                >
                  ▶ run now
                </button>
                <button
                  type="button"
                  className="pill pill-default"
                  onClick={() => startEdit(j)}
                  data-testid={`cron-row-edit-${j.name}`}
                >
                  ✎ edit
                </button>
                <button
                  type="button"
                  className="pill pill-rose"
                  onClick={() => deleteJob(j)}
                  data-testid={`cron-row-delete-${j.name}`}
                >
                  🗑 delete
                </button>
              </div>
            </div>
            {j.notes && <div className="cron-row-notes">📝 {j.notes}</div>}
          </div>
          );
        })}
      </div>

      {upcoming.length > 0 && (
        <div className="cron-upcoming" data-testid="cron-jobs-upcoming">
          <h4 className="cron-section-title">Enabled ({upcoming.length})</h4>
          <div className="cron-upcoming-list">
            {upcoming.map((j) => (
              <div key={j.id} className="cron-upcoming-row">
                <span className="cron-upcoming-bullet">⏰</span>
                <span className="cron-upcoming-name">{j.name}</span>
                <span className="cron-upcoming-meta">{describeSchedule(j)} → {j.agent}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentCronJobs;
