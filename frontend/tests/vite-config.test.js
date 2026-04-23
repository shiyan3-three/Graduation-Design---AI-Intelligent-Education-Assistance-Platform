import test from 'node:test';
import assert from 'node:assert/strict';

import viteConfig from '../vite.config.js';

test('vite config exposes the frontend proxy and default port', () => {
  const config =
    typeof viteConfig === 'function' ? viteConfig({ command: 'serve', mode: 'test' }) : viteConfig;

  assert.equal(config.server?.port, 5173);
  assert.deepEqual(config.server?.proxy?.['/api'], {
    target: 'http://localhost:8000',
    changeOrigin: true,
  });
});
