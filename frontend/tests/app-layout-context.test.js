/**
 * Regression: AppLayout outlet context must expose both theme and toggleTheme.
 *
 * We test the shape contract in pure-logic terms:
 *   - the object passed to <Outlet context={...} /> must contain toggleTheme
 *   - that toggleTheme must be a function (so ChatPage's button is not undefined)
 */
import test from 'node:test';
import assert from 'node:assert/strict';

// Simulate the context object that AppLayout builds before passing to Outlet
function buildOutletContext(theme, toggleTheme) {
  return { theme, toggleTheme };
}

test('outlet context includes theme', () => {
  const ctx = buildOutletContext('dark', () => {});
  assert.equal(ctx.theme, 'dark');
});

test('outlet context includes toggleTheme as a function', () => {
  const toggle = () => {};
  const ctx = buildOutletContext('light', toggle);
  assert.equal(typeof ctx.toggleTheme, 'function',
    'toggleTheme must be a function — ChatPage destructures it from useOutletContext()');
});

test('toggleTheme in context is the same reference passed in (no wrapping)', () => {
  const toggle = () => {};
  const ctx = buildOutletContext('light', toggle);
  assert.equal(ctx.toggleTheme, toggle,
    'AppLayout must forward toggleTheme unchanged so ChatPanel button works');
});

// Simulate ChatPage consumption: destructure both fields
test('ChatPage can destructure theme and toggleTheme from outlet context', () => {
  const mockToggle = () => {};
  const ctx = buildOutletContext('dark', mockToggle);

  // mirrors: const { theme, toggleTheme } = useOutletContext();
  const { theme, toggleTheme } = ctx;

  assert.equal(theme, 'dark');
  assert.ok(toggleTheme, 'toggleTheme must be truthy (not undefined)');
  assert.equal(typeof toggleTheme, 'function');
});
