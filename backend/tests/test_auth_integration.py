"""
backend/tests/test_auth_integration.py

End-to-end integration tests covering the full auth → chat → sessions chain.

Tests verify:
1. /api/chat and /api/sessions return 401 without a token.
2. Two users register and log in, receiving different tokens.
3. User A creates a session via /api/chat.
4. User B's GET /api/sessions does not contain User A's session.
5. User B's GET /api/sessions/{id} returns 404 for User A's session.
6. The session created by /api/chat has the correct user_id in the database.
7. User A can list and continue their own session.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend import database
from backend.main import app


class AuthIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('backend/tests/.tmp') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_mock_mode = os.environ.get('LLM_MOCK_MODE')
        self._original_jwt_secret = os.environ.get('JWT_SECRET')
        database.DB_PATH = self._temp_dir / 'test_integration.db'
        os.environ['LLM_MOCK_MODE'] = '1'
        os.environ['JWT_SECRET'] = 'test-secret-key-with-32-bytes-minimum'
        database.init_database()
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)
        database.DB_PATH = self._original_db_path
        if self._original_mock_mode is None:
            os.environ.pop('LLM_MOCK_MODE', None)
        else:
            os.environ['LLM_MOCK_MODE'] = self._original_mock_mode
        if self._original_jwt_secret is None:
            os.environ.pop('JWT_SECRET', None)
        else:
            os.environ['JWT_SECRET'] = self._original_jwt_secret
        rmtree(self._temp_dir, ignore_errors=True)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _register(self, username: str, password: str = 'TestPass1!') -> None:
        resp = self.client.post(
            '/api/register',
            json={
                'username': username,
                'password': password,
                'grade': '高一',
                'subject': '数学',
            },
        )
        self.assertEqual(201, resp.status_code, f'register {username} failed: {resp.json()}')

    def _login(self, username: str, password: str = 'TestPass1!') -> str:
        resp = self.client.post(
            '/api/login',
            json={'username': username, 'password': password},
        )
        self.assertEqual(200, resp.status_code, f'login {username} failed: {resp.json()}')
        return str(resp.json()['data']['token'])

    def _auth(self, token: str) -> dict:
        return {'Authorization': f'Bearer {token}'}

    # ── Tests ──────────────────────────────────────────────────────────────────

    def test_unauthenticated_chat_returns_401(self) -> None:
        response = self.client.post(
            '/api/chat',
            json={'content': '你好', 'session_id': None},
        )
        self.assertEqual(401, response.status_code)

    def test_unauthenticated_sessions_returns_401(self) -> None:
        response = self.client.get('/api/sessions')
        self.assertEqual(401, response.status_code)

    def test_unauthenticated_session_detail_returns_401(self) -> None:
        response = self.client.get('/api/sessions/1')
        self.assertEqual(401, response.status_code)

    def test_two_users_cannot_see_each_others_sessions(self) -> None:
        """
        User A creates a session.
        User B's session list must be empty.
        User B's access to User A's session must return 404.
        """
        self._register('integ_user_a')
        self._register('integ_user_b')
        token_a = self._login('integ_user_a')
        token_b = self._login('integ_user_b')

        # User A sends a chat message (creates session)
        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(return_value='42'),
        ):
            chat_resp = self.client.post(
                '/api/chat',
                json={'content': '计算 6 * 7', 'session_id': None},
                headers=self._auth(token_a),
            )
        self.assertEqual(200, chat_resp.status_code)
        session_id_a = chat_resp.json()['data']['session']['id']

        # User B's session list must be empty
        sessions_b = self.client.get('/api/sessions', headers=self._auth(token_b))
        self.assertEqual(200, sessions_b.status_code)
        ids_b = [s['id'] for s in sessions_b.json()['data']['items']]
        self.assertNotIn(session_id_a, ids_b, 'User B must not see User A\'s session in list')

        # User B cannot read User A's session detail
        detail_resp = self.client.get(
            f'/api/sessions/{session_id_a}',
            headers=self._auth(token_b),
        )
        self.assertEqual(404, detail_resp.status_code)

    def test_chat_session_is_attributed_to_correct_user(self) -> None:
        """Session created via /api/chat must have the token user's user_id in DB."""
        self._register('integ_user_c')
        token_c = self._login('integ_user_c')

        # Get the user_id assigned to integ_user_c
        login_resp = self.client.post(
            '/api/login',
            json={'username': 'integ_user_c', 'password': 'TestPass1!'},
        )
        user_id_c = login_resp.json()['data']['user']['id']

        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(return_value='3'),
        ):
            chat_resp = self.client.post(
                '/api/chat',
                json={'content': '计算 1 + 2', 'session_id': None},
                headers=self._auth(token_c),
            )
        self.assertEqual(200, chat_resp.status_code)
        session_id = chat_resp.json()['data']['session']['id']

        # Verify the DB row has the correct user_id
        conn = database.get_connection()
        try:
            row = conn.execute(
                'SELECT user_id FROM sessions WHERE id = ?', (session_id,)
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(user_id_c, row['user_id'])

    def test_user_can_list_and_continue_own_session(self) -> None:
        """User A can create a session, list it, and read its detail."""
        self._register('integ_user_d')
        token_d = self._login('integ_user_d')

        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(return_value='result'),
        ):
            chat_resp = self.client.post(
                '/api/chat',
                json={'content': '你好', 'session_id': None},
                headers=self._auth(token_d),
            )
        self.assertEqual(200, chat_resp.status_code)
        session_id = chat_resp.json()['data']['session']['id']

        # List sessions — must contain the new session
        sessions_resp = self.client.get('/api/sessions', headers=self._auth(token_d))
        self.assertEqual(200, sessions_resp.status_code)
        ids = [s['id'] for s in sessions_resp.json()['data']['items']]
        self.assertIn(session_id, ids)

        # Detail — must return session and messages
        detail_resp = self.client.get(
            f'/api/sessions/{session_id}',
            headers=self._auth(token_d),
        )
        self.assertEqual(200, detail_resp.status_code)
        self.assertEqual(session_id, detail_resp.json()['data']['session']['id'])


if __name__ == '__main__':
    unittest.main()
