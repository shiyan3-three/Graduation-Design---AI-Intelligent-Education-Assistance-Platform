/**
 * frontend/tests/request-json-401.test.js
 *
 * Regression tests for the 401 handling behaviour of requestJson():
 *
 *  1. Public endpoints (/api/login, /api/register) — a 401 response MUST NOT
 *     clear the auth session or redirect, so that the AuthPage can display the
 *     backend error message (e.g. "密码错误") to the user.
 *
 *  2. Protected endpoints (/api/sessions, /api/chat, …) — a 401 MUST clear
 *     the stored session so the user is treated as logged out.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

// ── localStorage shim ─────────────────────────────────────────────────────────
const _store = new Map();
const localStorage = {
  getItem:    (k) => _store.get(k) ?? null,
  setItem:    (k, v) => _store.set(k, String(v)),
  removeItem: (k) => _store.delete(k),
  clear:      () => _store.clear(),
};
global.localStorage = localStorage;

// Suppress window.location.href side-effects in the Node test environment.
global.window = { location: { href: '' } };

// ── fetch mock helper ─────────────────────────────────────────────────────────
function mockFetch(status, body) {
  global.fetch = async () => ({
    status,
    json: async () => body,
  });
}

// Lazy import: must come AFTER the globals above so the module sees them.
const {
  requestJson,
  saveAuthSession,
  getAuthToken,
} = await import('../src/services/api.js');

// Reference payload returned by backend when password is wrong.
const _wrongPasswordPayload = {
  success: false,
  message: '用户名或密码错误',
  error_code: 'INVALID_CREDENTIALS',
};

// ── Test 1: /api/login 401 must NOT clear session ─────────────────────────────
test('/api/login 返回 401 时不清 session、不跳转，并返回错误 payload', async () => {
  _store.clear();
  saveAuthSession('existing-valid-token', { username: 'alice' });

  mockFetch(401, _wrongPasswordPayload);

  const { response, payload } = await requestJson('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'alice', password: 'wrong-password' }),
  });

  // 1. Token must still be in localStorage (no clearAuthSession was called).
  assert.equal(
    getAuthToken(),
    'existing-valid-token',
    '登录失败不应清除已有 session',
  );

  // 2. The error payload must still be returned to the caller.
  assert.equal(response.status, 401);
  assert.equal(payload.error_code, 'INVALID_CREDENTIALS');
  assert.equal(payload.success, false);
});

// ── Test 2: /api/register 401 must NOT clear session either ──────────────────
test('/api/register 返回 401 时不清 session', async () => {
  _store.clear();
  saveAuthSession('existing-valid-token', { username: 'alice' });

  mockFetch(401, _wrongPasswordPayload);

  await requestJson('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'alice', password: 'x', grade: '高一', subject: '数学' }),
  });

  assert.equal(
    getAuthToken(),
    'existing-valid-token',
    '注册 401 不应清除已有 session',
  );
});

// ── Test 3: protected endpoint 401 MUST clear session ────────────────────────
test('受保护接口（/api/sessions）返回 401 时会清 session', async () => {
  _store.clear();
  saveAuthSession('expired-token', { username: 'alice' });

  mockFetch(401, {
    success: false,
    message: '未登录或登录已失效',
    error_code: 'UNAUTHORIZED',
  });

  await requestJson('/api/sessions', {});

  assert.equal(
    getAuthToken(),
    null,
    '受保护接口 401 应清除 session（token 应为 null）',
  );
});

// ── Test 4: /api/auth/me 401 clears session (same logic as other protected endpoints) ─
test('/api/auth/me 返回 401 时会清 session（无效 token 踢出）', async () => {
  _store.clear();
  saveAuthSession('forged-token', { username: 'hacker' });

  mockFetch(401, {
    success: false,
    message: '未登录或登录已失效',
    error_code: 'UNAUTHORIZED',
  });

  await requestJson('/api/auth/me', {});

  assert.equal(
    getAuthToken(),
    null,
    '无效 token 访问 /api/auth/me 应清除 session',
  );
});

// ── Test 5: fetch network error propagates so AuthPage try/catch can handle it ─
test('fetch 抛出网络错误时 requestJson 也抛出，让 AuthPage 可以 catch', async () => {
  global.fetch = async () => {
    throw new TypeError('Failed to fetch');
  };

  await assert.rejects(
    () => requestJson('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'alice', password: 'pw' }),
    }),
    TypeError,
    'requestJson must propagate fetch network errors so callers can catch them',
  );
});

