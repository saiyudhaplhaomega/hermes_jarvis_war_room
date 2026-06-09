/**
 * Centralized domain types for the War Room dashboard.
 *
 * D-2026-06-08-dash-4: previously each component defined its own
 * copies of TopologyNode / TopologyEdge / TopologyAgent, leading to
 * drift. This module is the single source of truth — components
 * re-export from here.
 *
 * Backend shape (from GET /companies/{id}/topology):
 *   { company_id, nodes: [...], agents: [...], edges: [...] }
 *
 *   nodes:  control-plane nodes (e.g. hermes-local-0). Not the
 *           same as agents — nodes are LLM runtimes, agents are
 *           roles that run on a node.
 *
 *   agents: rows from the `agents` table. Each has id, role,
 *           status, team, model, monthly_budget, etc.
 *
 *   edges:  rows from the `edges` table. type is
 *           "reports_to" or "collaborates_with".
 */

export interface TopologyNode {
  id: string;
  kind: string;          // "control" | "worker"
  address?: string;
  backend?: string;
  status?: string;
  namespace?: string;
  last_liveness_at?: string | null;
  created_at?: string;
  capacity_json?: string | null;
}

export interface TopologyAgent {
  id: string;
  company_id?: string;
  team_id?: string;
  node_id?: string;
  name?: string;
  role?: string;
  worker_type?: string;
  status?: string;       // "idle" | "active" | "busy" | "error"
  worker_kind?: string;  // "api" | "cli" | "local"
  model_binding?: string;
  monthly_budget_json?: string | null;
  hire_rate_json?: string | null;
  soul_path?: string | null;
  agent_card_json?: string | null;
  created_at?: string;
}

export interface TopologyEdge {
  id?: string;
  company_id?: string;
  type: "reports_to" | "collaborates_with";
  from_agent: string;
  to_agent: string;
}

export interface Topology {
  company_id: string;
  nodes: TopologyNode[];
  agents: TopologyAgent[];
  edges: TopologyEdge[];
}

/** Worker readiness for the operations dashboard. */
export type WorkerStatus = "ready" | "running" | "stalled" | "crashed" | "disabled";

/** Issue lifecycle. */
export type IssueState = "draft" | "open" | "in_progress" | "blocked" | "in_review" | "done" | "archived";

/** Agent role taxonomy. */
export type AgentRole =
  | "boss"
  | "manager"
  | "engineering-lead"
  | "qa-lead"
  | "security-lead"
  | "docs-lead"
  | "product-lead"
  | "scout"
  | "researcher"
  | "operator";
