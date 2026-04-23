import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { resolveStaticAsset } from '../static-assets.js';

const frontendDir = path.dirname(fileURLToPath(new URL('../static-assets.js', import.meta.url)));

test('resolveStaticAsset keeps the app entry alias for the sidebar page', () => {
  const asset = resolveStaticAsset(frontendDir, '/src/app.js');

  assert.deepEqual(asset, {
    filePath: path.join(frontendDir, 'src', 'sidebar-app.js'),
    contentType: 'text/javascript; charset=utf-8',
  });
});

test('resolveStaticAsset serves newly added src modules without explicit route entries', () => {
  const asset = resolveStaticAsset(frontendDir, '/src/message-element.js');

  assert.deepEqual(asset, {
    filePath: path.join(frontendDir, 'src', 'message-element.js'),
    contentType: 'text/javascript; charset=utf-8',
  });
});
