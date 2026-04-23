from __future__ import annotations

import os
import unittest
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import bcrypt
import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.main import app


class AuthApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-auth') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_jwt_secret = os.environ.get('JWT_SECRET')
        database.DB_PATH = self._temp_dir / 'test_auth.db'
        os.environ['JWT_SECRET'] = 'test-secret-key-with-32-bytes-minimum'
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
        rmtree(self._temp_dir, ignore_errors=True)

    def test_register_returns_201_and_persists_hashed_password(self) -> None:
        response = self.client.post(
            '/api/register',
            json={
                'username': 'alice',
                'password': 'Passw0rd!',
                'grade': '高一',
                'subject': '数学',
            },
        )

        self.assertEqual(201, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual('ok', payload['message'])
        self.assertEqual('alice', payload['data']['username'])
        self.assertEqual('高一', payload['data']['grade'])
        self.assertEqual('数学', payload['data']['subject'])
        self.assertIn('created_at', payload['data'])
        self.assertNotIn('password_hash', payload['data'])

        connection = database.get_connection()
        try:
            row = connection.execute(
                """
                SELECT username, grade, subject, password_hash
                FROM users
                WHERE username = ?
                """,
                ('alice',),
            ).fetchone()
        finally:
            connection.close()

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual('alice', row['username'])
        self.assertNotEqual('Passw0rd!', row['password_hash'])
        self.assertTrue(
            bcrypt.checkpw('Passw0rd!'.encode(), str(row['password_hash']).encode())
        )

    def test_register_returns_409_when_username_exists(self) -> None:
        self._seed_user(username='alice', password='ExistingPass1!')

        response = self.client.post(
            '/api/register',
            json={
                'username': 'alice',
                'password': 'AnotherPass1!',
                'grade': '高二',
                'subject': '物理',
            },
        )

        self.assertEqual(409, response.status_code)
        self.assertEqual(
            {
                'success': False,
                'message': '用户名已存在',
                'error_code': 'USERNAME_EXISTS',
            },
            response.json(),
        )

    def test_login_returns_jwt_and_user_profile(self) -> None:
        user_id = self._seed_user(
            username='alice',
            password='Passw0rd!',
            grade='高一',
            subject='数学',
        )

        response = self.client.post(
            '/api/login',
            json={
                'username': 'alice',
                'password': 'Passw0rd!',
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual('ok', payload['message'])
        self.assertEqual('Bearer', payload['data']['token_type'])
        self.assertEqual(604800, payload['data']['expires_in'])
        self.assertEqual(user_id, payload['data']['user']['id'])
        self.assertEqual('alice', payload['data']['user']['username'])
        self.assertEqual('高一', payload['data']['user']['grade'])
        self.assertEqual('数学', payload['data']['user']['subject'])
        self.assertIn('created_at', payload['data']['user'])

        token = payload['data']['token']
        decoded = jwt.decode(
            token,
            'test-secret-key-with-32-bytes-minimum',
            algorithms=['HS256'],
        )
        self.assertEqual(user_id, decoded['user_id'])
        self.assertEqual('alice', decoded['username'])
        self.assertIn('iat', decoded)
        self.assertIn('exp', decoded)

    def test_login_returns_401_when_password_is_wrong(self) -> None:
        self._seed_user(username='alice', password='Passw0rd!')

        response = self.client.post(
            '/api/login',
            json={
                'username': 'alice',
                'password': 'WrongPass1!',
            },
        )

        self.assertEqual(401, response.status_code)
        self.assertEqual(
            {
                'success': False,
                'message': '用户名或密码错误',
                'error_code': 'INVALID_CREDENTIALS',
            },
            response.json(),
        )

    def test_register_returns_400_when_required_field_is_missing(self) -> None:
        response = self.client.post(
            '/api/register',
            json={
                'username': 'alice',
                'grade': '高一',
                'subject': '数学',
            },
        )

        self.assertEqual(400, response.status_code)
        payload = response.json()
        self.assertFalse(payload['success'])
        self.assertEqual('请求字段缺失或格式错误', payload['message'])
        self.assertEqual('INVALID_REQUEST', payload['error_code'])
        self.assertIn('details', payload)

    # ── GET /api/auth/me ───────────────────────────────────────────────────────

    def test_get_me_returns_200_and_user_profile_with_valid_token(self) -> None:
        user_id = self._seed_user(username='alice', password='Passw0rd!')
        token = self._make_token(user_id, 'alice')

        response = self.client.get(
            '/api/auth/me',
            headers={'Authorization': f'Bearer {token}'},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(user_id, payload['data']['id'])
        self.assertEqual('alice', payload['data']['username'])

    def test_get_me_returns_unified_401_with_invalid_token(self) -> None:
        """A forged / tampered token must trigger the unified 401 error format."""
        response = self.client.get(
            '/api/auth/me',
            headers={'Authorization': 'Bearer this.is.not.a.valid.jwt'},
        )

        self.assertEqual(401, response.status_code)
        body = response.json()
        self.assertFalse(body['success'])
        self.assertEqual('UNAUTHORIZED', body['error_code'])
        # Must NOT fall through to FastAPI's bare {"detail": ...}
        self.assertNotIn('detail', body)

    def test_get_me_returns_unified_401_without_token(self) -> None:
        """No Authorization header must return unified 401, not bare detail."""
        response = self.client.get('/api/auth/me')

        self.assertEqual(401, response.status_code)
        body = response.json()
        self.assertFalse(body['success'])
        self.assertEqual('UNAUTHORIZED', body['error_code'])
        self.assertNotIn('detail', body)

    def _make_token(self, user_id: int, username: str) -> str:
        import time
        return jwt.encode(
            {
                'user_id': user_id,
                'username': username,
                'exp': int(time.time()) + 3600,
            },
            'test-secret-key-with-32-bytes-minimum',
            algorithm='HS256',
        )

    def _seed_user(
        self,
        username: str,
        password: str,
        grade: str = '高一',
        subject: str = '数学',
    ) -> int:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        connection = database.get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_hash, grade, subject)
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, grade, subject),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()

