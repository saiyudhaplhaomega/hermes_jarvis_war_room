import React from "react";
import { ErrorBoundary } from "react-error-boundary";
import { DashboardHeader } from "./DashboardHeader";
import { PanelHeader } from "./PanelHeader";
import { useView } from "../contexts/ViewContext";
import { usePanelVisibility } from "../contexts/panelVisibilityStore";
import { COMMAND_PANEL_LINKS } from "./commandMenuLinks";

import { MissionControlOverview } from "./MissionControlOverview";
import { RoleMatrix } from "./RoleMatrix";
import { AgentConstellation } from "./AgentConstellation";
import { MemoryNexus } from "./MemoryNexus";
import { DecisionLog } from "./DecisionLog";
import { KanbanFleet } from "./KanbanFleet";
import { ArmyOperations } from "./ArmyOperations";
import DispatchTerminal from "./DispatchTerminal";
import { DiscordNexus } from "./DiscordNexus";
import { CouncilChamber } from "./CouncilChamber";
import { GitHubWorkspace } from "./GitHubWorkspace";
import { SkillMarketplace } from "./SkillMarketplace";
import { AgentCronJobs } from "./AgentCronJobs";

const panelMap: Record<string, React.FC | React.ComponentType> = {
  "mission-control": MissionControlOverview,
  "role-matrix": RoleMatrix,
  "skill-marketplace": SkillMarketplace,
  "agent-constellation": AgentConstellation,
  "memory-nexus": MemoryNexus,
  "decision-log": DecisionLog,
  "kanban-fleet": KanbanFleet,
  "army-operations": ArmyOperations,
  "cron-jobs": AgentCronJobs,
  "dispatch-terminal": DispatchTerminal,
  "discord-nexus": DiscordNexus,
  "council-chamber": CouncilChamber,
  "github-workspace": GitHubWorkspace,
};

function PanelErrorFallback({ error }: { error: Error }) {
  return (
    <div className="p-4 border border-red-800 bg-red-950/30 rounded text-xs text-red-200">
      Panel error: {error.message}
    </div>
  );
}

function DashboardPanel({ id, children, title }: { id: string; children: React.ReactNode; title: string }) {
  const [collapsed, setCollapsed] = React.useState(false);
  return (
    <section id={id} className="card">
      <PanelHeader title={title} collapsible={true} collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      {!collapsed && children}
    </section>
  );
}

export default function Dashboard() {
  const { view } = useView();
  const { isPanelVisible } = usePanelVisibility();

  return (
    <div className="min-h-screen bg-[#0b0f17] text-gray-100">
      <DashboardHeader />
      {view === "chat" ? (
        <main className="h-[calc(100vh-64px)]">
          <ErrorBoundary FallbackComponent={PanelErrorFallback}>
            <DispatchTerminal fullPage />
          </ErrorBoundary>
        </main>
      ) : (
        <main
          className="p-2 sm:p-4 grid grid-cols-2 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-2 sm:gap-4"
          data-testid="dashboard-grid"
        >
          {COMMAND_PANEL_LINKS.filter((p) => isPanelVisible(p.id)).map((panel) => {
            const Component = panelMap[panel.id];
            if (!Component) return null;
            return (
              <ErrorBoundary key={panel.id} FallbackComponent={PanelErrorFallback}>
                <DashboardPanel id={panel.id} title={panel.label}>
                  <Component />
                </DashboardPanel>
              </ErrorBoundary>
            );
          })}
        </main>
      )}
    </div>
  );
}
