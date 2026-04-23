export const SCROLL_BOTTOM_THRESHOLD = 120;

export function shouldAutoScrollToBottom({
  isSending = false,
  hasStreamingMessage = false,
  justStartedSending = false,
  justFinishedDetail = false,
  distanceFromBottom = 0,
  threshold = SCROLL_BOTTOM_THRESHOLD,
} = {}) {
  if (isSending || hasStreamingMessage || justStartedSending || justFinishedDetail) {
    return true;
  }
  return distanceFromBottom < threshold;
}

export function scrollToConversationBottom(target, behavior = 'auto') {
  if (!target || typeof target.scrollIntoView !== 'function') {
    return;
  }
  target.scrollIntoView({ behavior, block: 'end' });
}

export function setScrollContainerToBottom(container) {
  if (!container) {
    return;
  }
  container.scrollTop = container.scrollHeight;
}
