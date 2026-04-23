from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ''}:
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from mcp.server.fastmcp import FastMCP

from backend.tools.calculator_tool import calculator_tool as _calculator_tool
from backend.tools.knowledge_tool import knowledge_tool as _knowledge_tool
from backend.tools.question_tool import question_tool as _question_tool


CALCULATOR_DESCRIPTION = '计算数学表达式并返回结果字符串，适用于算术、指数和常见函数。'
KNOWLEDGE_DESCRIPTION = '查询知识概念并返回结构化摘要，适用于定义、解释、介绍类问题。'
QUESTION_DESCRIPTION = '根据知识点返回一道结构化选择题，适用于学生主动要求练习、测验或出题的场景。'
mcp = FastMCP('EduTools')


@mcp.tool(description=CALCULATOR_DESCRIPTION)
def calculator_tool(expression: str) -> str:
    """计算数学表达式并返回结果字符串，适用于算术、指数和常见函数。"""
    return _calculator_tool(expression)


@mcp.tool(description=KNOWLEDGE_DESCRIPTION)
def knowledge_tool(topic: str) -> str:
    """查询知识概念并返回结构化摘要，适用于定义、解释、介绍类问题。"""
    return _knowledge_tool(topic)


@mcp.tool(description=QUESTION_DESCRIPTION)
def question_tool(topic: str) -> str:
    """根据知识点返回一道结构化选择题，适用于学生主动要求练习、测验或出题的场景。"""
    return _question_tool(topic)


def main() -> None:
    mcp.run()


if __name__ == '__main__':
    main()
