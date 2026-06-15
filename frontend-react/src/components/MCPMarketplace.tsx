import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client';
import { useProject } from '../contexts/ProjectContext';
import { PROJECT_SCOPES, scopeColor, scopeLabel } from '../utils/projectScopes';
import { PanelHeader } from './PanelHeader';

// MCPMarketplace (D-2026-06-15):
//   The MCP companion to SkillMarketplace. Each MCP entry is a
//   registry of how to install + use a Model Context Protocol server.
//   The dashboard does NOT install the MCP itself — it just stores
//   the metadata and shows the install command the user can paste.
//
//   Three ways to add an MCP:
//     1. Manual form (URL or name + summary + install command)
//     2. Import by pasting a GitHub URL or webpage URL
//     3. From chat: user types something like "add the playwright MCP"
//        in the chat, the chat calls /mcp/chat-intent →
//        /mcp/install-from-chat, and shows a confirmation card here.

interface MCPItem {
  name: string;
  summary: string;
  description: string;
  icon: string;
  source_type: 'github_url' | 'webpage_url' | 'name';
  source_url: string;
  source_repo: string;
  install_command: string;
  transport: 'stdio' | 'http' | 'sse' | 'websocket';
  scope: string;
  departments: string[];
  assigned_agents: string[];
  trust_tier: 'T1' | 'T2' | 'T3';
  added_by: string;
  added_at: string;
  notes: string;
}

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

function isEmoji(s: string): boolean {
  if (!s) return false;
  // Simple check: first 4 bytes are emoji codepoints
  return /\p{Extended_Pictographic}/u.test(s.slice(0, 4));
}

