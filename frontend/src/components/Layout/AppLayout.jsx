import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { GlobalHeader } from '../GlobalHeader/GlobalHeader.jsx';
import { useGlobalTheme } from '../../hooks/useGlobalTheme.js';
import { requestJson, getAuthToken, saveAuthSession } from '../../services/api.js';

export function AppLayout() {
  const { theme, toggleTheme } = useGlobalTheme();

  useEffect(() => {
    // On mount, validate the stored token against the backend.
    //
    // If the token is forged / expired, requestJson's global 401 handler will
    // automatically call clearAuthSession() and redirect to /login.
    //
    // We skip this when there is no token — ProtectedRoute already handles
    // the "no token" case synchronously before AppLayout ever mounts.
    //
    // Network errors are swallowed (fail open): a transient connectivity blip
    // must not log out a user who is otherwise legitimately authenticated.
    const token = getAuthToken();
    if (!token) return;

    requestJson('/api/auth/me').then(({ response, payload }) => {
      if (response?.ok && payload?.success && payload.data) {
        saveAuthSession(token, payload.data);
        window.dispatchEvent(new Event('edu-user-updated'));
      }
    }).catch(() => {
      // Network / proxy error: fail open.
    });
  }, []); // run once on mount

  return (
    <>
      <GlobalHeader theme={theme} onToggleTheme={toggleTheme} />
      <main style={{ paddingTop: '64px', minHeight: '100vh', background: 'var(--bg-global)' }}>
        <Outlet context={{ theme, toggleTheme }} />
      </main>
    </>
  );
}
