import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { Project } from '../types/dashboard';
import { api } from '../api/client';

interface ProjectCtx {
  project: Project | null;
  projects: Project[];
  setProject: (p: Project | null) => void;
  refresh: () => Promise<void>;
}

const Ctx = createContext<ProjectCtx | null>(null);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);

  const refresh = useCallback(async () => {
    try {
      console.log('ProjectContext: fetching projects...');
      const data = await api.projects();
      console.log('ProjectContext: got data', data);
      setProjects(data.projects || []);
      // active project is included in /project/list response
      if (data.active) {
        setProject(data.active);
      } else if ((data.projects || []).length > 0) {
        setProject(data.projects[0]);
      }
    } catch (e: any) {
      console.error('ProjectContext refresh error:', e.message || e);
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
