import { useOutletContext } from 'react-router-dom';
import { ChatPanel } from '../components/ChatPanelReact.jsx';
import { Sidebar } from '../components/SidebarReact.jsx';
import { useChatApp } from '../hooks/useChatAppReact.js';

export function ChatPage() {
  // theme comes from AppLayout (single source of truth)
  const { theme, toggleTheme } = useOutletContext();

  const {
    state,
    draft,
    setDraft,
    isSidebarOpen,
    openSidebar,
    closeSidebar,
    submitMessage,
    loadSessionDetail,
    createConversation,
    submitSuggestedPrompt,
  } = useChatApp();

  return (
    <div className="app-shell">
      <Sidebar
        sessions={state.sessions}
        currentSessionId={state.currentSessionId}
        isLoadingSessions={state.isLoadingSessions}
        onSelectSession={loadSessionDetail}
        onCreateConversation={createConversation}
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
      />

      <main className="app-shell__main">
        <ChatPanel
          state={state}
          draft={draft}
          onDraftChange={setDraft}
          onSubmit={() => submitMessage(draft)}
          onUseToolSuggestion={submitSuggestedPrompt}
          onToggleTheme={toggleTheme}
          theme={theme}
          onOpenSidebar={openSidebar}
        />
      </main>
    </div>
  );
}
