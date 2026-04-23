from __future__ import annotations

import asyncio
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


class McpServerScriptStartupTests(unittest.TestCase):
    def test_mcp_server_registers_all_three_tools(self) -> None:
        from backend import mcp_server

        tools = asyncio.run(mcp_server.mcp.list_tools())
        tool_names = [tool.name for tool in tools]

        self.assertEqual(
            ['calculator_tool', 'knowledge_tool', 'question_tool'],
            tool_names,
        )

    def test_mcp_server_can_start_in_script_mode(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        backend_dir = project_root / 'backend'
        script_path = backend_dir / 'mcp_server.py'
        snippet = textwrap.dedent(
            f"""
            import runpy
            from mcp.server.fastmcp.server import FastMCP

            FastMCP.run = lambda self, transport='stdio', mount_path=None: None
            runpy.run_path(r"{script_path}", run_name="__main__")
            print("script-start-ok")
            """
        )

        result = subprocess.run(
            [sys.executable, '-c', snippet],
            cwd=backend_dir,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertIn('script-start-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
