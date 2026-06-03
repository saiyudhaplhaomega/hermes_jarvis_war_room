export type DashboardViewName = 'chat' | 'dashboard';

export interface CommandPanelLink {
  id: string;
  label: string;
  icon: string;
  description: string;
}

export const COMMAND_PANEL_LINKS: CommandPanelLink[] = [
  { id: 'mission-control', label: 'Mission Control', icon: '🎯', description: 'System overview and active metrics' },
  { id: 'role-matrix', label: 'Agent Growth Studio', icon: '🧩', description: 'Provider/model dropdowns, skill feed, proposals, graveyard' },
  { id: 'agent-constellation', label: 'Agent Constellation', icon: '✨', description: 'Live agent topology and health' },
  { id: 'memory-nexus', label: 'Memory Nexus', icon: '🧠', description: 'Project-scoped memories' },
  { id: 'decision-log', label: 'Decision Log', icon: '📋', description: 'Recorded decisions and gates' },
  { id: 'kanban-fleet', label: 'Kanban Fleet', icon: '📊', description: 'Project-specific tasks and lanes' },
  { id: 'army-operations', label: 'Army Operations', icon: '🛰️', description: 'CLI worker missions, logs, diffs, approve/reject/rerun' },
  { id: 'dispatch-terminal', label: 'Dispatch Terminal', icon: '💬', description: 'Embedded command/chat panel' },
  { id: 'discord-nexus', label: 'Discord Nexus', icon: '🔌', description: 'Discord coordination status' },
  { id: 'council-chamber', label: 'Council Chamber', icon: '🏛️', description: 'Council review and approval gates' },
  { id: 'github-workspace', label: 'GitHub Workspace', icon: '📦', description: 'Repository and workspace controls' },
];