function skillIcon(m: MCPItem): string {
  if (m.icon && isEmoji(m.icon)) return m.icon;
  if (m.source_type === 'github_url') return '🔗';
  if (m.transport === 'http' || m.transport === 'sse') return '🌐';
  return '🔌';
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

function detectLocalKind(url: string): 'github_url' | 'webpage_url' | 'name' {
  const t = url.trim();
  if (/^https?:\/\/github\.com\//i.test(t)) return 'github_url';
  if (/^https?:\/\//i.test(t)) return 'webpage_url';
  return 'name';
}

function deriveNameFromUrl(url: string): string {
  const t = url.trim();
  const gh = t.match(/^https?:\/\/github\.com\/([A-Za-z0-9._-]+)\/([A-Za-z0-9._-]+?)(?:\.git)?\/?$/i);
  if (gh) return `${gh[1]}-${gh[2]}`.toLowerCase();
  const other = t.match(/^https?:\/\/([^/]+)(?:\/([^?#]*))?/i);
  if (other) {
    const host = other[1].replace(/^www\./, '');
    const path = (other[2] || '').replace(/\/$/, '').split('/').filter(Boolean);
    const last = path[path.length - 1] || host.split('.')[0];
    return last.toLowerCase().replace(/[^a-z0-9_\-]/g, '-').replace(/-+/g, '-').slice(0, 48) || 'unnamed-mcp';
  }
  return t.toLowerCase().replace(/[^a-z0-9_\-]/g, '-').replace(/-+/g, '-').slice(0, 64) || 'unnamed-mcp';
}

function deriveInstallFromUrl(url: string, name: string): string {
  const gh = url.match(/^https?:\/\/github\.com\/([A-Za-z0-9._-]+)\/([A-Za-z0-9._-]+?)(?:\.git)?\/?$/i);
  if (gh) {
    const owner = gh[1], repo = gh[2];
    // Common pattern: many MCPs are npm-scoped as @owner/repo or unscoped as owner/repo
    // Default to npx (most MCPs publish to npm)
    return `npx -y ${owner}/${repo}`;
  }
  return '';
}

function deriveSourceRepoFromUrl(url: string): string {
  const gh = url.match(/^https?:\/\/github\.com\/([A-Za-z0-9._-]+)\/([A-Za-z0-9._-]+?)(?:\.git)?\/?$/i);
  if (gh) return `${gh[1]}/${gh[2]}`;
  return '';
}

function emptyDraft(): Partial<MCPItem> {
  return {
    name: '',
    summary: '',
    description: '',
    icon: '🔌',
    source_type: 'name',
    source_url: '',
    source_repo: '',
    install_command: '',
    transport: 'stdio',
    scope: PROJECT_SCOPES.GLOBAL_HERMES,
    trust_tier: 'T3',
    notes: '',
  };
}

export function MCPMarketplace() {
  const { project } = useProject();
  const activeProject = project?.slug || PROJECT_SCOPES.DEFAULT;

  const [mcps, setMcps] = useState<MCPItem[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [error, setError] = useState<string>('');
  const [saveStatus, setSaveStatus] = useState<string>('');
  const [searchQ, setSearchQ] = useState('');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'github_url' | 'webpage_url' | 'name'>('all');
  const [trustFilter, setTrustFilter] = useState<'all' | 'T1' | 'T2' | 'T3'>('all');
  const [scopeFilter, setScopeFilter] = useState<string>('all');

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState<Partial<MCPItem>>(emptyDraft());
  const [formStatus, setFormStatus] = useState('');
  const [importStatus, setImportStatus] = useState('');
  const hasUserPickedScope = useRef<boolean>(false);

  // Chat-driven install state
  const [chatInstallResult, setChatInstallResult] = useState<{
    name: string;
    detected_kind: string;
    confirmation: string;
    run_command: string;
  } | null>(null);

  // Import-by-URL state
  const [importUrl, setImportUrl] = useState('');

  // ── Load data ───────────────────────────────────────────────
  async function refresh() {
    try {
      const [list, cacheData] = await Promise.all([
        api.listMCPs(),
        api.cache(activeProject || undefined).catch(() => null),
      ]);
      setMcps(list.mcps || []);
      if (cacheData) {
        const list = (cacheData.agents || []).map((a: any) => a.name).filter(Boolean);
        setAgents(sortAgents(list));
      }
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  // ── URL auto-fill helper ────────────────────────────────────
  function applyUrlToDraft(url: string) {
    if (!url.trim()) return;
    const kind = detectLocalKind(url);
    const name = deriveNameFromUrl(url);
    const fill: Partial<MCPItem> = {
      name: draft.name || name,
      source_type: kind,
      source_url: url.trim(),
      source_repo: kind === 'github_url' ? deriveSourceRepoFromUrl(url) : '',
      install_command: draft.install_command || deriveInstallFromUrl(url, name),
    };
    setDraft({ ...draft, ...fill });
  }

  // ── Form handlers ───────────────────────────────────────────
  function startCreate() {
    setDraft({ ...emptyDraft(), scope: PROJECT_SCOPES.GLOBAL_HERMES });
    setFormStatus('');
    setShowForm(true);
  }

  function cancelForm() {
    setShowForm(false);
    setDraft(emptyDraft());
    setFormStatus('');
  }

  async function saveDraft() {
    setFormStatus('saving…');
    if (!draft.name?.trim()) { setFormStatus('name is required'); return; }
    try {
      await api.addMCP({
        name: draft.name,
        summary: draft.summary || '',
        description: draft.description || '',
        icon: draft.icon || '🔌',
        source_type: draft.source_type || 'name',
        source_url: draft.source_url || '',
        source_repo: draft.source_repo || '',
        install_command: draft.install_command || '',
        transport: draft.transport || 'stdio',
        scope: draft.scope || PROJECT_SCOPES.GLOBAL_HERMES,
        trust_tier: draft.trust_tier || 'T3',
        notes: draft.notes || '',
      });
      setFormStatus(`added "${draft.name}"`);
      await refresh();
      cancelForm();
    } catch (e) {
      setFormStatus(`save failed: ${errorMessage(e)}`);
    }
  }

  async function removeMCP(m: MCPItem) {
    if (!confirm(`Remove MCP "${m.name}" from the catalog?`)) return;
    try {
      await api.removeMCP(m.name);
      await refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  // ── URL import handler ──────────────────────────────────────
  async function handleImportUrl() {
    setImportStatus('');
    if (!importUrl.trim()) { setImportStatus('paste a GitHub or webpage URL first'); return; }
    try {
      const result = await api.installMCPFromChat(importUrl.trim(), PROJECT_SCOPES.GLOBAL_HERMES, []);
      setImportStatus(`added ${result.detected_name} (${result.detected_kind})`);
      setChatInstallResult({
        name: result.detected_name,
        detected_kind: result.detected_kind,
        confirmation: result.confirmation,
        run_command: result.run_suggested_command,
      });
      setImportUrl('');
      await refresh();
    } catch (e) {
      setImportStatus(`import failed: ${errorMessage(e)}`);
    }
  }

  // ── Derived: filtered list ─────────────────────────────────
  const filtered = useMemo(() => {
    return mcps.filter((m) => {
      if (sourceFilter !== 'all' && m.source_type !== sourceFilter) return false;
      if (trustFilter !== 'all' && m.trust_tier !== trustFilter) return false;
      if (scopeFilter !== 'all' && (m.scope || '') !== scopeFilter) return false;
      if (searchQ) {
        const q = searchQ.toLowerCase();
        const hay = `${m.name} ${m.summary} ${m.description} ${m.source_url} ${m.source_repo} ${m.install_command}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [mcps, sourceFilter, trustFilter, scopeFilter, searchQ]);

  const scopeCounts = useMemo(() => {
    const c: Record<string, number> = { all: mcps.length };
    c[PROJECT_SCOPES.GLOBAL_HERMES] = mcps.filter((m) => (m.scope || '') === PROJECT_SCOPES.GLOBAL_HERMES).length;
    c[PROJECT_SCOPES.JARVIS_WAR_ROOM] = mcps.filter((m) => (m.scope || '') === PROJECT_SCOPES.JARVIS_WAR_ROOM).length;
    c[activeProject] = mcps.filter((m) => (m.scope || '') === activeProject).length;
    return c;
  }, [mcps, activeProject]);

  return (
    <div className="skill-marketplace" data-testid="mcp-marketplace">
      <PanelHeader
        title="MCP Marketplace"
        subtitle={`${mcps.length} MCP${mcps.length === 1 ? '' : 's'} registered · install commands shown, never run automatically · writes_profile_configs = false`}
        accent="cyan"
      />

      {error && (
        <div className="skill-mkt-error" data-testid="mcp-error">{error}</div>
      )}

      {/* D-2026-06-15: Quick URL import — paste a GitHub or webpage URL */}
      <div className="mcp-url-import" data-testid="mcp-url-import">
        <span className="mcp-url-import-label">Quick add:</span>
        <input
          type="text"
          placeholder="paste a GitHub URL or MCP docs page…"
          value={importUrl}
          onChange={(e) => setImportUrl(e.target.value)}
          data-testid="mcp-url-input"
          onKeyDown={(e) => { if (e.key === 'Enter') handleImportUrl(); }}
        />
        <button
          type="button"
          className="pill pill-emerald"
          onClick={handleImportUrl}
          data-testid="mcp-url-add"
        >
          ➕ Add MCP
        </button>
        {importStatus && <span className="mcp-url-import-status">{importStatus}</span>}
      </div>

      {chatInstallResult && (
        <div className="mcp-chat-confirm" data-testid="mcp-chat-confirm">
          <div className="mcp-chat-confirm-head">
            <span className="mcp-chat-confirm-icon">✅</span>
            <strong>Added MCP: {chatInstallResult.name}</strong>
            <span className="mcp-chat-confirm-kind">({chatInstallResult.detected_kind})</span>
            <button
              type="button"
              className="pill pill-default"
              onClick={() => setChatInstallResult(null)}
              data-testid="mcp-chat-confirm-dismiss"
            >
              dismiss
            </button>
          </div>
          <pre className="mcp-chat-confirm-body">{chatInstallResult.confirmation}</pre>
        </div>
      )}

      {/* Toolbar */}
      <div className="cron-scope-filter" data-testid="mcp-scope-filter">
        <button
          type="button"
          className={`cron-scope-pill ${scopeFilter === 'all' ? 'cron-scope-pill--on' : ''}`}
          onClick={() => setScopeFilter('all')}
          data-testid="mcp-scope-all"
        ><span>All</span><span className="cron-scope-pill-count">{scopeCounts.all}</span></button>
        <button
          type="button"
          className={`cron-scope-pill ${scopeFilter === PROJECT_SCOPES.GLOBAL_HERMES ? 'cron-scope-pill--on cron-scope-pill--amber' : ''}`}
          onClick={() => setScopeFilter(PROJECT_SCOPES.GLOBAL_HERMES)}
          data-testid="mcp-scope-global"
        ><span>🌍 Global Hermes</span><span className="cron-scope-pill-count">{scopeCounts[PROJECT_SCOPES.GLOBAL_HERMES]}</span></button>
        <button
          type="button"
          className={`cron-scope-pill ${scopeFilter === PROJECT_SCOPES.JARVIS_WAR_ROOM ? 'cron-scope-pill--on cron-scope-pill--cyan' : ''}`}
          onClick={() => setScopeFilter(PROJECT_SCOPES.JARVIS_WAR_ROOM)}
          data-testid="mcp-scope-warroom"
        ><span>⚔ Jarvis War Room</span><span className="cron-scope-pill-count">{scopeCounts[PROJECT_SCOPES.JARVIS_WAR_ROOM]}</span></button>
        <button
          type="button"
          className={`cron-scope-pill ${scopeFilter === activeProject ? 'cron-scope-pill--on cron-scope-pill--violet' : ''}`}
          onClick={() => setScopeFilter(activeProject)}
          data-testid="mcp-scope-active"
        ><span>📁 {activeProject}</span><span className="cron-scope-pill-count">{scopeCounts[activeProject] ?? 0}</span></button>
      </div>

      <div className="skill-mkt-filters" data-testid="mcp-filters">
        <input
          type="text"
          placeholder="Search MCP name, summary, source, install command…"
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          className="skill-mkt-search"
          data-testid="mcp-search"
        />
        <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value as any)} data-testid="mcp-source-filter">
          <option value="all">All sources</option>
          <option value="github_url">GitHub</option>
          <option value="webpage_url">Webpage</option>
          <option value="name">Manual</option>
        </select>
        <select value={trustFilter} onChange={(e) => setTrustFilter(e.target.value as any)} data-testid="mcp-trust-filter">
          <option value="all">All tiers</option>
          <option value="T1">T1 (verified)</option>
          <option value="T2">T2 (reviewed)</option>
          <option value="T3">T3 (community)</option>
        </select>
        <button type="button" className="pill pill-emerald" onClick={startCreate} data-testid="mcp-new">
          + New MCP
        </button>
        <button type="button" className="pill pill-default" onClick={refresh} data-testid="mcp-refresh">
          ↻ Refresh
        </button>
        <span className="cron-jobs-meta" data-testid="mcp-count">
          {filtered.length} of {mcps.length} MCP{mcps.length === 1 ? '' : 's'}
        </span>
      </div>

      {saveStatus && <div className="skill-mkt-save-status">{saveStatus}</div>}

      {/* Manual form */}
      {showForm && (
        <div className="cron-form" data-testid="mcp-form">
          <h4 className="cron-form-title">New MCP</h4>
          <div className="cron-form-grid">
            <label className="cron-field">
              <span>Name <span className="cron-req">*</span></span>
              <input
                type="text"
                placeholder="filesystem"
                value={draft.name || ''}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                data-testid="mcp-form-name"
              />
            </label>
            <label className="cron-field">
              <span>Source type <span className="cron-req">*</span></span>
              <select
                value={draft.source_type || 'name'}
                onChange={(e) => setDraft({ ...draft, source_type: e.target.value as any })}
                data-testid="mcp-form-source-type"
              >
                <option value="github_url">GitHub URL</option>
                <option value="webpage_url">Webpage URL</option>
                <option value="name">Bare name (no URL)</option>
              </select>
            </label>
            <label className="cron-field cron-field--wide">
              <span>Source URL</span>
              <input
                type="text"
                placeholder="https://github.com/microsoft/playwright-mcp"
                value={draft.source_url || ''}
                onChange={(e) => { setDraft({ ...draft, source_url: e.target.value }); applyUrlToDraft(e.target.value); }}
                data-testid="mcp-form-source-url"
              />
              <span className="cron-field-hint">
                Paste a URL and the form auto-fills name + install command + source_repo.
              </span>
            </label>
            <label className="cron-field">
              <span>Icon</span>
              <input
                type="text"
                placeholder="🔌"
                value={draft.icon || ''}
                onChange={(e) => setDraft({ ...draft, icon: e.target.value })}
                data-testid="mcp-form-icon"
              />
            </label>
            <label className="cron-field">
              <span>Transport</span>
              <select
                value={draft.transport || 'stdio'}
                onChange={(e) => setDraft({ ...draft, transport: e.target.value as any })}
                data-testid="mcp-form-transport"
              >
                <option value="stdio">stdio (most common)</option>
                <option value="http">http</option>
                <option value="sse">sse (server-sent events)</option>
                <option value="websocket">websocket</option>
              </select>
            </label>
            <label className="cron-field cron-field--wide">
              <span>Summary (1-2 sentences)</span>
              <input
                type="text"
                placeholder="Playwright MCP by Microsoft — browser automation for agents"
                value={draft.summary || ''}
                onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
                data-testid="mcp-form-summary"
              />
            </label>
            <label className="cron-field cron-field--wide">
              <span>Description</span>
              <textarea
                rows={2}
                placeholder="What does this MCP do?"
                value={draft.description || ''}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                data-testid="mcp-form-description"
              />
            </label>
            <label className="cron-field cron-field--wide">
              <span>Install command</span>
              <input
                type="text"
                placeholder="npx -y @microsoft/playwright-mcp"
                value={draft.install_command || ''}
                onChange={(e) => setDraft({ ...draft, install_command: e.target.value })}
                data-testid="mcp-form-install"
              />
              <span className="cron-field-hint">
                The user will run this themselves. The dashboard NEVER executes it.
              </span>
            </label>
            <label className="cron-field">
              <span>Scope</span>
              <select
                value={
                  draft.scope === PROJECT_SCOPES.GLOBAL_HERMES
                  || draft.scope === PROJECT_SCOPES.JARVIS_WAR_ROOM
                  || draft.scope === activeProject
                    ? draft.scope
                    : '__custom__'
                }
                onChange={(e) => {
                  hasUserPickedScope.current = true;
                  const v = e.target.value;
                  setDraft({ ...draft, scope: v === '__custom__' ? '' : v });
                }}
                data-testid="mcp-form-scope"
              >
                <option value={PROJECT_SCOPES.GLOBAL_HERMES}>🌍 Global Hermes</option>
                <option value={PROJECT_SCOPES.JARVIS_WAR_ROOM}>⚔ Jarvis War Room</option>
                <option value={activeProject}>📁 {activeProject}</option>
                <option value="__custom__">Custom…</option>
              </select>
            </label>
            <label className="cron-field">
              <span>Trust tier</span>
              <select
                value={draft.trust_tier || 'T3'}
                onChange={(e) => setDraft({ ...draft, trust_tier: e.target.value as any })}
                data-testid="mcp-form-trust"
              >
                <option value="T1">T1 (verified)</option>
                <option value="T2">T2 (reviewed)</option>
                <option value="T3">T3 (community)</option>
              </select>
            </label>
            <label className="cron-field cron-field--wide">
              <span>Notes</span>
              <input
                type="text"
                value={draft.notes || ''}
                onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
                data-testid="mcp-form-notes"
              />
            </label>
          </div>
          <div className="cron-form-actions">
            <button type="button" className="pill pill-emerald" onClick={saveDraft} data-testid="mcp-form-save">
              Add MCP
            </button>
            <button type="button" className="pill pill-default" onClick={cancelForm} data-testid="mcp-form-cancel">
              Cancel
            </button>
            {formStatus && <span className="cron-form-status" data-testid="mcp-form-status">{formStatus}</span>}
          </div>
        </div>
      )}

      {/* List */}
      <div className="skill-mkt-list" data-testid="mcp-list">
        {mcps.length === 0 && (
          <div className="cron-empty" data-testid="mcp-empty">
            No MCPs yet. Paste a GitHub URL above, click <b>+ New MCP</b>, or say "add the filesystem MCP" in chat.
          </div>
        )}
        {filtered.length === 0 && mcps.length > 0 && (
          <div className="cron-empty" data-testid="mcp-filter-empty">
            No MCPs match the current filters.
          </div>
        )}
        {filtered.map((m) => {
          const color = scopeColor(m.scope || '');
          return (
            <div key={m.name} className="skill-mkt-card" data-testid={`mcp-row-${m.name}`}>
              <div className="skill-mkt-card-head">
                <span className="skill-mkt-icon">
                  {isEmoji(skillIcon(m)) ? skillIcon(m) : '🔌'}
                </span>
                <span className="skill-mkt-name">{m.name}</span>
                <span className="pill pill-cyan">{m.source_type.replace('_url', '')}</span>
                <span className={`pill ${m.trust_tier === 'T1' ? 'pill-emerald' : m.trust_tier === 'T2' ? 'pill-amber' : 'pill-rose'}`}>
                  {m.trust_tier}
                </span>
                <span
                  className={`cron-scope-badge cron-scope-badge--${color}`}
                  data-testid={`mcp-row-scope-${m.name}`}
                  title={`Scope: ${scopeLabel(m.scope || '')}`}
                >
                  {m.scope === PROJECT_SCOPES.GLOBAL_HERMES && '🌍 '}
                  {m.scope === PROJECT_SCOPES.JARVIS_WAR_ROOM && '⚔ '}
                  {m.scope && m.scope !== PROJECT_SCOPES.GLOBAL_HERMES && m.scope !== PROJECT_SCOPES.JARVIS_WAR_ROOM && '📁 '}
                  {scopeLabel(m.scope || '')}
                </span>
                <span className="pill pill-default">{m.transport}</span>
              </div>
              {(m.summary || m.description) && (
                <div className="skill-mkt-card-body">
                  {m.summary && <div className="skill-mkt-summary" data-testid={`mcp-row-summary-${m.name}`}>{m.summary}</div>}
                </div>
              )}
              {m.source_url && (
                <div className="skill-mkt-source">🔗 {m.source_url}</div>
              )}
              {m.install_command && (
                <div className="mcp-install-cmd" data-testid={`mcp-row-install-${m.name}`}>
                  <span className="mcp-install-cmd-label">Run this to install:</span>
                  <code>{m.install_command}</code>
                </div>
              )}
              {m.assigned_agents && m.assigned_agents.length > 0 && (
                <div className="mcp-assigned-agents">
                  Assigned to: {m.assigned_agents.map((a) => <span key={a} className="pill pill-violet">{a}</span>)}
                </div>
              )}
              {m.notes && <div className="skill-mkt-imported-notes">📝 {m.notes}</div>}
              <div className="skill-mkt-card-actions">
                <span className="skill-mkt-card-meta">
                  Added {new Date(m.added_at).toLocaleDateString()} by {m.added_by}
                </span>
                <button type="button" className="pill pill-rose" onClick={() => removeMCP(m)} data-testid={`mcp-row-delete-${m.name}`}>
                  🗑 remove
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default MCPMarketplace;
