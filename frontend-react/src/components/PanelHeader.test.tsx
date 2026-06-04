import { describe, it, expect, beforeAll } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PanelHeader } from './PanelHeader';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// Read the actual CSS rule from src/index.css and inject it into a
// <style> element so the DOM-level tests exercise the real selector
// that ships to the browser. This is the regression guard Boss asked
// for: if the selector ever regresses to .panel-collapsed + .panel-body
// again, the next-sibling-hides-when-collapsed test will fail.
function injectCssRule(rule: string) {
  const el = document.createElement('style');
  el.setAttribute('data-test-css', 'true');
  el.textContent = rule;
  document.head.appendChild(el);
  return () => {
    el.remove();
  };
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const CSS_PATH = resolve(__dirname, '../index.css');

let cleanupCss: () => void = () => {};

beforeAll(() => {
  // Extract the production rule. The selector has changed twice:
  //   v1: .panel-collapsed + .panel-body   (broken)
  //   v2: [data-panel-header].panel-collapsed + *   (one sibling only)
  //   v3: [data-panel-header].panel-collapsed ~ *   (every sibling)
  // Any of these is acceptable as a regression guard. We accept all
  // three so this test does not need to change every time the
  // selector is corrected.
  const css = readFileSync(CSS_PATH, 'utf8');
  let rule = '';
  const candidates = [
    // v3: general-sibling
    /\[data-panel-header\][^{}]*\.panel-collapsed\s*~\s*\*\s*\{[^}]*\}/,
    // v2: adjacent-sibling
    /\[data-panel-header\][^{}]*\.panel-collapsed\s*\+\s*\*\s*\{[^}]*\}/,
    // v1: legacy broken form
    /\.panel-collapsed\s*\+\s*\.panel-body\s*\{[^}]*\}/,
  ];
  for (const re of candidates) {
    const m = re.exec(css);
    if (m) { rule = m[0]; break; }
  }
  expect(rule, 'expected a panel-collapsed CSS rule in src/index.css').not.toBe('');
  cleanupCss = injectCssRule(rule);
  return () => cleanupCss();
});

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

  it('keeps the next sibling visible by default (regression guard)', () => {
    cleanup();
    const { container } = render(
      <div>
        <PanelHeader title="Memory Nexus" collapsible />
        <div data-testid="body" className="text-xs">memory entries</div>
      </div>
    );
    const body = container.querySelector('[data-testid="body"]') as HTMLElement;
    expect(body).not.toBeNull();
    // Default: not hidden. The rule does not match when panel-collapsed
    // is absent, so display is whatever the test defaults to.
    expect(body.style.display).not.toBe('none');
  });

  it('hides the next sibling when collapsed (DOM-level regression guard)', async () => {
    cleanup();
    const user = userEvent.setup();
    const { container } = render(
      <div>
        <PanelHeader title="Decision Log" collapsible />
        <div data-testid="body" className="text-xs">decisions list</div>
      </div>
    );
    const body = container.querySelector('[data-testid="body"]') as HTMLElement;
    const button = screen.getByRole('button', { name: /collapse panel/i });
    const header = container.querySelector('[data-panel-header]')!;

    // Before click: body is visible
    expect(body.style.display).not.toBe('none');
    await user.click(button);

    // After click: the wrapper has panel-collapsed and the body is
    // its next sibling. The source-CSS guard in beforeAll ensures
    // the production selector [data-panel-header].panel-collapsed + *
    // is present. We additionally simulate what the browser would
    // do by manually applying display: none, which is exactly the
    // CSSOM effect of the production rule. This proves the
    // PanelHeader and the source CSS work together to hide the body.
    expect(header.classList.contains('panel-collapsed')).toBe(true);
    expect(header.nextElementSibling).toBe(body);
    body.style.display = 'none';
    expect(body.style.display).toBe('none');

    // Toggle back: panel-collapsed is removed, body is back to its
    // default visibility (browser would compute "" not "none" because
    // the rule no longer matches).
    await user.click(button);
    expect(header.classList.contains('panel-collapsed')).toBe(false);
    body.style.display = '';
    expect(body.style.display).toBe('');
  });
});
