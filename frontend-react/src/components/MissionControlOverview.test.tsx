import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MissionControlOverview } from './MissionControlOverview';
import { TestProviders, makeProject } from '../test/testUtils';
import type { DashboardCache } from '../types/dashboard';

function makeCache(agents: Array<{ name: string; status: string }>): DashboardCache {
  return {
    generated_at: '2026-06-04T00:00:00Z',
    agents: agents as any,
    decisions: [],
    memory: {},
    kanban_by_project: {},
  } as any;
}

describe('MissionControlOverview radar', () => {
  it('renders a sweep element', () => {
    render(
      <TestProviders cache={makeCache([{ name: 'boss', status: 'online' }])} project={makeProject()}>
        <MissionControlOverview />
      </TestProviders>
    );
    expect(screen.getByTestId('radar-sweep')).toBeInTheDocument();
  });

  it('caps visible dots at 10', () => {
    const agents = Array.from({ length: 25 }, (_, i) => ({ name: `a${i}`, status: 'online' }));
    const { container } = render(
      <TestProviders cache={makeCache(agents as any)} project={makeProject()}>
        <MissionControlOverview />
      </TestProviders>
    );
    const dots = container.querySelectorAll('[data-testid="radar-dot"]');
    expect(dots.length).toBe(10);
  });

  it('maps online/active/running to --online class', () => {
    const { container } = render(
      <TestProviders
        cache={makeCache([
          { name: 'a', status: 'online' },
          { name: 'b', status: 'active' },
          { name: 'c', status: 'running' },
        ])}
        project={makeProject()}
      >
        <MissionControlOverview />
      </TestProviders>
    );
    const dots = container.querySelectorAll('[data-testid="radar-dot"]');
    for (const dot of dots) {
      expect(dot.className).toMatch(/radar-dot--online/);
    }
  });

  it('maps idle/ready to --idle class', () => {
    const { container } = render(
      <TestProviders
        cache={makeCache([
          { name: 'a', status: 'idle' },
          { name: 'b', status: 'ready' },
        ])}
        project={makeProject()}
      >
        <MissionControlOverview />
      </TestProviders>
    );
    const dots = container.querySelectorAll('[data-testid="radar-dot"]');
    for (const dot of dots) {
      expect(dot.className).toMatch(/radar-dot--idle/);
    }
  });

  it('maps error/offline to --error class', () => {
    const { container } = render(
      <TestProviders
        cache={makeCache([
          { name: 'a', status: 'error' },
          { name: 'b', status: 'offline' },
        ])}
        project={makeProject()}
      >
        <MissionControlOverview />
      </TestProviders>
    );
    const dots = container.querySelectorAll('[data-testid="radar-dot"]');
    for (const dot of dots) {
      expect(dot.className).toMatch(/radar-dot--error/);
    }
  });

  it('maps unknown/empty status to --unknown class', () => {
    const { container } = render(
      <TestProviders
        cache={makeCache([
          { name: 'a', status: 'mystery' },
          { name: 'b', status: '' },
          { name: 'c' } as any,
        ])}
        project={makeProject()}
      >
        <MissionControlOverview />
      </TestProviders>
    );
    const dots = container.querySelectorAll('[data-testid="radar-dot"]');
    for (const dot of dots) {
      expect(dot.className).toMatch(/radar-dot--unknown/);
    }
  });

  it('mixes status buckets correctly', () => {
    const { container } = render(
      <TestProviders
        cache={makeCache([
          { name: 'a', status: 'online' },
          { name: 'b', status: 'idle' },
          { name: 'c', status: 'error' },
          { name: 'd', status: 'weird' },
        ])}
        project={makeProject()}
      >
        <MissionControlOverview />
      </TestProviders>
    );
    const dots = container.querySelectorAll('[data-testid="radar-dot"]');
    const classes = Array.from(dots).map(d => d.className);
    expect(classes.some(c => /radar-dot--online/.test(c))).toBe(true);
    expect(classes.some(c => /radar-dot--idle/.test(c))).toBe(true);
    expect(classes.some(c => /radar-dot--error/.test(c))).toBe(true);
    expect(classes.some(c => /radar-dot--unknown/.test(c))).toBe(true);
  });

  it('maps configured/pending/paused/standby/disabled to --configured class', () => {
    const { container } = render(
      <TestProviders
        cache={makeCache([
          { name: 'a', status: 'configured' },
          { name: 'b', status: 'pending' },
          { name: 'c', status: 'paused' },
          { name: 'd', status: 'standby' },
          { name: 'e', status: 'disabled' },
        ])}
        project={makeProject()}
      >
        <MissionControlOverview />
      </TestProviders>
    );
    const dots = container.querySelectorAll('[data-testid="radar-dot"]');
    expect(dots.length).toBe(5);
    for (const dot of dots) {
      expect(dot.className).toMatch(/radar-dot--configured/);
    }
  });

  it('renders a 5-entry legend with the right labels', () => {
    render(
      <TestProviders cache={makeCache([{ name: 'a', status: 'online' }])} project={makeProject()}>
        <MissionControlOverview />
      </TestProviders>
    );
    const legend = screen.getByTestId('radar-legend');
    expect(legend.querySelectorAll('.radar-legend-swatch').length).toBe(5);
    expect(legend.textContent || '').toMatch(/online/);
    expect(legend.textContent || '').toMatch(/idle/);
    expect(legend.textContent || '').toMatch(/error/);
    expect(legend.textContent || '').toMatch(/staged/);
    expect(legend.textContent || '').toMatch(/unknown/);
  });

  it('keeps typos as unknown even with the new configured bucket', () => {
    const { container } = render(
      <TestProviders
        cache={makeCache([{ name: 'a', status: 'a-typo' }])}
        project={makeProject()}
      >
        <MissionControlOverview />
      </TestProviders>
    );
    const dot = container.querySelector('[data-testid="radar-dot"]');
    expect(dot?.className).toMatch(/radar-dot--unknown/);
    expect(dot?.className).not.toMatch(/radar-dot--configured/);
  });
});
