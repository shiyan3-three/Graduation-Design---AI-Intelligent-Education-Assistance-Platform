import {
  createInitialState,
  failSubmission,
  finishSubmission,
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
};

let state = createInitialState();

elements.form?.addEventListener('submit', async (event) => {
  event.preventDefault();

  const submission = startSubmission(state, elements.input?.value ?? '');
  state = submission.nextState;
  render();

  if (!submission.requestBody) {
    return;
  }

  if (elements.input) {
    elements.input.value = '';
  }

  render();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(submission.requestBody),
    });
    const payload = await readJson(response);

    if (!response.ok) {
      state = failSubmission(
        state,
        payload?.message || '发送失败，请稍后重试。'
      );
      render();
      return;
    }

    state = finishSubmission(state, payload?.data);
    render();
  } catch (_) {
    state = failSubmission(state, '无法连接后端服务，请确认后端已启动。');
    render();
  }
});

render();

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
    !elements.sessionHint
  ) {
    return;
  }

  const viewModel = getViewModel(state);

  elements.sendButton.disabled = viewModel.sendButtonDisabled;
  elements.sendButton.textContent = viewModel.sendButtonLabel;
  elements.sessionHint.textContent = viewModel.sessionHint;

  elements.errorBanner.hidden = !viewModel.errorText;
  elements.errorBanner.textContent = viewModel.errorText;
  elements.emptyState.hidden = !viewModel.emptyStateVisible;

  elements.messageList.replaceChildren();
  for (const message of viewModel.messages) {
    elements.messageList.append(createMessageElement(message));
  }
}

function createMessageElement(message) {
  return buildMessageElement(message);
}
