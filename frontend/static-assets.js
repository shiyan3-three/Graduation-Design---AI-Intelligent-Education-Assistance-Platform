import path from 'node:path';

const ASSET_CONTENT_TYPES = {
  html: 'text/html; charset=utf-8',
  css: 'text/css; charset=utf-8',
  js: 'text/javascript; charset=utf-8',
};

export function resolveStaticAsset(frontendDir, pathname) {
  const directAsset = DIRECT_ASSETS.get(pathname);
  if (directAsset) {
    return {
      filePath: path.join(frontendDir, directAsset.relativePath),
      contentType: directAsset.contentType,
    };
  }

  if (!pathname.startsWith('/src/')) {
    return null;
  }

  const relativeModulePath = pathname.slice('/src/'.length);
  if (!isSafeRelativeModulePath(relativeModulePath)) {
    return null;
  }

  return {
    filePath: path.join(frontendDir, 'src', relativeModulePath),
    contentType: ASSET_CONTENT_TYPES.js,
  };
}

const DIRECT_ASSETS = new Map([
  ['/', { relativePath: 'chat-sidebar.html', contentType: ASSET_CONTENT_TYPES.html }],
  ['/styles.css', { relativePath: 'chat-sidebar.css', contentType: ASSET_CONTENT_TYPES.css }],
  ['/src/app.js', { relativePath: path.join('src', 'sidebar-app.js'), contentType: ASSET_CONTENT_TYPES.js }],
]);

function isSafeRelativeModulePath(relativeModulePath) {
  return (
    relativeModulePath.length > 0 &&
    !relativeModulePath.includes('..') &&
    /^[A-Za-z0-9._/-]+$/.test(relativeModulePath)
  );
}
