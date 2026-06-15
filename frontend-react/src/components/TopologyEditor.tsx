/**
 * TopologyEditor — 2D read-only canvas of the company's agent hierarchy.
 *
 * D-2026-06-08-topology-editor (sub-phase 2):
 *   - Renders agents as xyflow nodes, edges as lines
 *   - Uses dagre to auto-layout top-down
 *   - Read-only in sub-phase 2; sub-phase 3 will add click-to-edit
 *
 * Sub-phase 2 deliberately does NOT cover write endpoints (POST /edges).
 * See decisions/D-2026-06-08-topology-editor.md v2 for the full plan.
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';

import { api } from '../api/client';
import type { Topology } from '../types/dashboard';

const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

type AgentNodeData = {
  label: string;
  role: string;
  team: string;
  workerType: string;
  status: string;
};

function AgentNode({ data }: NodeProps<Node<AgentNodeData>>) {
  return (
    <div
      className="rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-xs text-slate-100 shadow"
      data-testid={`topology-node-${data.role}-${data.label}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      <div className="font-semibold">{data.label}</div>
      <div className="text-slate-400">team: {data.team} · {data.workerType}</div>
      <div className="text-slate-500">status: {data.status}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
    </div>
  );
}

const nodeTypes = { agent: AgentNode };

/**
 * Error boundary around the xyflow canvas. ReactFlow depends on real DOM
 * measurements (ZoomPane needs element sizes); in jsdom it throws, so we
 * catch and fall back to a plain HTML rendering for tests AND for any
 * host that can't run the canvas (e.g. screen readers, headless servers).
 */
class CanvasErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.warn('TopologyEditor canvas failed, falling back to plain list:', error.message, info.componentStack);
  }
  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

function layoutWithDagre(nodes: Node<AgentNodeData>[], edges: Edge[]): { nodes: Node<AgentNodeData>[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 60 });

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));

  dagre.layout(g);

  const laidOutNodes = nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
    };
  });
  return { nodes: laidOutNodes, edges };
}

function shapeTopology(topo: Topology): { nodes: Node<AgentNodeData>[]; edges: Edge[] } {
  const agentNodes: Node<AgentNodeData>[] = topo.agents.map((a) => ({
    id: a.id,
    type: 'agent',
    position: { x: 0, y: 0 },
    data: {
      label: a.name ?? a.id,
      role: a.role ?? 'unknown',
      team: a.team_id ?? 'default',
      workerType: a.worker_type ?? a.model_binding ?? 'unknown',
      status: a.status ?? 'unknown',
    },
  }));

  const edges: Edge[] = topo.edges
    .filter((e) => e.from_agent && e.to_agent)
    .map((e) => ({
      id: e.id ?? `${e.from_agent}->${e.to_agent}:${e.type}`,
      source: e.from_agent!,
      target: e.to_agent!,
      label: e.type,
    }));

  // If there are no agents but there are control-plane nodes, still show
  // them as placeholders so the user knows the topology is loaded.
  if (agentNodes.length === 0 && topo.nodes.length > 0) {
    topo.nodes.forEach((n, idx) => {
      agentNodes.push({
        id: n.id,
        type: 'agent',
        position: { x: 0, y: idx * (NODE_HEIGHT + 20) },
        data: { label: n.id, role: n.kind, team: 'control', workerType: n.backend ?? 'local', status: n.status ?? 'unknown' },
      });
    });
  }

  return layoutWithDagre(agentNodes, edges);
}

/**
 * Plain-HTML fallback renderer (no ReactFlow, no jsdom dependency).
 * Shows the same data as a list of agent cards. Used both in tests and
 * as the error boundary's fallback.
 */
function PlainTopologyList({ nodes, edges }: { nodes: Node<AgentNodeData>[]; edges: Edge[] }) {
  return (
    <div className="space-y-2 p-2" data-testid="topology-plain-list">
      {nodes.map((n) => (
        <div
          key={n.id}
          data-testid={`topology-node-${n.id}`}
          className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        >
          <div className="font-semibold text-slate-100">{n.data.label}</div>
          <div className="text-slate-400">team: {n.data.team} · {n.data.workerType}</div>
          <div className="text-slate-500">status: {n.data.status}</div>
        </div>
      ))}
      {edges.map((e) => (
        <div
          key={e.id}
          data-testid={`topology-edge-${e.id}`}
          className="text-xs text-slate-500"
        >
          {e.source} → {e.target} ({e.label})
        </div>
      ))}
    </div>
  );
}

export function TopologyEditor({ companyId }: { companyId: string }) {
  const [topology, setTopology] = useState<Topology | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.fetchTopology(companyId)
      .then((t) => { if (!cancelled) { setTopology(t); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setError(String(e?.message ?? e)); setLoading(false); } });
    return () => { cancelled = true; };
  }, [companyId]);

  const { nodes, edges } = useMemo(
    () => (topology ? shapeTopology(topology) : { nodes: [], edges: [] }),
    [topology]
  );

  if (loading) {
    return (
      <div className="rounded border border-slate-700 p-4" data-testid="topology-loading">
        <div className="text-slate-400">Loading topology for {companyId}…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded border border-red-700 bg-red-950 p-4" data-testid="topology-error">
        <div className="text-red-300">Failed to load topology: {error}</div>
      </div>
    );
  }

  return (
    <div
      className="h-[480px] w-full rounded border border-slate-700"
      data-testid="topology-editor"
    >
      <CanvasErrorBoundary fallback={<PlainTopologyList nodes={nodes} edges={edges} />}>
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={true}
          >
            <Background gap={16} size={1} />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </ReactFlowProvider>
      </CanvasErrorBoundary>
      <div className="sr-only" aria-label="Topology edge list">
        {edges.map((e) => (
          <span key={e.id} data-testid={`topology-edge-${e.id}`}>
            {e.source} to {e.target} ({String(e.label ?? '')})
          </span>
        ))}
      </div>
    </div>
  );
}
