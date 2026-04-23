import { useLayoutEffect, useRef } from 'react';

import { InputBar } from './InputBarReact.jsx';
import { MessageBubble } from './MessageBubbleReact.jsx';
import { ThemeToggle } from './ThemeToggleReact.jsx';
import {
  scrollToConversationBottom,
  setScrollContainerToBottom,
  shouldAutoScrollToBottom,
} from '../chat-scroll.js';

export function ChatPanel({
  state,
  draft,
  onDraftChange,
  onSubmit,
  onUseToolSuggestion,
  onToggleTheme,
  theme,
  onOpenSidebar,
}) {
  const streamEndRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const wasSendingRef = useRef(false);
  const wasLoadingDetailRef = useRef(false);

  useLayoutEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const hasStreamingMessage = state.messages.some((message) => message.streaming);
    const justStartedSending = state.isSending && !wasSendingRef.current;
    const justFinishedDetail = !state.isLoadingSessionDetail && wasLoadingDetailRef.current;
    wasSendingRef.current = state.isSending;
    wasLoadingDetailRef.current = state.isLoadingSessionDetail;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;

    if (
      !shouldAutoScrollToBottom({
        isSending: state.isSending,
        hasStreamingMessage,
        justStartedSending,
        justFinishedDetail,
        distanceFromBottom,
      })
    ) {
      return;
    }

    const scrollNow = () => {
      setScrollContainerToBottom(container);
      scrollToConversationBottom(streamEndRef.current, 'auto');
    };
    scrollNow();
    const frameId = requestAnimationFrame(scrollNow);
    const timeoutId = window.setTimeout(scrollNow, 80);

    return () => {
      cancelAnimationFrame(frameId);
      window.clearTimeout(timeoutId);
    };
  }, [state.messages, state.isSending, state.isLoadingSessionDetail]);

  const currentSessionText = state.currentSessionId
    ? `当前会话 #${state.currentSessionId}`
    : '准备开启新会话';

  const hasMessages = state.messages.length > 0;

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (state.isSending || state.isLoadingSessionDetail) return;
      onSubmit();
    }
  }

  return (
    <section className="chat-panel">
      <header className="chat-panel__header">
        <div className="chat-panel__header-main">
          <button type="button" className="chat-panel__menu-button" onClick={onOpenSidebar}>
            会话
          </button>
          <div>
            <p className="chat-panel__eyebrow">辅导工作台</p>
            <h2 className="chat-panel__title">专注对话，清晰思考</h2>
          </div>
        </div>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </header>

      <div className="chat-panel__status-row">
        <p className="chat-panel__session-hint">{currentSessionText}</p>
        {state.isLoadingSessionDetail ? (
          <p className="chat-panel__loading-text">正在切换会话…</p>
        ) : null}
      </div>

      {state.error ? <div className="chat-panel__error">{state.error}</div> : null}

      <div className="chat-panel__stream" ref={scrollContainerRef}>
        {!hasMessages && !state.isLoadingSessionDetail ? (
          <div className="empty-state">
            <p className="empty-state__eyebrow">准备开始</p>
            <h3>把问题交给 AI 辅导助手</h3>
            <p>
              你可以直接提问概念、计算题，或者让它出一道练习题。历史会话和工具调用状态都会保留在这里。
            </p>
          </div>
        ) : null}

        <ul className="message-list">
          {state.messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onUseToolSuggestion={onUseToolSuggestion}
            />
          ))}

          {state.isSending && !state.messages.some((m) => m.streaming) ? (
            <li className="message-row role-assistant">
              <article className="message-bubble role-assistant is-loading">
                <header className="message-bubble__meta">
                  <span className="message-bubble__label role-assistant">AI</span>
                </header>
                <div className="loading-dots" aria-label="AI 正在处理">
                  <span />
                  <span />
                  <span />
                </div>
                <p className="message-bubble__content">AI 正在整理思路并准备回复…</p>
              </article>
            </li>
          ) : null}
        </ul>

        <div ref={streamEndRef} />
      </div>

      <InputBar
        value={draft}
        onChange={onDraftChange}
        onSubmit={onSubmit}
        onKeyDown={handleKeyDown}
        disabled={state.isSending || state.isLoadingSessionDetail}
      />
    </section>
  );
}
