import { CONFIG } from '../utils/config';
import type {
  DashboardCache, KanbanCard, Project,
  Agent, Decision, MemoryItem, DiscordThread,
  RolePayload, RoleMapping,
  SkillItem, AgentSkillAssignment, AgentSkillPayload,
  AgentProposal, AgentProposalRequest, RemovedAgent, Workspace,
  ArmyRun, ArmyRunRequest, ArmyWorker,
  Topology,
  CatalogPayload, CatalogSkill
} from '../types/dashboard';

export type { Topology, TopologyNode, TopologyAgent, TopologyEdge } from '../types/dashboard';

const API = CONFIG.API_BASE;
const TOKEN = CONFIG.TOKEN;

type ChatResponse = {
  response?: string;
  message?: string;
  agent?: string;
  mode?: string;
  tier?: number;
  cost?: string;
  exec?: string;
  [key: string]: unknown;
};

function authHeaders(extra?: HeadersInit): HeadersInit {
  return {
    ...extra,
    ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
  };
}

function q(path: string, params?: Record<string, string>) {
  let url = `${API}${path}`;
  const query = new URLSearchParams();
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v) query.set(k, v);
    }
  }
  const suffix = query.toString();
  if (suffix) url += `?${suffix}`;
  return url;
}

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = q(path, params);
  const r = await fetch(url, { headers: authHeaders({ Accept: 'application/json' }), credentials: 'same-origin' });
  if (!r.ok) console.warn('API GET failed:', path, r.status);
  if (!r.ok) throw new Error(`GET ${path} ${r.status}`);
  return r.json();
}

async function post<T>(path: string, body: unknown, params?: Record<string, string>): Promise<T> {
  const r = await fetch(q(path, params), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json', Accept: 'application/json' }),
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`POST ${path} ${r.status}`);
  return r.json();
}

