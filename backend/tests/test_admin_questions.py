from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import bcrypt
import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.main import app


_JWT_SECRET = 'test-secret-key-with-32-bytes-minimum'
_JWT_ALGORITHM = 'HS256'
_ADMIN_ID = 9999
_NORMAL_USER_ID = 81


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


class AdminQuestionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-admin-questions') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_jwt_secret = os.environ.get('JWT_SECRET')
        database.DB_PATH = self._temp_dir / 'test_admin_questions.db'
        os.environ['JWT_SECRET'] = _JWT_SECRET
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

    def test_login_response_contains_is_admin(self) -> None:
        self._seed_user(91, 'site_admin', 'Passw0rd!', is_admin=True)

        response = self.client.post(
            '/api/login',
            json={'username': 'site_admin', 'password': 'Passw0rd!'},
        )

        self.assertEqual(200, response.status_code)
        user = response.json()['data']['user']
        self.assertTrue(user['is_admin'])

    def test_toggle_admin_requires_admin_and_toggles_status(self) -> None:
        self._seed_user(_NORMAL_USER_ID, 'normal_user')

        no_token = self.client.put(f'/api/admin/users/{_NORMAL_USER_ID}/admin')
        normal = self.client.put(
            f'/api/admin/users/{_NORMAL_USER_ID}/admin',
            headers=_auth_headers(_NORMAL_USER_ID, 'normal_user'),
        )
        promoted = self.client.put(
            f'/api/admin/users/{_NORMAL_USER_ID}/admin',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )
        demoted = self.client.put(
            f'/api/admin/users/{_NORMAL_USER_ID}/admin',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(401, no_token.status_code)
        self.assertEqual(403, normal.status_code)
        self.assertEqual(200, promoted.status_code)
        self.assertTrue(promoted.json()['data']['is_admin'])
        self.assertEqual(200, demoted.status_code)
        self.assertFalse(demoted.json()['data']['is_admin'])

    def test_toggle_admin_rejects_self_toggle(self) -> None:
        response = self.client.put(
            f'/api/admin/users/{_ADMIN_ID}/admin',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(400, response.status_code)
        self.assertFalse(response.json()['success'])

    def test_get_admin_questions_requires_admin_and_supports_filters(self) -> None:
        self._seed_user(_NORMAL_USER_ID, 'normal_user')
        self._seed_question(1, 'Math', 'Quadratic', 'Find the vertex.', 'A')
        self._seed_question(2, 'Math', 'Linear', 'Find the slope.', 'B')
        self._seed_question(3, 'Physics', 'Force', 'Find the net force.', 'C')

        no_token = self.client.get('/api/admin/questions')
        normal = self.client.get(
            '/api/admin/questions',
            headers=_auth_headers(_NORMAL_USER_ID, 'normal_user'),
        )
        admin = self.client.get(
            '/api/admin/questions?subject=Math&topic=quad',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(401, no_token.status_code)
        self.assertEqual(403, normal.status_code)
        self.assertEqual(200, admin.status_code)
        items = admin.json()['data']['items']
        self.assertEqual(1, len(items))
        self.assertEqual(1, items[0]['id'])
        self.assertEqual('A. Option A\nB. Option B\nC. Option C\nD. Option D', items[0]['options'])

    def test_post_admin_questions_returns_422_when_required_field_missing(self) -> None:
        response = self.client.post(
            '/api/admin/questions',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
            json={
                'subject': 'Math',
                'topic': 'Quadratic',
                'options': 'A. One\nB. Two\nC. Three\nD. Four',
                'answer': 'A',
            },
        )

        self.assertEqual(422, response.status_code)
        self.assertFalse(response.json()['success'])

    def test_post_admin_questions_creates_question_and_splits_options(self) -> None:
        response = self.client.post(
            '/api/admin/questions',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
            json={
                'subject': 'Math',
                'topic': 'Quadratic',
                'question': 'What is the vertex of y = x^2?',
                'options': 'A. (0, 0)\nB. (1, 0)\nC. (0, 1)\nD. (1, 1)',
                'answer': 'A',
            },
        )

        self.assertEqual(201, response.status_code)
        item = response.json()['data']
        self.assertEqual('manual', item['source'])
        self.assertEqual('A. (0, 0)\nB. (1, 0)\nC. (0, 1)\nD. (1, 1)', item['options'])

        row = self._fetch_question(item['id'])
        self.assertEqual('(0, 0)', row['option_a'])
        self.assertEqual('(1, 1)', row['option_d'])

    def test_put_admin_questions_updates_visible_fields(self) -> None:
        self._seed_question(11, 'Math', 'Linear', 'Old question', 'A')

        response = self.client.put(
            '/api/admin/questions/11',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
            json={
                'subject': 'Physics',
                'topic': 'Force',
                'question': 'Updated question',
                'options': 'A. Alpha\nB. Beta\nC. Gamma\nD. Delta',
                'answer': 'D',
            },
        )
        listed = self.client.get(
            '/api/admin/questions?subject=Physics&topic=Force',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(200, response.status_code)
        item = listed.json()['data']['items'][0]
        self.assertEqual('Updated question', item['question'])
        self.assertEqual('D', item['answer'])
        self.assertEqual('A. Alpha\nB. Beta\nC. Gamma\nD. Delta', item['options'])

    def test_delete_admin_questions_deletes_and_second_delete_returns_404(self) -> None:
        self._seed_question(21, 'Math', 'Linear', 'Delete me', 'A')

        first = self.client.delete(
            '/api/admin/questions/21',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )
        second = self.client.delete(
            '/api/admin/questions/21',
            headers=_auth_headers(_ADMIN_ID, 'admin'),
        )

        self.assertEqual(200, first.status_code)
        self.assertIsNone(self._fetch_question(21))
        self.assertEqual(404, second.status_code)

    def _seed_user(
        self,
        user_id: int,
        username: str,
        password: str = 'dev-only-hash',
        is_admin: bool = False,
    ) -> None:
        password_hash = (
            bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if password != 'dev-only-hash'
            else password
        )
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT OR REPLACE INTO users (
                    id, username, password_hash, grade, subject, is_admin
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, password_hash, 'Grade 1', 'Math', int(is_admin)),
            )
            connection.commit()
        finally:
            connection.close()

    def _seed_question(
        self,
        question_id: int,
        subject: str,
        topic: str,
        question: str,
        answer: str,
    ) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT INTO question_bank (
                    id, subject, topic, question,
                    option_a, option_b, option_c, option_d,
                    answer, explanation, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    subject,
                    topic,
                    question,
                    'Option A',
                    'Option B',
                    'Option C',
                    'Option D',
                    answer,
                    '',
                    'test',
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def _fetch_question(self, question_id: int):
        connection = database.get_connection()
        try:
            return connection.execute(
                """
                SELECT *
                FROM question_bank
                WHERE id = ?
                """,
                (question_id,),
            ).fetchone()
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
