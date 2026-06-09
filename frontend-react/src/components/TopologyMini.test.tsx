/**
 * Tests for TopologyMini (D-2026-06-08-dash-2).
 *
 * TopologyMini is a compact read-only SVG preview of the company
 * org chart. The full TopologyEditor is 234 LOC; this one renders
 * in a fixed-height box (~220px) with no toolbar, no drag handles,
 * and an "Expand" button to open the full editor in a drawer.
 */
import { describe, it, expect, beforeAll, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';

// Mock the API client before importing the component
vi.mock('../api/client', () => ({
  api: {
    fetchTopology: vi.fn(),
  },
}));

import { TopologyMini } from './TopologyMini';
import { api } from '../api/client';

const fakeTopology = {
  company_id: 'jarvis-war-room',
  nodes: [],
  agents: [
    { id: 'jarvis-boss', role: 'boss', status: 'active' },
    { id: 'jarvis-manager', role: 'manager', status: 'active' },
    { id: 'jarvis-engineering-lead', role: 'engineering lead', status: 'idle' },
    { id: 'jarvis-qa-lead', role: 'qa lead', status: 'idle' },
  ],
  edges: [
    { from_agent: 'jarvis-manager', to_agent: 'jarvis-boss', type: 'reports_to' },
    { from_agent: 'jarvis-engineering-lead', to_agent: 'jarvis-manager', type: 'reports_to' },
    { from_agent: 'jarvis-qa-lead', to_agent: 'jarvis-engineering-lead', type: 'reports_to' },
  ],
};

beforeAll(() => {
  // jsdom does not implement SVG getComputedTextLength etc; that's fine
  // — we test structure, not rendering metrics.
});

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe('TopologyMini', () => {
  it('shows a loading state while the topology is being fetched', () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
    render(<TopologyMini companyId="jarvis-war-room" />);
    expect(screen.getByTestId('topology-mini-loading')).toBeInTheDocument();
  });

  it('renders one SVG dot per agent after loading', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue(fakeTopology);
    render(<TopologyMini companyId="jarvis-war-room" />);
    const mini = await screen.findByTestId('topology-mini');
    expect(mini).toBeInTheDocument();
    // 4 agents -> 4 <g> groups
    const groups = mini.querySelectorAll('svg g');
    // Each agent has 1 group; also no nested groups in our layout
    expect(groups.length).toBeGreaterThanOrEqual(4);
  });

  it('renders one SVG line per reports_to edge', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue(fakeTopology);
    render(<TopologyMini companyId="jarvis-war-room" />);
    const mini = await screen.findByTestId('topology-mini');
    const lines = mini.querySelectorAll('svg line');
    // 3 reports_to edges in the fake data
    expect(lines.length).toBe(3);
  });

  it('shows the agent/edge/level count in the footer', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue(fakeTopology);
    render(<TopologyMini companyId="jarvis-war-room" />);
    const mini = await screen.findByTestId('topology-mini');
    expect(mini.textContent).toMatch(/4 agents/);
    expect(mini.textContent).toMatch(/3 edges/);
  });

  it('shows an error message when the API fails', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('network down')
    );
    render(<TopologyMini companyId="jarvis-war-room" />);
    const err = await screen.findByTestId('topology-mini-error');
    expect(err.textContent).toMatch(/network down/);
  });

  it('shows an empty state when there are zero agents', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue({
      company_id: 'jarvis-war-room',
      nodes: [],
      agents: [],
      edges: [],
    });
    render(<TopologyMini companyId="jarvis-war-room" />);
    const empty = await screen.findByTestId('topology-mini-empty');
    expect(empty).toBeInTheDocument();
  });

  it('renders the Expand button when onExpand is provided', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue(fakeTopology);
    const onExpand = vi.fn();
    render(<TopologyMini companyId="jarvis-war-room" onExpand={onExpand} />);
    const btn = await screen.findByTestId('topology-mini-expand');
    fireEvent.click(btn);
    expect(onExpand).toHaveBeenCalledTimes(1);
  });

  it('omits the Expand button when no onExpand callback is given', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue(fakeTopology);
    render(<TopologyMini companyId="jarvis-war-room" />);
    const mini = await screen.findByTestId('topology-mini');
    expect(mini.querySelector('[data-testid="topology-mini-expand"]')).toBeNull();
  });
});
