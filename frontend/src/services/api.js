// ── Storage key constants ─────────────────────────────────────────────────────
const _TOKEN_KEY = 'token';
const _USER_KEY = 'edu_user';

// ── Auth session helpers ──────────────────────────────────────────────────────

/** Read the stored JWT token (null if absent). */
export function getAuthToken() {
    return localStorage.getItem(_TOKEN_KEY);
}

/** Persist the raw JWT token (legacy helper, kept for compatibility). */
export function saveAuthToken(token) {
    localStorage.setItem(_TOKEN_KEY, token);
}

/**
 * Clear the JWT token.  Also removes edu_user so the two stores stay in sync.
 * Kept for backward-compatibility; prefer clearAuthSession() for new code.
 */
export function clearAuthToken() {
    localStorage.removeItem(_TOKEN_KEY);
    localStorage.removeItem(_USER_KEY);
}

/**
 * Atomically persist both the JWT token and the user profile.
 * @param {string} token  - Bearer token returned by /api/login
 * @param {object} user   - User object (id, username, grade, subject, …)
 */
export function saveAuthSession(token, user) {
    localStorage.setItem(_TOKEN_KEY, token);
    localStorage.setItem(_USER_KEY, JSON.stringify(user));
}

/** Atomically remove both the JWT token and the user profile. */
export function clearAuthSession() {
    localStorage.removeItem(_TOKEN_KEY);
    localStorage.removeItem(_USER_KEY);
}

// ── Core request helper ───────────────────────────────────────────────────────

/**
 * URL prefixes that are public (no JWT required).
 * A 401 from these endpoints means a business-level auth failure
 * (e.g. wrong password) — NOT a stale session — so we must NOT clear
 * the current session or redirect to /login.
 */
const _PUBLIC_PATHS = ['/api/login', '/api/register'];

/**
 * Sends a JSON API request.
 * - Automatically injects `Authorization: Bearer <token>` when a token exists.
 * - On 401 from protected endpoints, clears the auth session and redirects
 *   to /login.  Public endpoints (/api/login, /api/register) are excluded
 *   so that wrong-password errors reach the UI normally.
 */
export async function requestJson(url, init = {}) {
    const token = getAuthToken();
    const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

    const mergedInit = {
        ...init,
        headers: {...authHeaders, ...(init.headers || {}) },
    };

    const response = await fetch(url, mergedInit);

    const isPublicPath = _PUBLIC_PATHS.some((p) => url.startsWith(p));
    if (response.status === 401 && !isPublicPath) {
        clearAuthSession();
        // Guard: window may not be available in SSR / test environments.
        if (typeof window !== 'undefined') {
            window.location.href = '/login';
        }
    }

    const payload = await readJson(response);
    return { response, payload };
}

async function readJson(response) {
    try {
        return await response.json();
    } catch (_) {
        return null;
    }
}

// ── Auth endpoints ────────────────────────────────────────────────────────────

export async function loginUser(username, password) {
    return requestJson('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });
}

export async function registerUser(username, password, grade, subject) {
    return requestJson('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, grade, subject }),
    });
}

// ── Analytics endpoints ───────────────────────────────────────────────────────

export async function fetchAnalyticsTags() {
    return requestJson('/api/analytics/tags');
}

export async function fetchAnalyticsReport() {
    return requestJson('/api/analytics/report');
}

export async function fetchAnalyticsSummary() {
    return requestJson('/api/analytics/summary');
}

export async function fetchSessions() {
    return requestJson('/api/sessions');
}

// ── Admin endpoints ───────────────────────────────────────────────────────────

export async function fetchAdminStats() {
    return requestJson('/api/admin/stats');
}

export async function fetchAdminUsers() {
    return requestJson('/api/admin/users');
}

export async function toggleAdminUser(userId) {
    return requestJson(`/api/admin/users/${userId}/admin`, {
        method: 'PUT',
    });
}

export async function deleteAdminUser(userId) {
    return requestJson(`/api/admin/users/${userId}`, {
        method: 'DELETE',
    });
}

export async function fetchAdminQuestions(filters = {}) {
    const query = new URLSearchParams();
    if (filters.subject) query.set('subject', filters.subject);
    if (filters.topic) query.set('topic', filters.topic);
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return requestJson(`/api/admin/questions${suffix}`);
}

