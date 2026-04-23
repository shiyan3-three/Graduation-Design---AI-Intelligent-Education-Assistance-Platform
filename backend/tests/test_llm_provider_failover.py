from __future__ import annotations

import asyncio
import json
import os
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import httpx

from backend.services.llm import generate_assistant_reply
from backend.tools.question_tool import generate_question_with_llm


class _AsyncProviderResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)
        self.request = httpx.Request('POST', 'https://example.invalid')

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = httpx.Response(
                self.status_code,
                request=self.request,
                text=self.text,
            )
            raise httpx.HTTPStatusError('provider failed', request=self.request, response=response)

    def json(self) -> Dict[str, Any]:
        return self._payload


class _AsyncProviderClient:
    def __init__(self, requests: List[Dict[str, Any]]) -> None:
        self._requests = requests

    async def __aenter__(self) -> '_AsyncProviderClient':
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, json: Dict[str, Any], headers: Dict[str, str]) -> _AsyncProviderResponse:
        self._requests.append({'url': url, 'json': json, 'headers': headers})
        if url.startswith('https://relay-a.example'):
            return _AsyncProviderResponse(
                503,
                {'error': {'message': 'upstream busy', 'code': 'internal_error'}},
            )
        return _AsyncProviderResponse(
            200,
            {'choices': [{'message': {'role': 'assistant', 'content': '备用中转已接管。'}}]},
        )


class _AsyncClientFactory:
    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> _AsyncProviderClient:
        return _AsyncProviderClient(self.requests)


class _SyncProviderResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)
        self.request = httpx.Request('POST', 'https://example.invalid')

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = httpx.Response(
                self.status_code,
                request=self.request,
                text=self.text,
            )
            raise httpx.HTTPStatusError('provider failed', request=self.request, response=response)

    def json(self) -> Dict[str, Any]:
        return self._payload


class _SyncProviderClient:
    def __init__(self, requests: List[Dict[str, Any]]) -> None:
        self._requests = requests

    def __enter__(self) -> '_SyncProviderClient':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, json: Dict[str, Any], headers: Dict[str, str]) -> _SyncProviderResponse:
        self._requests.append({'url': url, 'json': json, 'headers': headers})
        if url.startswith('https://relay-a.example'):
            return _SyncProviderResponse(
                503,
                {'error': {'message': 'upstream busy', 'code': 'internal_error'}},
            )
        return _SyncProviderResponse(
            200,
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': (
                                '{"question":"关于二次函数的一道题","options":{"A":"1","B":"2","C":"3","D":"4"},'
                                '"answer":"B","explanation":"备用中转生成","source":"llm_generated"}'
                            ),
                        }
                    }
                ]
            },
        )


class _SyncClientFactory:
    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> _SyncProviderClient:
        return _SyncProviderClient(self.requests)


class LlmProviderFailoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_provider_configs = os.environ.get('LLM_PROVIDER_CONFIGS')
        self._original_mock_mode = os.environ.get('LLM_MOCK_MODE')
        os.environ['LLM_MOCK_MODE'] = '0'
        os.environ['LLM_PROVIDER_CONFIGS'] = json.dumps(
            [
                {
                    'name': 'relay-a',
                    'base_url': 'https://relay-a.example/v1',
                    'api_key': 'key-a',
                    'model': 'deepseek-3.2',
                },
                {
                    'name': 'relay-b',
                    'base_url': 'https://relay-b.example/v1',
                    'api_key': 'key-b',
                    'model': 'glm-5',
                },
            ]
        )

    def tearDown(self) -> None:
        self._restore_env('LLM_PROVIDER_CONFIGS', self._original_provider_configs)
        self._restore_env('LLM_MOCK_MODE', self._original_mock_mode)

    def test_generate_assistant_reply_fails_over_to_next_provider(self) -> None:
        factory = _AsyncClientFactory()

        with patch('backend.services.llm.httpx.AsyncClient', factory):
            reply = asyncio.run(
                generate_assistant_reply(
                    [{'role': 'user', 'content': '你好，你是谁'}]
                )
            )

        self.assertEqual('备用中转已接管。', reply.content)
        self.assertEqual(2, len(factory.requests))
        self.assertTrue(factory.requests[0]['url'].startswith('https://relay-a.example'))
        self.assertTrue(factory.requests[1]['url'].startswith('https://relay-b.example'))

    def test_generate_question_with_llm_fails_over_to_next_provider(self) -> None:
        factory = _SyncClientFactory()

        with patch('backend.tools.question_tool_impl.httpx.Client', factory):
            payload = generate_question_with_llm('二次函数')

        self.assertEqual('llm_generated', payload['source'])
        self.assertEqual('B', payload['answer'])
        self.assertEqual(2, len(factory.requests))
        self.assertTrue(factory.requests[0]['url'].startswith('https://relay-a.example'))
        self.assertTrue(factory.requests[1]['url'].startswith('https://relay-b.example'))

    def _restore_env(self, key: str, value: Optional[str]) -> None:
        if value is None:
            os.environ.pop(key, None)
            return

        os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
