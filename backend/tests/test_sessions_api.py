"""
backend/tests/test_sessions_api.py

Tests for GET /api/sessions and GET /api/sessions/{id}.

All endpoints now require JWT authentication.  Each test helper generates a
short-lived token for the seed user via the same secret the backend uses, so
requests are authenticated without touching the login flow.

NOTE: user_id=1 is reserved by database.ensure_test_user (demo_user).
      Tests that insert new users use id=11 / 12 to avoid collisions.
"""
from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from shutil import rmtree
from typing import Optional
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.main import app

_JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')
_JWT_ALGO = 'HS256'

# user_id=1 is reserved by ensure_test_user; use 11/12 for fresh inserts.
_USER_A_ID = 11
_USER_B_ID = 12


def _make_token(user_id: int, username: str) -> str:
    return jwt.encode(
        {
            'user_id': user_id,
            'username': username,
            'exp': int(time.time()) + 3600,
        },
        _JWT_SECRET,
        algorithm=_JWT_ALGO,
    )


def _auth_headers(user_id: int, username: str) -> dict:
    return {'Authorization': f'Bearer {_make_token(user_id, username)}'}


class SessionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('backend/tests/.tmp') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        database.DB_PATH = self._temp_dir / 'test_sessions.db'
        database.init_database()
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)
        database.DB_PATH = self._original_db_path
        rmtree(self._temp_dir, ignore_errors=True)

    # ── GET /api/sessions ──────────────────────────────────────────────────────

    def test_get_sessions_requires_auth(self) -> None:
        response = self.client.get('/api/sessions')
        self.assertEqual(401, response.status_code)

    def test_get_sessions_returns_unified_error_format_when_unauthenticated(self) -> None:
        """
        Without a token, /api/sessions must return the project's unified error
        envelope — NOT FastAPI's default {"detail": "..."} — so that all clients
        can rely on a consistent response shape.
        """
        response = self.client.get('/api/sessions')

        self.assertEqual(401, response.status_code)
        body = response.json()
        # Must use unified envelope
        self.assertFalse(body['success'])
        self.assertIn('error_code', body, 'unified format must include error_code')
        self.assertEqual('UNAUTHORIZED', body['error_code'])
        self.assertIn('message', body, 'unified format must include message')
        # Must NOT be FastAPI's bare detail format
        self.assertNotIn('detail', body, 'response must NOT use FastAPI default {detail} format')

    def test_get_session_detail_returns_unified_error_format_when_unauthenticated(self) -> None:
        """Same unified-format contract for the session detail endpoint."""
        response = self.client.get('/api/sessions/1')

        self.assertEqual(401, response.status_code)
        body = response.json()
        self.assertFalse(body['success'])
        self.assertEqual('UNAUTHORIZED', body['error_code'])
        self.assertNotIn('detail', body)


    def test_get_sessions_returns_current_user_sessions_sorted_by_updated_at_desc(self) -> None:
        self._seed_user(user_id=_USER_A_ID)
        self._seed_session(session_id=1, user_id=_USER_A_ID, title='较早会话', updated_at='2026-03-24 09:00:00')
        self._seed_session(session_id=2, user_id=_USER_A_ID, title='较新会话', updated_at='2026-03-24 10:00:00')
        self._seed_user(user_id=_USER_B_ID)
        self._seed_session(session_id=3, user_id=_USER_B_ID, title='其他用户会话', updated_at='2026-03-24 11:00:00')

        response = self.client.get(
            '/api/sessions',
            headers=_auth_headers(_USER_A_ID, f'user_{_USER_A_ID}'),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual('ok', payload['message'])
        # Only User A's sessions; sorted newest-first
        self.assertEqual([2, 1], [item['id'] for item in payload['data']['items']])
        self.assertEqual(
            ['id', 'user_id', 'title', 'created_at', 'updated_at'],
            list(payload['data']['items'][0].keys()),
        )

    def test_get_sessions_hides_other_users_sessions(self) -> None:
        """User B must not see User A's sessions."""
        self._seed_user(user_id=_USER_A_ID)
        self._seed_session(session_id=10, user_id=_USER_A_ID, title='A的会话', updated_at='2026-03-24 09:00:00')
        self._seed_user(user_id=_USER_B_ID)

        response = self.client.get(
            '/api/sessions',
            headers=_auth_headers(_USER_B_ID, f'user_{_USER_B_ID}'),
        )

        self.assertEqual(200, response.status_code)
        items = response.json()['data']['items']
        self.assertEqual([], items, 'User B must see an empty list')

    # ── GET /api/sessions/{id} ─────────────────────────────────────────────────

    def test_get_session_detail_requires_auth(self) -> None:
        response = self.client.get('/api/sessions/999')
        self.assertEqual(401, response.status_code)

    def test_get_session_detail_returns_session_and_messages_sorted_by_sequence_no(self) -> None:
        self._seed_user(user_id=_USER_A_ID)
        self._seed_session(session_id=10, user_id=_USER_A_ID, title='历史会话', updated_at='2026-03-24 12:00:00')
        self._seed_message(
            message_id=102, session_id=10, sequence_no=2, role='assistant',
            content='第二条消息', tools_used=None,
        )
        self._seed_message(
            message_id=101, session_id=10, sequence_no=1, role='user',
            content='第一条消息',
            tools_used='[{"tool_name":"calculator_tool","status":"success"}]',
        )

        response = self.client.get(
            '/api/sessions/10',
            headers=_auth_headers(_USER_A_ID, f'user_{_USER_A_ID}'),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(10, payload['data']['session']['id'])
        self.assertEqual([1, 2], [item['sequence_no'] for item in payload['data']['messages']])
        self.assertEqual(
            ['id', 'session_id', 'sequence_no', 'role', 'content', 'tools_used', 'created_at'],
            list(payload['data']['messages'][0].keys()),
        )
        self.assertEqual('calculator_tool', payload['data']['messages'][0]['tools_used'][0]['tool_name'])

    def test_get_session_detail_returns_404_when_session_belongs_to_other_user(self) -> None:
        """User B cannot read User A's session detail."""
        self._seed_user(user_id=_USER_A_ID)
        self._seed_session(session_id=10, user_id=_USER_A_ID, title='A的会话', updated_at='2026-03-24 12:00:00')
        self._seed_user(user_id=_USER_B_ID)

        response = self.client.get(
            '/api/sessions/10',
            headers=_auth_headers(_USER_B_ID, f'user_{_USER_B_ID}'),
        )

        self.assertEqual(404, response.status_code)
        self.assertFalse(response.json()['success'])

    def test_get_session_detail_returns_404_when_session_does_not_exist(self) -> None:
        self._seed_user(user_id=_USER_A_ID)
        response = self.client.get(
            '/api/sessions/999',
            headers=_auth_headers(_USER_A_ID, f'user_{_USER_A_ID}'),
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                'success': False,
                'message': '会话不存在或不属于当前用户',
                'error_code': 'SESSION_NOT_FOUND',
            },
            response.json(),
        )

    # ── Seed helpers ───────────────────────────────────────────────────────────

    def _seed_user(self, user_id: int) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT OR IGNORE INTO users (id, username, password_hash, grade, subject)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, f'user_{user_id}', 'dev-only-hash', '高一', '数学'),
            )
            connection.commit()
        finally:
            connection.close()

    def _seed_session(
        self,
        session_id: int,
        user_id: int,
        title: str,
        updated_at: str,
        created_at: str = '2026-03-24 08:00:00',
    ) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT INTO sessions (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, title, created_at, updated_at),
            )
            connection.commit()
        finally:
            connection.close()

    def _seed_message(
        self,
        message_id: int,
        session_id: int,
        sequence_no: int,
        role: str,
        content: str,
        tools_used: Optional[str],
        created_at: str = '2026-03-24 08:00:00',
    ) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT INTO messages (id, session_id, sequence_no, role, content, tools_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, session_id, sequence_no, role, content, tools_used, created_at),
            )
            connection.commit()
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
