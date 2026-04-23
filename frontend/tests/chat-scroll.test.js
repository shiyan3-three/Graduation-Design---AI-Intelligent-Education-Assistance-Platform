import test from 'node:test';
import assert from 'node:assert/strict';

import { shouldAutoScrollToBottom } from '../src/chat-scroll.js';

test('streaming messages always keep the conversation pinned to the bottom', () => {
  assert.equal(
    shouldAutoScrollToBottom({
      hasStreamingMessage: true,
      distanceFromBottom: 900,
    }),
    true,
  );
});

test('loaded session detail scrolls to the latest message even for long conversations', () => {
  assert.equal(
    shouldAutoScrollToBottom({
      justFinishedDetail: true,
      distanceFromBottom: 2400,
    }),
    true,
  );
});

test('idle conversations do not steal scroll when user is reading older messages', () => {
  assert.equal(
    shouldAutoScrollToBottom({
      distanceFromBottom: 900,
    }),
    false,
  );
});
