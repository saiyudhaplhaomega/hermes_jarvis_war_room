import { useEffect, useMemo, useRef, useState } from 'react';

// RoleMatrixSkillFeed (D-2026-06-14):
//   The Skill Feed in the Agent Growth Studio, but as a proper
//   searchable dropdown. One agent selector at the top, a search
//   input that opens a filterable list of skills, checkboxes per
//   row, and a chips strip of currently-selected skills.
//
//   This replaces the old "every agent gets a giant grid of all
//   skills" layout that cluttered the panel.

type Skill = { name: string; description?: string; summary?: string; trust_tier?: string; icon_url?: string };

function isEmoji(s: string): boolean {
  return /[\p{Emoji}\p{Extended_Pictographic}]/u.test(s);
}

function skillIcon(s: Skill): string {
  if (s.icon_url) return s.icon_url;
  if (s.trust_tier === 'T1') return '✅';
  if (s.trust_tier === 'T2') return '📦';
  return '🧩';
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

export function RoleMatrixSkillPicker({
  skills,
  selected,
  onToggle,
  placeholder = 'Search skills…',
  emptyMessage = 'No skills match the current search.',
}: {
  skills: Skill[];
  selected: string[];
  onToggle: (name: string, on: boolean) => void;
  placeholder?: string;
  emptyMessage?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const filtered = useMemo(() => {
    const ql = query.trim().toLowerCase();
    return skills.filter((s) => {
      if (!ql) return true;
      const hay = `${s.name} ${s.description || ''} ${s.summary || ''}`.toLowerCase();
      return hay.includes(ql);
    });
  }, [skills, query]);

  const sel = new Set(selected);
  const hasSelected = selected.length > 0;

  return (
    <div className="rm-skill-picker" ref={ref} data-testid="rm-skill-picker">
      <div className="rm-skill-picker-input-row">
        <input
          type="search"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          data-testid="rm-skill-picker-input"
          className="rm-skill-picker-input"
        />
        <button
          type="button"
          className="rm-skill-picker-toggle"
          onClick={() => setOpen((v) => !v)}
          data-testid="rm-skill-picker-toggle"
          aria-label="Toggle skill list"
        >
          {open ? '▴' : '▾'}
        </button>
      </div>
      {hasSelected && (
        <div className="rm-skill-chips" data-testid="rm-skill-chips">
          <span className="rm-skill-chips-label">Selected ({selected.length}):</span>
          {selected.map((name) => {
            const s = skills.find((x) => x.name === name);
            const icon = s ? skillIcon(s) : '🧩';
            return (
              <span key={name} className="rm-skill-chip" data-testid={`rm-skill-chip-${name}`}>
                <span className="rm-skill-chip-icon">{isEmoji(icon) ? icon : '🧩'}</span>
                <span className="rm-skill-chip-name">{name}</span>
                <button
                  type="button"
                  className="rm-skill-chip-x"
                  onClick={() => onToggle(name, false)}
                  data-testid={`rm-skill-chip-x-${name}`}
                  aria-label={`Remove ${name}`}
                >×</button>
              </span>
            );
          })}
          <button
            type="button"
            className="rm-skill-chips-clear"
            onClick={() => selected.forEach((n) => onToggle(n, false))}
            data-testid="rm-skill-chips-clear"
          >
            clear all
          </button>
        </div>
      )}
      {open && (
        <div className="rm-skill-picker-menu" data-testid="rm-skill-picker-menu">
          <div className="rm-skill-picker-list">
            {filtered.length === 0 && (
              <div className="rm-skill-empty" data-testid="rm-skill-empty">{emptyMessage}</div>
            )}
            {filtered.map((s) => {
              const inBasket = sel.has(s.name);
              const icon = skillIcon(s);
              return (
                <label
                  key={s.name}
                  className={`rm-skill-picker-row ${inBasket ? 'rm-skill-picker-row--in' : ''}`}
                  data-testid={`rm-skill-picker-row-${s.name}`}
                >
                  <input
                    type="checkbox"
                    checked={inBasket}
                    onChange={(e) => onToggle(s.name, e.target.checked)}
                    data-testid={`rm-skill-picker-checkbox-${s.name}`}
                  />
                  <span className="rm-skill-icon">
                    {isEmoji(icon) ? icon : '🧩'}
                  </span>
                  <div className="rm-skill-picker-body">
                    <div className="rm-skill-picker-head">
                      <span className="rm-skill-picker-name">{s.name}</span>
                      {s.trust_tier && (
                        <span className={`pill ${s.trust_tier === 'T1' ? 'pill-emerald' : s.trust_tier === 'T2' ? 'pill-amber' : 'pill-rose'}`}>
                          {s.trust_tier}
                        </span>
                      )}
                    </div>
                    <div className="rm-skill-picker-summary" data-testid={`rm-skill-picker-summary-${s.name}`}>
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
  );
}

export function RoleMatrixSkillFeed({
  agentNames,
  skills,
  currentAssignments,
  onChange,
}: {
  agentNames: string[];
  skills: Skill[];
  currentAssignments: { agent: string; skills: string[]; notes?: string }[];
  onChange: (agent: string, skills: string[]) => void;
}) {
  const sorted = useMemo(() => sortAgents(agentNames), [agentNames]);
  const [selectedAgent, setSelectedAgent] = useState<string>(sorted[0] || '');

  // Keep the selected agent valid when the list changes
  useEffect(() => {
    if (!sorted.includes(selectedAgent) && sorted.length) {
      setSelectedAgent(sorted[0]);
    }
  }, [sorted, selectedAgent]);

  const currentSkills = useMemo(
    () => currentAssignments.find((a) => a.agent === selectedAgent)?.skills || [],
    [currentAssignments, selectedAgent],
  );

  return (
    <div className="rm-skill-feed" data-testid="rm-skill-feed">
      <div className="rm-skill-feed-controls">
        <label className="rm-skill-feed-agent">
          <span className="rm-skill-feed-label">Agent</span>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            data-testid="rm-skill-feed-agent-select"
            aria-label="Agent to assign skills to"
          >
            {sorted.length === 0 && <option value="">(no agents loaded)</option>}
            {sorted.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </label>
        <div className="rm-skill-feed-count" data-testid="rm-skill-feed-count">
          {currentSkills.length} of {skills.length} skills selected for {selectedAgent || '…'}
        </div>
      </div>
      <RoleMatrixSkillPicker
        skills={skills}
        selected={currentSkills}
        onToggle={(name, on) => {
          const next = on
            ? Array.from(new Set([...currentSkills, name]))
            : currentSkills.filter((n) => n !== name);
          onChange(selectedAgent, next);
        }}
        placeholder={`Search ${skills.length} skills to assign to ${selectedAgent || 'agent'}…`}
        emptyMessage="No skills match. Try a different search term."
      />
    </div>
  );
}

export default RoleMatrixSkillFeed;
