/**
 * TopologyMini — compact read-only preview of the company org chart.
 *
 * D-2026-06-08-dash-2: saves ~80% of the vertical space the full
 * TopologyEditor takes, by rendering just node dots + edge lines
 * (no xyflow controls, no drag handles, no toolbar). Click
 * "Expand" to open the full editor in a modal drawer.
 *
 * Visual model:
 *   - Up to 4 levels: boss → manager → lead → worker
 *   - Each node is a small dot with role-color border
 *   - Edges are SVG lines
 *   - Health dots (green/yellow/red) come from agent.status
 */
import { useEffect, useMemo, useState } from 'react';
import { api, type TopologyNode, type TopologyEdge, type TopologyAgent } from '../api/client';

interface Props {
  companyId: string;
  /** When the user clicks "Expand" we ask the parent to show the full editor. */
  onExpand?: () => void;
  /** Height of the preview area in px (default 220). */
  height?: number;
}

interface PositionedNode {
  id: string;
  role: string;
  status: string;
  x: number;
  y: number;
  level: number;
}

function roleColor(role: string): string {
  const r = role.toLowerCase();
  if (r.includes('boss')) return '#f59e0b';
  if (r.includes('manager')) return '#a78bfa';
  if (r.includes('engineering') || r.includes('product') || r.includes('docs')) return '#60a5fa';
  if (r.includes('qa') || r.includes('security')) return '#34d399';
  if (r.includes('scout') || r.includes('researcher')) return '#f472b6';
  return '#9ca3af';
}

function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (s === 'active' || s === 'idle' || s === 'ready') return '#22c55e';
  if (s === 'busy' || s === 'in_progress') return '#eab308';
  if (s === 'error' || s === 'down' || s === 'failed') return '#ef4444';
  return '#6b7280';
}

function buildTree(
  agents: TopologyAgent[],
  edges: TopologyEdge[]
): { positioned: PositionedNode[]; byLevel: PositionedNode[][] } {
  // Find the root: an agent that nobody reports to
  const hasParent = new Set(edges.filter(e => e.type === 'reports_to').map(e => e.from_agent));
  const roots = agents.filter(a => !hasParent.has(a.id));
  const root = roots[0] ?? agents[0];
  if (!root) return { positioned: [], byLevel: [] };

  // BFS by reports_to edges to assign levels
  const levelOf: Record<string, number> = { [root.id]: 0 };
  const queue = [root.id];
  while (queue.length) {
    const cur = queue.shift()!;
    const kids = edges
      .filter(e => e.type === 'reports_to' && e.to_agent === cur)
      .map(e => e.from_agent);
    for (const k of kids) {
      if (levelOf[k] === undefined) {
        levelOf[k] = (levelOf[cur] ?? 0) + 1;
        queue.push(k);
      }
    }
  }
  // Any agent not reached (orphan) goes on level 0
  for (const a of agents) {
    if (levelOf[a.id] === undefined) levelOf[a.id] = 0;
  }

  // Group by level, lay out horizontally within each level
  const levels: Record<number, TopologyAgent[]> = {};
  for (const a of agents) {
    const l = levelOf[a.id];
    (levels[l] ??= []).push(a);
  }
  const maxLevel = Math.max(...Object.keys(levels).map(Number), 0);
  const positioned: PositionedNode[] = [];
  const byLevel: PositionedNode[][] = [];
  for (let l = 0; l <= maxLevel; l++) {
    const items = levels[l] ?? [];
    items.forEach((a, i) => {
      positioned.push({
        id: a.id,
        role: a.role || a.id,
        status: a.status || 'idle',
        x: items.length === 1 ? 0.5 : i / (items.length - 1),
        y: l,
        level: l,
      });
    });
    byLevel.push(items.map((a, i) => ({
      id: a.id,
      role: a.role || a.id,
      status: a.status || 'idle',
      x: items.length === 1 ? 0.5 : i / (items.length - 1),
      y: l,
      level: l,
    })));
  }
  return { positioned, byLevel };
}

export function TopologyMini({ companyId, onExpand, height = 220 }: Props) {
  const [topology, setTopology] = useState<{
    nodes: TopologyNode[];
    agents: TopologyAgent[];
    edges: TopologyEdge[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const t = await api.fetchTopology(companyId);
        if (!cancelled) setTopology(t);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [companyId]);

  const { positioned, byLevel } = useMemo(
    () => (topology ? buildTree(topology.agents, topology.edges) : { positioned: [], byLevel: [] }),
    [topology]
  );

  if (error) {
    return (
      <div className="text-xs text-red-400 mono p-2" data-testid="topology-mini-error">
        Failed to load topology: {error.slice(0, 80)}
      </div>
    );
  }
  if (!topology) {
    return (
      <div className="text-xs text-gray-500 mono p-2" data-testid="topology-mini-loading">
        Loading org chart…
      </div>
    );
  }
  if (positioned.length === 0) {
    return (
      <div className="text-xs text-gray-500 mono p-2" data-testid="topology-mini-empty">
        No agents yet. Add some via Agent Growth Studio.
      </div>
    );
  }

  // SVG canvas
  const padding = 16;
  const maxLevel = Math.max(...byLevel.map(l => l.length), 1);
  const levelHeight = 38;
  const totalH = byLevel.length * levelHeight + padding * 2;
  const totalW = 320; // fixed width; dots are positioned by x fraction
  const innerW = totalW - padding * 2;
  const innerH = totalH - padding * 2;

  const px = (p: PositionedNode) => ({
    cx: padding + p.x * innerW,
    cy: padding + (p.y / Math.max(byLevel.length - 1, 1)) * innerH,
  });

  return (
    <div data-testid="topology-mini" className="text-xs">
      <svg
        viewBox={`0 0 ${totalW} ${totalH}`}
        width="100%"
        height={height}
        preserveAspectRatio="xMidYMid meet"
        style={{ display: 'block' }}
        role="img"
        aria-label="Mini org chart preview"
      >
        {/* Edges */}
        {topology.edges
          .filter(e => e.type === 'reports_to')
          .map((e, i) => {
            const from = positioned.find(p => p.id === e.from_agent);
            const to = positioned.find(p => p.id === e.to_agent);
            if (!from || !to) return null;
            const f = px(from);
            const t = px(to);
            return (
              <line
                key={i}
                x1={f.cx} y1={f.cy} x2={t.cx} y2={t.cy}
                stroke="#374151"
                strokeWidth={1}
                strokeDasharray="2 2"
              />
            );
          })}
        {/* Nodes */}
        {positioned.map(p => {
          const { cx, cy } = px(p);
          const c = roleColor(p.role);
          const s = statusColor(p.status);
          return (
            <g key={p.id} transform={`translate(${cx}, ${cy})`}>
              <circle r={9} fill="#111827" stroke={c} strokeWidth={1.5} />
              <circle r={3} fill={s} />
              <text
                y={22}
                textAnchor="middle"
                fontSize="9"
                fill="#9ca3af"
                style={{ fontFamily: 'monospace' }}
              >
                {p.id.length > 14 ? p.id.slice(0, 12) + '…' : p.id}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex justify-between items-center pt-1 text-[10px] text-gray-500 mono">
        <span>{topology.agents.length} agents · {topology.edges.length} edges · {maxLevel} levels</span>
        {onExpand && (
          <button
            type="button"
            onClick={onExpand}
            className="text-jarvis-accent hover:underline"
            data-testid="topology-mini-expand"
          >
            Expand ▸
          </button>
        )}
      </div>
    </div>
  );
}
