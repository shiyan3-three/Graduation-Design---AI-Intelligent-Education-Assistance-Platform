import { useEffect, useState } from 'react';

import {
    appendStreamingDelta,
    createInitialState,
    failSessionDetailLoad,
    failSessionsLoad,
    failStreamingAssistant,
    finalizeStreamingAssistant,
    finishSessionDetailLoad,
    finishSessionsLoad,
    startNewConversation,
    startSessionDetailLoad,
    startSessionsLoad,
    startStreamingAssistant,
    startSubmission,
} from '../chat-state.js';
import { requestJson, streamChatRequest } from '../services/api.js';


export function useChatApp() {
    const [state, setState] = useState(createInitialState);
    const [draft, setDraft] = useState('');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    useEffect(() => {
        void loadSessions();
    }, []);

    async function submitMessage(rawContent, options = {}) {
        const submission = startSubmission(state, rawContent, options);
        setState(submission.nextState);

        if (!submission.requestBody) {
            return;
        }

        setDraft('');

        try {
            await streamChatRequest(submission.requestBody, {
                onDelta: (chunk) => {
                    setState((current) => {
                        const last = current.messages[current.messages.length - 1];
                        const base = last && last.streaming ? current : startStreamingAssistant(current);
                        return appendStreamingDelta(base, chunk);
                    });
                },
                onDone: (event) => {
                    setState((current) =>
                        finalizeStreamingAssistant(current, event.session_id, event.message_id, event.tools_used)
                    );
                    void loadSessions({ silent: true });
                },
                onError: (message) => {
                    setState((current) => failStreamingAssistant(current, message));
                },
            });
        } catch (_) {
            setState((current) => failStreamingAssistant(current, '无法连接后端服务，请确认后端已启动。'));
        }
    }

    async function loadSessions(options = {}) {
        if (!options.silent) {
            setState((currentState) => startSessionsLoad(currentState));
        }

        try {
            const { response, payload } = await requestJson('/api/sessions');
            if (!response.ok) {
                setState((currentState) =>
                    failSessionsLoad(currentState, (payload && payload.message) || '历史会话加载失败，请稍后重试。')
                );
                return;
            }

            setState((currentState) => finishSessionsLoad(currentState, payload && payload.data && payload.data.items));
        } catch (_) {
            setState((currentState) =>
                failSessionsLoad(currentState, '无法加载历史会话，请确认后端已启动。')
            );
        }
    }

    async function loadSessionDetail(sessionId) {
        setState((currentState) => startSessionDetailLoad(currentState, sessionId));
        setIsSidebarOpen(false);

        try {
            const { response, payload } = await requestJson(`/api/sessions/${sessionId}`);
            if (!response.ok) {
                setState((currentState) =>
                    failSessionDetailLoad(currentState, (payload && payload.message) || '会话详情加载失败，请稍后重试。')
                );
                return;
            }

            setState((currentState) => finishSessionDetailLoad(currentState, payload && payload.data));
        } catch (_) {
            setState((currentState) =>
                failSessionDetailLoad(currentState, '无法加载会话详情，请确认后端已启动。')
            );
        }
    }

    function createConversation() {
        setState((currentState) => startNewConversation(currentState));
        setDraft('');
        setIsSidebarOpen(false);
    }

    function submitSuggestedPrompt(toolSuggestion) {
        if (!toolSuggestion || !toolSuggestion.recommended_prompt || !toolSuggestion.tool_name) {
            return;
        }

        void submitMessage(toolSuggestion.recommended_prompt, {
            toolPreference: toolSuggestion.tool_name,
        });
    }

    return {
        state,
        draft,
        setDraft,
        isSidebarOpen,
        openSidebar: () => setIsSidebarOpen(true),
        closeSidebar: () => setIsSidebarOpen(false),
        submitMessage,
        loadSessionDetail,
        createConversation,
        submitSuggestedPrompt,
    };
}
