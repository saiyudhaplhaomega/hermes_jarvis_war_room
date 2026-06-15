import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { Project } from '../types/dashboard';
import { api } from '../api/client';

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

interface ProjectCtx {
  project: Project | null;
  projects: Project[];
  setProject: (p: Project | null) => void;
  refresh: () => Promise<void>;
}

const Ctx = createContext<ProjectCtx | null>(null);

// D-2026-06-09 (post-sprint cleanup): export the context object so
// tests can mount providers in arbitrary compositions. Matches the
// pattern in KanbanContext.tsx and the new DashboardContext export.
export const ProjectContext = Ctx;

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);

  const refresh = useCallback(async () => {
    try {
      const data = await api.projects();
      setProjects(data.projects || []);

      if (data.active) {
        setProject(data.active);
      } else if ((data.projects || []).length > 0) {
        setProject(data.projects[0]);
      }
    } catch (e: unknown) {
      console.error('ProjectContext refresh error:', errorMessage(e));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const doSetProject = useCallback(async (p: Project | null) => {
    if (p) {
      await api.selectProject(p.slug);
    }
    setProject(p);
  }, []);

  return (
    <Ctx.Provider value={{ project, projects, setProject: doSetProject, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useProject() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useProject must be inside ProjectProvider');
  return ctx;
}
