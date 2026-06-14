import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client';
import type { CatalogPayload, CatalogSkill } from '../types/dashboard';
import { useProject } from '../contexts/ProjectContext';
import { PanelHeader } from './PanelHeader';

// D-2026-06-14 (Skill Marketplace v3 — user feedback):
//
// Three jobs, all safety-locked (writes_profile_configs: false):
//
//   1. IMPORT — collapsible form at the top. Paste a GitHub URL (or
//      local path), give the skill a name + 1-2 sentence summary, pick
//      an icon (emoji or URL), a trust tier, and which departments can
//      see it. Persists to `agent_skill_catalog.json`.
//
//   2. ASSIGN — pick a target agent (Orchestrator pinned at the top
//      via `sortAgents`) and a project. Then open the **searchable
//      dropdown** to add skills to the basket. The dropdown is a single
//      text input + a filtered list with checkbox + icon + name +
//      summary (1-2 sentence blurb). Each selected skill appears as a
//      removable chip below the input. Click "Assign N skills to
//      <agent>" to save (upserts per-agent per-project record in
//      `agent_skill_assignments.json`).
//
//   3. MANAGE — list the user's already-imported skills with a delete
//      button per row. (Filesystem skills are read-only and not listed
//      here — they're in the dropdown for assignment.)
//
// Per-agent per-project assignments are read back from the backend on
// agent/project change so the basket is pre-populated with what the
// agent already has.

const TRUST_TIERS: Array<{ value: 'T1' | 'T2' | 'T3' | ''; label: string; tone: string }> = [
  { value: '', label: 'All', tone: 'pill-default' },
  { value: 'T1', label: 'T1 curated', tone: 'pill-emerald' },
  { value: 'T2', label: 'T2 bulk', tone: 'pill-amber' },
  { value: 'T3', label: 'T3 community', tone: 'pill-rose' },
];

const DEPARTMENTS = [
  'all', 'jarvis-frontend', 'jarvis-backend', 'jarvis-ui_ux', 'jarvis-mobile',
  'jarvis-devops', 'jarvis-security-lead', 'jarvis-qa-lead',
  'jarvis-data-ml', 'jarvis-marketing', 'jarvis-sales',
  'jarvis-product-lead', 'jarvis-finance', 'jarvis-legal',
  'jarvis-customer-success', 'jarvis-researcher', 'jarvis-docs-lead',
  'jarvis-secretary', 'jarvis-engineering-lead', 'jarvis-boss',
];

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function skillIcon(s: CatalogSkill): string {
  if (s.icon_url) return s.icon_url;
  if (s.trust_tier === 'T1') return '✅';
  if (s.trust_tier === 'T2') return '📦';
  return '🧩';
}

