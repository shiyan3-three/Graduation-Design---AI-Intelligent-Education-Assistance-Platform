function createLocalMessageId() {
    return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createInitialState() {
    return {
        currentSessionId: null,
        isSending: false,
        isLoadingSessions: false,
        isLoadingSessionDetail: false,
        error: '',
        messages: [],
        sessions: [],
    };
}

export function startNewConversation(state) {
    return {
        ...state,
        currentSessionId: null,
        isSending: false,
        isLoadingSessionDetail: false,
        error: '',
        messages: [],
    };
}

export function startSubmission(
    state,
    rawContent,
    optionsOrCreateId = {},
    createId = createLocalMessageId
) {
    const options =
        typeof optionsOrCreateId === 'function' ? {} : optionsOrCreateId || {};
    const resolveId =
        typeof optionsOrCreateId === 'function' ? optionsOrCreateId : createId;

    if (state.isSending || state.isLoadingSessionDetail) {
        return {
            requestBody: null,
            nextState: state,
        };
    }

    const content = rawContent.trim();
    if (!content) {
        return {
            requestBody: null,
            nextState: {
                ...state,
                isSending: false,
                error: '请输入消息内容。',
            },
        };
    }

    const requestBody = {
        content,
        session_id: state.currentSessionId || null,
    };
    if (typeof options.toolPreference === 'string' && options.toolPreference) {
        requestBody.tool_preference = options.toolPreference;
    }

    return {
        requestBody,
        nextState: {
            ...state,
            isSending: true,
            error: '',
            messages: [
                ...state.messages,
                {
                    id: resolveId(),
                    role: 'user',
                    content,
                    pending: true,
                    failed: false,
                    toolsUsed: null,
                },
            ],
        },
    };
}

export function finishSubmission(state, responseData) {
    const userMessage = normalizeApiMessage(responseData && responseData.user_message);
    const assistantMessage = normalizeApiMessage(responseData && responseData.assistant_message);
    let messages = replaceLatestPendingUserMessage(state.messages, userMessage);

    if (assistantMessage) {
        messages = [...messages, assistantMessage];
    }

    return {
        ...state,
        currentSessionId: normalizeSessionId(responseData && responseData.session && responseData.session.id, state.currentSessionId),
        isSending: false,
        error: '',
        messages,
    };
}

export function failSubmission(state, errorMessage) {
    return {
        ...state,
        isSending: false,
        error: errorMessage || '发送失败，请稍后重试。',
        messages: markLatestPendingMessageAsFailed(state.messages),
    };
}

export function startStreamingAssistant(state) {
    const messages = state.messages.map((m, i) =>
        i === state.messages.length - 1 && m.role === 'user' && m.pending ? {...m, pending: false } :
        m
    );
    return {
        ...state,
        messages: [
            ...messages,
            {
                id: createLocalMessageId(),
                role: 'assistant',
                content: '',
                streaming: true,
                pending: false,
                failed: false,
                toolsUsed: null,
                toolSuggestion: null,
            },
        ],
    };
}

export function appendStreamingDelta(state, chunk) {
    const messages = [...state.messages];
    const lastIndex = messages.length - 1;
    if (lastIndex < 0 || !messages[lastIndex].streaming) {
        return state;
    }
    messages[lastIndex] = {
        ...messages[lastIndex],
        content: messages[lastIndex].content + chunk,
    };
    return {...state, messages };
}

export function finalizeStreamingAssistant(state, sessionId, messageId, toolsUsed) {
    const messages = [...state.messages];
    const lastIndex = messages.length - 1;
    if (lastIndex >= 0 && messages[lastIndex].streaming) {
        messages[lastIndex] = {
            ...messages[lastIndex],
            id: messageId != null ? String(messageId) : messages[lastIndex].id,
            streaming: false,
            toolsUsed: Array.isArray(toolsUsed) ? toolsUsed : null,
        };
    }
    return {
        ...state,
        currentSessionId: typeof sessionId === 'number' && Number.isInteger(sessionId) ?
            sessionId : state.currentSessionId,
        isSending: false,
        error: '',
        messages,
    };
}

export function failStreamingAssistant(state, errorMessage) {
    const lastIndex = state.messages.length - 1;
    const hasStreamingTail = lastIndex >= 0 && state.messages[lastIndex].streaming;
    const messages = hasStreamingTail ?
        state.messages.slice(0, lastIndex) : [...state.messages];
    return {
        ...state,
        isSending: false,
        error: errorMessage || '发送失败，请稍后重试。',
        messages: markLatestUserMessageAsFailed(messages),
    };
}

export function startSessionsLoad(state) {
    return {
        ...state,
        isLoadingSessions: true,
        error: '',
    };
}

export function finishSessionsLoad(state, sessions) {
    return {
        ...state,
        isLoadingSessions: false,
        error: '',
        sessions: normalizeSessions(sessions),
    };
}

export function failSessionsLoad(state, errorMessage) {
    return {
        ...state,
        isLoadingSessions: false,
        error: errorMessage || '历史会话加载失败，请稍后重试。',
    };
}

export function startSessionDetailLoad(state, sessionId) {
    return {
        ...state,
        currentSessionId: normalizeSessionId(sessionId, state.currentSessionId),
        isLoadingSessionDetail: true,
        error: '',
    };
}

export function finishSessionDetailLoad(state, responseData) {
    return {
        ...state,
        currentSessionId: normalizeSessionId(responseData && responseData.session && responseData.session.id, state.currentSessionId),
        isLoadingSessionDetail: false,
        error: '',
        messages: normalizeMessages(responseData && responseData.messages),
    };
}

export function failSessionDetailLoad(state, errorMessage) {
    return {
        ...state,
        isLoadingSessionDetail: false,
        error: errorMessage || '会话详情加载失败，请稍后重试。',
    };
}

function normalizeSessions(sessions) {
    if (!Array.isArray(sessions)) {
        return [];
    }

    return sessions
        .map((session) => normalizeSession(session))
        .filter((session) => session !== null);
}

function normalizeSession(session) {
    const id = normalizeSessionId(session && session.id, null);
    if (id === null || typeof(session && session.title) !== 'string') {
        return null;
    }

    return {
        id,
        user_id: Number(session.user_id || 0),
        title: session.title,
        created_at: String(session.created_at || ''),
        updated_at: String(session.updated_at || ''),
    };
}

function normalizeMessages(messages) {
    if (!Array.isArray(messages)) {
        return [];
    }

    return messages
        .map((message) => normalizeApiMessage(message))
        .filter((message) => message !== null);
}

function normalizeApiMessage(message) {
    if (!message || typeof message.role !== 'string' || typeof message.content !== 'string') {
        return null;
    }

    return {
        id: String(message.id !== null && message.id !== undefined ? message.id : createLocalMessageId()),
        role: message.role,
        content: message.content,
        pending: false,
        failed: false,
        toolsUsed: Array.isArray(message.tools_used) ? message.tools_used : null,
        toolSuggestion: normalizeToolSuggestion(message.tool_suggestion),
    };
}

function normalizeToolSuggestion(toolSuggestion) {
    if (!toolSuggestion || typeof toolSuggestion !== 'object') {
        return null;
    }

    const toolName =
        typeof toolSuggestion.tool_name === 'string' ? toolSuggestion.tool_name : '';
    const recommendedPrompt =
        typeof toolSuggestion.recommended_prompt === 'string' ?
        toolSuggestion.recommended_prompt :
        '';

    if (!toolName || !recommendedPrompt) {
        return null;
    }

    return {
        tool_name: toolName,
        recommended_prompt: recommendedPrompt,
    };
}

function normalizeSessionId(value, fallback) {
    if (typeof value === 'number' && Number.isInteger(value)) {
        return value;
    }

    return fallback !== undefined ? fallback : null;
}

function replaceLatestPendingUserMessage(messages, userMessage) {
    const targetIndex = findLatestPendingUserMessageIndex(messages);
    if (targetIndex === -1) {
        return userMessage ? [...messages, userMessage] : [...messages];
    }

    return messages.map((message, index) => {
        if (index !== targetIndex) {
            return message;
        }

        return userMessage !== null && userMessage !== undefined ? userMessage : {...message, pending: false };
    });
}

function markLatestPendingMessageAsFailed(messages) {
    const targetIndex = findLatestPendingUserMessageIndex(messages);
    if (targetIndex === -1) {
        return [...messages];
    }

    return messages.map((message, index) => {
        if (index !== targetIndex) {
            return message;
        }

        return {
            ...message,
            pending: false,
            failed: true,
        };
    });
}

function markLatestUserMessageAsFailed(messages) {
    const targetIndex = findLatestUserMessageIndex(messages);
    if (targetIndex === -1) {
        return [...messages];
    }

    return messages.map((message, index) => {
        if (index !== targetIndex) {
            return message;
        }

        return {
            ...message,
            pending: false,
            failed: true,
        };
    });
}

function findLatestPendingUserMessageIndex(messages) {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
        const message = messages[index];
        if (message.role === 'user' && message.pending) {
            return index;
        }
    }

    return -1;
}

function findLatestUserMessageIndex(messages) {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
        const message = messages[index];
        if (message.role === 'user') {
            return index;
        }
    }

    return -1;
}
