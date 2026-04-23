"""
backend/tests/test_chat_tools_api.py

Tests for POST /api/chat.

Endpoint now requires JWT authentication.  All requests carry
`Authorization: Bearer <token>` generated from the same secret as the backend.

The token user_id=1 (demo_user) is always seeded by database.init_database(),
so no extra seed step is needed for basic tests.
"""
from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from shutil import rmtree
from typing import Optional
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from backend import database
from backend.main import app

_JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')
_JWT_ALGO = 'HS256'
# demo_user is always user_id=1 (seeded by init_database via ensure_test_user)
_TEST_USER_ID = 1
_TEST_USERNAME = 'demo_user'


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


def _auth_headers(user_id: int = _TEST_USER_ID, username: str = _TEST_USERNAME) -> dict:
    return {'Authorization': f'Bearer {_make_token(user_id, username)}'}


class ChatToolsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('backend/tests/.tmp') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_mock_mode = os.environ.get('LLM_MOCK_MODE')
        self._original_api_key = os.environ.get('LLM_API_KEY')
        self._original_model = os.environ.get('LLM_MODEL')
        database.DB_PATH = self._temp_dir / 'test_chat_tools.db'
        os.environ['LLM_MOCK_MODE'] = '1'
        os.environ.pop('LLM_API_KEY', None)
        os.environ.pop('LLM_MODEL', None)
        database.init_database()  # seeds demo_user with user_id=1
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)
        database.DB_PATH = self._original_db_path
        self._restore_env('LLM_MOCK_MODE', self._original_mock_mode)
        self._restore_env('LLM_API_KEY', self._original_api_key)
        self._restore_env('LLM_MODEL', self._original_model)
        rmtree(self._temp_dir, ignore_errors=True)

    # ── Auth guard ─────────────────────────────────────────────────────────────

    def test_post_chat_returns_401_when_no_token(self) -> None:
        response = self.client.post(
            '/api/chat',
            json={'content': '你好', 'session_id': None},
        )
        self.assertEqual(401, response.status_code)

    # ── Tool: calculator ───────────────────────────────────────────────────────

    def test_post_chat_uses_calculator_tool_and_persists_tools_used(self) -> None:
        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(return_value='1024'),
        ) as mcp_call:
            response = self.client.post(
                '/api/chat',
                json={
                    'content': '请计算 2^10 是多少？',
                    'session_id': None,
                },
                headers=_auth_headers(),
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('1024', payload['data']['assistant_message']['content'])
        self.assertEqual(
            'calculator_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        self.assertEqual(
            '1024',
            payload['data']['assistant_message']['tools_used'][0]['result'],
        )
        mcp_call.assert_awaited_once_with('calculator_tool', {'expression': '2^10'})

    def test_post_chat_supports_chinese_power_phrase(self) -> None:
        response = self.client.post(
            '/api/chat',
            json={
                'content': '计算 2 的 10 次方',
                'session_id': None,
            },
            headers=_auth_headers(),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('1024', payload['data']['assistant_message']['content'])
        self.assertEqual(
            'calculator_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        self.assertEqual(
            '1024',
            payload['data']['assistant_message']['tools_used'][0]['result'],
        )

    # ── Tool: knowledge ────────────────────────────────────────────────────────

    def test_post_chat_uses_knowledge_tool_and_persists_tools_used(self) -> None:
        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(
                return_value='1. 勾股定理：直角三角形两直角边平方和等于斜边平方。\n来源：百度百科'
            ),
        ) as mcp_call:
            response = self.client.post(
                '/api/chat',
                json={
                    'content': '什么是勾股定理',
                    'session_id': None,
                },
                headers=_auth_headers(),
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('勾股定理', payload['data']['assistant_message']['content'])
        self.assertEqual(
            'knowledge_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        self.assertIn(
            '百度百科',
            payload['data']['assistant_message']['tools_used'][0]['result'],
        )
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '勾股定理'})

    # ── Tool: question ─────────────────────────────────────────────────────────

    def test_post_chat_uses_question_tool_and_persists_tools_used(self) -> None:
        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(
                return_value='{"question":"关于勾股定理的一道选择题","options":{"A":"1","B":"2","C":"3","D":"4"},"answer":"B","explanation":"mock","source":"llm_generated"}'
            ),
        ) as mcp_call:
            response = self.client.post(
                '/api/chat',
                json={
                    'content': '给我出一道关于勾股定理的题',
                    'session_id': None,
                },
                headers=_auth_headers(),
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(
            'question_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        tool_result = payload['data']['assistant_message']['tools_used'][0]['result']
        self.assertIn('"question"', tool_result)
        self.assertIn('"options"', tool_result)
        mcp_call.assert_awaited_once_with('question_tool', {'topic': '勾股定理'})

    # ── Error resilience ───────────────────────────────────────────────────────

    def test_post_chat_returns_tool_error_text_without_crashing(self) -> None:
        response = self.client.post(
            '/api/chat',
            json={
                'content': '请计算 2 + ) 的结果',
                'session_id': None,
            },
            headers=_auth_headers(),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('错误', payload['data']['assistant_message']['content'])
        self.assertEqual(
            'error',
            payload['data']['assistant_message']['tools_used'][0]['status'],
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _restore_env(self, key: str, value: Optional[str]) -> None:
        if value is None:
            os.environ.pop(key, None)
            return
        os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