function isEmoji(s: string): boolean {
  // very rough — matches if the first char is in an emoji range
  return /[\p{Emoji}\p{Extended_Pictographic}]/u.test(s);
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

export function SkillMarketplace() {
  const { project } = useProject();
  const activeProject = project?.slug || 'default';

  const [catalog, setCatalog] = useState<CatalogPayload | null>(null);
  const [importedSkills, setImportedSkills] = useState<any[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [department, setDepartment] = useState<string>('all');
  const [trustFilter, setTrustFilter] = useState<'T1' | 'T2' | 'T3' | ''>('T1');
  const [targetAgent, setTargetAgent] = useState<string>('');
  const [targetProject, setTargetProject] = useState<string>(activeProject);
  const [basket, setBasket] = useState<Set<string>>(new Set());
  const [saveStatus, setSaveStatus] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // ── Dropdown state ──────────────────────────────────────────────
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [dropdownQuery, setDropdownQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  // ── Import form ─────────────────────────────────────────────────
  const [importOpen, setImportOpen] = useState(false);
  const [importName, setImportName] = useState('');
  const [importSummary, setImportSummary] = useState('');
  const [importDescription, setImportDescription] = useState('');
  const [importSourceRepo, setImportSourceRepo] = useState('');
  const [importSourcePath, setImportSourcePath] = useState('');
  const [importIcon, setImportIcon] = useState('');
  const [importTrust, setImportTrust] = useState<'T1' | 'T2' | 'T3'>('T3');
  const [importDepartments, setImportDepartments] = useState<string[]>(['jarvis-boss']);
  const [importStatus, setImportStatus] = useState<string>('');

  // Close the dropdown on outside-click
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  // Initial load
  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.catalog(),
      api.listImportedSkills(),
      api.cache(activeProject || undefined),
    ])
      .then(([cat, imp, cacheData]) => {
        setCatalog(cat);
        setImportedSkills(imp?.skills || []);
        const list = (cacheData?.agents || []).map((a) => a.name).filter(Boolean);
        const sorted = sortAgents(list);
        setAgents(sorted);
        if (sorted.length && !targetAgent) {
          setTargetAgent(sorted[0]);
        }
      })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeProject) setTargetProject(activeProject);
  }, [activeProject]);

  // Pre-populate basket with the agent's current assignment
  useEffect(() => {
    if (!targetAgent) return;
    api.agentSkillsByProject(targetAgent, targetProject)
      .then((data) => setBasket(new Set(data.skills || [])))
      .catch(() => setBasket(new Set()));
  }, [targetAgent, targetProject]);

  // ── Filtered list shown in the dropdown ────────────────────────
  const dropdownSkills = useMemo<CatalogSkill[]>(() => {
    if (!catalog) return [];
    const ql = dropdownQuery.trim().toLowerCase();
    return catalog.skills.filter((s) => {
      if (department && department !== 'all' && !(s.departments || []).includes(department)) return false;
      if (trustFilter && s.trust_tier !== trustFilter) return false;
      if (ql) {
        const hay = `${s.name} ${s.description || ''} ${s.summary || ''} ${(s.departments || []).join(' ')}`.toLowerCase();
        if (!hay.includes(ql)) return false;
      }
      return true;
    });
  }, [catalog, department, trustFilter, dropdownQuery]);

  function toggleBasket(name: string) {
    setBasket((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function addAllVisible() {
    setBasket((prev) => {
      const next = new Set(prev);
      for (const s of dropdownSkills) next.add(s.name);
      return next;
    });
  }

  function clearBasket() {
    setBasket(new Set());
    setSaveStatus('cleared (unsaved)');
  }

  async function handleAssign() {
    if (!targetAgent) {
      setError('pick a target agent first');
      return;
    }
    setSaveStatus('saving…');
    setError('');
    try {
      const skills = Array.from(basket);
      await api.saveAgentSkillsByProject(targetProject, targetAgent, skills, '');
      setSaveStatus(
        `assigned ${skills.length} skill(s) to ${targetAgent} for project ${targetProject}`,
      );
      setDropdownOpen(false);
    } catch (e) {
      setError(errorMessage(e));
      setSaveStatus('');
    }
  }

  // ── Import flow ────────────────────────────────────────────────
  async function handleImport() {
    setError('');
    setImportStatus('');
    if (!importName.trim() || !importSummary.trim()) {
      setImportStatus('name and summary are required');
      return;
    }
    try {
      const result = await (api as any).importSkill({
        name: importName.trim(),
        summary: importSummary.trim(),
        description: importDescription.trim(),
        source_repo: importSourceRepo.trim(),
        source_path: importSourcePath.trim(),
        icon_url: importIcon.trim(),
        trust_tier: importTrust,
        departments: importDepartments,
        category: 'user-imported',
      });
      setImportStatus(
        `imported "${result.skill.name}" — catalog now has ${result.catalog_size} user-imported skill(s)`,
      );
      // Refresh both the catalog and the imported-skills list
      const [cat, imp] = await Promise.all([api.catalog(), api.listImportedSkills()]);
      setCatalog(cat);
      setImportedSkills(imp?.skills || []);
      // Auto-add to basket + open the dropdown so the user can pick an agent
      setBasket((prev) => {
        const next = new Set(prev);
        next.add(result.skill.name);
        return next;
      });
      setDropdownOpen(true);
      // Reset form
      setImportName('');
      setImportSummary('');
      setImportDescription('');
      setImportSourceRepo('');
      setImportSourcePath('');
      setImportIcon('');
      setImportTrust('T3');
      setImportDepartments(['jarvis-boss']);
    } catch (e) {
      setImportStatus(`import failed: ${errorMessage(e)}`);
    }
  }

  async function handleDeleteImport(name: string) {
    if (!confirm(`Remove imported skill "${name}" from the catalog?`)) return;
    try {
      await (api as any).removeImportedSkill(name);
      const [cat, imp] = await Promise.all([api.catalog(), api.listImportedSkills()]);
      setCatalog(cat);
      setImportedSkills(imp?.skills || []);
      setBasket((prev) => {
        const next = new Set(prev);
        next.delete(name);
        return next;
      });
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  function toggleImportDept(dept: string) {
    setImportDepartments((prev) =>
      prev.includes(dept) ? prev.filter((d) => d !== dept) : [...prev, dept],
    );
  }

  return (
    <div className="dashboard-card skill-marketplace" data-testid="skill-marketplace">
      <PanelHeader
        title="Skill Marketplace + Agent Growth"
        subtitle={`Browse ${catalog?.summary?.total_skills ?? '…'} skills · import from GitHub · assign to any agent in any project.`}
        accent="cyan"
      />

      {/* ── IMPORT FORM (collapsible) ──────────────────────────── */}
      <div className="skill-mkt-import" data-testid="skill-mkt-import-panel">
        <button
          type="button"
          className="skill-mkt-toggle"
          onClick={() => setImportOpen((v) => !v)}
          data-testid="skill-mkt-toggle-import"
        >
          {importOpen ? '▾' : '▸'} {importOpen ? 'Hide' : 'Show'} import form
          {importStatus && <span className="skill-mkt-import-status"> · {importStatus}</span>}
        </button>
        {importOpen && (
          <div className="skill-mkt-import-body">
            <p className="skill-mkt-hint">
              Add a skill from a copied GitHub repo (or any local path). Fields
              marked <span className="skill-mkt-req">*</span> are required.
              Imported skills persist locally and are immediately available
              for assignment — no profile mutation.
            </p>
            <div className="skill-mkt-form-grid">
              <label className="skill-mkt-field">
                <span>Name <span className="skill-mkt-req">*</span></span>
                <input
                  type="text"
                  placeholder="code-review-assistant"
                  value={importName}
                  onChange={(e) => setImportName(e.target.value)}
                  data-testid="skill-mkt-import-name"
                />
              </label>
              <label className="skill-mkt-field">
                <span>1-2 sentence summary <span className="skill-mkt-req">*</span></span>
                <input
                  type="text"
                  placeholder="Reviews PRs for style, security, test coverage. Posts inline comments + a summary verdict."
                  value={importSummary}
                  onChange={(e) => setImportSummary(e.target.value)}
                  data-testid="skill-mkt-import-summary"
                  maxLength={400}
                />
              </label>
              <label className="skill-mkt-field">
                <span>Long description (optional)</span>
                <input
                  type="text"
                  placeholder="Detailed description shown in the skill detail view"
                  value={importDescription}
                  onChange={(e) => setImportDescription(e.target.value)}
                  data-testid="skill-mkt-import-description"
                  maxLength={2000}
                />
              </label>
              <label className="skill-mkt-field">
                <span>Source repo (GitHub URL or local path)</span>
                <input
                  type="text"
                  placeholder="https://github.com/user/skills"
                  value={importSourceRepo}
                  onChange={(e) => setImportSourceRepo(e.target.value)}
                  data-testid="skill-mkt-import-repo"
                />
              </label>
              <label className="skill-mkt-field">
                <span>Path within repo (optional)</span>
                <input
                  type="text"
                  placeholder="skills/code-review-assistant/SKILL.md"
                  value={importSourcePath}
                  onChange={(e) => setImportSourcePath(e.target.value)}
                  data-testid="skill-mkt-import-path"
                />
              </label>
              <label className="skill-mkt-field">
                <span>Icon (emoji or URL)</span>
                <input
                  type="text"
                  placeholder="🔍  or  https://example.com/logo.png"
                  value={importIcon}
                  onChange={(e) => setImportIcon(e.target.value)}
                  data-testid="skill-mkt-import-icon"
                  maxLength={500}
                />
              </label>
              <label className="skill-mkt-field">
                <span>Trust tier</span>
                <select
                  value={importTrust}
                  onChange={(e) => setImportTrust(e.target.value as 'T1' | 'T2' | 'T3')}
                  data-testid="skill-mkt-import-trust"
                >
                  <option value="T1">T1 — curated (I trust this)</option>
                  <option value="T2">T2 — bulk (community-reviewed)</option>
                  <option value="T3">T3 — community (any source)</option>
                </select>
              </label>
              <div className="skill-mkt-field skill-mkt-field--wide">
                <span>Departments (who can use this skill)</span>
                <div className="skill-mkt-dept-grid">
                  {DEPARTMENTS.filter((d) => d !== 'all').map((d) => (
                    <label key={d} className="skill-mkt-dept-pick">
                      <input
                        type="checkbox"
                        checked={importDepartments.includes(d)}
                        onChange={() => toggleImportDept(d)}
                        data-testid={`skill-mkt-import-dept-${d}`}
                      />
                      <span>{d}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="skill-mkt-import-actions">
              <button
                type="button"
                className="pill pill-emerald"
                onClick={handleImport}
                data-testid="skill-mkt-import-submit"
              >
                Import skill
              </button>
              <button
                type="button"
                className="pill pill-default"
                onClick={() => {
                  setImportName('');
                  setImportSummary('');
                  setImportDescription('');
                  setImportSourceRepo('');
                  setImportSourcePath('');
                  setImportIcon('');
                  setImportTrust('T3');
                  setImportDepartments(['jarvis-boss']);
                  setImportStatus('');
                }}
                data-testid="skill-mkt-import-reset"
              >
                Reset
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── ASSIGN WIDGET (agent + project + searchable dropdown) ── */}
      <div className="skill-mkt-assign" data-testid="skill-mkt-assign-panel">
        <div className="skill-mkt-assign-row">
          <label className="skill-mkt-control">
            <span className="skill-mkt-label">Target agent</span>
            <select
              value={targetAgent}
              onChange={(e) => setTargetAgent(e.target.value)}
              data-testid="skill-mkt-target-agent"
              aria-label="Target agent"
            >
              {agents.length === 0 && <option value="">(no agents loaded)</option>}
              {agents.map((a) => (
                <option key={a} value={a}>
                  {a === targetAgent ? '🎯 ' : ''}{a}
                </option>
              ))}
            </select>
          </label>
          <label className="skill-mkt-control">
            <span className="skill-mkt-label">Project</span>
            <input
              type="text"
              value={targetProject}
              onChange={(e) => setTargetProject(e.target.value)}
              data-testid="skill-mkt-target-project"
            />
          </label>
          <div className="skill-mkt-assign-actions">
            <button
              type="button"
              className="pill pill-emerald"
              onClick={handleAssign}
              data-testid="skill-mkt-assign-save"
              disabled={!targetAgent}
            >
              Assign {basket.size} skill{basket.size === 1 ? '' : 's'} to {targetAgent || '…'}
            </button>
            <button
              type="button"
              className="pill pill-rose"
              onClick={clearBasket}
              data-testid="skill-mkt-clear"
            >
              Clear
            </button>
          </div>
        </div>

        {/* ── THE DROPDOWN (searchable, checkboxes) ── */}
        <div className="skill-mkt-dd" ref={dropdownRef} data-testid="skill-mkt-dd">
          <div className="skill-mkt-dd-input-row">
            <input
              type="search"
              placeholder={`Search ${catalog?.skills?.length ?? '…'} skills to add to ${targetAgent || 'agent'}'s basket…`}
              value={dropdownQuery}
              onChange={(e) => setDropdownQuery(e.target.value)}
              onFocus={() => setDropdownOpen(true)}
              data-testid="skill-mkt-dd-input"
              className="skill-mkt-dd-search"
            />
            <button
              type="button"
              className="skill-mkt-dd-toggle"
              onClick={() => setDropdownOpen((v) => !v)}
              data-testid="skill-mkt-dd-toggle"
              aria-label="Toggle skill list"
            >
              {dropdownOpen ? '▴' : '▾'}
            </button>
          </div>

          {dropdownOpen && (
            <div className="skill-mkt-dd-menu" data-testid="skill-mkt-dd-menu">
              <div className="skill-mkt-dd-filters">
                <label className="skill-mkt-control">
                  <span className="skill-mkt-label">Department</span>
                  <select
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    data-testid="skill-mkt-department"
                  >
                    {DEPARTMENTS.map((d) => (
                      <option key={d} value={d}>
                        {d === 'all' ? 'all' : d}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="skill-mkt-control skill-mkt-control--grow">
                  <span className="skill-mkt-label">Trust tier</span>
                  <div className="skill-mkt-pills">
                    {TRUST_TIERS.map((t) => (
                      <button
                        key={t.value || 'all'}
                        type="button"
                        className={`pill ${trustFilter === t.value ? 'pill-active' : ''} ${t.tone}`}
                        onClick={() => setTrustFilter(t.value)}
                        data-testid={`skill-mkt-trust-${t.value || 'all'}`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>
                <button
                  type="button"
                  className="pill pill-violet"
                  onClick={addAllVisible}
                  data-testid="skill-mkt-dd-add-all"
                  disabled={dropdownSkills.length === 0}
                >
                  + add all visible
                </button>
              </div>

              <div className="skill-mkt-dd-list" data-testid="skill-mkt-dd-list">
                {loading && <div className="skill-mkt-empty">loading catalog…</div>}
                {!loading && dropdownSkills.length === 0 && (
                  <div className="skill-mkt-empty" data-testid="skill-mkt-empty">
                    no skills match. Try a different department, trust tier, or search term.
                  </div>
                )}
                {dropdownSkills.map((s) => {
                  const inBasket = basket.has(s.name);
                  const icon = skillIcon(s);
                  return (
                    <label
                      key={s.name}
                      className={`skill-mkt-dd-row ${inBasket ? 'skill-mkt-dd-row--in-basket' : ''}`}
                      data-testid={`skill-mkt-dd-row-${s.name}`}
                    >
                      <input
                        type="checkbox"
                        checked={inBasket}
                        onChange={() => toggleBasket(s.name)}
                        data-testid={`skill-mkt-dd-checkbox-${s.name}`}
                      />
                      <span className="skill-mkt-dd-icon">
                        {isEmoji(icon) ? icon : <img src={icon} alt="" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />}
                      </span>
                      <div className="skill-mkt-dd-body">
                        <div className="skill-mkt-dd-head">
                          <span className="skill-mkt-dd-name">{s.name}</span>
                          <span className={`pill ${s.trust_tier === 'T1' ? 'pill-emerald' : s.trust_tier === 'T2' ? 'pill-amber' : 'pill-rose'}`}>
                            {s.trust_tier}
                          </span>
                          {s.category && <span className="pill pill-default">{s.category}</span>}
                        </div>
                        <div className="skill-mkt-dd-summary" data-testid={`skill-mkt-dd-summary-${s.name}`}>
                          {s.summary || s.description || '(no description)'}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── BASKET chips ── */}
        {basket.size > 0 && (
          <div className="skill-mkt-basket" data-testid="skill-mkt-basket">
            <span className="skill-mkt-basket-label">Basket ({basket.size}):</span>
            {[...basket].map((name) => {
              const s = catalog?.skills?.find((x) => x.name === name);
              const icon = s ? skillIcon(s) : '🧩';
              return (
                <span key={name} className="skill-mkt-chip" data-testid={`skill-mkt-chip-${name}`}>
                  <span className="skill-mkt-chip-icon">{isEmoji(icon) ? icon : '🧩'}</span>
                  <span className="skill-mkt-chip-name">{name}</span>
                  <button
                    type="button"
                    className="skill-mkt-chip-x"
                    onClick={() => toggleBasket(name)}
                    data-testid={`skill-mkt-chip-x-${name}`}
                    aria-label={`Remove ${name} from basket`}
                  >×</button>
                </span>
              );
            })}
            <button
              type="button"
              className="skill-mkt-basket-clear"
              onClick={clearBasket}
              data-testid="skill-mkt-basket-clear"
            >
              clear all
            </button>
          </div>
        )}

        {saveStatus && (
          <div className="skill-mkt-status" data-testid="skill-mkt-assign-status">
            {saveStatus}
          </div>
        )}
        {error && (
          <div className="skill-mkt-error" data-testid="skill-mkt-assign-error">
            {error}
          </div>
        )}
      </div>

      {/* ── USER-IMPORTED SKILLS (manage) ──────────────────────── */}
      {importedSkills.length > 0 && (
        <div className="skill-mkt-imported" data-testid="skill-mkt-imported">
          <h4 className="skill-mkt-section-title">Your imported skills ({importedSkills.length})</h4>
          <div className="skill-mkt-imported-list">
            {importedSkills.map((s) => {
              const icon = s.icon_url || '🧩';
              return (
                <div key={s.name} className="skill-mkt-imported-row" data-testid={`skill-mkt-imported-row-${s.name}`}>
                  <span className="skill-mkt-dd-icon">{isEmoji(icon) ? icon : '🧩'}</span>
                  <div className="skill-mkt-imported-body">
                    <div className="skill-mkt-imported-name">{s.name}</div>
                    <div className="skill-mkt-imported-summary">{s.summary || s.description || '(no description)'}</div>
                    {s.source_repo && (
                      <div className="skill-mkt-imported-source">📦 {s.source_repo}</div>
                    )}
                  </div>
                  <span className="pill pill-default">{s.trust_tier}</span>
                  <button
                    type="button"
                    className="skill-mkt-imported-del"
                    onClick={() => handleDeleteImport(s.name)}
                    data-testid={`skill-mkt-imported-del-${s.name}`}
                    aria-label={`Delete imported skill ${s.name}`}
                  >
                    Delete
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default SkillMarketplace;
