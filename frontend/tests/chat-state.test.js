import test from 'node:test';
import assert from 'node:assert/strict';

import {
  appendStreamingDelta,
  createInitialState,
  failSubmission,
  failStreamingAssistant,
  finishSubmission,
  startNewConversation,
  startStreamingAssistant,
  startSubmission,
} from '../src/chat-state.js';
import { getViewModel } from '../src/chat-view.js';

test('startSubmission trims content and builds the api payload', () => {
  const state = createInitialState();

  const result = startSubmission(state, '  你好，帮我复习函数极限  ', () => 'local-1');

  assert.deepEqual(result.requestBody, {
    content: '你好，帮我复习函数极限',
    session_id: null,
  });
  assert.equal(result.nextState.isSending, true);
  assert.equal(result.nextState.error, '');
  assert.deepEqual(result.nextState.messages, [
    {
      id: 'local-1',
      role: 'user',
      content: '你好，帮我复习函数极限',
      pending: true,
      failed: false,
      toolsUsed: null,
    },
  ]);
});

test('startSubmission reuses the current session id for follow-up messages', () => {
  const state = {
    ...createInitialState(),
    currentSessionId: 9,
    messages: [{ id: '1', role: 'assistant', content: '上一条回复', pending: false, failed: false }],
  };

  const result = startSubmission(state, '继续讲一下', () => 'local-2');

  assert.equal(result.requestBody.session_id, 9);
  assert.equal(result.nextState.messages.at(-1)?.content, '继续讲一下');
});

test('finishSubmission stores the returned session id and appends the assistant reply', () => {
  const state = {
    ...createInitialState(),
    isSending: true,
    messages: [{ id: 'local-3', role: 'user', content: '什么是导数', pending: true, failed: false }],
  };

  const nextState = finishSubmission(state, {
    session: { id: 12 },
    user_message: { id: 101, role: 'user', content: '什么是导数' },
    assistant_message: { id: 102, role: 'assistant', content: '导数描述函数变化率。' },
  });

  assert.equal(nextState.currentSessionId, 12);
  assert.equal(nextState.isSending, false);
  assert.equal(nextState.messages[0].id, '101');
  assert.equal(nextState.messages[0].pending, false);
  assert.equal(nextState.messages[1].role, 'assistant');
  assert.equal(nextState.messages[1].content, '导数描述函数变化率。');
});

test('failSubmission keeps the attempted user message and exposes an error', () => {
  const state = {
    ...createInitialState(),
    isSending: true,
    messages: [{ id: 'local-4', role: 'user', content: '这次会失败', pending: true, failed: false }],
  };

  const nextState = failSubmission(state, '无法连接后端服务，请确认后端已启动。');

  assert.equal(nextState.isSending, false);
  assert.equal(nextState.error, '无法连接后端服务，请确认后端已启动。');
  assert.equal(nextState.messages[0].failed, true);
  assert.equal(nextState.messages[0].pending, false);
});

test('failStreamingAssistant marks pending user message as failed before first delta', () => {
  const submission = startSubmission(createInitialState(), '网络会中断', () => 'local-stream-1');

  const nextState = failStreamingAssistant(submission.nextState, '流式读取中断，请重试。');

  assert.equal(nextState.isSending, false);
  assert.equal(nextState.error, '流式读取中断，请重试。');
  assert.equal(nextState.messages.length, 1);
  assert.equal(nextState.messages[0].role, 'user');
  assert.equal(nextState.messages[0].failed, true);
  assert.equal(nextState.messages[0].pending, false);
});

test('failStreamingAssistant removes streaming assistant and marks the triggering user message failed', () => {
  const submission = startSubmission(createInitialState(), '讲讲二次函数', () => 'local-stream-2');
  const streamingState = appendStreamingDelta(
    startStreamingAssistant(submission.nextState),
    '二次函数',
  );

  const nextState = failStreamingAssistant(streamingState, 'SSE error');

  assert.equal(nextState.isSending, false);
  assert.equal(nextState.error, 'SSE error');
  assert.equal(nextState.messages.length, 1);
  assert.equal(nextState.messages[0].role, 'user');
  assert.equal(nextState.messages[0].failed, true);
  assert.equal(nextState.messages[0].pending, false);
});

test('finishSubmission preserves assistant tool metadata from the api response', () => {
  const state = {
    ...createInitialState(),
    isSending: true,
    messages: [{ id: 'local-5', role: 'user', content: '什么是勾股定理', pending: true, failed: false }],
  };

  const nextState = finishSubmission(state, {
    session: { id: 18 },
    user_message: { id: 201, role: 'user', content: '什么是勾股定理', tools_used: null },
    assistant_message: {
      id: 202,
      role: 'assistant',
      content: '勾股定理描述了直角三角形三边之间的关系。',
      tools_used: [
        {
          tool_name: 'knowledge_tool',
          status: 'success',
        },
      ],
    },
  });

  assert.deepEqual(nextState.messages[1].toolsUsed, [
    {
      tool_name: 'knowledge_tool',
      status: 'success',
    },
  ]);
});

test('getViewModel exposes loading state, labels, and rendered message metadata', () => {
  const viewModel = getViewModel({
    currentSessionId: 12,
    isSending: true,
    error: '请求失败',
    messages: [
      { id: '101', role: 'user', content: '你好', pending: false, failed: false },
      { id: '102', role: 'assistant', content: '你好，我可以帮你复习高数。', pending: false, failed: false },
    ],
  });

  assert.equal(viewModel.sendButtonDisabled, true);
  assert.equal(viewModel.sendButtonLabel, '发送中…');
  assert.equal(viewModel.errorText, '请求失败');
  assert.equal(viewModel.emptyStateVisible, false);
  assert.deepEqual(viewModel.messages.map((message) => message.label), ['用户', 'AI']);
});
