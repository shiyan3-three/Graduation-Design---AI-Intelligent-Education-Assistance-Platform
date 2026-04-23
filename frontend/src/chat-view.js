import { getToolLabel } from './tool-labels.js';

const ROLE_LABELS = {
  user: '用户',
  assistant: 'AI',
};

export function getViewModel(state) {
  const messages = (state.messages ?? []).map((message) => ({
    id: message.id,
    role: message.role,
    label: ROLE_LABELS[message.role] ?? '系统',
    content: message.content,
    pending: message.pending,
    failed: message.failed,
    toolsUsed: mapToolsUsed(message.toolsUsed),
    toolSuggestion: mapToolSuggestion(message.toolSuggestion),
  }));
  const sessions = (state.sessions ?? []).map((session) => ({
    id: session.id,
    title: session.title,
    isActive: session.id === state.currentSessionId,
  }));

  return {
    messages,
    sessions,
    errorText: state.error,
    emptyStateVisible: messages.length === 0 && !state.isLoadingSessionDetail,
    sidebarStatusText: state.isLoadingSessions
      ? '加载历史会话中...'
      : sessions.length === 0
        ? '暂无历史会话'
        : `共 ${sessions.length} 个历史会话`,
    sessionsEmptyVisible: sessions.length === 0 && !state.isLoadingSessions,
    sendButtonDisabled: state.isSending || state.isLoadingSessionDetail,
    sendButtonLabel: state.isSending ? '发送中…' : '发送',
    sessionHint: state.currentSessionId
      ? `当前会话 #${state.currentSessionId}`
      : '准备开启新会话',
  };
}

function mapToolsUsed(toolsUsed) {
  if (!Array.isArray(toolsUsed) || toolsUsed.length === 0) {
    return null;
  }

  return toolsUsed.map((tool) => {
    const toolName = typeof tool?.tool_name === 'string' ? tool.tool_name : '';
    return {
      label: getToolLabel(toolName),
      status: tool?.status === 'error' ? 'error' : 'success',
    };
  });
}

function mapToolSuggestion(toolSuggestion) {
  if (!toolSuggestion || typeof toolSuggestion !== 'object') {
    return null;
  }

  const toolName =
    typeof toolSuggestion.tool_name === 'string' ? toolSuggestion.tool_name : '';
  const recommendedPrompt =
    typeof toolSuggestion.recommended_prompt === 'string'
      ? toolSuggestion.recommended_prompt
      : '';

  if (!toolName || !recommendedPrompt) {
    return null;
  }

  return {
    toolName,
    label: getToolLabel(toolName),
    recommendedPrompt,
  };
}
