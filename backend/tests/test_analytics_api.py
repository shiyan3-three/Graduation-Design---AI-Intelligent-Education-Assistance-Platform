from __future__ import annotations

import asyncio
import os
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from shutil import rmtree
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.models import ChatRequest
from backend.routers.chat import post_chat
from backend.main import app
from backend.services.llm import AssistantReply


_JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')
_JWT_ALGORITHM = 'HS256'
_USER_A_ID = 21
_USER_B_ID = 22


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


def _auth_headers(user_id: int, username: str) -> dict:
    return {'Authorization': f'Bearer {_make_token(user_id, username)}'}


class AnalyticsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-analytics') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        database.DB_PATH = self._temp_dir / 'test_analytics.db'
        database.init_database()
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)
        database.DB_PATH = self._original_db_path
        rmtree(self._temp_dir, ignore_errors=True)

    def test_get_analytics_tags_returns_frequency_for_current_user_only(self) -> None:
        self._seed_user(_USER_A_ID)
        self._seed_user(_USER_B_ID)
        message_a1 = self._seed_session_with_assistant_message(101, _USER_A_ID, 1001)
        message_a2 = self._seed_session_with_assistant_message(102, _USER_A_ID, 1002)
        message_b = self._seed_session_with_assistant_message(201, _USER_B_ID, 2001)
        self._seed_tag(message_a1, '二次函数')
        self._seed_tag(message_a2, '二次函数')
        self._seed_tag(message_a2, '配方法')
        self._seed_tag(message_b, '牛顿第二定律')

        response = self.client.get(
            '/api/analytics/tags',
            headers=_auth_headers(_USER_A_ID, 'user_21'),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual('ok', payload['message'])
        self.assertEqual(
            [
                {'tag': '二次函数', 'count': 2},
                {'tag': '配方法', 'count': 1},
            ],
            payload['data']['items'],
        )

    def test_get_analytics_report_returns_focus_areas_top3_not_weak_points(self) -> None:
        self._seed_user(_USER_A_ID)
        message_ids = [
            self._seed_session_with_assistant_message(session_id, _USER_A_ID, message_id)
            for session_id, message_id in ((301, 3001), (302, 3002), (303, 3003), (304, 3004))
        ]
        self._seed_tag(message_ids[0], '二次函数')
        self._seed_tag(message_ids[1], '二次函数')
        self._seed_tag(message_ids[2], '配方法')
        self._seed_tag(message_ids[3], '概率统计')

        response = self.client.get(
            '/api/analytics/report',
            headers=_auth_headers(_USER_A_ID, 'user_21'),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertNotIn('weak_points', payload['data'])
        self.assertEqual(
            [
                {'tag': '二次函数', 'count': 2, 'rank': 1},
                {'tag': '概率统计', 'count': 1, 'rank': 2},
                {'tag': '配方法', 'count': 1, 'rank': 3},
            ],
            payload['data']['focus_areas'],
        )

    def test_get_analytics_summary_without_token_returns_401(self) -> None:
        response = self.client.get('/api/analytics/summary')

        self.assertEqual(401, response.status_code)
        payload = response.json()
        self.assertFalse(payload['success'])
        self.assertEqual('UNAUTHORIZED', payload['error_code'])

    def test_get_analytics_summary_returns_zeroes_for_user_without_activity(self) -> None:
        self._seed_user(_USER_A_ID)

        response = self.client.get(
            '/api/analytics/summary',
            headers=_auth_headers(_USER_A_ID, 'user_21'),
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                'total_study_days': 0,
                'streak_days': 0,
                'recommend_complete_rate': None,
            },
            response.json()['data'],
        )

    def test_get_analytics_summary_calculates_current_user_metrics(self) -> None:
        self._seed_user(_USER_A_ID)
        self._seed_user(_USER_B_ID)
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        four_days_ago = today - timedelta(days=4)
        self._seed_session_on_date(401, _USER_A_ID, today)
        self._seed_session_on_date(402, _USER_A_ID, today)
        self._seed_session_on_date(403, _USER_A_ID, yesterday)
        self._seed_session_on_date(404, _USER_A_ID, two_days_ago)
        self._seed_session_on_date(405, _USER_A_ID, four_days_ago)
        self._seed_session_on_date(501, _USER_B_ID, today)
        self._seed_recommendation(601, _USER_A_ID, 'completed')
        self._seed_recommendation(602, _USER_A_ID, 'completed')
        self._seed_recommendation(603, _USER_A_ID, 'completed')
        self._seed_recommendation(604, _USER_A_ID, 'skipped')
        self._seed_recommendation(605, _USER_A_ID, 'pending')
        self._seed_recommendation(701, _USER_B_ID, 'skipped')

        response = self.client.get(
            '/api/analytics/summary',
            headers=_auth_headers(_USER_A_ID, 'user_21'),
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                'total_study_days': 4,
                'streak_days': 3,
                'recommend_complete_rate': 75,
            },
            response.json()['data'],
        )

    def test_get_analytics_summary_returns_zero_streak_when_latest_session_is_stale(
        self,
    ) -> None:
        self._seed_user(_USER_A_ID)
        two_days_ago = date.today() - timedelta(days=2)
        three_days_ago = date.today() - timedelta(days=3)
        self._seed_session_on_date(801, _USER_A_ID, two_days_ago)
        self._seed_session_on_date(802, _USER_A_ID, three_days_ago)

        response = self.client.get(
            '/api/analytics/summary',
            headers=_auth_headers(_USER_A_ID, 'user_21'),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(2, payload['data']['total_study_days'])
        self.assertEqual(0, payload['data']['streak_days'])
        self.assertIsNone(payload['data']['recommend_complete_rate'])

    def test_post_chat_persists_extracted_tags_for_assistant_message(self) -> None:
        with patch(
            'backend.routers.chat.generate_assistant_reply',
            AsyncMock(return_value=AssistantReply(content='二次函数可以写成顶点式，也可以用配方法求顶点。')),
        ), patch(
            'backend.routers.chat.extract_message_tags',
            AsyncMock(return_value=['二次函数', '配方法', '二次函数']),
        ):
            response = self.client.post(
                '/api/chat',
                json={'content': '讲讲二次函数', 'session_id': None},
                headers=_auth_headers(1, 'demo_user'),
            )

        self.assertEqual(200, response.status_code)
        assistant_message_id = response.json()['data']['assistant_message']['id']
        connection = database.get_connection()
        try:
            rows = connection.execute(
                """
                SELECT tag
                FROM message_tags
                WHERE message_id = ?
                ORDER BY tag ASC
                """,
                (assistant_message_id,),
            ).fetchall()
        finally:
            connection.close()

        self.assertEqual(['二次函数', '配方法'], [row['tag'] for row in rows])

    def test_post_chat_still_returns_200_when_tag_extraction_fails(self) -> None:
        with patch(
            'backend.routers.chat.generate_assistant_reply',
            AsyncMock(return_value=AssistantReply(content='这里是正常的 AI 回复。')),
        ), patch(
            'backend.routers.chat.extract_message_tags',
            AsyncMock(side_effect=RuntimeError('tagging unavailable')),
        ):
            response = self.client.post(
                '/api/chat',
                json={'content': '你好', 'session_id': None},
                headers=_auth_headers(1, 'demo_user'),
            )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()['success'])

    def test_post_chat_schedules_slow_tagging_without_awaiting_it(self) -> None:
        background_tasks = _FakeBackgroundTasks()
        slow_tagging = AsyncMock()

        with patch(
            'backend.routers.chat.generate_assistant_reply',
            AsyncMock(return_value=AssistantReply(content='二次函数可以用配方法求顶点。')),
        ), patch(
            'backend.routers.chat._tag_assistant_message_safely',
            slow_tagging,
        ):
            response = asyncio.run(
                post_chat(
                    ChatRequest(content='讲讲二次函数', session_id=None),
                    background_tasks=background_tasks,
                    user_id=1,
                )
            )

        self.assertEqual(200, response.status_code)
        slow_tagging.assert_not_awaited()
        self.assertEqual(1, len(background_tasks.tasks))
        task = background_tasks.tasks[0]
        self.assertIs(slow_tagging, task.func)
        self.assertIn('二次函数', task.args[1])

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

    def _seed_session_with_assistant_message(
        self,
        session_id: int,
        user_id: int,
        message_id: int,
    ) -> int:
        connection = database.get_connection()
        try:
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
            connection.commit()
            return message_id
        finally:
            connection.close()

    def _seed_session_on_date(self, session_id: int, user_id: int, study_date: date) -> None:
        timestamp = f'{study_date.isoformat()} 08:00:00'
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT INTO sessions (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, f'session-{session_id}', timestamp, timestamp),
            )
            connection.commit()
        finally:
            connection.close()

    def _seed_recommendation(self, item_id: int, user_id: int, status: str) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                """
                INSERT INTO recommendation_items (
                    id, user_id, recommended_topic, question_payload, source, status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item_id, user_id, 'topic', '{}', 'question_tool', status),
            )
            connection.commit()
        finally:
            connection.close()

    def _seed_tag(self, message_id: int, tag: str) -> None:
        connection = database.get_connection()
        try:
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


class _CapturedTask:
    def __init__(self, func, args, kwargs) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs


class _FakeBackgroundTasks:
    def __init__(self) -> None:
        self.tasks: list[_CapturedTask] = []

    def add_task(self, func, *args, **kwargs) -> None:
        self.tasks.append(_CapturedTask(func, args, kwargs))


if __name__ == '__main__':
    unittest.main()
