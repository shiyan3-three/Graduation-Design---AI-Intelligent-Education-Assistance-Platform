from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.main import app


_JWT_SECRET = 'test-secret-key-with-32-bytes-minimum'
_JWT_ALGORITHM = 'HS256'
_ADMIN_ID = 9999
_NORMAL_USER_ID = 71


def _make_token(user_id: int, username: str) -> str:
    return jwt.encode(
        {
            'user_id': user_id,
            'username': username,
            'exp': int(time.time()) + 3600,
        },
        _JWT_SECRET,
        algorithm=_JWT_ALGORITHM,
    )


def _auth_headers(user_id: int, username: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {_make_token(user_id, username)}'}


class AdminApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-admin') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_jwt_secret = os.environ.get('JWT_SECRET')
        self._original_admin_usernames = os.environ.get('ADMIN_USERNAMES')
        self._original_admin_username = os.environ.get('ADMIN_USERNAME')
        database.DB_PATH = self._temp_dir / 'test_admin.db'
        os.environ['JWT_SECRET'] = _JWT_SECRET
        os.environ.pop('ADMIN_USERNAMES', None)
        os.environ.pop('ADMIN_USERNAME', None)
        database.init_database()
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)
        database.DB_PATH = self._original_db_path
        if self._original_jwt_secret is None:
            os.environ.pop('JWT_SECRET', None)
        else:
            os.environ['JWT_SECRET'] = self._original_jwt_secret
        if self._original_admin_usernames is None:
            os.environ.pop('ADMIN_USERNAMES', None)
        else:
            os.environ['ADMIN_USERNAMES'] = self._original_admin_usernames
        if self._original_admin_username is None:
            os.environ.pop('ADMIN_USERNAME', None)
        else:
            os.environ['ADMIN_USERNAME'] = self._original_admin_username
        rmtree(self._temp_dir, ignore_errors=True)

    def test_get_admin_users_without_token_returns_401(self) -> None:
        response = self.client.get('/api/admin/users')

        self.assertEqual(401, response.status_code)
        self.assertEqual('UNAUTHORIZED', response.json()['error_code'])

    def test_get_admin_users_with_normal_user_token_returns_403(self) -> None:
        response = self.client.get(
            '/api/admin/users',
            headers=_auth_headers(1, 'demo_user'),
        )

        self.assertEqual(403, response.status_code)
        self.assertFalse(response.json()['success'])

    def test_get_admin_users_with_admin_token_returns_all_users(self) -> None:
        self._seed_user(_NORMAL_USER_ID)

        response = self.client.get(
            '/api/admin/users',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        items = payload['data']['items']
        users_by_id = {item['id']: item for item in items}
        self.assertIn(1, users_by_id)
        self.assertIn(_ADMIN_ID, users_by_id)
        self.assertIn(_NORMAL_USER_ID, users_by_id)
        self.assertFalse(users_by_id[1]['is_admin'])
        self.assertTrue(users_by_id[_ADMIN_ID]['is_admin'])
        self.assertEqual(
            ['id', 'username', 'grade', 'subject', 'created_at', 'is_admin'],
            list(items[0].keys()),
        )

    def test_get_admin_stats_with_admin_token_returns_system_counts(self) -> None:
        self._seed_user(_NORMAL_USER_ID)
        self._seed_activity(_NORMAL_USER_ID)

        response = self.client.get(
            '/api/admin/stats',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(200, response.status_code)
        stats = response.json()['data']
        self.assertEqual(
            {
                'total_users': 3,
                'total_sessions': 1,
                'total_messages': 2,
                'total_recommendations': 1,
            },
            stats,
        )

    def test_delete_admin_user_removes_normal_user(self) -> None:
        self._seed_user(_NORMAL_USER_ID)
        self._seed_activity(_NORMAL_USER_ID)

        response = self.client.delete(
            f'/api/admin/users/{_NORMAL_USER_ID}',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()['success'])
        self.assertIsNone(self._fetch_user(_NORMAL_USER_ID))
        self.assertEqual(0, self._count_rows('sessions'))
        self.assertEqual(0, self._count_rows('messages'))
        self.assertEqual(0, self._count_rows('recommendation_items'))

    def test_delete_admin_user_rejects_self_delete(self) -> None:
        response = self.client.delete(
            f'/api/admin/users/{_ADMIN_ID}',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(400, response.status_code)
        self.assertFalse(response.json()['success'])
        self.assertIsNotNone(self._fetch_user(_ADMIN_ID))

    def test_init_database_promotes_configured_admin_usernames(self) -> None:
        self._seed_named_user(201, 'admin1')
        self._seed_named_user(202, 'teacher_admin')
        os.environ['ADMIN_USERNAMES'] = 'admin1, teacher_admin, missing_admin'

        database.init_database()

        self.assertTrue(self._fetch_user_by_username('admin1')['is_admin'])
        self.assertTrue(self._fetch_user_by_username('teacher_admin')['is_admin'])
        self.assertIsNone(self._fetch_user_by_username('missing_admin'))

    def _seed_user(self, user_id: int) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT OR IGNORE INTO users (id, username, password_hash, grade, subject)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, f'user_{user_id}', 'dev-only-hash', 'Grade 1', 'Math'),
            )
            connection.commit()
        finally:
            connection.close()

    def _seed_named_user(self, user_id: int, username: str) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT OR IGNORE INTO users (
                    id, username, password_hash, grade, subject, is_admin
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, 'dev-only-hash', 'Grade 1', 'Math', 0),
            )
            connection.commit()
        finally:
            connection.close()

    def _seed_activity(self, user_id: int) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT INTO sessions (id, user_id, title)
                VALUES (?, ?, ?)
                """,
                (1001, user_id, 'admin stats session'),
            )
            connection.execute(
                """
                INSERT INTO messages (id, session_id, sequence_no, role, content)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
                """,
                (
                    2001,
                    1001,
                    1,
                    'user',
                    'question',
                    2002,
                    1001,
                    2,
                    'assistant',
                    'answer',
                ),
            )
            connection.execute(
                """
                INSERT INTO recommendation_items (
                    id, user_id, recommended_topic, question_payload, source, status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (3001, user_id, 'quadratic function', '{}', 'question_tool', 'pending'),
            )
            connection.commit()
        finally:
            connection.close()

    def _fetch_user(self, user_id: int):
        connection = database.get_connection()
        try:
            return connection.execute(
                """
                SELECT id, username, is_admin
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        finally:
            connection.close()

    def _fetch_user_by_username(self, username: str):
        connection = database.get_connection()
        try:
            return connection.execute(
                """
                SELECT id, username, is_admin
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        finally:
            connection.close()

    def _count_rows(self, table: str) -> int:
        if table not in {'sessions', 'messages', 'recommendation_items'}:
            raise ValueError(f'Unexpected table name: {table}')
        connection = database.get_connection()
        try:
            return int(connection.execute(f'SELECT COUNT(*) AS count FROM {table}').fetchone()['count'])
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
