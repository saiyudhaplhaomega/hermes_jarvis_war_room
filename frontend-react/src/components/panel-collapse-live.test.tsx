import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { MemoryNexus } from './MemoryNexus';
import { DecisionLog } from './DecisionLog';
import { DiscordNexus } from './DiscordNexus';
import { CouncilChamber } from './CouncilChamber';
import { GitHubWorkspace } from './GitHubWorkspace';
import { AgentConstellation } from './AgentConstellation';
import { KanbanFleet } from './KanbanFleet';
import { RoleMatrix } from './RoleMatrix';
import { KanbanContext } from '../contexts/KanbanContext';
import { ProjectContext } from '../contexts/ProjectContext';
import { DashboardContext } from '../contexts/DashboardContext';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const CSS_PATH = resolve(__dirname, '../index.css');

// Source-CSS regression guard: both rules must be present in
// src/index.css. If either regresses, the live test below will still
// pass on a stale build, so this guard is the real safety net.
let cssSource = '';
beforeAll(() => {
  cssSource = readFileSync(CSS_PATH, 'utf8');
  // The production rule hides every following sibling of the header.
  expect(
    cssSource,
    'expected [data-panel-header].panel-collapsed ~ * in src/index.css'
  ).toMatch(/\[data-panel-header\][^{}]*\.panel-collapsed\s*~\s*\*/);

  // The production rule drops the card's min-height when a header
  // inside it is collapsed, via :has().
  expect(
    cssSource,
    'expected .card:has([data-panel-header].panel-collapsed) in src/index.css'
  ).toMatch(/\.card\s*:\s*has\(\s*\[data-panel-header\][^{}]*\.panel-collapsed\s*\)/);
  expect(
    cssSource,
    'expected .premium-card:has([data-panel-header].panel-collapsed) in src/index.css'
  ).toMatch(/\.premium-card\s*:\s*has\(\s*\[data-panel-header\][^{}]*\.panel-collapsed\s*\)/);
});

// In jsdom, dynamic <style> rule resolution via getComputedStyle is
// limited, so we test the *intent* of the rule: every direct
// sibling of the header is gone from the visible count. We also
// ensure the :has() rule can find the header inside the card (which
// the rule depends on for cascade).
const PROD_HIDE = '[data-panel-header].panel-collapsed ~ * { display: none; }';
const PROD_HAS  = '.card:has([data-panel-header].panel-collapsed), ' +
                  '.premium-card:has([data-panel-header].panel-collapsed) { min-height: 0; }';

function applyCss() {
  const el = document.createElement('style');
  el.textContent = PROD_HIDE + '\n' + PROD_HAS;
  document.head.appendChild(el);
  return () => el.remove();
}

function makeProjectCtx() {
  return {
    project: { slug: 'trading_armageddon', name: 'Trading Armageddon', active: false },
    projects: [],
    setProject: () => {},
    refresh: async () => {},
  } as any;
}
function makeDashboardCtx() {
  return {
    cache: {
      generated_at: '2026-06-04T00:00:00Z',
      agents: [
        { name: 'a', status: 'online' },
        { name: 'b', status: 'idle' },
        { name: 'c', status: 'configured' },
      ],
      tasks: [],
      kanban_by_project: { trading_armageddon: [] },
      decisions: [],
      memory: {},
    } as any,
    loading: false,
    error: null,
    refresh: async () => {},
  } as any;
}
function makeKanbanCtx() {
  return {
    state: { cards: [] },
    refresh: async () => {},
  } as any;
}

function setup(children: React.ReactNode) {
  cleanup();
  const removeCss = applyCss();
  const utils = render(
    <DashboardContext.Provider value={makeDashboardCtx()}>
      <ProjectContext.Provider value={makeProjectCtx()}>
        <KanbanContext.Provider value={makeKanbanCtx()}>
          {children}
        </KanbanContext.Provider>
      </ProjectContext.Provider>
    </DashboardContext.Provider>
  );
  return { ...utils, cleanup: () => { removeCss(); cleanup(); } };
}

function visibleSiblingCount(container: HTMLElement): number {
  const card = container.querySelector('.card, .premium-card');
  if (!card) return -1;
  const header = card.querySelector('[data-panel-header]');
  if (!header) return -1;
  let visible = 0;
  let cur = header.nextElementSibling;
  while (cur) {
    const cs = getComputedStyle(cur as HTMLElement);
    if (cs.display !== 'none') visible++;
    cur = cur.nextElementSibling;
  }
  return visible;
}

describe('panel collapse live behavior (scope + shrink)', () => {
  it('MemoryNexus: hides ALL direct siblings after the header (RED before fix)', () => {
    const { container } = setup(<MemoryNexus />);
    const before = visibleSiblingCount(container);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(before).toBeGreaterThan(1);
    expect(after).toBe(0);
  });

  it('DecisionLog: hides ALL direct siblings after the header (RED before fix)', () => {
    const { container } = setup(<DecisionLog />);
    const before = visibleSiblingCount(container);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(before).toBeGreaterThan(1);
    expect(after).toBe(0);
  });

  it('CouncilChamber: hides its single sibling (footer is nested inside it)', () => {
    const { container } = setup(<CouncilChamber />);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(after).toBe(0);
  });

  it('DiscordNexus: hides its single sibling', () => {
    const { container } = setup(<DiscordNexus />);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(after).toBe(0);
  });

  it('GitHubWorkspace: hides its single sibling', () => {
    const { container } = setup(<GitHubWorkspace />);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(after).toBe(0);
  });

  it('AgentConstellation: hides its single sibling', () => {
    const { container } = setup(<AgentConstellation />);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(after).toBe(0);
  });

  it('KanbanFleet: hides its single sibling', () => {
    const { container } = setup(<KanbanFleet />);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(after).toBe(0);
  });

  it('RoleMatrix: hides ALL 3 direct siblings (RED before fix)', () => {
    const { container } = setup(<RoleMatrix />);
    const before = visibleSiblingCount(container);
    const btn = screen.getByRole('button', { name: /collapse panel/i });
    fireEvent.click(btn);
    const after = visibleSiblingCount(container);
    expect(before).toBeGreaterThan(2);
    expect(after).toBe(0);
  });
});