export const api = {
  health: () => get<Record<string, unknown>>('/health'),
  cache: (project?: string) => get<DashboardCache>('/dashboard/cache', project ? { project } : undefined),
  agents: () => get<Agent[]>('/dashboard/agents'),
  kanban: (project?: string) => get<{ tasks: KanbanCard[] }>('/kanban/tasks', project ? { project } : undefined),
  decisions: (project?: string) => get<Decision[]>('/dashboard/decisions', project ? { project } : undefined),
  memory: (project?: string) => get<Record<string, MemoryItem>>('/dashboard/memory', project ? { project } : undefined),
  discordThreads: () => get<{ threads: DiscordThread[]; total: number }>('/discord/threads'),
  metrics: () => get<Record<string, unknown>>('/dashboard/metrics'),
  projects: () => get<{ projects: Project[]; active?: Project }>('/project/list'),
  activeProject: () => get<{ active?: Project }>('/project/active'),
  selectProject: (slug: string) => post<{ active?: Project }>('/project/select', { slug }),
  sessions: (project: string) => get<Record<string, unknown>>(`/project/${project}/sessions`),
  chat: (msg: string, mode: string, project?: string, agent?: string) =>
    post<ChatResponse>('/chat', { message: msg, mode, project, agent }),
  modes: () => get<Record<string, unknown>>('/modes'),
  roles: () => get<RolePayload>('/roles'),
  saveRoles: (roles: RoleMapping[]) => post<RolePayload>('/roles', { roles }),
  roleModels: () => get<{ models: RolePayload['models'] }>('/models'),
  testRole: (role: RoleMapping) => post<Record<string, unknown>>('/roles/test', role),
  skills: () => get<{ skills: SkillItem[]; writes_profile_configs: false }>('/skills'),
  agentSkills: () => get<AgentSkillPayload>('/agents/skills'),
  saveAgentSkills: (assignments: AgentSkillAssignment[]) => post<AgentSkillPayload>('/agents/skills', { assignments }),
  agentProposals: () => get<{ proposals: AgentProposal[]; writes_profile_configs: false; storage: string }>('/agents/proposals'),
  proposeAgent: (request: AgentProposalRequest) => post<AgentProposal>('/agents/propose', request),
  removedAgents: () => get<{ removed_agents: RemovedAgent[]; writes_profile_configs: false; storage: string }>('/agents/removed'),
  removeAgent: (agentName: string, reason: string) => post<{ removed_agent: RemovedAgent; writes_profile_configs: false }>('/agents/remove', { agent_name: agentName, reason }),
  restoreAgent: (removedId: string) => post<{ restored_agent: string; removed_id: string; writes_profile_configs: false }>('/agents/restore', { removed_id: removedId }),
  permanentlyDeleteAgent: (removedId: string, confirmText: string) => post<{ permanently_deleted_agent: string; removed_id: string; writes_profile_configs: false }>('/agents/permanent-delete', { removed_id: removedId, confirm_text: confirmText }),
  heartbeat: (taskId: string, progress: string) =>
    post<Record<string, unknown>>(`/kanban/${taskId}/heartbeat`, { progress }),
  blockTask: (taskId: string, reason?: string) =>
    post<Record<string, unknown>>(`/kanban/${taskId}/block`, { reason }),
  unblockTask: (taskId: string) =>
    post<Record<string, unknown>>(`/kanban/${taskId}/unblock`, {}),
  completeTask: (taskId: string, summary?: string) =>
    post<Record<string, unknown>>(`/kanban/${taskId}/complete`, { summary }),
  workspaces: () => get<{ workspaces: Workspace[] }>('/workspace/list'),
  cloneWorkspace: (url: string, alias: string) =>
    post<Record<string, unknown>>('/workspace/clone', { url, alias }),
  removeWorkspace: (alias: string) =>
    post<Record<string, unknown>>(`/workspace/remove/${alias}`, {}),
  armyWorkers: () => get<{ workers: ArmyWorker[]; writes_profile_configs: false }>('/army/workers'),
  armyRuns: () => get<{ runs: ArmyRun[]; writes_profile_configs: false }>('/army/runs'),
  spawnArmyRun: (request: ArmyRunRequest) => post<{ run: ArmyRun; writes_profile_configs: false }>('/army/runs', request),
  armyRun: (runId: string) => get<{ run: ArmyRun; writes_profile_configs: false }>(`/army/runs/${runId}`),
  armyLogs: (runId: string) => get<{ run_id: string; logs: string; writes_profile_configs: false }>(`/army/runs/${runId}/logs`),
  armyDiff: (runId: string) => get<{ run_id: string; diff: string; writes_profile_configs: false }>(`/army/runs/${runId}/diff`),
  rejectArmyRun: (runId: string, reason: string) => post<{ run: ArmyRun; writes_profile_configs: false }>(`/army/runs/${runId}/reject`, { reason }),
  rerunArmyRun: (runId: string) => post<{ run: ArmyRun; writes_profile_configs: false }>(`/army/runs/${runId}/rerun`, {}),
  approveArmyRun: (runId: string) => post<{ run: ArmyRun; merged: false; writes_profile_configs: false }>(`/army/runs/${runId}/approve`, {}),
  // D-2026-06-08-topology-editor sub-phase 2: read-only topology view
  fetchTopology: (companyId: string) => get<Topology>(`/companies/${companyId}/topology`),
  // D-2026-06-09 (Phase 2): skill catalog + per-project assignment
  catalog: (filters?: { trust_tier?: string; department?: string; category?: string; q?: string }) =>
    get<CatalogPayload>('/catalog', filters as Record<string, string> | undefined),
  catalogByDepartment: (department: string) =>
    get<{ department: string; count: number; skills: CatalogSkill[]; writes_profile_configs: false }>(`/catalog/by-department/${department}`),
  refreshCatalog: () => post<{ version: number; count: number; skills: CatalogSkill[]; writes_profile_configs: false }>('/catalog/refresh', {}),
  importSkill: (payload: {
    name: string;
    summary: string;
    description?: string;
    source_repo?: string;
    source_path?: string;
    icon_url?: string;
    trust_tier?: 'T1' | 'T2' | 'T3';
    departments?: string[];
    category?: string;
  }) => post<{ writes_profile_configs: false; updated: boolean; skill: any; catalog_size: number }>('/skills/import', payload),
  listImportedSkills: () => get<{ writes_profile_configs: false; count: number; skills: any[] }>('/skills/imports'),
  removeImportedSkill: async (name: string) => {
    const url = `${API}/skills/imports/${encodeURIComponent(name)}`;
    const r = await fetch(url, { method: 'DELETE', headers: authHeaders({}) });
    if (!r.ok) throw new Error(`DELETE ${url} ${r.status}`);
    return r.json();
  },
  agentSkillsByProject: (agent: string, project: string = 'default') =>
    get<{ agent: string; project: string; skills: string[]; notes: string; writes_profile_configs: false }>(`/agents/${agent}/skills-by-project`, { project }),
  saveAgentSkillsByProject: (project: string, agent: string, skills: string[], notes: string = '') =>
    post<{ agent: string; project: string; skills: string[]; notes: string; writes_profile_configs: false }>('/agents/skills-by-project', { project, agent, skills, notes }),
  refreshCatalog: () => post<{ version: number; updated_at: string; count: number; writes_profile_configs: false }>('/catalog/refresh', {}),

  // ── Agent Cron Jobs (D-2026-06-14) ────────────────────────────
  listCronJobs: (params?: { agent?: string; enabled?: boolean }) =>
    get<{ writes_profile_configs: false; count: number; jobs: any[] }>('/cron/jobs', params as any),
  getCronJob: (id: string) =>
    get<any>(`/cron/jobs/${encodeURIComponent(id)}`),
  createCronJob: (payload: any) =>
    post<{ writes_profile_configs: false; created: string; job: any }>('/cron/jobs', payload),
  updateCronJob: async (id: string, updates: any) => {
    const url = `${API}/cron/jobs/${encodeURIComponent(id)}`;
    const r = await fetch(url, {
      method: 'PATCH',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(updates),
    });
    if (!r.ok) throw new Error(`PATCH ${url} ${r.status}: ${await r.text()}`);
    return r.json();
  },
  deleteCronJob: async (id: string) => {
    const url = `${API}/cron/jobs/${encodeURIComponent(id)}`;
    const r = await fetch(url, { method: 'DELETE', headers: authHeaders({}) });
    if (!r.ok) throw new Error(`DELETE ${url} ${r.status}`);
    return r.json();
  },
  runCronJobNow: (id: string) =>
    post<{ writes_profile_configs: false; dispatched: boolean; agent: string; job: any }>(`/cron/jobs/${encodeURIComponent(id)}/run`, {}),

  // ── MCP Catalog (D-2026-06-15) ─────────────────────────────
  listMCPs: () => get<{ writes_profile_configs: false; storage: string; count: number; mcps: any[] }>('/mcp/catalog'),
  getMCP: (name: string) => get<any>(`/mcp/catalog/${encodeURIComponent(name)}`),
  addMCP: (payload: any) =>
    post<{ writes_profile_configs: false; count: number; mcps: any[] }>('/mcp/catalog/add', payload),
  removeMCP: async (name: string) => {
    const url = `${API}/mcp/catalog/${encodeURIComponent(name)}`;
    const r = await fetch(url, { method: 'DELETE', headers: authHeaders({}) });
    if (!r.ok) throw new Error(`DELETE ${url} ${r.status}`);
    return r.json();
  },
  refreshMCPCatalog: () =>
    post<{ writes_profile_configs: false; count: number; mcps: any[] }>('/mcp/catalog/refresh', {}),
  detectChatIntent: (text: string) =>
    post<{ is_mcp_intent: boolean; confidence: number; reason: string; extracted: any }>('/mcp/chat-intent', { text }),
  installMCPFromChat: (text: string, scope: string = 'global-hermes', assign_to: string[] = []) =>
    post<{
      writes_profile_configs: false;
      detected_kind: string;
      detected_name: string;
      detected_url: string;
      catalog_size: number;
      mcp: any;
      confirmation: string;
      run_suggested_command: string;
    }>('/mcp/install-from-chat', { text, scope, assign_to }),
};

// Backward-compatible named export used by older tests/components.
export const fetchTopology = api.fetchTopology;
