import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type {
  AgentProposal,
  AgentProposalRequest,
  RemovedAgent,
  AgentSkillAssignment,
  RoleMapping,
  RolePayload,
  SkillItem,
} from '../types/dashboard';
import { PanelHeader } from './PanelHeader';
import { RoleMatrixSkillFeed, RoleMatrixSkillPicker } from './RoleMatrixSkillFeed';

const STATUS_CLASS: Record<RoleMapping['status'], string> = {
  active: 'text-emerald-300 border-emerald-400/40 bg-emerald-400/10',
  standby: 'text-amber-300 border-amber-400/40 bg-amber-400/10',
  disabled: 'text-gray-400 border-gray-500/40 bg-gray-500/10',
};

function cloneRoles(roles: RoleMapping[]): RoleMapping[] {
  return roles.map(role => ({ ...role }));
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function safeSlug(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9_.-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48);
}

function daysUntil(value: string): number {
  const end = new Date(value).getTime();
  if (!Number.isFinite(end)) return 0;
  return Math.max(0, Math.ceil((end - Date.now()) / 86_400_000));
}

function emptyRole(index: number): RoleMapping {
  return {
    role_id: `custom-${Date.now().toString(36)}-${index}`,
    label: 'New Role',
    assigned_agent: '',
    provider: '',
    model: '',
    status: 'standby',
    platform: 'dashboard',
    notes: 'Dashboard-local role. No profile configs changed.',
  };
}

function emptyProposal(agentNames: string[], skills: SkillItem[]): AgentProposalRequest {
  return {
    agent_name: `jarvis-${safeSlug('new-agent')}`,
    description: '',
    provider: '',
    model: '',
    clone_from: agentNames.includes('jarvis-docs-lead') ? 'jarvis-docs-lead' : 'jarvis',
    skills: skills.slice(0, 3).map(skill => skill.name),
    notes: '',
  };
}