export async function createAdminQuestion(payload) {
    return requestJson('/api/admin/questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
}

export async function updateAdminQuestion(questionId, payload) {
    return requestJson(`/api/admin/questions/${questionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
}

export async function deleteAdminQuestion(questionId) {
    return requestJson(`/api/admin/questions/${questionId}`, {
        method: 'DELETE',
    });
}

// ── Streaming chat ────────────────────────────────────────────────────────────

/**
 * Sends a POST /api/chat/stream request and consumes the SSE response.
 * @param {object}   body      - Request body (content, session_id, …)
 * @param {function} onDelta   - Called with each text chunk (string)
 * @param {function} onDone    - Called with the done event object {session_id, message_id, tools_used}
 * @param {function} onError   - Called with an error message string
 */
const TYPEWRITER_CHUNK_SIZE = 8;
const TYPEWRITER_DELAY_MS = 18;

export async function streamChatRequest(
    body,
    callbacksOrOnDelta,
    maybeOnDone,
    maybeOnError,
    options = {}
) {
    const callbacks =
        typeof callbacksOrOnDelta === 'object' && callbacksOrOnDelta !== null ?
        callbacksOrOnDelta : {
            onDelta: callbacksOrOnDelta,
            onDone: maybeOnDone,
            onError: maybeOnError,
        };
    const onDelta = typeof callbacks.onDelta === 'function' ? callbacks.onDelta : () => {};
    const onDone = typeof callbacks.onDone === 'function' ? callbacks.onDone : () => {};
    const onError = typeof callbacks.onError === 'function' ? callbacks.onError : () => {};
    const typewriterChunkSize = Math.max(
        1,
        Number(options.typewriterChunkSize || TYPEWRITER_CHUNK_SIZE)
    );
    const typewriterDelayMs = Math.max(
        0,
        Number(options.typewriterDelayMs !== undefined ? options.typewriterDelayMs : TYPEWRITER_DELAY_MS)
    );
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    let response;
    try {
        response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });
    } catch (_) {
        onError('无法连接后端服务，请确认后端已启动。');
        return;
    }

    if (response.status === 401) {
        clearAuthSession();
        if (typeof window !== 'undefined') window.location.href = '/login';
        return;
    }

    if (!response.ok) {
        let message = `请求失败（${response.status}）`;
        try {
            const data = await response.json();
            if (data && data.message) message = data.message;
        } catch (_) { /* ignore */ }
        onError(message);
        return;
    }

    if (!response.body || typeof response.body.getReader !== 'function') {
        onError('当前浏览器不支持流式读取，请更新浏览器后重试。');
        return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            // SSE events are separated by double-newline
            const parts = buffer.split('\n\n');
            const tail = parts.pop();
            buffer = tail !== undefined ? tail : '';

            for (const part of parts) {
                const shouldStop = await processSseBlock(part, {
                    onDelta,
                    onDone,
                    onError,
                    typewriterChunkSize,
                    typewriterDelayMs,
                });
                if (shouldStop) return;
            }
        }

        if (buffer.trim()) {
            await processSseBlock(buffer, {
                onDelta,
                onDone,
                onError,
                typewriterChunkSize,
                typewriterDelayMs,
            });
        }
    } catch (_) {
        onError('流式读取中断，请重试。');
    }
}

async function processSseBlock(part, handlers) {
    const line = part.trim();
    if (!line.startsWith('data:')) return false;

    const jsonStr = line.slice(5).trim();
    let event;
    try {
        event = JSON.parse(jsonStr);
    } catch (_) {
        return false;
    }

    if (event.type === 'delta') {
        await emitTypewriterDelta(String(event.content || ''), handlers);
        return false;
    }

    if (event.type === 'done') {
        handlers.onDone(event);
        return false;
    }

    if (event.type === 'error') {
        handlers.onError(String(event.message || '流式生成失败'));
        return true;
    }

    return false;
}

async function emitTypewriterDelta(content, handlers) {
    if (!content) return;

    for (let index = 0; index < content.length; index += handlers.typewriterChunkSize) {
        handlers.onDelta(content.slice(index, index + handlers.typewriterChunkSize));
        await wait(handlers.typewriterDelayMs);
    }
}

function wait(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

// ── Recommend endpoints ───────────────────────────────────────────────────────

export async function fetchRecommend() {
    return requestJson('/api/recommend');
}

export async function submitRecommendFeedback(id, status) {
    return requestJson('/api/recommend/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, status }),
    });
}
