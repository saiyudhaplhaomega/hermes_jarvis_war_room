import React from 'react';

interface Props {
  title: string;
  badge?: string;
  right?: React.ReactNode;
}

export function PanelHeader({ title, badge, right }: Props) {
  return (
    <div className="flex justify-between items-center border-b border-jarvis-border pb-2 mb-3">
      <h2 className="text-sm font-bold uppercase tracking-wider text-gray-300">{title}</h2>
      <div className="flex items-center gap-2">
        {badge && <span className="text-[10px] text-gray-500 mono">{badge}</span>}
        {right}
      </div>
    </div>
  );
}
