import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const store = new Map();
global.localStorage = {
  getItem: (key) => store.get(key) ?? null,
  setItem: (key, value) => store.set(key, String(value)),
  removeItem: (key) => store.delete(key),
  clear: () => store.clear(),
};

const { isStoredAdmin, readStoredUser } = await import('../src/admin-access.js');

test('isStoredAdmin only allows users with is_admin true', () => {
  store.clear();
  localStorage.setItem('edu_user', JSON.stringify({ username: 'admin', is_admin: true }));
  assert.equal(isStoredAdmin(), true);

  localStorage.setItem('edu_user', JSON.stringify({ username: 'student', is_admin: false }));
  assert.equal(isStoredAdmin(), false);

  localStorage.setItem('edu_user', JSON.stringify({ username: 'student' }));
  assert.equal(isStoredAdmin(), false);
});

test('readStoredUser tolerates missing and invalid localStorage JSON', () => {
  store.clear();
  assert.deepEqual(readStoredUser(), {});

  localStorage.setItem('edu_user', '{broken');
  assert.deepEqual(readStoredUser(), {});
});

test('admin route, header entry, and page files are wired', () => {
  const appPath = fileURLToPath(new URL('../src/App.jsx', import.meta.url));
  const headerPath = fileURLToPath(
    new URL('../src/components/GlobalHeader/GlobalHeader.jsx', import.meta.url)
  );
  const pagePath = fileURLToPath(
    new URL('../src/pages/AdminPage/index.jsx', import.meta.url)
  );
  const cssPath = fileURLToPath(
    new URL('../src/pages/AdminPage/AdminPage.module.css', import.meta.url)
  );

  const appSource = readFileSync(appPath, 'utf8');
  const headerSource = readFileSync(headerPath, 'utf8');

  assert.match(appSource, /path="\/admin"/);
  assert.match(appSource, /AdminPage/);
  assert.match(headerSource, /isStoredAdmin/);
  assert.match(headerSource, /handleAction\('admin'\)/);
  assert.equal(existsSync(pagePath), true);
  assert.equal(existsSync(cssPath), true);
});

test('admin requests convert network rejection into a user-facing message', async () => {
  const { runAdminRequest } = await import('../src/pages/AdminPage/admin-request.js');

  const result = await runAdminRequest(
    () => Promise.reject(new TypeError('Failed to fetch')),
    '系统统计加载失败'
  );

  assert.deepEqual(result, {
    ok: false,
    message: '网络异常，请检查后端服务是否已启动',
  });
});
