from __future__ import annotations

import json
import os
import time
import unittest
from pathlib import Path
from shutil import rmtree
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.main import app


_JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')
_JWT_ALGORITHM = 'HS256'
_TEST_USER_ID = 1
_TEST_USERNAME = 'demo_user'


def _make_token(user_id: int = _TEST_USER_ID, username: str = _TEST_USERNAME) -> str:
    return jwt.encode(
        {
            'user_id': user_id,
            'username': username,
            'exp': int(time.time()) + 3600,
        },
        _JWT_SECRET,
        algorithm=_JWT_ALGORITHM,
    )


def _auth_headers() -> Dict[str, str]:
    return {'Authorization': f'Bearer {_make_token()}'}


def _parse_sse_events(body: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for block in body.replace('\r\n', '\n').strip().split('\n\n'):
        if not block:
            continue
        data_lines = [
            line.removeprefix('data:').strip()
            for line in block.splitlines()
            if line.startswith('data:')
        ]
        if data_lines:
            events.append(json.loads('\n'.join(data_lines)))
    return events


class ChatStreamApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-chat-stream') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_mock_mode = os.environ.get('LLM_MOCK_MODE')
        self._original_api_key = os.environ.get('LLM_API_KEY')
        self._original_model = os.environ.get('LLM_MODEL')
        database.DB_PATH = self._temp_dir / 'test_chat_stream.db'
        os.environ['LLM_MOCK_MODE'] = '1'
        os.environ.pop('LLM_API_KEY', None)
        os.environ.pop('LLM_MODEL', None)
        database.init_database()
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)
        database.DB_PATH = self._original_db_path
        self._restore_env('LLM_MOCK_MODE', self._original_mock_mode)
        self._restore_env('LLM_API_KEY', self._original_api_key)
        self._restore_env('LLM_MODEL', self._original_model)
        rmtree(self._temp_dir, ignore_errors=True)

    def test_post_chat_stream_returns_401_when_no_token(self) -> None:
        response = self.client.post(
            '/api/chat/stream',
            json={'content': '你好', 'session_id': None},
        )

        self.assertEqual(401, response.status_code)

    def test_post_chat_stream_returns_400_when_content_is_blank(self) -> None:
        response = self.client.post(
            '/api/chat/stream',
            json={'content': '   ', 'session_id': None},
            headers=_auth_headers(),
        )

        self.assertEqual(400, response.status_code)

    def test_post_chat_stream_yields_delta_and_done_events_and_persists_message(self) -> None:
        response = self.client.post(
            '/api/chat/stream',
            json={'content': '你好，我想先聊聊今天的学习状态。', 'session_id': None},
            headers=_auth_headers(),
        )

        self.assertEqual(200, response.status_code)
        self.assertIn('text/event-stream', response.headers['content-type'])
        events = _parse_sse_events(response.text)
        self.assertGreaterEqual(len([event for event in events if event['type'] == 'delta']), 2)
        self.assertEqual('done', events[-1]['type'])
        self.assertIsInstance(events[-1]['session_id'], int)
        self.assertGreater(events[-1]['session_id'], 0)
        self.assertIsInstance(events[-1]['message_id'], int)
        self.assertGreater(events[-1]['message_id'], 0)
        self.assertEqual([], events[-1]['tools_used'])

        streamed_content = ''.join(
            event['content'] for event in events if event['type'] == 'delta'
        )
        connection = database.get_connection()
        try:
            row = connection.execute(
                """
                SELECT content
                FROM messages
                WHERE id = ? AND role = 'assistant'
                """,
                (events[-1]['message_id'],),
            ).fetchone()
        finally:
            connection.close()

        self.assertIsNotNone(row)
        self.assertEqual(streamed_content, row['content'])

    def test_post_chat_stream_direct_tool_reply_yields_done_with_tools_used(self) -> None:
        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(return_value='1024'),
        ):
            response = self.client.post(
                '/api/chat/stream',
                json={'content': '请计算 2^10 是多少？', 'session_id': None},
                headers=_auth_headers(),
            )

        self.assertEqual(200, response.status_code)
        events = _parse_sse_events(response.text)
        delta_events = [event for event in events if event['type'] == 'delta']
        self.assertEqual(1, len(delta_events))
        self.assertIn('1024', delta_events[0]['content'])
        self.assertEqual('done', events[-1]['type'])
        self.assertEqual('calculator_tool', events[-1]['tools_used'][0]['tool_name'])

    def _restore_env(self, key: str, value: Optional[str]) -> None:
        if value is None:
            os.environ.pop(key, None)
            return
        os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
