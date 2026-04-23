import test from 'node:test';
import assert from 'node:assert/strict';
import { ReadableStream } from 'node:stream/web';
import { TextEncoder } from 'node:util';

const _store = new Map();
global.localStorage = {
  getItem: (key) => _store.get(key) ?? null,
  setItem: (key, value) => _store.set(key, String(value)),
  removeItem: (key) => _store.delete(key),
  clear: () => _store.clear(),
};
global.window = { location: { href: '' } };

const { saveAuthSession, streamChatRequest } = await import('../src/services/api.js');

function makeStream(chunks) {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

test('streamChatRequest types large SSE delta chunks into smaller UI updates', async () => {
  _store.clear();
  saveAuthSession('token-1', { username: 'demo' });
  const seenChunks = [];
  let doneEvent = null;

  global.fetch = async (url, init) => {
    assert.equal(url, '/api/chat/stream');
    assert.equal(init.headers.Authorization, 'Bearer token-1');
    return {
      status: 200,
      ok: true,
      body: makeStream([
        'data: {"type":"delta","content":"abcdef"}\n\n',
        'data: {"type":"done","session_id":7,"message_id":8,"tools_used":[]}\n\n',
      ]),
    };
  };

  await streamChatRequest(
    { content: 'hello', session_id: null },
    (chunk) => seenChunks.push(chunk),
    (event) => {
      doneEvent = event;
    },
    (message) => {
      throw new Error(message);
    },
    { typewriterChunkSize: 2, typewriterDelayMs: 0 },
  );

  assert.deepEqual(seenChunks, ['ab', 'cd', 'ef']);
  assert.equal(doneEvent.session_id, 7);
  assert.equal(doneEvent.message_id, 8);
});
