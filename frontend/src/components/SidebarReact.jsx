import { useNavigate } from 'react-router-dom';
import { clearAuthSession } from '../services/api.js';

export function Sidebar({
  sessions,
  currentSessionId,
  isLoadingSessions,
  onSelectSession,
  onCreateConversation,
  isOpen,
  onClose,
}) {
  const navigate = useNavigate();

  const sidebarStatusText = isLoadingSessions
    ? '加载历史会话中…'
    : sessions.length === 0
      ? '暂时还没有历史会话'
      : `共 ${sessions.length} 个历史会话`;

  const handleLogout = () => {
    clearAuthSession();
    navigate('/login', { replace: true });
  };

  return (
    <>
      <button
        type="button"
        className={`sidebar-backdrop${isOpen ? ' is-open' : ''}`}
        aria-label="关闭侧栏"
        onClick={onClose}
      />
      <aside className={`sidebar${isOpen ? ' is-open' : ''}`}>
        <div className="sidebar__brand">
          <p className="sidebar__eyebrow">AI Tutor</p>
          <h1 className="sidebar__title">智能教育辅导平台</h1>
          <p className="sidebar__subtitle">{sidebarStatusText}</p>
        </div>

        <button type="button" className="sidebar__new-session" onClick={onCreateConversation}>
          新建辅导会话
        </button>

        <ul className="sidebar__session-list" style={{ flexGrow: 1, overflowY: 'auto' }}>
          {sessions.length === 0 ? (
            <li className="sidebar__placeholder">发出第一条消息后，新的会话就会出现在这里。</li>
          ) : (
            sessions.map((session) => (
              <li key={session.id}>
                <button
                  type="button"
                  className={`sidebar__session-button${
                    session.id === currentSessionId ? ' is-active' : ''
                  }`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <span className="sidebar__session-title">{session.title}</span>
                  {session.id === currentSessionId ? (
                    <span className="sidebar__session-badge">当前会话</span>
                  ) : null}
                </button>
              </li>
            ))
          )}
        </ul>

        {/* LOGOUT BUTTON */}
        <div className="sidebar__footer" style={{ padding: '24px', borderTop: '1px solid var(--color-border)', marginTop: 'auto' }}>
          <button 
            type="button" 
            className="sidebar__new-session" 
            style={{ backgroundColor: 'transparent', color: 'var(--color-text)', border: '1px solid var(--color-border)' }}
            onClick={handleLogout}
          >
            退出系统节点
          </button>
        </div>
      </aside>
    </>
  );
}
