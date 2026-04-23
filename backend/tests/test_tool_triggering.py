from __future__ import annotations

import asyncio
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
from backend.services.llm import AssistantReply, generate_assistant_reply


_JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')
_JWT_ALGORITHM = 'HS256'
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
        algorithm=_JWT_ALGORITHM,
    )


def _auth_headers(
    user_id: int = _TEST_USER_ID,
    username: str = _TEST_USERNAME,
) -> dict:
    return {'Authorization': f'Bearer {_make_token(user_id, username)}'}


class ToolTriggeringTests(unittest.TestCase):
    def test_generate_assistant_reply_in_mock_mode_supports_natural_math_prompt(self) -> None:
        mcp_call = AsyncMock(return_value='42')
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '1',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                reply = asyncio.run(
                    generate_assistant_reply(
                        [
                            {
                                'role': 'user',
                                'content': '帮我算一下 6 × 7 等于多少？',
                            }
                        ]
                    )
                )

        self.assertIn('42', reply.content)
        self.assertEqual('calculator_tool', reply.tools_used[0]['tool_name'])
        self.assertEqual('42', reply.tools_used[0]['result'])
        mcp_call.assert_awaited_once_with('calculator_tool', {'expression': '6 * 7'})

    def test_generate_assistant_reply_in_mock_mode_falls_back_to_direct_calculator_when_mcp_fails(
        self,
    ) -> None:
        mcp_call = AsyncMock(side_effect=RuntimeError('mcp down'))
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '1',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                with patch('backend.services.llm.calculator_tool', return_value='42') as direct_call:
                    reply = asyncio.run(
                        generate_assistant_reply(
                            [
                                {
                                    'role': 'user',
                                    'content': '帮我算一下 6 × 7 等于多少？',
                                }
                            ]
                        )
                    )

        self.assertIn('42', reply.content)
        self.assertEqual('calculator_tool', reply.tools_used[0]['tool_name'])
        self.assertEqual('42', reply.tools_used[0]['result'])
        mcp_call.assert_awaited_once_with('calculator_tool', {'expression': '6 * 7'})
        direct_call.assert_called_once_with('6 * 7')

    def test_generate_assistant_reply_in_mock_mode_supports_topic_is_question_shorthand(self) -> None:
        mcp_call = AsyncMock(return_value='1. 热量守恒定律：在封闭系统中，总能量保持不变。')
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '1',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                reply = asyncio.run(
                    generate_assistant_reply(
                        [
                            {
                                'role': 'user',
                                'content': '热量守恒定律是？',
                            }
                        ]
                    )
                )

        self.assertIn('热量守恒定律', reply.content)
        self.assertEqual('knowledge_tool', reply.tools_used[0]['tool_name'])
        self.assertIn('总能量保持不变', reply.tools_used[0]['result'])
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '热量守恒定律'})

    def test_generate_assistant_reply_in_mock_mode_falls_back_to_direct_knowledge_when_mcp_fails(
        self,
    ) -> None:
        mcp_call = AsyncMock(side_effect=RuntimeError('mcp down'))
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '1',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                with patch(
                    'backend.services.llm.knowledge_tool',
                    return_value='1. 热量守恒定律：在封闭系统中，总能量保持不变。',
                ) as direct_call:
                    reply = asyncio.run(
                        generate_assistant_reply(
                            [
                                {
                                    'role': 'user',
                                    'content': '热量守恒定律是？',
                                }
                            ]
                        )
                    )

        self.assertIn('热量守恒定律', reply.content)
        self.assertEqual('knowledge_tool', reply.tools_used[0]['tool_name'])
        self.assertIn('总能量保持不变', reply.tools_used[0]['result'])
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '热量守恒定律'})
        direct_call.assert_called_once_with('热量守恒定律')

    def test_generate_assistant_reply_in_mock_mode_returns_tool_suggestion_for_bare_topic(self) -> None:
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '1',
            },
            clear=False,
        ):
            reply = asyncio.run(
                generate_assistant_reply(
                    [
                        {
                            'role': 'user',
                            'content': '勾股定理',
                        }
                    ]
                )
            )

        self.assertEqual([], reply.tools_used)
        self.assertIsNotNone(reply.tool_suggestion)
        self.assertEqual('knowledge_tool', reply.tool_suggestion['tool_name'])
        self.assertEqual('请解释勾股定理', reply.tool_suggestion['recommended_prompt'])

    def test_generate_assistant_reply_in_mock_mode_supports_question_prompt(self) -> None:
        mcp_call = AsyncMock(
            return_value='{"question":"关于勾股定理的一道选择题","options":{"A":"1","B":"2","C":"3","D":"4"},"answer":"B","explanation":"mock","source":"llm_generated"}'
        )
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '1',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                reply = asyncio.run(
                    generate_assistant_reply(
                        [
                            {
                                'role': 'user',
                                'content': '\u7ed9\u6211\u51fa\u4e00\u9053\u5173\u4e8e\u52fe\u80a1\u5b9a\u7406\u7684\u9898',
                            }
                        ]
                    )
                )

        self.assertEqual('question_tool', reply.tools_used[0]['tool_name'])
        self.assertIn('"question"', reply.tools_used[0]['result'])
        mcp_call.assert_awaited_once_with('question_tool', {'topic': '勾股定理'})

    def test_generate_assistant_reply_in_mock_mode_falls_back_to_direct_question_when_mcp_fails(
        self,
    ) -> None:
        mcp_call = AsyncMock(side_effect=RuntimeError('mcp down'))
        question_payload = (
            '{"question":"关于勾股定理的一道选择题","options":{"A":"1","B":"2","C":"3","D":"4"},'
            '"answer":"B","explanation":"mock","source":"llm_generated"}'
        )
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '1',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                with patch(
                    'backend.services.llm.question_tool',
                    return_value=question_payload,
                ) as direct_call:
                    reply = asyncio.run(
                        generate_assistant_reply(
                            [
                                {
                                    'role': 'user',
                                    'content': '给我出一道关于勾股定理的题',
                                }
                            ]
                        )
                    )

        self.assertEqual('question_tool', reply.tools_used[0]['tool_name'])
        self.assertIn('"question"', reply.tools_used[0]['result'])
        mcp_call.assert_awaited_once_with('question_tool', {'topic': '勾股定理'})
        direct_call.assert_called_once_with('勾股定理')

    def test_generate_assistant_reply_in_live_mode_still_routes_knowledge_prompt_before_llm(self) -> None:
        llm_call = AsyncMock(side_effect=AssertionError('live llm should not be called'))
        mcp_call = AsyncMock(
            return_value='1. 勾股定理：直角三角形两直角边平方和等于斜边平方。'
        )
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '0',
                'LLM_API_KEY': 'live-key',
                'LLM_MODEL': 'deepseek-3.2',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                with patch('backend.services.llm._call_openai_compatible_api', llm_call):
                    reply = asyncio.run(
                        generate_assistant_reply(
                            [
                                {
                                    'role': 'user',
                                    'content': '什么是勾股定理',
                                }
                            ]
                        )
                    )

        self.assertEqual('knowledge_tool', reply.tools_used[0]['tool_name'])
        self.assertIn('勾股定理', reply.content)
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '勾股定理'})
        llm_call.assert_not_awaited()

    def test_generate_assistant_reply_in_live_mode_still_uses_llm_for_plain_chat(self) -> None:
        llm_call = AsyncMock(return_value=AssistantReply(content='你好，我是教育辅导助手。'))
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '0',
                'LLM_API_KEY': 'live-key',
                'LLM_MODEL': 'deepseek-3.2',
            },
            clear=False,
        ):
            with patch('backend.services.llm._call_openai_compatible_api', llm_call):
                reply = asyncio.run(
                    generate_assistant_reply(
                        [
                            {
                                'role': 'user',
                                'content': '你好啊，你是谁',
                            }
                        ]
                    )
                )

        self.assertEqual('你好，我是教育辅导助手。', reply.content)
        self.assertEqual([], reply.tools_used)
        llm_call.assert_awaited_once()


class ToolTriggeringApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-tool-triggering') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_mock_mode = os.environ.get('LLM_MOCK_MODE')
        self._original_api_key = os.environ.get('LLM_API_KEY')
        self._original_model = os.environ.get('LLM_MODEL')
        database.DB_PATH = self._temp_dir / 'test_tool_triggering.db'
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

    def test_post_chat_supports_natural_math_prompt(self) -> None:
        response = self.client.post(
            '/api/chat',
            json={
                'content': '帮我算一下 6 × 7 等于多少？',
                'session_id': None,
            },
            headers=_auth_headers(),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(
            'calculator_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        self.assertEqual(
            '42',
            payload['data']['assistant_message']['tools_used'][0]['result'],
        )

    def test_post_chat_supports_topic_is_question_shorthand(self) -> None:
        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(
                return_value='1. 热量守恒定律：在封闭系统中，总能量保持不变。\n来源：百度搜索'
            ),
        ) as mcp_call:
            response = self.client.post(
                '/api/chat',
                json={
                    'content': '热量守恒定律是？',
                    'session_id': None,
                },
                headers=_auth_headers(),
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(
            'knowledge_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        self.assertIn('热量守恒定律', payload['data']['assistant_message']['content'])
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '热量守恒定律'})

    def test_post_chat_returns_tool_suggestion_for_bare_topic(self) -> None:
        response = self.client.post(
            '/api/chat',
            json={
                'content': '勾股定理',
                'session_id': None,
            },
            headers=_auth_headers(),
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual([], payload['data']['assistant_message']['tools_used'])
        self.assertEqual(
            'knowledge_tool',
            payload['data']['assistant_message']['tool_suggestion']['tool_name'],
        )
        self.assertEqual(
            '请解释勾股定理',
            payload['data']['assistant_message']['tool_suggestion']['recommended_prompt'],
        )

    def test_post_chat_accepts_tool_preference_to_force_knowledge_tool(self) -> None:
        with patch(
            'backend.services.llm.call_mcp_tool',
            AsyncMock(
                return_value='1. 勾股定理：直角三角形两直角边平方和等于斜边平方。\n来源：百度搜索'
            ),
        ) as mcp_call:
            response = self.client.post(
                '/api/chat',
                json={
                    'content': '请解释勾股定理',
                    'session_id': None,
                    'tool_preference': 'knowledge_tool',
                },
                headers=_auth_headers(),
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(
            'knowledge_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        self.assertNotIn('tool_suggestion', payload['data']['assistant_message'])
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '勾股定理'})

    def test_post_chat_in_live_mode_still_prefers_knowledge_tool_before_llm(self) -> None:
        llm_call = AsyncMock(side_effect=AssertionError('live llm should not be called'))
        mcp_call = AsyncMock(
            return_value='1. 勾股定理：直角三角形两直角边平方和等于斜边平方。\n来源：百度搜索'
        )
        with patch.dict(
            os.environ,
            {
                'LLM_MOCK_MODE': '0',
                'LLM_API_KEY': 'live-key',
                'LLM_MODEL': 'deepseek-3.2',
            },
            clear=False,
        ):
            with patch('backend.services.llm.call_mcp_tool', mcp_call):
                with patch('backend.services.llm._call_openai_compatible_api', llm_call):
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
        self.assertEqual(
            'knowledge_tool',
            payload['data']['assistant_message']['tools_used'][0]['tool_name'],
        )
        self.assertIn('勾股定理', payload['data']['assistant_message']['content'])
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '勾股定理'})
        llm_call.assert_not_awaited()

    def _restore_env(self, key: str, value: Optional[str]) -> None:
        if value is None:
            os.environ.pop(key, None)
            return

        os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
