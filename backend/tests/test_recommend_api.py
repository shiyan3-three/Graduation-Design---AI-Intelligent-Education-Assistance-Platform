from __future__ import annotations

import json
import os
import time
import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import Mock, patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.main import app


_JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')
_JWT_ALGORITHM = 'HS256'
_USER_ID = 41
_OTHER_USER_ID = 42


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


def _question_payload(topic: str) -> dict:
    return {
        'question': f'{topic} 的基础练习题是（  ）',
        'options': {
            'A': '选项 A',
            'B': '选项 B',
            'C': '选项 C',
            'D': '选项 D',
        },
        'answer': 'A',
        'explanation': f'{topic} 的解析。',
        'source': 'question_tool',
    }


class RecommendApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-recommend') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        database.DB_PATH = self._temp_dir / 'test_recommend.db'
        database.init_database()
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)
        database.DB_PATH = self._original_db_path
        rmtree(self._temp_dir, ignore_errors=True)

    def test_get_recommend_without_token_returns_401(self) -> None:
        response = self.client.get('/api/recommend')

        self.assertEqual(401, response.status_code)
        payload = response.json()
        self.assertFalse(payload['success'])
        self.assertEqual('UNAUTHORIZED', payload['error_code'])

    def test_get_recommend_returns_empty_items_when_user_has_no_tags(self) -> None:
        self._seed_user(_USER_ID)

        response = self.client.get(
            '/api/recommend',
            headers=_auth_headers(_USER_ID, 'user_41'),
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {'success': True, 'message': 'ok', 'data': {'items': []}},
            response.json(),
        )

    def test_get_recommend_generates_questions_for_top3_tags_and_persists_pending(
        self,
    ) -> None:
        self._seed_user(_USER_ID)
        self._seed_user(_OTHER_USER_ID)
        self._seed_tagged_messages(
            _USER_ID,
            [
                '二次函数',
                '二次函数',
                '二次函数',
                '牛顿第二定律',
                '牛顿第二定律',
                '光合作用',
            ],
        )
        self._seed_tagged_messages(_OTHER_USER_ID, ['不应推荐'])

        def fake_question_tool(topic: str) -> str:
            return json.dumps(_question_payload(topic), ensure_ascii=False)

        with patch(
            'backend.routers.recommend.question_tool',
            Mock(side_effect=fake_question_tool),
        ) as question_tool_mock:
            response = self.client.get(
                '/api/recommend',
                headers=_auth_headers(_USER_ID, 'user_41'),
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        items = payload['data']['items']
        self.assertEqual(3, len(items))
        self.assertEqual(
            ['二次函数', '牛顿第二定律', '光合作用'],
            [item['recommended_topic'] for item in items],
        )
        self.assertEqual(
            ['二次函数', '牛顿第二定律', '光合作用'],
            [call.args[0] for call in question_tool_mock.call_args_list],
        )
        for item in items:
            self.assertEqual('question_tool', item['source'])
            self.assertEqual('pending', item['status'])
            self.assertIsNone(item['feedback_at'])
            self.assertIsInstance(item['question_payload'], dict)
            self.assertIsInstance(item['question_payload']['options'], dict)

        rows = self._fetch_recommendation_rows(_USER_ID)
        self.assertEqual(3, len(rows))
        self.assertTrue(all(row['status'] == 'pending' for row in rows))
        self.assertIsInstance(json.loads(rows[0]['question_payload']), dict)

    def test_get_recommend_reuses_existing_pending_without_calling_question_tool(
        self,
    ) -> None:
        self._seed_user(_USER_ID)
        self._seed_tagged_messages(_USER_ID, ['二次函数', '二次函数'])
        existing_id = self._seed_recommendation(_USER_ID, '二次函数')

        with patch('backend.routers.recommend.question_tool') as question_tool_mock:
            response = self.client.get(
                '/api/recommend',
                headers=_auth_headers(_USER_ID, 'user_41'),
            )

        self.assertEqual(200, response.status_code)
        question_tool_mock.assert_not_called()
        items = response.json()['data']['items']
        self.assertEqual(1, len(items))
        self.assertEqual(existing_id, items[0]['id'])
        self.assertEqual('二次函数', items[0]['recommended_topic'])
        self.assertIsInstance(items[0]['question_payload'], dict)

    def test_get_recommend_skips_failed_question_tool_result(self) -> None:
        self._seed_user(_USER_ID)
        self._seed_tagged_messages(_USER_ID, ['二次函数', '二次函数', '光合作用'])

        with patch(
            'backend.routers.recommend.question_tool',
            Mock(
                side_effect=[
                    '出题错误：provider unavailable',
                    json.dumps(_question_payload('光合作用'), ensure_ascii=False),
                ]
            ),
        ):
            response = self.client.get(
                '/api/recommend',
                headers=_auth_headers(_USER_ID, 'user_41'),
            )

        self.assertEqual(200, response.status_code)
        items = response.json()['data']['items']
        self.assertEqual(1, len(items))
        self.assertEqual('光合作用', items[0]['recommended_topic'])
        self.assertEqual(1, len(self._fetch_recommendation_rows(_USER_ID)))

    def test_post_feedback_marks_pending_recommendation_completed(self) -> None:
        self._seed_user(_USER_ID)
        item_id = self._seed_recommendation(_USER_ID, '二次函数')

        response = self.client.post(
            '/api/recommend/feedback',
            json={'id': item_id, 'status': 'completed'},
            headers=_auth_headers(_USER_ID, 'user_41'),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        item = payload['data']
        self.assertEqual(item_id, item['id'])
        self.assertEqual('completed', item['status'])
        self.assertIsNotNone(item['feedback_at'])
        self.assertIsInstance(item['question_payload'], dict)
        self.assertIsInstance(item['question_payload']['options'], dict)

        row = self._fetch_recommendation_row(item_id)
        self.assertEqual('completed', row['status'])
        self.assertIsNotNone(row['feedback_at'])

    def test_post_feedback_marks_pending_recommendation_skipped(self) -> None:
        self._seed_user(_USER_ID)
        item_id = self._seed_recommendation(_USER_ID, '光合作用')

        response = self.client.post(
            '/api/recommend/feedback',
            json={'id': item_id, 'status': 'skipped'},
            headers=_auth_headers(_USER_ID, 'user_41'),
        )

        self.assertEqual(200, response.status_code)
        item = response.json()['data']
        self.assertEqual('skipped', item['status'])
        self.assertIsNotNone(item['feedback_at'])
        self.assertEqual('skipped', self._fetch_recommendation_row(item_id)['status'])

    def test_post_feedback_returns_409_when_recommendation_already_completed(
        self,
    ) -> None:
        self._seed_user(_USER_ID)
        item_id = self._seed_recommendation(_USER_ID, '二次函数', status='completed')

        response = self.client.post(
            '/api/recommend/feedback',
            json={'id': item_id, 'status': 'skipped'},
            headers=_auth_headers(_USER_ID, 'user_41'),
        )

        self.assertEqual(409, response.status_code)
        payload = response.json()
        self.assertFalse(payload['success'])
        self.assertEqual('RECOMMENDATION_ALREADY_COMPLETED', payload['error_code'])

    def test_post_feedback_returns_404_for_missing_or_foreign_recommendation(
        self,
    ) -> None:
        self._seed_user(_USER_ID)
        self._seed_user(_OTHER_USER_ID)
        foreign_item_id = self._seed_recommendation(_OTHER_USER_ID, '牛顿第二定律')

        missing_response = self.client.post(
            '/api/recommend/feedback',
            json={'id': 999999, 'status': 'completed'},
            headers=_auth_headers(_USER_ID, 'user_41'),
        )
        foreign_response = self.client.post(
            '/api/recommend/feedback',
            json={'id': foreign_item_id, 'status': 'completed'},
            headers=_auth_headers(_USER_ID, 'user_41'),
        )

        self.assertEqual(404, missing_response.status_code)
        self.assertEqual(404, foreign_response.status_code)
        self.assertEqual('RECOMMENDATION_NOT_FOUND', missing_response.json()['error_code'])
        self.assertEqual('RECOMMENDATION_NOT_FOUND', foreign_response.json()['error_code'])

    def test_post_feedback_without_token_returns_401(self) -> None:
        response = self.client.post(
            '/api/recommend/feedback',
            json={'id': 1, 'status': 'completed'},
        )

        self.assertEqual(401, response.status_code)
        self.assertEqual('UNAUTHORIZED', response.json()['error_code'])

    def test_post_feedback_returns_400_when_status_is_invalid(self) -> None:
        self._seed_user(_USER_ID)
        item_id = self._seed_recommendation(_USER_ID, '二次函数')

        response = self.client.post(
            '/api/recommend/feedback',
            json={'id': item_id, 'status': 'pending'},
            headers=_auth_headers(_USER_ID, 'user_41'),
        )

        self.assertEqual(400, response.status_code)
        payload = response.json()
        self.assertFalse(payload['success'])
        self.assertEqual('INVALID_REQUEST', payload['error_code'])

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

    def _seed_tagged_messages(self, user_id: int, tags: list[str]) -> None:
        connection = database.get_connection()
        try:
            for index, tag in enumerate(tags, start=1):
                session_id = user_id * 1000 + index
                message_id = user_id * 100000 + index
                connection.execute(
                    """
                    INSERT INTO sessions (id, user_id, title)
                    VALUES (?, ?, ?)
                    """,
                    (session_id, user_id, f'session-{session_id}'),
                )
                connection.execute(
                    """
                    INSERT INTO messages (id, session_id, sequence_no, role, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (message_id, session_id, 1, 'assistant', f'message-{message_id}'),
                )
                connection.execute(
                    """
                    INSERT INTO message_tags (message_id, tag)
                    VALUES (?, ?)
                    """,
                    (message_id, tag),
                )
            connection.commit()
        finally:
            connection.close()

    def _seed_recommendation(
        self,
        user_id: int,
        topic: str,
        status: str = 'pending',
    ) -> int:
        connection = database.get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO recommendation_items (
                    user_id, recommended_topic, question_payload, source, status, feedback_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    topic,
                    json.dumps(_question_payload(topic), ensure_ascii=False),
                    'question_tool',
                    status,
                    '2026-04-21T10:00:00Z' if status != 'pending' else None,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def _fetch_recommendation_rows(self, user_id: int):
        connection = database.get_connection()
        try:
            return connection.execute(
                """
                SELECT id, recommended_topic, question_payload, source, status
                FROM recommendation_items
                WHERE user_id = ?
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

    def _fetch_recommendation_row(self, item_id: int):
        connection = database.get_connection()
        try:
            return connection.execute(
                """
                SELECT id, recommended_topic, question_payload, source, status, feedback_at
                FROM recommendation_items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
