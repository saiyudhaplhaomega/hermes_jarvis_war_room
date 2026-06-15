import React, { Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";
import "./App.css";

import { PanelVisibilityProvider } from "./contexts/PanelVisibilityContext";
import { ViewProvider } from "./contexts/ViewContext";
import { ProjectProvider } from "./contexts/ProjectContext";
import { DashboardProvider } from "./contexts/DashboardContext";
import { KanbanProvider } from "./contexts/KanbanContext";
import { ChatProvider } from "./contexts/ChatContext";

function ErrorFallback({ error }: { error: Error }) {
  return (
    <div className="error-boundary">
      <h2>Something went wrong</h2>
      <pre>{error.message}</pre>
    </div>
  );
}

const Dashboard = React.lazy(() => import("./components/Dashboard"));

function App() {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <Suspense fallback={<div className="loading">Loading...</div>}>
        <PanelVisibilityProvider>
          <ViewProvider>
            <ProjectProvider>
              <DashboardProvider>
                <KanbanProvider>
                  <ChatProvider>
                    <Dashboard />
                  </ChatProvider>
                </KanbanProvider>
              </DashboardProvider>
            </ProjectProvider>
          </ViewProvider>
        </PanelVisibilityProvider>
      </Suspense>
    </ErrorBoundary>
  );
}

export default App;
