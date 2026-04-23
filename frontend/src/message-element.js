export function createMessageElement(message) {
  const item = document.createElement('li');
  item.className = `message-item role-${message.role}`;

  const bubble = document.createElement('article');
  bubble.className = 'message-bubble';

  const meta = document.createElement('div');
  meta.className = 'message-meta';

  const label = document.createElement('span');
  label.className = 'message-label';
  label.textContent = message.label;
  meta.append(label);

  if (message.pending || message.failed) {
    const status = document.createElement('span');
    status.className = `message-status ${message.failed ? 'is-failed' : 'is-pending'}`;
    status.textContent = message.failed ? '发送失败' : '发送中...';
    meta.append(status);
  }

  const toolTags = createToolTagsElement(message.toolsUsed);
  const content = document.createElement('p');
  content.className = 'message-content';
  content.textContent = message.content;
  const toolSuggestion = createToolSuggestionElement(message);

  bubble.append(meta);
  if (toolTags) {
    bubble.append(toolTags);
  }
  bubble.append(content);
  if (toolSuggestion) {
    bubble.append(toolSuggestion);
  }
  item.append(bubble);
  return item;
}

function createToolTagsElement(toolsUsed) {
  if (!Array.isArray(toolsUsed) || toolsUsed.length === 0) {
    return null;
  }

  const container = document.createElement('div');
  container.className = 'tool-tags';

  for (const tool of toolsUsed) {
    container.append(createToolTagElement(tool));
  }

  return container;
}

function createToolTagElement(tool) {
  const tag = document.createElement('span');
  const isError = tool?.status === 'error';
  tag.className = `tool-tag ${isError ? 'is-error' : 'is-success'}`;
  tag.textContent = `🔧 ${tool?.label ?? ''} ${isError ? '失败' : '成功'}`;
  return tag;
}

function createToolSuggestionElement(message) {
  if (!message?.toolSuggestion) {
    return null;
  }

  const container = document.createElement('div');
  container.className = 'tool-suggestion';

  const text = document.createElement('p');
  text.className = 'tool-suggestion__text';
  text.textContent = `当前问题可能适合使用${message.toolSuggestion.label}。`;

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'tool-suggestion__button';
  button.textContent = '使用工具';
  button.dataset.toolSuggestionMessageId = String(message.id ?? '');

  container.append(text);
  container.append(button);
  return container;
}
