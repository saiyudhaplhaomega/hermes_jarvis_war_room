export interface Agent {
  name: string;
  tier: number;
  status: string;
  last_seen?: string;
  model?: string;
  provider?: string;
  role?: string;
  project?: string;
  source: string;
}

export interface KanbanCard {
  id: string;
  title: string;
  status: 'todo' | 'ready' | 'running' | 'done' | 'blocked' | 'review' | 'archived' | 'cancelled';
  assignee: string;
  priority: number;
  project: string;
  last_heartbeat_at?: string;
  body?: string;
  created_at?: string;
  updated_at?: string;
  parents?: string;
  blocked_by_parents?: boolean;
  comment_count?: number;
  run_count?: number;
  color?: string;
}

export type ChatMessage = {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent?: string;
  mode?: string;
  tier?: number;
  cost?: string;
  ts: number;
  exec?: string;
};

export interface Decision {
  id: string;
  title: string;
  source: string;
  project?: string;
  tier?: number;
  created_at?: string;
}

export interface MemoryItem {
  key: string;
  source: string;
  project?: string;
  title?: string;
  kind?: string;
  updated_at?: string;
}

export interface DiscordThread {
  event: string;
  guild_id: string;
  channel_id: string;
  thread_id: string;
  thread_name: string;
  participant_bots: string[];
  last_message_ts?: string;
}

export interface MetricSnapshot {
  tokens?: number;
  cost?: number;
  budget?: number;
}

export interface Project {
  slug: string;
  name: string;
  repo_url?: string;
  repo_path?: string;
  active?: boolean;
}

export interface DashboardCache {
  generated_at: string;
  agents: Agent[];
  tasks: KanbanCard[];
  kanban_by_project: Record<string, KanbanCard[]>;
  decisions: Decision[];
  memory: Record<string, MemoryItem>;
  metrics: MetricSnapshot;
  gateway: Record<string, unknown>;
  projects: Project[];
  sessions: Record<string, unknown>[];
}

export interface RoleMapping {
  role_id: string;
  label: string;
  assigned_agent: string;
  provider: string;
  model: string;
  status: 'active' | 'standby' | 'disabled';
  platform: string;
  notes: string;
}

export interface RoleAgentChoice {
  name: string;
  description?: string;
  provider?: string;
  model?: string;
  source: string;
}

export interface RoleModelChoice {
  provider: string;
  model: string;
  source: string;
}

export interface RolePayload {
  version: number;
  updated_at?: string;
  writes_profile_configs: false;
  storage: string;
  roles: RoleMapping[];
  available_agents: RoleAgentChoice[];
  models: RoleModelChoice[];
}

export interface SkillItem {
  name: string;
  description: string;
  category: string;
  source: string;
}

export interface AgentSkillAssignment {
  agent: string;
  skills: string[];
  notes: string;
}

export interface AgentSkillPayload {
  version: number;
  updated_at?: string;
  storage: string;
  writes_profile_configs: false;
  assignments: AgentSkillAssignment[];
}

export interface AgentProposalRequest {
  agent_name: string;
  description: string;
  provider: string;
  model: string;
  clone_from: string;
  skills: string[];
  notes: string;
}

export interface AgentProposal {
  proposal_id: string;
  status: 'proposed' | 'approved' | 'provisioned' | 'rejected';
  created_at: string;
  created_by: string;
  request: AgentProposalRequest;
  draft_config: Record<string, unknown>;
  writes_profile_configs: false;
  safety_note: string;
}

export interface RemovedAgent {
  removed_id: string;
  agent_name: string;
  status: 'removed' | 'restored' | 'permanently_deleted' | 'expired';
  removed_at: string;
  expires_at: string;
  retention_days: number;
  removed_by: string;
  reason: string;
  writes_profile_configs: false;
  backup?: {
    proposal?: AgentProposal;
    assignment?: AgentSkillAssignment | null;
  } | null;
  restored_at?: string;
  permanently_deleted_at?: string;
  safety_note?: string;
}

export interface Workspace {
  alias: string;
  url: string;
  path?: string;
}

export interface ArmyWorker {
  id: 'claude' | 'codex' | 'minimax' | string;
  label: string;
  kind: 'cli' | 'provider' | string;
  available: boolean;
  path: string;
  notes: string;
}

export type ArmyRunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'needs_review' | 'approved' | 'rejected';

export interface ArmyRun {
  run_id: string;
  parent_run_id: string;
  worker: string;
  task: string;
  repo: string;
  status: ArmyRunStatus;
  created_at: string;
  updated_at: string;
  started_at: string;
  finished_at: string;
  exit_code: number | null;
  workspace_path: string;
  log_path: string;
  reject_reason: string;
  writes_profile_configs: false;
}

export interface ArmyRunRequest {
  worker: string;
  task: string;
  repo?: string;
  dry_run?: boolean;
}

// D-2026-06-08-dash-4: types now live in src/domain.ts (single source
// of truth). Re-exported here for backward compatibility with any
// existing imports of `from '../types/dashboard'`.
export type {
  TopologyNode,
  TopologyAgent,
  TopologyEdge,
  Topology,
  WorkerStatus,
  IssueState,
  AgentRole,
} from '../domain';
