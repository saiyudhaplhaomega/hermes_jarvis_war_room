import { ViewProvider, useView } from './contexts/ViewContext';
import type { ReactNode } from 'react';
import { ProjectProvider } from './contexts/ProjectContext';
import { KanbanProvider } from './contexts/KanbanContext';
import { ChatProvider } from './contexts/ChatContext';
import { DashboardProvider } from './contexts/DashboardContext';
import { ConnectionProvider } from './contexts/ConnectionContext';
import { DashboardHeader } from './components/DashboardHeader';
import { AgentConstellation } from './components/AgentConstellation';
import { MemoryNexus } from './components/MemoryNexus';
import { DecisionLog } from './components/DecisionLog';
import { KanbanFleet } from './components/KanbanFleet';
import DispatchTerminal from './components/DispatchTerminal';
import { DiscordNexus } from './components/DiscordNexus';
import { CouncilChamber } from './components/CouncilChamber';
import { GitHubWorkspace } from './components/GitHubWorkspace';
import { AuditStrip } from './components/AuditStrip';
import { SessionDrawer } from './components/SessionDrawer';
import { MissionControlOverview } from './components/MissionControlOverview';
import { RoleMatrix } from './components/RoleMatrix';
import { ArmyOperations } from './components/ArmyOperations';
import { PanelVisibilityProvider } from './contexts/PanelVisibilityContext';
import { usePanelVisibility } from './contexts/panelVisibilityStore';

function ChatView() {
  return (
    <div className="flex flex-col h-[calc(100vh-56px)]">
      <DispatchTerminal fullPage />
    </div>
  );
}

function PanelSection({ id, className = '', children }: { id: string; className?: string; children: ReactNode }) {
  const { isPanelVisible } = usePanelVisibility();
  if (!isPanelVisible(id)) return null;
  return <section id={id} className={`dashboard-section ${className}`.trim()}>{children}</section>;
}

function DashboardView() {
  return (
    <main className="p-4 premium-shell dashboard-layout">
      <div className="dashboard-top-row">
        <PanelSection id="mission-control"><MissionControlOverview /></PanelSection>
        <PanelSection id="role-matrix" className="agent-growth-section"><RoleMatrix /></PanelSection>
      </div>
      <div className="dashboard-panel-grid">
        <PanelSection id="kanban-fleet" className="wide-panel"><KanbanFleet /></PanelSection>
        <PanelSection id="army-operations" className="wide-panel"><ArmyOperations /></PanelSection>
        <PanelSection id="agent-constellation"><AgentConstellation /></PanelSection>
        <PanelSection id="memory-nexus"><MemoryNexus /></PanelSection>
        <PanelSection id="decision-log"><DecisionLog /></PanelSection>
        <PanelSection id="dispatch-terminal"><DispatchTerminal /></PanelSection>
        <PanelSection id="discord-nexus"><DiscordNexus /></PanelSection>
        <PanelSection id="council-chamber"><CouncilChamber /></PanelSection>
        <PanelSection id="github-workspace"><GitHubWorkspace /></PanelSection>
      </div>
    </main>
  );
}

function Body() {
  const { view } = useView();
  return view === 'chat' ? <ChatView /> : <DashboardView />;
}

export default function App() {
  return (
    <ConnectionProvider>
      <DashboardProvider>
        <ViewProvider>
          <ProjectProvider>
            <KanbanProvider>
              <ChatProvider>
                <PanelVisibilityProvider>
                  <div className="min-h-screen bg-jarvis-bg text-jarvis-text font-sans app-cosmos">
                    <DashboardHeader />
                    <Body />
                    <AuditStrip />
                    <SessionDrawer />
                  </div>
                </PanelVisibilityProvider>
              </ChatProvider>
            </KanbanProvider>
          </ProjectProvider>
        </ViewProvider>
      </DashboardProvider>
    </ConnectionProvider>
  );
}
