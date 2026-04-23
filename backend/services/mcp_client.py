from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    server_params = StdioServerParameters(
        command=sys.executable,
        args=['-m', 'backend.mcp_server'],
        env=os.environ.copy(),
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            text = _extract_text_content(result.content)
            if result.isError:
                raise RuntimeError(text or f'MCP tool {tool_name} returned an error.')
            if not text:
                raise RuntimeError(f'MCP tool {tool_name} returned empty content.')
            return text


def _extract_text_content(content: Any) -> str:
    parts: list[str] = []
    for item in content or []:
        text = getattr(item, 'text', None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return '\n'.join(parts).strip()
