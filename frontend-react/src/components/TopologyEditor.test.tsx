/**
 * Tests for the TopologyEditor React component (sub-phase 2, D-2026-06-08).
 *
 * Sub-phase 2 = the static 2D xyflow-based read-only canvas that consumes
 * GET /companies/{id}/topology and renders agents as nodes, edges as lines.
 * Sub-phase 3 will add write endpoints and the click-to-add-node UI.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { TopologyEditor } from '../components/TopologyEditor';
import * as api from '../api/client';

// Mock the API client so tests don't need the FastAPI server.
// api/client.ts has `export const api = { fetchTopology, ... }`, but the
// tests access it via `api.fetchTopology` after `import * as api`. So we
// need both: a named export AND the default module shape.
vi.mock('../api/client', () => {
  const fetchTopology = vi.fn();
  return {
    api: { fetchTopology },
    fetchTopology, // also expose as a named export for the test's import
  };
});

const fakeTopology = {
  company_id: 'jarvis-war-room',
  nodes: [
    { id: 'hermes-local-0', kind: 'control', backend: 'local', status: 'active' },
  ],
  agents: [
    { id: 'jarvis-boss', name: 'Boss', role: 'boss', team_id: 'leadership',
      worker_type: 'codex', status: 'idle' },
    { id: 'jarvis-manager', name: 'Manager', role: 'manager', team_id: 'leadership',
      worker_type: 'codex', status: 'idle' },
    { id: 'jarvis-engineering-lead', name: 'Engineering Lead', role: 'eng-lead',
      team_id: 'engineering', worker_type: 'codex', status: 'idle' },
  ],
  edges: [
    { id: 'e1', type: 'reports_to', from_agent: 'jarvis-manager', to_agent: 'jarvis-boss' },
    { id: 'e2', type: 'reports_to', from_agent: 'jarvis-engineering-lead',
      to_agent: 'jarvis-manager' },
  ],
};

describe('TopologyEditor (sub-phase 2, read-only)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it('renders without crashing when topology is empty', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue({
      company_id: 'jarvis-war-room', nodes: [], agents: [], edges: [],
    });
    render(<TopologyEditor companyId="jarvis-war-room" />);
    // First render shows the loading state, then transitions to the editor
    // view (which is empty but present). Wait for the loading state to clear.
    await waitFor(() => {
      expect(screen.queryByTestId('topology-loading')).not.toBeInTheDocument();
    });
    expect(screen.getByTestId('topology-editor')).toBeInTheDocument();
  });

  it('shows a loading state while the API call is in flight', () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise(() => {}) // never resolves
    );
    render(<TopologyEditor companyId="jarvis-war-room" />);
    expect(screen.getByTestId('topology-loading')).toBeInTheDocument();
  });

  it('renders one node per agent and one edge per topology edge', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockResolvedValue(fakeTopology);
    render(<TopologyEditor companyId="jarvis-war-room" />);
    await waitFor(() => {
      // 3 agent nodes (the mock has no control-plane node)
      expect(screen.getAllByTestId(/^topology-node-/)).toHaveLength(3);
      // 2 edges
      expect(screen.getAllByTestId(/^topology-edge-/)).toHaveLength(2);
    });
  });

  it('shows an error message when the API call fails', async () => {
    (api.fetchTopology as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('network down')
    );
    render(<TopologyEditor companyId="jarvis-war-room" />);
    await waitFor(() => {
      expect(screen.getByTestId('topology-error')).toBeInTheDocument();
    });
    // The actual error from api/client.ts wraps the original message; we
    // accept any error string that includes the word "topology" to confirm
    // we routed through the error branch.
    expect(screen.getByTestId('topology-error').textContent).toMatch(/topology/i);
  });
});
