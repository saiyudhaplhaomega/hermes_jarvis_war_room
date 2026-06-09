/**
 * Tests for usePanelState — persistent panel collapse state.
 * D-2026-06-08-dash-1
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePanelState } from './usePanelState';

beforeEach(() => {
  // Wipe any persisted state from prior tests
  for (let i = window.localStorage.length - 1; i >= 0; i--) {
    const key = window.localStorage.key(i);
    if (key && key.startsWith('jarvis.dashboard.panel.')) {
      window.localStorage.removeItem(key);
    }
  }
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('usePanelState', () => {
  it('starts expanded by default (no localStorage entry)', () => {
    const { result } = renderHook(() => usePanelState('topology'));
    expect(result.current.collapsed).toBe(false);
    expect(result.current.persisted).toBe(true); // we have localStorage in jsdom
  });

  it('honors defaultCollapsed=true when no stored value', () => {
    const { result } = renderHook(() => usePanelState('army', true));
    expect(result.current.collapsed).toBe(true);
  });

  it('reads from localStorage on first render', () => {
    window.localStorage.setItem('jarvis.dashboard.panel.topology.collapsed', '1');
    const { result } = renderHook(() => usePanelState('topology'));
    expect(result.current.collapsed).toBe(true);
  });

  it('toggle() flips the state and writes to localStorage', () => {
    const { result } = renderHook(() => usePanelState('topology'));
    expect(result.current.collapsed).toBe(false);
    act(() => result.current.toggle());
    expect(result.current.collapsed).toBe(true);
    expect(window.localStorage.getItem('jarvis.dashboard.panel.topology.collapsed')).toBe('1');
    act(() => result.current.toggle());
    expect(result.current.collapsed).toBe(false);
    expect(window.localStorage.getItem('jarvis.dashboard.panel.topology.collapsed')).toBe('0');
  });

  it('setCollapsed() is explicit and still persists', () => {
    const { result } = renderHook(() => usePanelState('kanban'));
    act(() => result.current.setCollapsed(true));
    expect(result.current.collapsed).toBe(true);
    expect(window.localStorage.getItem('jarvis.dashboard.panel.kanban.collapsed')).toBe('1');
  });

  it('two different panel ids have independent state', () => {
    const a = renderHook(() => usePanelState('topology'));
    const b = renderHook(() => usePanelState('kanban'));
    act(() => a.result.current.setCollapsed(true));
    expect(a.result.current.collapsed).toBe(true);
    expect(b.result.current.collapsed).toBe(false);
  });

  it('survives a "reload" (re-render with stored value)', () => {
    const first = renderHook(() => usePanelState('army'));
    act(() => first.result.current.setCollapsed(true));
    first.unmount();
    // Simulate a fresh page load
    const second = renderHook(() => usePanelState('army'));
    expect(second.result.current.collapsed).toBe(true);
  });

  it('returns a stable toggle callback across renders', () => {
    const { result, rerender } = renderHook(() => usePanelState('army'));
    const first = result.current.toggle;
    rerender();
    expect(result.current.toggle).toBe(first);
  });
});
