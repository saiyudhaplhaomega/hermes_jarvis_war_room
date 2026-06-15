import React, { useState } from 'react';

interface Props {
  title: string;
  subtitle?: string;
  badge?: string;
  accent?: string;
  right?: React.ReactNode;
  collapsible?: boolean;
  /**
   * Current collapsed state. If provided, the parent owns the state
   * (pair with onToggle). If omitted, this component uses local
   * useState, so collapses will not survive a page refresh.
   *
   * D-2026-06-08-dash-1: prefer the controlled form (wire to
   * `usePanelState` from ../hooks/usePanelState) for persistence.
   */
  collapsed?: boolean;
  /** Called when the user clicks the toggle. */
  onToggle?: () => void;
}

export function PanelHeader({
  title,
  subtitle,
  badge,
  right,
  collapsible = false,
  collapsed: collapsedProp,
  onToggle: onToggleProp,
}: Props) {
  const isControlled = collapsedProp !== undefined;
  const [localCollapsed, setLocalCollapsed] = useState(false);
  const collapsed = isControlled ? collapsedProp : localCollapsed;
  const onToggle = onToggleProp ?? (() => setLocalCollapsed((v) => !v));

  return (
    <div
      data-panel-header
      data-collapsed={collapsed ? 'true' : 'false'}
      className={collapsed ? 'panel-collapsed' : undefined}
    >
      <div className="flex justify-between items-center border-b border-jarvis-border pb-2 mb-3">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-gray-300">{title}</h2>
          {subtitle && <p className="mt-1 text-xs normal-case tracking-normal text-gray-500">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-2">
          {badge && <span className="text-[10px] text-gray-500 mono">{badge}</span>}
          {right}
          {collapsible && (
            <button
              type="button"
              className="panel-header-toggle"
              aria-label={collapsed ? 'Expand panel' : 'Collapse panel'}
              aria-expanded={!collapsed}
              data-testid="panel-toggle"
              onClick={onToggle}
            >
              <span
                className="panel-collapse-icon"
                data-collapsed={collapsed ? 'true' : 'false'}
                aria-hidden
              >
                {collapsed ? '▸' : '▾'}
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
