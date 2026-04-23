import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolveStaticAsset } from './static-assets.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 5173);
const host = process.env.HOST || '127.0.0.1';
const backendOrigin = process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000';

const server = createServer(async (request, response) => {
  const requestUrl = new URL(request.url || '/', `http://${request.headers.host || `${host}:${port}`}`);
  const isSessionDetailRequest = /^\/api\/sessions\/\d+$/.test(requestUrl.pathname);

  if (requestUrl.pathname === '/api/chat') {
    await handleBackendProxy(request, response, '/api/chat', ['POST']);
    return;
  }

  if (requestUrl.pathname === '/api/sessions') {
    await handleBackendProxy(request, response, '/api/sessions', ['GET']);
    return;
  }

  if (isSessionDetailRequest) {
    await handleBackendProxy(request, response, requestUrl.pathname, ['GET']);
    return;
  }

  if (requestUrl.pathname === '/favicon.ico') {
    response.writeHead(204);
    response.end();
    return;
  }

  const asset = resolveStaticAsset(__dirname, requestUrl.pathname);
  if (!asset) {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not Found');
    return;
  }

  try {
    const fileContent = await readFile(asset.filePath);
    response.writeHead(200, { 'Content-Type': asset.contentType });
    response.end(fileContent);
  } catch (error) {
    response.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end(`Failed to load asset: ${error.message}`);
  }
});

server.listen(port, host, () => {
  console.log(`Frontend server running at http://${host}:${port}`);
});

async function handleBackendProxy(request, response, backendPath, allowedMethods) {
  const method = request.method || 'GET';

  if (!allowedMethods.includes(method)) {
    response.writeHead(405, { 'Content-Type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ message: 'Method Not Allowed' }));
    return;
  }

  try {
    const requestOptions = { method };
    if (!['GET', 'HEAD'].includes(method)) {
      requestOptions.headers = {
        'Content-Type': request.headers['content-type'] || 'application/json',
      };
      requestOptions.body = await readRequestBody(request);
    }

    const backendResponse = await fetch(`${backendOrigin}${backendPath}`, requestOptions);

    const payload = await backendResponse.text();
    response.writeHead(backendResponse.status, {
      'Content-Type':
        backendResponse.headers.get('content-type') || 'application/json; charset=utf-8',
    });
    response.end(payload);
  } catch (_) {
    response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    response.end(
      JSON.stringify({
        message: '无法连接后端服务，请确认后端已启动。',
        error_code: 'BACKEND_UNAVAILABLE',
      })
    );
  }
}

async function readRequestBody(request) {
  const chunks = [];

  for await (const chunk of request) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }

  return Buffer.concat(chunks).toString('utf-8');
}