export function RoleMatrix() {
  const [payload, setPayload] = useState<RolePayload | null>(null);
  const [roles, setRoles] = useState<RoleMapping[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [assignments, setAssignments] = useState<AgentSkillAssignment[]>([]);
  const [proposals, setProposals] = useState<AgentProposal[]>([]);
  const [removedAgents, setRemovedAgents] = useState<RemovedAgent[]>([]);
  const [proposalDraft, setProposalDraft] = useState<AgentProposalRequest | null>(null);
  const [pendingRemove, setPendingRemove] = useState<AgentProposal | null>(null);
  const [removeReason, setRemoveReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [savingSkills, setSavingSkills] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [message, setMessage] = useState('Loading role matrix...');

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.roles(),
      api.skills(),
      api.agentSkills(),
      api.agentProposals(),
      api.removedAgents(),
    ])
      .then(([roleData, skillData, skillAssignments, proposalData, removedData]) => {
        if (cancelled) return;
        setPayload(roleData);
        setRoles(cloneRoles(roleData.roles));
        setSkills(skillData.skills);
        setAssignments(skillAssignments.assignments);
        setProposals(proposalData.proposals);
        setRemovedAgents(removedData.removed_agents);
        setProposalDraft(emptyProposal(roleData.available_agents.map(agent => agent.name), skillData.skills));
        setMessage('Agent Growth Studio loaded. Profile mutations are proposal-gated.');
      })
      .catch((error: unknown) => {
        if (!cancelled) setMessage(`Agent Growth Studio failed: ${errorMessage(error)}`);
      });
    return () => { cancelled = true; };
  }, []);

  const agentNames = useMemo(() => payload?.available_agents.map(agent => agent.name).sort() || [], [payload]);
  const providers = useMemo(() => {
    const seen = new Set<string>();
    for (const item of payload?.models || []) {
      if (item.provider) seen.add(item.provider);
    }
    for (const role of roles) {
      if (role.provider) seen.add(role.provider);
    }
    return Array.from(seen).sort();
  }, [payload, roles]);
  const activeCount = roles.filter(role => role.status === 'active').length;

  function modelOptions(provider: string): string[] {
    const seen = new Set<string>();
    for (const item of payload?.models || []) {
      if (!provider || item.provider === provider) seen.add(item.model);
    }
    return Array.from(seen).filter(Boolean).sort();
  }

  function updateRole(index: number, patch: Partial<RoleMapping>) {
    setRoles(current => current.map((role, i) => i === index ? { ...role, ...patch } : role));
  }

  function addRole() {
    setRoles(current => [...current, emptyRole(current.length + 1)]);
    setMessage('Added dashboard-local role row. Save role overlay to persist it.');
  }

  function removeRole(index: number) {
    const role = roles[index];
    const ok = window.confirm(`Remove role row "${role?.label || 'unnamed'}" from the dashboard overlay? This does not delete any Hermes agent profile.`);
    if (!ok) return;
    setRoles(current => current.filter((_role, i) => i !== index));
  }

  async function save() {
    setSaving(true);
    try {
      const data = await api.saveRoles(roles);
      setPayload(data);
      setRoles(cloneRoles(data.roles));
      setMessage(`Saved ${data.roles.length} dashboard-local role mappings. No profiles changed.`);
    } catch (error: unknown) {
      setMessage(`Save failed: ${errorMessage(error)}`);
    } finally {
      setSaving(false);
    }
  }

  function updateAssignment(agent: string, skill: string, checked: boolean) {
    setAssignments(current => {
      const existing = current.find(item => item.agent === agent) || { agent, skills: [], notes: '' };
      const nextSkills = checked
        ? Array.from(new Set([...existing.skills, skill])).sort()
        : existing.skills.filter(item => item !== skill);
      const updated = { ...existing, skills: nextSkills };
      const without = current.filter(item => item.agent !== agent);
      return [...without, updated].sort((a, b) => a.agent.localeCompare(b.agent));
    });
  }

  function assignmentFor(agent: string): AgentSkillAssignment {
    return assignments.find(item => item.agent === agent) || { agent, skills: [], notes: '' };
  }

  async function saveSkills() {
    setSavingSkills(true);
    try {
      const data = await api.saveAgentSkills(assignments.filter(item => item.skills.length || item.notes));
      setAssignments(data.assignments);
      setMessage(`Saved skills for ${data.assignments.length} agents. Overlay only; no profile configs changed.`);
    } catch (error: unknown) {
      setMessage(`Skill save failed: ${errorMessage(error)}`);
    } finally {
      setSavingSkills(false);
    }
  }

  function setProposalField<K extends keyof AgentProposalRequest>(key: K, value: AgentProposalRequest[K]) {
    setProposalDraft(current => current ? { ...current, [key]: value } : current);
  }

  function toggleProposalSkill(skill: string, checked: boolean) {
    setProposalDraft(current => {
      if (!current) return current;
      const next = checked
        ? Array.from(new Set([...current.skills, skill])).sort()
        : current.skills.filter(item => item !== skill);
      return { ...current, skills: next };
    });
  }

  async function proposeAgent() {
    if (!proposalDraft) return;
    setProposing(true);
    try {
      const proposal = await api.proposeAgent(proposalDraft);
      setProposals(current => [proposal, ...current]);
      setMessage(`Proposed ${proposal.request.agent_name}. No profile directory was created.`);
    } catch (error: unknown) {
      setMessage(`Proposal failed: ${errorMessage(error)}`);
    } finally {
      setProposing(false);
    }
  }

  async function confirmRemoveAgent() {
    if (!pendingRemove) return;
    try {
      const data = await api.removeAgent(pendingRemove.request.agent_name, removeReason || 'Removed from Agent Growth Studio');
      setRemovedAgents(current => [data.removed_agent, ...current]);
      setProposals(current => current.filter(item => item.proposal_id !== pendingRemove.proposal_id));
      setAssignments(current => current.filter(item => item.agent !== pendingRemove.request.agent_name));
      setMessage(`Removed ${pendingRemove.request.agent_name}. Backup retained for ${data.removed_agent.retention_days} days.`);
      setPendingRemove(null);
      setRemoveReason('');
    } catch (error: unknown) {
      setMessage(`Remove failed: ${errorMessage(error)}`);
    }
  }

  async function restoreAgent(removed: RemovedAgent) {
    const ok = window.confirm(`Restore ${removed.agent_name} from backup? This restores the dashboard proposal and skill overlay only.`);
    if (!ok) return;
    try {
      await api.restoreAgent(removed.removed_id);
      const [proposalData, assignmentData, removedData] = await Promise.all([api.agentProposals(), api.agentSkills(), api.removedAgents()]);
      setProposals(proposalData.proposals);
      setAssignments(assignmentData.assignments);
      setRemovedAgents(removedData.removed_agents);
      setMessage(`Restored ${removed.agent_name} from backup. No profile configs changed.`);
    } catch (error: unknown) {
      setMessage(`Restore failed: ${errorMessage(error)}`);
    }
  }

  async function permanentlyDeleteAgent(removed: RemovedAgent) {
    const confirmText = window.prompt(`Permanently delete the dashboard backup for ${removed.agent_name}? Type exactly: DELETE ${removed.agent_name}`);
    if (!confirmText) return;
    try {
      await api.permanentlyDeleteAgent(removed.removed_id, confirmText);
      const data = await api.removedAgents();
      setRemovedAgents(data.removed_agents);
      setMessage(`Permanently deleted backup for ${removed.agent_name}. No Hermes profile configs changed.`);
    } catch (error: unknown) {
      setMessage(`Permanent delete failed: ${errorMessage(error)}`);
    }
  }

  return (
    <div className="card premium-card agent-growth-card">
      <PanelHeader
        title="Agent Growth Studio"
        badge={`${activeCount} active`}
        right={<span className="mono text-[10px] text-emerald-300">PROFILE-SAFE OVERLAY</span>}
        collapsible
      />

      <div className="mb-3 grid grid-cols-1 lg:grid-cols-4 gap-3 text-xs">
        <div className="glass-mini">
          <div className="mono text-gray-400 uppercase tracking-widest">Storage</div>
          <div className="truncate text-gray-200" title={payload?.storage || ''}>{payload?.storage || 'loading'}</div>
        </div>
        <div className="glass-mini">
          <div className="mono text-gray-400 uppercase tracking-widest">Safety Contract</div>
          <div className="text-emerald-300">writes_profile_configs = false</div>
        </div>
        <div className="glass-mini">
          <div className="mono text-gray-400 uppercase tracking-widest">Choices</div>
          <div className="text-cyan-300">{agentNames.length} agents · {providers.length} providers · {skills.length} skills</div>
        </div>
        <div className="glass-mini">
          <div className="mono text-gray-400 uppercase tracking-widest">Proposals</div>
          <div className="text-amber-300">{proposals.length} pending/recorded</div>
        </div>
      </div>

      <div
        className="mb-4 overflow-x-auto rounded-lg border border-white/5"
        data-testid="role-table-scroll"
        role="region"
        aria-label="Role assignments table (scrolls horizontally on narrow screens)"
      >
        <table className="w-full text-xs role-table">
          <thead>
            <tr className="mono text-gray-500 uppercase tracking-widest text-[10px]">
              <th>Role</th>
              <th>Agent</th>
              <th>Provider</th>
              <th>Model</th>
              <th>Status</th>
              <th>Notes</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((role, index) => {
              const models = modelOptions(role.provider);
              return (
                <tr key={role.role_id}>
                  <td>
                    <input value={role.label} onChange={event => updateRole(index, { label: event.target.value })} placeholder="role label" />
                    <div className="mono text-[10px] text-gray-500">{role.role_id}</div>
                  </td>
                  <td>
                    <select value={role.assigned_agent} onChange={event => updateRole(index, { assigned_agent: event.target.value })}>
                      <option value="">Unassigned</option>
                      {agentNames.map(name => <option key={name} value={name}>{name}</option>)}
                    </select>
                  </td>
                  <td>
                    <select value={role.provider} onChange={event => updateRole(index, { provider: event.target.value, model: '' })}>
                      <option value="">Provider</option>
                      {providers.map(provider => <option key={provider} value={provider}>{provider}</option>)}
                    </select>
                  </td>
                  <td>
                    <select value={role.model} onChange={event => updateRole(index, { model: event.target.value })}>
                      <option value="">Model</option>
                      {models.map(model => <option key={`${role.provider}:${model}`} value={model}>{model}</option>)}
                      {role.model && !models.includes(role.model) ? <option value={role.model}>{role.model}</option> : null}
                    </select>
                  </td>
                  <td>
                    <select className={STATUS_CLASS[role.status]} value={role.status} onChange={event => updateRole(index, { status: event.target.value as RoleMapping['status'] })}>
                      <option value="active">active</option>
                      <option value="standby">standby</option>
                      <option value="disabled">disabled</option>
                    </select>
                  </td>
                  <td><input value={role.notes} onChange={event => updateRole(index, { notes: event.target.value })} placeholder="role notes" /></td>
                  <td><button type="button" className="ghost-button" onClick={() => removeRole(index)}>Remove</button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Bootstrap-style row of 3 sub-sections, no nesting ──────
         D-2026-06-14: replaced the 3-col rigid grid that forced
         horizontal overflow on narrow cards. New layout: 1 col on
         mobile, 2 on md, 3 on lg+. Each section has min-w-0 so
         children can shrink instead of blowing out the card.
         The "Add Agent" CTA is now a sticky-top banner above its
         own form so it's never hidden. */}
      <div className="row-of-sections">
        {/* ── Skill Feed (col 1) ───────────────────────────────── */}
        <section className="growth-section" data-testid="growth-section-skill-feed">
          <div className="growth-section-head">
            <div>
              <div className="growth-section-title">🎯 Skill Feed</div>
              <div className="growth-section-sub">Pick an agent, then search and tick the skills. Selected skills appear as chips below the input.</div>
            </div>
            <button
              type="button"
              className="premium-button shrink-0"
              onClick={saveSkills}
              disabled={savingSkills}
              data-testid="growth-save-skills"
            >
              {savingSkills ? 'Saving…' : 'Save skills'}
            </button>
          </div>
          <RoleMatrixSkillFeed
            agentNames={agentNames}
            skills={skills}
            currentAssignments={assignments}
            onChange={(agent, skills) => setAssignments(prev => {
              const next = [...prev];
              const idx = next.findIndex(a => a.agent === agent);
              if (idx >= 0) next[idx] = { ...next[idx], agent, skills, notes: next[idx].notes || '' };
              else next.push({ agent, skills, notes: '' });
              return next;
            })}
          />
        </section>

        {/* ── Add Agent (col 2) ────────────────────────────────── */}
        <section className="growth-section" data-testid="growth-section-add-agent">
          {/* Sticky CTA: always visible regardless of scroll position
              inside the panel. This is the "Add Agent" the user said
              was hidden in the previous layout. */}
          <div className="growth-section-sticky-cta">
            <div>
              <div className="growth-section-title">➕ Add Agent</div>
              <div className="growth-section-sub">Propose a new agent. Profile creation stays human-gated.</div>
            </div>
            <button
              type="button"
              className="premium-button shrink-0"
              onClick={proposeAgent}
              disabled={proposing || !proposalDraft || !proposalDraft.agent_name || !proposalDraft.provider || !proposalDraft.model}
              data-testid="growth-propose-agent"
              title={!proposalDraft?.agent_name ? 'Type a name first' : !proposalDraft?.provider ? 'Pick a provider' : !proposalDraft?.model ? 'Pick a model' : 'Submit proposal'}
            >
              {proposing ? 'Proposing…' : 'Add Agent'}
            </button>
          </div>
          {proposalDraft ? (
            <div className="growth-form">
              <label className="growth-form-field">
                <span className="growth-form-label">Agent name</span>
                <input
                  value={proposalDraft.agent_name}
                  onChange={event => setProposalField('agent_name', safeSlug(event.target.value).startsWith('jarvis-') ? safeSlug(event.target.value) : `jarvis-${safeSlug(event.target.value)}`)}
                  placeholder="jarvis-new-agent"
                />
              </label>
              <label className="growth-form-field">
                <span className="growth-form-label">Description</span>
                <input
                  value={proposalDraft.description}
                  onChange={event => setProposalField('description', event.target.value)}
                  placeholder="what does this agent do"
                />
              </label>
              <label className="growth-form-field">
                <span className="growth-form-label">Clone from</span>
                <select value={proposalDraft.clone_from} onChange={event => setProposalField('clone_from', event.target.value)}>
                  {agentNames.map(name => <option key={name} value={name}>{name}</option>)}
                </select>
              </label>
              <div className="grid grid-cols-2 gap-2 min-w-0">
                <label className="growth-form-field">
                  <span className="growth-form-label">Provider</span>
                  <select value={proposalDraft.provider} onChange={event => setProposalField('provider', event.target.value)}>
                    <option value="">— pick —</option>
                    {providers.map(provider => <option key={provider} value={provider}>{provider}</option>)}
                  </select>
                </label>
                <label className="growth-form-field">
                  <span className="growth-form-label">Model</span>
                  <select value={proposalDraft.model} onChange={event => setProposalField('model', event.target.value)}>
                    <option value="">— pick —</option>
                    {modelOptions(proposalDraft.provider).map(model => <option key={model} value={model}>{model}</option>)}
                  </select>
                </label>
              </div>
              <label className="growth-form-field">
                <span className="growth-form-label">Notes</span>
                <textarea
                  value={proposalDraft.notes}
                  onChange={event => setProposalField('notes', event.target.value)}
                  placeholder="why this agent should exist"
                  rows={2}
                />
              </label>
              <div className="growth-form-field">
                <span className="growth-form-label">Seed skills (optional)</span>
                <RoleMatrixSkillPicker
                  skills={skills}
                  selected={proposalDraft.skills}
                  onToggle={(name, on) => {
                    setProposalDraftField('skills', on
                      ? Array.from(new Set([...(proposalDraft.skills || []), name]))
                      : (proposalDraft.skills || []).filter(n => n !== name));
                  }}
                  placeholder={`Search ${skills.length} skills…`}
                  emptyMessage="No skills match."
                />
              </div>
            </div>
          ) : (
            <div className="text-xs text-gray-500 p-2">Loading proposal form…</div>
          )}
          {proposals.length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/5">
              <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-2">
                Recent proposals ({proposals.length})
              </div>
              <div className="space-y-2">
                {proposals.slice(0, 4).map(proposal => (
                  <div key={proposal.proposal_id} className="proposal-card">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-gray-100 truncate min-w-0">{proposal.request.agent_name}</span>
                      <span className="mono text-[10px] text-amber-300 shrink-0">{proposal.status}</span>
                    </div>
                    <div className="text-[11px] text-gray-400 truncate">{proposal.request.provider} / {proposal.request.model}</div>
                    <button type="button" className="danger-button mt-2 w-full" onClick={() => { setPendingRemove(proposal); setRemoveReason(''); }}>
                      Remove with 7-day backup
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ── Removed Agents (col 3) ───────────────────────────── */}
        <section className="growth-section" data-testid="growth-section-removed">
          <div className="growth-section-head">
            <div>
              <div className="growth-section-title">🗑 Removed Agents</div>
              <div className="growth-section-sub">7-day recovery vault. Nothing is permanently deleted here.</div>
            </div>
          </div>
          <div className="removed-agent-list">
            {removedAgents.length ? removedAgents.slice(0, 8).map(removed => {
              const backupSkills = removed.backup?.assignment?.skills || removed.backup?.proposal?.request.skills || [];
              return (
                <div key={removed.removed_id} className="removed-agent-card">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-gray-100 truncate min-w-0">{removed.agent_name}</span>
                    <span className={removed.status === 'removed' ? 'mono text-[10px] text-rose-300 shrink-0' : 'mono text-[10px] text-gray-400 shrink-0'}>{removed.status}</span>
                  </div>
                  <div className="text-[11px] text-gray-400">Removed {new Date(removed.removed_at).toLocaleString()}</div>
                  <div className="text-[11px] text-amber-300">{daysUntil(removed.expires_at)} days left</div>
                  <div className="text-[11px] text-cyan-300">{backupSkills.length} backed-up skills</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button type="button" className="ghost-button" disabled={removed.status !== 'removed'} onClick={() => restoreAgent(removed)}>Restore</button>
                    <button type="button" className="danger-button" disabled={removed.status === 'permanently_deleted'} onClick={() => permanentlyDeleteAgent(removed)}>Delete</button>
                  </div>
                </div>
              );
            }) : <div className="text-xs text-gray-500">No removed agents yet.</div>}
          </div>
        </section>
      </div>

      {pendingRemove ? (
        <div className="confirm-backdrop" role="presentation">
          <div className="confirm-modal" role="dialog" aria-modal="true" aria-label="Confirm agent removal">
            <div className="mono text-[10px] text-rose-300 uppercase tracking-widest">Confirm removal</div>
            <h3>Remove {pendingRemove.request.agent_name}?</h3>
            <p>This will hide the dashboard proposal and skill overlay, then save a recovery backup for 7 days. No Hermes profile directory, config file, or skill file will be deleted.</p>
            <label className="confirm-label">
              Reason / recovery note
              <textarea value={removeReason} onChange={event => setRemoveReason(event.target.value)} rows={3} placeholder="Why is this agent being removed?" />
            </label>
            <div className="confirm-actions">
              <button type="button" className="ghost-button" onClick={() => { setPendingRemove(null); setRemoveReason(''); }}>Cancel</button>
              <button type="button" className="danger-button" onClick={confirmRemoveAgent}>Yes, remove and keep 7-day backup</button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="mt-3 flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div className="text-xs text-gray-400">{message}</div>
        <div className="flex gap-2">
          <button type="button" onClick={addRole} className="ghost-button">Add role row</button>
          <button type="button" onClick={save} disabled={saving || !roles.length} className="premium-button">
            {saving ? 'Saving...' : 'Save role overlay'}
          </button>
        </div>
      </div>
    </div>
  );
}
