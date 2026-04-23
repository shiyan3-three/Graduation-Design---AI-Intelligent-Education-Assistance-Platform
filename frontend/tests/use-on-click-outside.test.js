/**
 * Tests for useOnClickOutside logic (pure handler coverage — no JSDOM needed).
 *
 * We test the decision function extracted from the hook:
 *   "if the ref contains the event target → ignore; otherwise → call handler"
 */
import test from 'node:test';
import assert from 'node:assert/strict';

// Simulate the core conditional inside useOnClickOutside
function shouldDismiss(ref, eventTarget) {
  if (!ref.current) return false;
  if (ref.current.contains(eventTarget)) return false;
  return true;
}

test('shouldDismiss returns false when ref is not yet attached', () => {
  const ref = { current: null };
  const target = {};
  assert.equal(shouldDismiss(ref, target), false);
});

test('shouldDismiss returns false when click is inside the ref element', () => {
  const inner = {};
  const container = {
    contains: (t) => t === inner,
  };
  const ref = { current: container };
  assert.equal(shouldDismiss(ref, inner), false);
});

test('shouldDismiss returns true when click is outside the ref element', () => {
  const outsideEl = {};
  const container = {
    contains: () => false,
  };
  const ref = { current: container };
  assert.equal(shouldDismiss(ref, outsideEl), true);
});

// ── Global theme toggle (pure state logic) ────────────────────────────────────
import { getNextTheme } from '../src/theme-state.js';

test('theme toggles dark → light when stored theme changes', () => {
  // AppLayout calls getNextTheme; verify the contract once more for new context
  assert.equal(getNextTheme('dark'), 'light');
  assert.equal(getNextTheme('light'), 'dark');
});
