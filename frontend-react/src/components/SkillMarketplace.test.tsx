// D-2026-06-09 (Phase 2): Vitest hoists vi.mock factories to the top
// of the file, so we cannot reference SAMPLE_CATALOG from there.
// The mock data is inlined inside the factory.
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { api } from '../api/client';
import type { CatalogPayload } from '../types/dashboard';
import { SkillMarketplace } from './SkillMarketplace';
import { ProjectProvider } from '../contexts/ProjectContext';

vi.mock('../api/client', () => ({
  api: {
    catalog: vi.fn(),
    catalogByDepartment: vi.fn(),
    agentSkillsByProject: vi.fn(),
    saveAgentSkillsByProject: vi.fn(),
    refreshCatalog: vi.fn(),
    projects: vi.fn(),
    activeProject: vi.fn(),
    selectProject: vi.fn(),
  },
}));

const SAMPLE_CATALOG = {
  version: 1,
  updated_at: '2026-06-09T00:00:00Z',
  summary: {
    total_skills: 3,
    by_trust_tier: { T1: 2, T2: 1 },
    by_source: { 'test/repo': 3 },
    by_category: { engineering: 2, security: 1 },
  },
  sources: [{ repo: 'test/repo', tier: 'T1', kind: 'curated', license: 'MIT', trust_tier: 'T1' }],
  skills: [
    { id: 'test/fe-skill', name: 'fe-skill', description: 'frontend test skill', category: 'engineering', source_repo: 'test/repo', source_path: 'fe/SKILL.md', trust_tier: 'T1', departments: ['jarvis-frontend'], mcp_servers: [], review_status: 'curated', provenance: { added_by: 't', added_at: '2026-06-09T00:00:00Z' }, hash: 'h1' },
    { id: 'test/be-skill', name: 'be-skill', description: 'backend test skill', category: 'engineering', source_repo: 'test/repo', source_path: 'be/SKILL.md', trust_tier: 'T1', departments: ['jarvis-backend'], mcp_servers: [], review_status: 'curated', provenance: { added_by: 't', added_at: '2026-06-09T00:00:00Z' }, hash: 'h2' },
    { id: 'test/sec-skill', name: 'sec-skill', description: 'security bulk skill', category: 'security', source_repo: 'test/repo', source_path: 'sec/SKILL.md', trust_tier: 'T2', departments: ['jarvis-security-lead'], mcp_servers: [], review_status: 'bulk', provenance: { added_by: 't', added_at: '2026-06-09T00:00:00Z' }, hash: 'h3' },
  ],
  writes_profile_configs: false,
} satisfies CatalogPayload;

const EMPTY_ASSIGN = (agent: string) => ({ agent, project: 'default', skills: [], notes: '', writes_profile_configs: false as const });

function mountWithProject() {
  return render(
    <ProjectProvider>
      <SkillMarketplace />
    </ProjectProvider>
  );
}

describe('SkillMarketplace', () => {
  beforeEach(() => {
    vi.mocked(api.catalog).mockReset();
    vi.mocked(api.catalogByDepartment).mockReset();
    vi.mocked(api.agentSkillsByProject).mockReset();
    vi.mocked(api.saveAgentSkillsByProject).mockReset();
    vi.mocked(api.refreshCatalog).mockReset();
    vi.mocked(api.projects).mockReset();
    vi.mocked(api.activeProject).mockReset();
    vi.mocked(api.selectProject).mockReset();
    // Default: catalog loads, assignments are empty
    vi.mocked(api.projects).mockResolvedValue({ projects: [], active: undefined });
    vi.mocked(api.activeProject).mockResolvedValue({ active: undefined });
    vi.mocked(api.selectProject).mockImplementation(async () => ({ active: undefined }));
    vi.mocked(api.catalog).mockResolvedValue(SAMPLE_CATALOG);
    vi.mocked(api.agentSkillsByProject).mockImplementation(async (agent: string) => EMPTY_ASSIGN(agent));
    vi.mocked(api.saveAgentSkillsByProject).mockImplementation(async (project, agent, skills) => ({
      project, agent, skills, notes: '', writes_profile_configs: false as const,
    }));
  });

  it('loads and renders the catalog', async () => {
    mountWithProject();
    await waitFor(() => expect(screen.getByTestId('skill-mkt-list')).toBeInTheDocument());
    // With default department=jarvis-frontend and trust=T1, only the frontend skill should show
    expect(screen.getByTestId('skill-mkt-row-test/fe-skill')).toBeInTheDocument();
    expect(screen.queryByTestId('skill-mkt-row-test/be-skill')).not.toBeInTheDocument();
  });

  it('toggles a skill and saves it to the per-project endpoint', async () => {
    mountWithProject();
    await waitFor(() => expect(screen.getByTestId('skill-mkt-row-test/fe-skill')).toBeInTheDocument());
    // Check the box
    fireEvent.click(screen.getByTestId('skill-mkt-checkbox-test/fe-skill'));
    // Save
    fireEvent.click(screen.getByTestId('skill-mkt-save'));
    await waitFor(() => expect(vi.mocked(api.saveAgentSkillsByProject)).toHaveBeenCalled());
    expect(vi.mocked(api.saveAgentSkillsByProject)).toHaveBeenCalledWith('default', 'jarvis-frontend', ['test/fe-skill'], '');
  });

  it('filters by trust tier', async () => {
    mountWithProject();
    await waitFor(() => expect(screen.getByTestId('skill-mkt-list')).toBeInTheDocument());
    // Change department — this triggers the (department, project) assignment fetch
    // in a useEffect. Wait for the mock to be called with the new department so
    // React has settled state from the resolved promise before we assert on rows.
    fireEvent.change(screen.getByTestId('skill-mkt-department'), { target: { value: 'jarvis-security-lead' } });
    await waitFor(() =>
      expect(vi.mocked(api.agentSkillsByProject)).toHaveBeenCalledWith('jarvis-security-lead', 'default')
    );
    // The empty list stays empty because the default trust filter is T1 and
    // sec-skill is T2. Switch trust filter to T2 and wait for the row.
    fireEvent.click(screen.getByTestId('skill-mkt-trust-T2'));
    await waitFor(() => expect(screen.getByTestId('skill-mkt-row-test/sec-skill')).toBeInTheDocument());
    expect(screen.getByTestId('skill-mkt-row-test/sec-skill')).toBeInTheDocument();
  });

  it('shows project slug in the meta strip', async () => {
    mountWithProject();
    await waitFor(() => expect(screen.getByTestId('skill-mkt-project')).toBeInTheDocument());
    expect(screen.getByTestId('skill-mkt-project').textContent).toContain('default');
  });
});
