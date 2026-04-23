import { useEffect, useState } from 'react';

import {
  createInitialState,
  failSessionDetailLoad,
  failSessionsLoad,
  failSubmission,
  finishSessionDetailLoad,
  finishSessionsLoad,
  finishSubmission,
  startNewConversation,
  startSessionDetailLoad,
  startSessionsLoad,
  startSubmission,
} from '../chat-state.js';
import { requestJson } from '../services/api.js';
import { getNextTheme, resolveInitialTheme } from '../theme-state.js';

const THEME_STORAGE_KEY = 'frontend-theme';

export function useChatApp() {
  const [state, setState] = useState(createInitialState);
  const [draft, setDraft] = useState('');
  const [theme, setTheme] = useState(() =>
    resolveInitialTheme(() => {
      if (typeof window === 'undefined') {
        return 'light';
      }

      return window.localStorage.getItem(THEME_STORAGE_KEY);
    })
  );
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    void loadSessions();
  }, []);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
    }

    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(THEME_STORAGE_KEY, theme);
      } catch (_) {
        // Ignore localStorage errors and keep the current in-memory theme.
      }
    }
  }, [theme]);

  async function submitMessage(rawContent, options = {}) {
    const submission = startSubmission(state, rawContent, options);
    setState(submission.nextState);

    if (!submission.requestBody) {
      return;
    }

    setDraft('');

    try {
      const { response, payload } = await requestJson('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(submission.requestBody),
      });

      if (!response.ok) {
        setState((currentState) =>
          failSubmission(currentState, payload?.message || '发送失败，请稍后重试。')
        );
        return;
      }

      setState((currentState) => finishSubmission(currentState, payload?.data));
      await loadSessions({ silent: true });
    } catch (_) {
      setState((currentState) =>
        failSubmission(currentState, '无法连接后端服务，请确认后端已启动。')
      );
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
          failSessionsLoad(currentState, payload?.message || '历史会话加载失败，请稍后重试。')
        );
        return;
      }

      setState((currentState) => finishSessionsLoad(currentState, payload?.data?.items));
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
          failSessionDetailLoad(currentState, payload?.message || '会话详情加载失败，请稍后重试。')
        );
        return;
      }

      setState((currentState) => finishSessionDetailLoad(currentState, payload?.data));
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
    if (!toolSuggestion?.recommended_prompt || !toolSuggestion?.tool_name) {
      return;
    }

    void submitMessage(toolSuggestion.recommended_prompt, {
      toolPreference: toolSuggestion.tool_name,
    });
  }

  function toggleTheme() {
    setTheme((currentTheme) => getNextTheme(currentTheme));
  }

  return {
    state,
    draft,
    setDraft,
    theme,
    toggleTheme,
    isSidebarOpen,
    openSidebar: () => setIsSidebarOpen(true),
    closeSidebar: () => setIsSidebarOpen(false),
    submitMessage,
    loadSessionDetail,
    createConversation,
    submitSuggestedPrompt,
  };
}
