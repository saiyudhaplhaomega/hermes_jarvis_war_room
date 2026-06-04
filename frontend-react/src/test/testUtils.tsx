import { DashboardContext } from '../contexts/DashboardContext';
import { ProjectContext } from '../contexts/ProjectContext';
import type { ReactNode } from 'react';
import type { Project } from '../types/dashboard';

export function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    slug: 'trading_armageddon',
    name: 'Trading Armageddon',
    active: false,
    ...overrides,
  };
}

export function TestProviders({
  children,
  cache = null,
  error = null,
  project = null,
}: {
  children: ReactNode;
  cache?: any;
  error?: string | null;
  project?: Project | null;
}) {
  const dashValue: any = {
    cache,
    loading: false,
    error: error ?? null,
    refresh: async () => {},
  };
  const projValue: any = {
    project,
    projects: project ? [project] : [],
    setProject: () => {},
    refresh: async () => {},
  };
  return (
    <DashboardContext.Provider value={dashValue}>
      <ProjectContext.Provider value={projValue}>
        {children}
      </ProjectContext.Provider>
    </DashboardContext.Provider>
  );
}
