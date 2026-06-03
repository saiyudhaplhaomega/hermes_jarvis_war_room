import React, { useMemo, memo } from 'react';
import { useKanban } from '../contexts/KanbanContext';
import { useProject } from '../contexts/ProjectContext';
import { PanelHeader } from './PanelHeader';
import type { KanbanCard } from '../types/dashboard';

const COLUMNS = ['todo', 'ready', 'running', 'done'] as const;

function isStale(card: KanbanCard): boolean {
  if (card.status !== 'running' || !card.last_heartbeat_at) return false;
  const hb = new Date(card.last_heartbeat_at).getTime();
  return Date.now() - hb > 15 * 60 * 1000;
}

const KanbanCardItem = memo(function KanbanCardItem({ card }: { card: KanbanCard }) {
  const stale = isStale(card);
  let extraClass = '';
  if (card.status === 'blocked') extraClass = ' blocked';
  else if (card.status === 'review') extraClass = ' review';
  if (stale) extraClass += ' stale';

  const depCount = card.parents ? card.parents.split(',').filter(Boolean).length : 0;

  const progressWidth = useMemo(() => {
    let hash = 0;
    for (let i = 0; i < card.id.length; i++) hash = ((hash << 5) - hash) + card.id.charCodeAt(i);
    return `${20 + (Math.abs(hash) % 60)}%`;
  }, [card.id]);

  return (
    <div className={`kanban-card border-l-2${extraClass}`}
         style={{ borderLeftColor: card.color || '#6b7280' }}>
      <div className="font-semibold text-gray-200 text-xs flex items-center gap-1">
        {card.title}
        {depCount > 0 && <span className="dep-badge" title={`Depends on: ${card.parents}`}>{'⛓'} {depCount}</span>}
        {card.last_heartbeat_at && <span className="heartbeat">{'●'}</span>}
      </div>
      <div className="flex justify-between text-[10px] text-gray-400 mt-1">
        <span>{card.assignee}</span>
        <span>{card.status} {card.project ? `| ${card.project}` : ''}</span>
      </div>
      {card.status === 'running' && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: progressWidth }} />
        </div>
      )}
      <div className="card-details">
        <div>ID: {card.id} · Priority: {card.priority}</div>
        {card.body && <div className="truncate">{card.body.slice(0, 80)}</div>}
        {card.blocked_by_parents && <div className="text-amber-400">{'⏳'} Waiting for parent tasks</div>}
        {stale && <div className="text-red-400">{'⚠'} Stale worker (&gt;15min)</div>}
        <div className="flex gap-2 mt-1">
          {!!card.comment_count && <span className="text-gray-500">{'💬'} {card.comment_count}</span>}
          {!!card.run_count && <span className="text-gray-500">{'▶'} {card.run_count}</span>}
        </div>
      </div>
    </div>
  );
});

export function KanbanFleet() {
  const { state, refresh } = useKanban();
  const { project } = useProject();

  React.useEffect(() => {
    refresh(project?.slug);
  }, [project?.slug, refresh]);

  const filtered = useMemo(() => {
    if (!project) return [];
    return state.cards.filter(c =>
      c.project === project.slug ||
      (c.project === '' && (c as any).tenant === project.slug)
    );
  }, [state.cards, project]);

  const byCol = useMemo(() => {
    const map: Record<string, KanbanCard[]> = {};
    COLUMNS.forEach(c => map[c] = []);
    filtered.forEach(c => {
      const col = COLUMNS.includes(c.status as any) ? c.status : 'todo';
      map[col].push(c);
    });
    COLUMNS.forEach(c => map[c].sort((a, b) => (b.priority || 0) - (a.priority || 0)));
    return map;
  }, [filtered]);

  return (
    <div className="card md:col-span-2 lg:col-span-2">
      <PanelHeader
        title="Kanban Fleet"
        badge={project ? `Project: ${project.slug}` : 'No project selected'}
        right={<span className="text-xs text-gray-500 mono">{filtered.length} cards</span>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {COLUMNS.map(col => (
          <div key={col} className="kanban-col">
            <div className="text-xs font-bold text-gray-500 uppercase mb-2">
              {col} <span className="float-right">{byCol[col].length}</span>
            </div>
            {byCol[col].map(card => (
              <KanbanCardItem key={card.id} card={card} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
