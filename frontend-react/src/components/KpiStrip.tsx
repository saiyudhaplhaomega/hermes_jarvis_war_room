/**
 * KpiStrip — a one-row strip of key performance indicators.
 *
 * D-2026-06-08-dash-3: replaces the 4 separate header blocks in
 * ArmyOperations / MissionControl / KanbanFleet with a single row of
 * compact metric cards. Saves ~120px of vertical space per page.
 *
 * Each KPI is just a number + a label. Optional color via `tone`.
 */
export type KpiTone = 'neutral' | 'good' | 'warn' | 'bad';

export interface KpiItem {
  /** Short label, 1-2 words (e.g. "Active agents"). */
  label: string;
  /** Main value, displayed big. Can be a number or short string. */
  value: string | number;
  /** Optional sublabel, e.g. "of 13 total". */
  sublabel?: string;
  /** Color tone. */
  tone?: KpiTone;
  /** Optional testid. */
  testid?: string;
}

interface Props {
  items: KpiItem[];
}

const TONE_CLASS: Record<KpiTone, string> = {
  neutral: 'text-gray-200',
  good: 'text-green-400',
  warn: 'text-yellow-400',
  bad: 'text-red-400',
};

export function KpiStrip({ items }: Props) {
  return (
    <div
      data-testid="kpi-strip"
      className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2"
    >
      {items.map((it, i) => (
        <div
          key={i}
          data-testid={it.testid ?? `kpi-${it.label.toLowerCase().replace(/\s+/g, '-')}`}
          className="border border-jarvis-border rounded p-2 bg-jarvis-bg-soft"
        >
          <div className="text-[10px] uppercase tracking-wider text-gray-500 mono">
            {it.label}
          </div>
          <div className={`text-lg font-bold mono ${TONE_CLASS[it.tone ?? 'neutral']}`}>
            {it.value}
          </div>
          {it.sublabel && (
            <div className="text-[10px] text-gray-500 mono">{it.sublabel}</div>
          )}
        </div>
      ))}
    </div>
  );
}
