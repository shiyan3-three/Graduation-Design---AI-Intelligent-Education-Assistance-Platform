import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createInitialState,
  finishSessionDetailLoad,
  finishSessionsLoad,
  startSessionDetailLoad,
  startSessionsLoad,
} from '../src/chat-state.js';
import { getViewModel } from '../src/chat-view.js';

function createSession(id, title) {
  return {
    id,
    user_id: 1,
    title,
    created_at: '2026-04-14T10:00:00Z',
    updated_at: '2026-04-14T10:05:00Z',
  };
}

function createMessage(id, role, content, sequenceNo) {
  return {
    id,
    session_id: 22,
    sequence_no: sequenceNo,
    role,
    content,
    tools_used: null,
    created_at: '2026-04-14T10:05:00Z',
  };
}

test('startSessionsLoad marks the sidebar as loading', () => {
  const nextState = startSessionsLoad(createInitialState());

  assert.equal(nextState.isLoadingSessions, true);
  assert.equal(nextState.error, '');
  assert.deepEqual(nextState.sessions, []);
});

test('finishSessionsLoad stores the returned sessions for sidebar rendering', () => {
  const loadingState = {
    ...createInitialState(),
    isLoadingSessions: true,
  };

  const nextState = finishSessionsLoad(loadingState, [
    createSession(5, '导数练习'),
    createSession(3, '函数基础'),
  ]);

  assert.equal(nextState.isLoadingSessions, false);
  assert.deepEqual(
    nextState.sessions.map((session) => session.title),
    ['导数练习', '函数基础']
  );
});

test('startSessionDetailLoad marks the chosen session as active while loading messages', () => {
  const state = finishSessionsLoad(createInitialState(), [
    createSession(5, '导数练习'),
    createSession(3, '函数基础'),
  ]);

  const nextState = startSessionDetailLoad(state, 3);

  assert.equal(nextState.currentSessionId, 3);
  assert.equal(nextState.isLoadingSessionDetail, true);
  assert.equal(nextState.error, '');
});

test('finishSessionDetailLoad replaces the main area messages with the selected session detail', () => {
  const loadingState = {
    ...createInitialState(),
    currentSessionId: 22,
    isLoadingSessionDetail: true,
    messages: [{ id: 'stale', role: 'assistant', content: '旧消息', pending: false, failed: false }],
  };

  const nextState = finishSessionDetailLoad(loadingState, {
    session: createSession(22, '二次函数'),
    messages: [
      createMessage(101, 'user', '第一条消息', 1),
      createMessage(102, 'assistant', '第二条消息', 2),
    ],
  });

  assert.equal(nextState.currentSessionId, 22);
  assert.equal(nextState.isLoadingSessionDetail, false);
  assert.deepEqual(
    nextState.messages.map((message) => [message.role, message.content]),
    [
      ['user', '第一条消息'],
      ['assistant', '第二条消息'],
    ]
  );
});

test('getViewModel exposes sidebar items and loading hints', () => {
  const viewModel = getViewModel({
    ...createInitialState(),
    currentSessionId: 5,
    isLoadingSessions: true,
    sessions: [createSession(5, '导数练习'), createSession(3, '函数基础')],
    messages: [{ id: '102', role: 'assistant', content: '你好', pending: false, failed: false }],
  });

  assert.equal(viewModel.sidebarStatusText, '加载历史会话中...');
  assert.equal(viewModel.sessionsEmptyVisible, false);
  assert.deepEqual(
    viewModel.sessions.map((session) => [session.title, session.isActive]),
    [
      ['导数练习', true],
      ['函数基础', false],
    ]
  );
});
