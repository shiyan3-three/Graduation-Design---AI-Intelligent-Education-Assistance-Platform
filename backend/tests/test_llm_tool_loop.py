from __future__ import annotations

import asyncio
import os
import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

from backend.services.llm import generate_assistant_reply


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


class _AsyncClientFactory:
    def __init__(self, responses: List[Dict[str, Any]]) -> None:
        self._responses = responses
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> '_FakeAsyncClient':
        return _FakeAsyncClient(self._responses, self.requests)


class _FakeAsyncClient:
    def __init__(self, responses: List[Dict[str, Any]], requests: List[Dict[str, Any]]) -> None:
        self._responses = responses
        self._requests = requests

    async def __aenter__(self) -> '_FakeAsyncClient':
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, json: Dict[str, Any], headers: Dict[str, str]) -> _FakeResponse:
        self._requests.append(
            {
                'url': url,
                'json': json,
                'headers': headers,
            }
        )
        return _FakeResponse(self._responses.pop(0))


class LlmToolLoopTests(unittest.TestCase):
    def test_generate_assistant_reply_executes_tool_calls_before_final_answer(self) -> None:
        responses = [
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': '',
                            'tool_calls': [
                                {
                                    'id': 'call_1',
                                    'type': 'function',
                                    'function': {
                                        'name': 'calculator_tool',
                                        'arguments': '{"expression":"2^10"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': '2^10 的结果是 1024。',
                        }
                    }
                ]
            },
        ]
        factory = _AsyncClientFactory(responses)

        with patch.dict(
            os.environ,
            {
                'LLM_API_KEY': 'test-key',
                'LLM_MODEL': 'test-model',
                'LLM_BASE_URL': 'https://example.com/v1',
                'LLM_MOCK_MODE': '0',
            },
            clear=False,
        ):
            with patch('backend.services.llm.httpx.AsyncClient', factory):
                with patch(
                    'backend.services.llm.call_mcp_tool',
                    AsyncMock(return_value='1024'),
                ) as mcp_call:
                    reply = asyncio.run(
                        generate_assistant_reply(
                            [
                                {
                                    'role': 'user',
                                    'content': '我有一道数学小题，需要你借助工具处理。',
                                }
                            ]
                        )
                    )

        self.assertEqual('2^10 的结果是 1024。', reply.content)
        self.assertEqual('calculator_tool', reply.tools_used[0]['tool_name'])
        self.assertEqual('1024', reply.tools_used[0]['result'])
        self.assertEqual('calculator_tool', factory.requests[0]['json']['tools'][0]['function']['name'])
        self.assertEqual('tool', factory.requests[1]['json']['messages'][-1]['role'])
        self.assertEqual('1024', factory.requests[1]['json']['messages'][-1]['content'])
        mcp_call.assert_awaited_once_with('calculator_tool', {'expression': '2^10'})

    def test_generate_assistant_reply_in_mock_mode_supports_chinese_power_phrase(self) -> None:
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
                            'content': '计算 2 的 10 次方',
                        }
                    ]
                )
            )

        self.assertIn('1024', reply.content)
        self.assertEqual('calculator_tool', reply.tools_used[0]['tool_name'])
        self.assertEqual('1024', reply.tools_used[0]['result'])

    def test_generate_assistant_reply_executes_knowledge_tool_calls_before_final_answer(self) -> None:
        responses = [
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': '',
                            'tool_calls': [
                                {
                                    'id': 'call_knowledge_1',
                                    'type': 'function',
                                    'function': {
                                        'name': 'knowledge_tool',
                                        'arguments': '{"topic":"什么是勾股定理"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': '勾股定理描述了直角三角形三边之间的关系。',
                        }
                    }
                ]
            },
        ]
        factory = _AsyncClientFactory(responses)

        with patch.dict(
            os.environ,
            {
                'LLM_API_KEY': 'test-key',
                'LLM_MODEL': 'test-model',
                'LLM_BASE_URL': 'https://example.com/v1',
                'LLM_MOCK_MODE': '0',
            },
            clear=False,
        ):
            with patch('backend.services.llm.httpx.AsyncClient', factory):
                with patch(
                    'backend.services.llm.call_mcp_tool',
                    AsyncMock(return_value='1. 勾股定理：直角三角形两直角边平方和等于斜边平方。'),
                ) as mcp_call:
                    reply = asyncio.run(
                        generate_assistant_reply(
                            [
                                {
                                    'role': 'user',
                                    'content': '我在复习一道几何内容，帮我详细说明一下。',
                                }
                            ]
                        )
                    )

        self.assertIn('勾股定理', reply.content)
        self.assertEqual('knowledge_tool', reply.tools_used[0]['tool_name'])
        self.assertIn('直角三角形', reply.tools_used[0]['result'])
        self.assertEqual('knowledge_tool', factory.requests[0]['json']['tools'][1]['function']['name'])
        self.assertEqual('tool', factory.requests[1]['json']['messages'][-1]['role'])
        self.assertIn('勾股定理', factory.requests[1]['json']['messages'][-1]['content'])
        mcp_call.assert_awaited_once_with('knowledge_tool', {'topic': '什么是勾股定理'})

    def test_generate_assistant_reply_executes_question_tool_calls_before_final_answer(self) -> None:
        responses = [
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': '',
                            'tool_calls': [
                                {
                                    'id': 'call_question_1',
                                    'type': 'function',
                                    'function': {
                                        'name': 'question_tool',
                                        'arguments': '{"topic":"\\u52fe\\u80a1\\u5b9a\\u7406"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': '\u6211\u7ed9\u4f60\u51fa\u4e86\u4e00\u9053\u5173\u4e8e\u52fe\u80a1\u5b9a\u7406\u7684\u9898\u3002',
                        }
                    }
                ]
            },
        ]
        factory = _AsyncClientFactory(responses)

        with patch.dict(
            os.environ,
            {
                'LLM_API_KEY': 'test-key',
                'LLM_MODEL': 'test-model',
                'LLM_BASE_URL': 'https://example.com/v1',
                'LLM_MOCK_MODE': '0',
            },
            clear=False,
        ):
            with patch('backend.services.llm.httpx.AsyncClient', factory):
                with patch(
                    'backend.services.llm.call_mcp_tool',
                    AsyncMock(
                        return_value='{"question":"\\u5173\\u4e8e\\u52fe\\u80a1\\u5b9a\\u7406\\u7684\\u4e00\\u9053\\u9009\\u62e9\\u9898","options":{"A":"1","B":"2","C":"3","D":"4"},"answer":"B","explanation":"mock","source":"llm_generated"}'
                    ),
                ) as mcp_call:
                    reply = asyncio.run(
                        generate_assistant_reply(
                            [
                                {
                                    'role': 'user',
                                    'content': '\u5e2e\u6211\u51c6\u5907\u4e00\u9053\u7ec3\u4e60\u9898\uff0c\u6211\u60f3\u505a\u4e2a\u5c0f\u6d4b\u9a8c\u3002',
                                }
                            ]
                        )
                    )

        self.assertIn('\u52fe\u80a1\u5b9a\u7406', reply.content)
        self.assertEqual('question_tool', reply.tools_used[0]['tool_name'])
        self.assertIn('"question"', reply.tools_used[0]['result'])
        self.assertEqual('question_tool', factory.requests[0]['json']['tools'][2]['function']['name'])
        self.assertEqual('tool', factory.requests[1]['json']['messages'][-1]['role'])
        self.assertIn('"question"', factory.requests[1]['json']['messages'][-1]['content'])
        mcp_call.assert_awaited_once_with('question_tool', {'topic': '勾股定理'})

if __name__ == '__main__':
    unittest.main()
