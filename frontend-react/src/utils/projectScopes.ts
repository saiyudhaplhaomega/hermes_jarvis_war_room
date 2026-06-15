// Project Scopes (D-2026-06-14):
// The dashboard has 3 project scopes:
//
//   1. global-hermes    - the top-level Hermes folder on the user's
//                          machine (~/.hermes or %LOCALAPPDATA%/hermes).
//                          Things created here apply to the WHOLE
//                          Hermes installation, not any one project.
//                          Anything imported from a GitHub repo
//                          defaults to this scope unless the user
//                          picks a different one.
//
//   2. jarvis-war-room  - the Jarvis War Room workspace itself
//                          (the dashboard, the launcher, the council,
//                          the research, etc.). Things created here
//                          are scoped to the war room but NOT to any
//                          one user project.
//
//   3. <user-project>   - a specific user project (e.g. hello-world,
//                          my-app, etc.). Things created here are
//                          scoped to that project.
//
// The `useProject()` context still owns the chat-active project.
// These scopes are additionally available in the Cron Jobs and
// Skill Marketplace panels.

export const PROJECT_SCOPES = {
  GLOBAL_HERMES: 'global-hermes',
  JARVIS_WAR_ROOM: 'jarvis-war-room',
  DEFAULT: 'default',
} as const;

export type ProjectScopeSlug = typeof PROJECT_SCOPES[keyof typeof PROJECT_SCOPES];

export interface ProjectScope {
  slug: string;
  label: string;
  icon: string;
  description: string;
  /** UI color hint: 'amber' for top-level, 'cyan' for war-room, 'violet' for user project. */
  color: 'amber' | 'cyan' | 'violet' | 'gray';
}

export const SCOPE_DEFINITIONS: ProjectScope[] = [
  {
    slug: PROJECT_SCOPES.GLOBAL_HERMES,
    label: 'Global Hermes',
    icon: '🌍',
    description: 'Top-level Hermes folder. Applies to the whole installation, not any one project. New GitHub repo imports land here by default.',
    color: 'amber',
  },
  {
    slug: PROJECT_SCOPES.JARVIS_WAR_ROOM,
    label: 'Jarvis War Room',
    icon: '⚔',
    description: 'The War Room workspace itself — dashboard, launcher, council, research. Scoped to the war room but not to a user project.',
    color: 'cyan',
  },
];

export const SCOPE_DESCRIPTIONS: Record<string, string> = Object.fromEntries(
  SCOPE_DEFINITIONS.map((s) => [s.slug, s.description]),
);

/**
 * Returns the badge color class for a given project slug.
 * - 'global-hermes' → amber
 * - 'jarvis-war-room' → cyan
 * - 'default' or unrecognized → gray
 * - any other value → violet (treated as a user project)
 */
export function scopeColor(slug: string): ProjectScope['color'] {
  if (slug === PROJECT_SCOPES.GLOBAL_HERMES) return 'amber';
  if (slug === PROJECT_SCOPES.JARVIS_WAR_ROOM) return 'cyan';
  if (slug === PROJECT_SCOPES.DEFAULT) return 'gray';
  return 'violet';
}

/** Friendly display label for a project slug. */
export function scopeLabel(slug: string): string {
  if (slug === PROJECT_SCOPES.GLOBAL_HERMES) return 'Global Hermes';
  if (slug === PROJECT_SCOPES.JARVIS_WAR_ROOM) return 'Jarvis War Room';
  if (slug === PROJECT_SCOPES.DEFAULT) return 'Default';
  return slug;
}
