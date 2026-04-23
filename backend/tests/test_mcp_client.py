from __future__ import annotations

import asyncio
import os
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

from backend.services.mcp_client import call_mcp_tool


class _FakeClientSession:
    def __init__(self, read, write) -> None:
        self._result = SimpleNamespace(
            content=[SimpleNamespace(text='ok')],
            isError=False,
        )

    async def __aenter__(self) -> '_FakeClientSession':
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def initialize(self) -> None:
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, str]):
        return self._result


class McpClientEnvTests(unittest.TestCase):
    def test_call_mcp_tool_passes_parent_env_to_stdio_server(self) -> None:
        captured_params: dict[str, object] = {}
        original_value = os.environ.get('APP_DB_PATH')
        os.environ['APP_DB_PATH'] = 'project-scipt/runtime/backend_runtime.db'

        def fake_server_parameters(**kwargs):
            captured_params.update(kwargs)
            return SimpleNamespace(**kwargs)

        @asynccontextmanager
        async def fake_stdio_client(server):
            yield object(), object()

        try:
            with patch('mcp.client.stdio.StdioServerParameters', side_effect=fake_server_parameters):
                with patch('mcp.client.stdio.stdio_client', side_effect=fake_stdio_client):
                    with patch('mcp.client.session.ClientSession', _FakeClientSession):
                        result = asyncio.run(call_mcp_tool('question_tool', {'topic': '二次函数'}))
        finally:
            if original_value is None:
                os.environ.pop('APP_DB_PATH', None)
            else:
                os.environ['APP_DB_PATH'] = original_value

        self.assertEqual('ok', result)
        self.assertIn('env', captured_params)
        env = captured_params['env']
        self.assertIsInstance(env, dict)
        self.assertEqual('project-scipt/runtime/backend_runtime.db', env.get('APP_DB_PATH'))


if __name__ == '__main__':
    unittest.main()
