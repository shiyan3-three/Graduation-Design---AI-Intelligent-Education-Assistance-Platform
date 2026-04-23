import { ToolBadge } from './ToolBadge.jsx';

const ROLE_LABELS = {
  user: '用户',
  assistant: 'AI',
};

export function MessageBubble({ message, onUseToolSuggestion }) {
  const role = message.role === 'assistant' ? 'assistant' : 'user';
  const hasToolSuggestion =
    role === 'assistant' &&
    message.toolSuggestion?.recommended_prompt &&
    message.toolSuggestion?.tool_name;

  return (
    <li className={`message-row role-${role}`}>
      <article className={`message-bubble role-${role}`}>
        <header className="message-bubble__meta">
          <span className={`message-bubble__label role-${role}`}>{ROLE_LABELS[role]}</span>
          {message.pending ? <span className="message-bubble__status">发送中…</span> : null}
          {message.failed ? <span className="message-bubble__status is-failed">发送失败</span> : null}
        </header>

        {Array.isArray(message.toolsUsed) && message.toolsUsed.length > 0 ? (
          <div className="message-bubble__tools">
            {message.toolsUsed.map((tool, index) => (
              <ToolBadge key={`${message.id}-tool-${index}`} tool={tool} />
            ))}
          </div>
        ) : null}

        <p className="message-bubble__content">{message.content}</p>

        {hasToolSuggestion ? (
          <div className="tool-suggestion-card">
            <p className="tool-suggestion-card__text">
              当前问题更适合使用
              <strong>{message.toolSuggestion.label}</strong>
              来获取结果。
            </p>
            <button
              type="button"
              className="tool-suggestion-card__button"
              onClick={() => onUseToolSuggestion(message.toolSuggestion)}
            >
              使用工具
            </button>
          </div>
        ) : null}
      </article>
    </li>
  );
}
