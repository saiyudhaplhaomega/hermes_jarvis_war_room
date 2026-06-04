import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PanelHeader } from './PanelHeader';

describe('PanelHeader', () => {
  it('renders the title and badge', () => {
    render(<PanelHeader title="Mission Control" badge="live" />);
    expect(screen.getByText('Mission Control')).toBeInTheDocument();
    expect(screen.getByText('live')).toBeInTheDocument();
  });

  it('is not collapsible by default', () => {
    const { container } = render(<PanelHeader title="X" />);
    expect(container.querySelector('.panel-collapsed')).toBeNull();
    expect(screen.queryByRole('button', { name: /collapse/i })).toBeNull();
  });

  it('renders a collapse toggle when collapsible is true', () => {
    render(<PanelHeader title="Agent Growth Studio" collapsible />);
    expect(screen.getByRole('button', { name: /collapse panel/i })).toBeInTheDocument();
  });

  it('starts expanded by default (no panel-collapsed class)', () => {
    const { container } = render(<PanelHeader title="Kanban Fleet" collapsible />);
    const section = container.querySelector('[data-panel-header]');
    expect(section).not.toBeNull();
    expect(section!.classList.contains('panel-collapsed')).toBe(false);
  });

  it('toggles collapsed state on click', async () => {
    const user = userEvent.setup();
    const { container } = render(<PanelHeader title="Memory Nexus" collapsible />);
    const section = container.querySelector('[data-panel-header]')!;
    const button = screen.getByRole('button', { name: /collapse panel/i });
    expect(button.getAttribute('aria-expanded')).toBe('true');
    await user.click(button);
    expect(section.classList.contains('panel-collapsed')).toBe(true);
    expect(button.getAttribute('aria-expanded')).toBe('false');
    await user.click(button);
    expect(section.classList.contains('panel-collapsed')).toBe(false);
    expect(button.getAttribute('aria-expanded')).toBe('true');
  });
});
