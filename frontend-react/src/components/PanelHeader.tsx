import React, { useState } from 'react';

interface Props {
  title: string;
  badge?: string;
  right?: React.ReactNode;
  collapsible?: boolean;
}

export function PanelHeader({ title, badge, right, collapsible = false }: Props) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      data-panel-header
      className={collapsed ? 'panel-collapsed' : undefined}
    >
      <div className="flex justify-between items-center border-b border-jarvis-border pb-2 mb-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-gray-300">{title}</h2>
        <div className="flex items-center gap-2">
          {badge && <span className="text-[10px] text-gray-500 mono">{badge}</span>}
          {right}
          {collapsible && (
            <button
              type="button"
              className="panel-header-toggle"
              aria-label="Collapse panel"
              aria-expanded={!collapsed}
              onClick={() => setCollapsed(value => !value)}
            >
              <span className="panel-collapse-icon" aria-hidden>▾</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
