/**
 * Tests for KpiStrip (D-2026-06-08-dash-3).
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KpiStrip, type KpiItem } from './KpiStrip';

describe('KpiStrip', () => {
  it('renders one card per item', () => {
    const items: KpiItem[] = [
      { label: 'Active agents', value: 5, sublabel: 'of 13' },
      { label: 'Open issues', value: 3, tone: 'warn' },
      { label: 'Memory entries', value: 142 },
      { label: 'Council votes', value: 8, tone: 'good' },
    ];
    render(<KpiStrip items={items} />);
    expect(screen.getByTestId('kpi-strip')).toBeInTheDocument();
    expect(screen.getByTestId('kpi-active-agents')).toBeInTheDocument();
    expect(screen.getByTestId('kpi-open-issues')).toBeInTheDocument();
    expect(screen.getByTestId('kpi-memory-entries')).toBeInTheDocument();
    expect(screen.getByTestId('kpi-council-votes')).toBeInTheDocument();
  });

  it('renders the value, label, and sublabel for each card', () => {
    render(
      <KpiStrip
        items={[{ label: 'Active agents', value: 5, sublabel: 'of 13' }]}
      />
    );
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Active agents')).toBeInTheDocument();
    expect(screen.getByText('of 13')).toBeInTheDocument();
  });

  it('renders zero items without crashing', () => {
    const { container } = render(<KpiStrip items={[]} />);
    expect(screen.getByTestId('kpi-strip')).toBeInTheDocument();
    expect(container.querySelectorAll('[data-testid^="kpi-"]').length).toBe(1); // only the strip itself
  });

  it('applies the right tone color class', () => {
    const { container } = render(
      <KpiStrip
        items={[
          { label: 'Good', value: 1, tone: 'good' },
          { label: 'Warn', value: 2, tone: 'warn' },
          { label: 'Bad', value: 3, tone: 'bad' },
          { label: 'Neutral', value: 4 },
        ]}
      />
    );
    expect(container.querySelector('.text-green-400')).not.toBeNull();
    expect(container.querySelector('.text-yellow-400')).not.toBeNull();
    expect(container.querySelector('.text-red-400')).not.toBeNull();
    // 4 items; only 3 have tone
    expect(container.querySelectorAll('.text-gray-200').length).toBeGreaterThan(0);
  });
});
