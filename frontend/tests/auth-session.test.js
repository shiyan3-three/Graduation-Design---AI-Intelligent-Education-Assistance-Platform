/**
 * Tests for auth session helpers (api.js) and ProtectedRoute guard logic.
 * These are pure-logic / localStorage tests — no DOM or React required.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

// ── Minimal localStorage shim ────────────────────────────────────────────────
const store = new Map();
const localStorage = {
  getItem: (k) => store.get(k) ?? null,
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
};
global.localStorage = localStorage;
// ─────────────────────────────────────────────────────────────────────────────

// Dynamic import after shim is in place
const { getAuthToken, saveAuthSession, clearAuthSession, clearAuthToken } =
  await import('../src/services/api.js');

// ── saveAuthSession ──────────────────────────────────────────────────────────
test('saveAuthSession writes token to localStorage', () => {
  store.clear();
  saveAuthSession('tok-123', { username: 'alice', grade: '高二', subject: '数学' });
  assert.equal(localStorage.getItem('token'), 'tok-123');
});

test('saveAuthSession writes edu_user JSON to localStorage', () => {
  store.clear();
  saveAuthSession('tok-abc', { username: 'bob', grade: '高一', subject: '物理' });
  const stored = JSON.parse(localStorage.getItem('edu_user'));
  assert.equal(stored.username, 'bob');
  assert.equal(stored.grade, '高一');
  assert.equal(stored.subject, '物理');
});

// ── clearAuthSession ─────────────────────────────────────────────────────────
test('clearAuthSession removes both token and edu_user', () => {
  store.clear();
  saveAuthSession('tok-xyz', { username: 'carol' });
  clearAuthSession();
  assert.equal(localStorage.getItem('token'), null);
  assert.equal(localStorage.getItem('edu_user'), null);
});

// ── clearAuthToken (legacy) still removes token ──────────────────────────────
test('clearAuthToken removes token and edu_user (via updated impl)', () => {
  store.clear();
  saveAuthSession('tok-legacy', { username: 'dave' });
  clearAuthToken();
  assert.equal(localStorage.getItem('token'), null);
  assert.equal(localStorage.getItem('edu_user'), null);
});

// ── getAuthToken ─────────────────────────────────────────────────────────────
test('getAuthToken returns null when no token stored', () => {
  store.clear();
  assert.equal(getAuthToken(), null);
});

test('getAuthToken returns token after saveAuthSession', () => {
  store.clear();
  saveAuthSession('tok-get', { username: 'eve' });
  assert.equal(getAuthToken(), 'tok-get');
});

// ── ProtectedRoute guard logic (pure) ────────────────────────────────────────
// We test the underlying decision: "if no token → redirect, else render"
test('ProtectedRoute allows access when token exists', () => {
  store.clear();
  saveAuthSession('valid-token', { username: 'fred' });
  // Simulate the guard condition from ProtectedRoute.jsx
  const token = getAuthToken();
  assert.ok(token, 'should have a token → allow access');
});

test('ProtectedRoute blocks access when token is absent', () => {
  store.clear();
  const token = getAuthToken();
  assert.equal(token, null, 'no token → should redirect to /login');
});
