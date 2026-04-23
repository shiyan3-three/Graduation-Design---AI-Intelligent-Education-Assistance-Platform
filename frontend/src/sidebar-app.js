import {
  createInitialState,
  failSessionDetailLoad,
  failSessionsLoad,
  failSubmission,
  finishSessionDetailLoad,
  finishSessionsLoad,
  finishSubmission,
  startSessionDetailLoad,
  startSessionsLoad,
  startSubmission,
} from './chat-state.js';
import { getViewModel } from './chat-view.js';
import { createMessageElement as buildMessageElement } from './message-element.js';

const elements = {
  form: document.querySelector('#chat-form'),
  input: document.querySelector('#message-input'),
  sendButton: document.querySelector('#send-button'),
  messageList: document.querySelector('#message-list'),
  emptyState: document.querySelector('#empty-state'),
  errorBanner: document.querySelector('#error-banner'),
  sessionHint: document.querySelector('#session-hint'),
  sessionList: document.querySelector('#session-list'),
  sessionStatus: document.querySelector('#session-status'),
};

let state = createInitialState();

elements.form?.addEventListener('submit', (event) => {
  void handleSubmit(event);
});

elements.messageList?.addEventListener('click', (event) => {
  const trigger = event.target.closest('[data-tool-suggestion-message-id]');
  if (!trigger || state.isSending) {
    return;
  }

  const message = findMessageById(trigger.dataset.toolSuggestionMessageId);
  const toolSuggestion = message?.toolSuggestion;
  if (!toolSuggestion?.recommended_prompt || !toolSuggestion?.tool_name) {
    return;
  }

  void submitMessage(toolSuggestion.recommended_prompt, {
    toolPreference: toolSuggestion.tool_name,
  });
});

elements.sessionList?.addEventListener('click', (event) => {
  const trigger = event.target.closest('[data-session-id]');
  if (!trigger) {
    return;
  }

  const sessionId = Number(trigger.dataset.sessionId);
  if (!Number.isInteger(sessionId)) {
    return;
  }

  void loadSessionDetail(sessionId);
});

render();
void loadSessions();

async function handleSubmit(event) {
  event.preventDefault();
  await submitMessage(elements.input?.value ?? '');
}

async function submitMessage(rawContent, options = {}) {
  const submission = startSubmission(state, rawContent, options);
  state = submission.nextState;
  render();

  if (!submission.requestBody) {
    return;
  }

  if (elements.input) {
    elements.input.value = '';
  }

  try {
    const { response, payload } = await requestJson('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(submission.requestBody),
    });

    if (!response.ok) {
      state = failSubmission(state, payload?.message || '发送失败，请稍后重试。');
      render();
      return;
    }

    state = finishSubmission(state, payload?.data);
    render();
    await loadSessions();
  } catch (_) {
    state = failSubmission(state, '无法连接后端服务，请确认后端已启动。');
    render();
  }
}

async function loadSessions() {
  state = startSessionsLoad(state);
  render();

  try {
    const { response, payload } = await requestJson('/api/sessions');
    if (!response.ok) {
      state = failSessionsLoad(state, payload?.message || '历史会话加载失败，请稍后重试。');
      render();
      return;
    }

    state = finishSessionsLoad(state, payload?.data?.items);
    render();
  } catch (_) {
    state = failSessionsLoad(state, '无法加载历史会话，请确认后端已启动。');
    render();
  }
}

async function loadSessionDetail(sessionId) {
  state = startSessionDetailLoad(state, sessionId);
  render();

  try {
    const { response, payload } = await requestJson(`/api/sessions/${sessionId}`);
    if (!response.ok) {
      state = failSessionDetailLoad(state, payload?.message || '会话详情加载失败，请稍后重试。');
      render();
      return;
    }

    state = finishSessionDetailLoad(state, payload?.data);
    render();
  } catch (_) {
    state = failSessionDetailLoad(state, '无法加载会话详情，请确认后端已启动。');
    render();
  }
}

async function requestJson(url, init) {
  const response = await fetch(url, init);
  const payload = await readJson(response);
  return { response, payload };
}

async function readJson(response) {
  try {
    return await response.json();
  } catch (_) {
    return null;
  }
}

function render() {
  if (
    !elements.sendButton ||
    !elements.messageList ||
    !elements.emptyState ||
    !elements.errorBanner ||
    !elements.sessionHint ||
    !elements.sessionList ||
    !elements.sessionStatus
  ) {
    return;
  }

  const viewModel = getViewModel(state);

  elements.sendButton.disabled = viewModel.sendButtonDisabled;
  elements.sendButton.textContent = viewModel.sendButtonLabel;
  elements.sessionHint.textContent = viewModel.sessionHint;
  elements.sessionStatus.textContent = viewModel.sidebarStatusText;

  elements.errorBanner.hidden = !viewModel.errorText;
  elements.errorBanner.textContent = viewModel.errorText;
  elements.emptyState.hidden = !viewModel.emptyStateVisible;

  elements.messageList.replaceChildren();
  for (const message of viewModel.messages) {
    elements.messageList.append(createMessageElement(message));
  }

  elements.sessionList.replaceChildren();
  if (viewModel.sessionsEmptyVisible) {
    elements.sessionList.append(createSessionPlaceholder());
    return;
  }

  for (const session of viewModel.sessions) {
    elements.sessionList.append(createSessionElement(session));
  }
}

function createSessionElement(session) {
  const item = document.createElement('li');
  item.className = 'session-item';

  const button = document.createElement('button');
  button.type = 'button';
  button.className = `session-button${session.isActive ? ' is-active' : ''}`;
  button.dataset.sessionId = String(session.id);

  const title = document.createElement('span');
  title.className = 'session-button__title';
  title.textContent = session.title || '未命名会话';

  button.append(title);

  if (session.isActive) {
    const meta = document.createElement('span');
    meta.className = 'session-button__meta';
    meta.textContent = '当前会话';
    button.append(meta);
  }

  item.append(button);
  return item;
}

function createSessionPlaceholder() {
  const item = document.createElement('li');
  item.className = 'session-item';

  const placeholder = document.createElement('div');
  placeholder.className = 'session-placeholder';
  placeholder.textContent = '当前还没有历史会话。发送第一条消息后，新的会话会出现在这里。';

  item.append(placeholder);
  return item;
}

function createMessageElement(message) {
  return buildMessageElement(message);
}

function findMessageById(messageId) {
  if (!messageId) {
    return null;
  }

  return state.messages.find((message) => String(message.id) === String(messageId)) ?? null;
}
