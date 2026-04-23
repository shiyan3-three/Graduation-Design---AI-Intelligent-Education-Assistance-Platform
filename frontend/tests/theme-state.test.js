import test from 'node:test';
import assert from 'node:assert/strict';

import {
  getNextTheme,
  normalizeTheme,
  resolveInitialTheme,
} from '../src/theme-state.js';

test('normalizeTheme keeps known themes and falls back to light', () => {
  assert.equal(normalizeTheme('light'), 'light');
  assert.equal(normalizeTheme('dark'), 'dark');
  assert.equal(normalizeTheme('unknown'), 'light');
  assert.equal(normalizeTheme(null), 'light');
});

test('getNextTheme toggles between light and dark', () => {
  assert.equal(getNextTheme('light'), 'dark');
  assert.equal(getNextTheme('dark'), 'light');
});

test('resolveInitialTheme reads persisted value before falling back to light', () => {
  assert.equal(resolveInitialTheme(() => 'dark'), 'dark');
  assert.equal(resolveInitialTheme(() => 'light'), 'light');
  assert.equal(resolveInitialTheme(() => 'invalid'), 'light');
  assert.equal(resolveInitialTheme(() => {
    throw new Error('storage unavailable');
  }), 'light');
});
