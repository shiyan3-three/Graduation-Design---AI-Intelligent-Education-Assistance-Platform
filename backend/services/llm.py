from __future__ import annotations

import logging
import json
import re
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx

from backend.env import load_backend_env
from backend.services.llm_provider_support import (
    describe_provider,
    load_provider_settings,
    should_retry_provider_error,
)
from backend.services.mcp_client import call_mcp_tool
from backend.tools import calculator_tool, knowledge_tool, question_tool


load_backend_env()


LOGGER = logging.getLogger(__name__)
SYSTEM_PROMPT = (
    "你是一名耐心的 AI 教育辅导助手。"
    "请用简洁、友好的中文回答学生问题，并优先给出启发式讲解。"
    "当问题涉及数学表达式计算时，请优先调用 calculator_tool。"
    "当问题涉及知识解释、概念介绍或定义说明时，请优先调用 knowledge_tool。"
    "当学生明确要求出一道练习题、选择题或测验题时，请优先调用 question_tool。"
)
TOOL_DEFINITIONS = [
    {
        'type': 'function',
        'function': {
            'name': 'calculator_tool',
            'description': '计算数学表达式并返回结果字符串，适用于算术、指数和常见函数。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'expression': {
                        'type': 'string',
                        'description': '需要计算的数学表达式，例如 2^10、sqrt(16) 或 sin(pi/2)。',
                    }
                },
                'required': ['expression'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'knowledge_tool',
            'description': '查询知识概念并返回结构化摘要，适用于定义、解释、介绍类问题。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'topic': {
                        'type': 'string',
                        'description': '需要查询的知识主题，例如勾股定理、牛顿第一定律或二次函数。',
                    }
                },
                'required': ['topic'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'question_tool',
            'description': '根据知识点返回一道结构化选择题，适用于学生主动要求练习、测验或出题的场景。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'topic': {
                        'type': 'string',
                        'description': '需要围绕其出题的知识点，例如勾股定理、牛顿第一定律或热力学第一定律。',
                    }
                },
                'required': ['topic'],
                'additionalProperties': False,
            },
        },
    },
]
MAX_TOOL_ROUNDS = 3
MATH_PROMPT_PREFIXES = (
    '请帮我计算',
    '请帮我算一下',
    '请帮我算',
    '请计算',
    '帮我计算',
    '帮我算一下',
    '帮我算',
    '请算一下',
    '算一下',
    '计算',
    'calc',
    'evaluate',
)
MATH_RESULT_SUFFIX_PATTERNS = (
    r'\s*是多少$',
    r'\s*等于多少$',
    r'\s*等于几$',
    r'\s*结果是多少$',
    r'\s*的结果$',
    r'\s*结果$',
    r'\s*怎么算$',
)
KNOWLEDGE_TOPIC_KEYWORDS = (
    '定理',
    '定律',
    '原理',
    '理论',
    '概念',
    '现象',
    '公式',
    '函数',
    '导数',
    '积分',
    '矩阵',
    '向量',
    '极限',
    '反应',
    '守恒',
    '算法',
    '模型',
)
QUESTION_REQUEST_PATTERNS = (
    r'^给我出一道关于(?P<topic>.+?)的?(?:选择)?题$',
    r'^给我出一道(?P<topic>.+?)的?(?:选择)?题$',
    r'^给我一道关于(?P<topic>.+?)的?(?:选择)?题$',
    r'^来一道关于(?P<topic>.+?)的?(?:选择)?题$',
    r'^来一道(?P<topic>.+?)的?(?:选择)?题$',
    r'^出一道关于(?P<topic>.+?)的?(?:选择)?题$',
    r'^出一道(?P<topic>.+?)的?(?:选择)?题$',
    r'^考考我(?P<topic>.+?)(?:吧)?$',
)
GENERIC_TOPIC_WORDS = {'这个', '那个', '这个东西', '那个东西', '这个概念', '那个概念', '它', '这', '那'}
MATH_SYMBOL_TRANSLATION = str.maketrans(
    {
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '＋': '+',
        '－': '-',
        '×': '*',
        '÷': '/',
        '，': ',',
        '。': '.',
    }
)


@dataclass
class AssistantReply:
    content: str
    tools_used: List[Dict[str, Any]] = field(default_factory=list)
    tool_suggestion: Optional[Dict[str, Any]] = None


async def generate_assistant_reply(
    conversation: List[Dict[str, Any]],
    tool_preference: Optional[str] = None,
) -> AssistantReply:
    settings = _load_settings()
    latest_user_message = _extract_latest_user_message(conversation)
    direct_reply = await _build_direct_tool_reply(latest_user_message, tool_preference)
    if direct_reply is not None:
        return direct_reply

    suggestion_reply = _build_tool_suggestion_reply(latest_user_message)
    if suggestion_reply is not None:
        return suggestion_reply

    if _mock_mode_enabled(settings):
        LOGGER.warning(
            "LLM settings are incomplete or mock mode is enabled. Falling back to local tool-aware mock reply."
        )
        return await _build_mock_reply(latest_user_message)

    try:
        return await _call_openai_compatible_api(settings, conversation)
    except Exception as exc:
        LOGGER.warning("LLM API call failed. Falling back to local tool-aware mock reply: %s", exc)
        return await _build_mock_reply(latest_user_message)


async def generate_assistant_reply_stream(
    conversation: List[Dict[str, Any]],
    tool_preference: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    settings = _load_settings()
    latest_user_message = _extract_latest_user_message(conversation)
    direct_reply = await _build_direct_tool_reply(latest_user_message, tool_preference)
    if direct_reply is not None:
        yield {'type': 'delta', 'content': direct_reply.content}
        yield _build_stream_done_event(direct_reply)
        return

    suggestion_reply = _build_tool_suggestion_reply(latest_user_message)
    if suggestion_reply is not None:
        async for event in _stream_reply_chunks(suggestion_reply, chunk_size=8):
            yield event
        return

    if _mock_mode_enabled(settings):
        LOGGER.warning(
            "LLM settings are incomplete or mock mode is enabled. Falling back to local tool-aware mock stream."
        )
        reply = await _build_mock_reply(latest_user_message)
        async for event in _stream_reply_chunks(reply, chunk_size=8):
            yield event
        return

    has_streamed_event = False
    try:
        async for event in _call_openai_compatible_api_stream(settings, conversation):
            has_streamed_event = True
            yield event
    except Exception as exc:
        if has_streamed_event:
            LOGGER.warning("LLM streaming API call failed after streaming started: %s", exc)
            yield {'type': 'error', 'message': '流式生成中断，请稍后重试。'}
            return
        LOGGER.warning("LLM streaming API call failed. Falling back to local mock stream: %s", exc)
        reply = await _build_mock_reply(latest_user_message)
        async for event in _stream_reply_chunks(reply, chunk_size=8):
            yield event


async def _stream_reply_chunks(
    reply: AssistantReply, chunk_size: int
) -> AsyncGenerator[Dict[str, Any], None]:
    import asyncio
    for chunk in _chunk_text(reply.content, chunk_size):
        yield {'type': 'delta', 'content': chunk}
        await asyncio.sleep(0.05)
    yield _build_stream_done_event(reply)


def _chunk_text(text: str, chunk_size: int) -> List[str]:
    if not text:
        return []
    return [text[index:index + chunk_size] for index in range(0, len(text), chunk_size)]


def _build_stream_done_event(reply: AssistantReply) -> Dict[str, Any]:
    return {
        'type': 'done',
        'tools_used': reply.tools_used,
        'tool_suggestion': reply.tool_suggestion,
    }


def _load_settings() -> Dict[str, Any]:
    return load_provider_settings()


def _mock_mode_enabled(settings: Dict[str, Any]) -> bool:
    return settings["mock_mode"] or not _extract_provider_settings(settings)


def _extract_latest_user_message(conversation: List[Dict[str, Any]]) -> str:
    for item in reversed(conversation):
        if item.get("role") == "user":
            content = item.get("content", "")
            if isinstance(content, str):
                return content
    return ""


async def _build_direct_tool_reply(
    user_message: str,
    tool_preference: Optional[str] = None,
) -> Optional[AssistantReply]:
    normalized = user_message.strip()
    if not normalized:
        return None

    if tool_preference == 'calculator_tool':
        expression = _extract_expression_from_text(normalized)
        if expression:
            return await _build_calculator_reply(expression)
        return AssistantReply(content='我已经切换到计算工具，但当前消息里还缺少清晰可计算的表达式。')

    if tool_preference == 'knowledge_tool':
        topic = (
            _extract_knowledge_topic_from_text(normalized)
            or _extract_knowledge_suggestion_topic(normalized)
            or _clean_topic_candidate(normalized)
        )
        if topic:
            return await _build_knowledge_reply(topic)
        return AssistantReply(content='我已经切换到知识查询工具，但当前消息里还缺少明确的查询主题。')

    if tool_preference == 'question_tool':
        topic = (
            _extract_question_topic_from_text(normalized)
            or _extract_knowledge_topic_from_text(normalized)
            or _extract_knowledge_suggestion_topic(normalized)
            or _clean_topic_candidate(normalized)
        )
        if topic:
            return await _build_question_reply(topic)
        return AssistantReply(content='我已经切换到出题工具，但当前消息里还缺少明确的知识点。')

    expression = _extract_expression_from_text(normalized)
    if expression:
        return await _build_calculator_reply(expression)

    question_topic = _extract_question_topic_from_text(normalized)
    if question_topic:
        return await _build_question_reply(question_topic)

    topic = _extract_knowledge_topic_from_text(normalized)
    if topic:
        return await _build_knowledge_reply(topic)

    return None


def _build_tool_suggestion_reply(user_message: str) -> Optional[AssistantReply]:
    topic = _extract_knowledge_suggestion_topic(user_message)
    if not topic:
        return None

    return AssistantReply(
        content='这条消息更像是在提一个知识主题。如果你希望我改用工具查询，可以点击下方的“使用工具”。',
        tool_suggestion={
            'tool_name': 'knowledge_tool',
            'recommended_prompt': f'请解释{topic}',
        },
    )


async def _build_calculator_reply(expression: str) -> AssistantReply:
    result = await _call_calculator_tool_with_fallback(expression)
    record = _build_tool_record(
        tool_name='calculator_tool',
        arguments={'expression': expression},
        result=result,
        status='error' if result.startswith('计算错误') else 'success',
    )
    if record['status'] == 'success':
        return AssistantReply(
            content=f"我用 calculator_tool 计算了一下，{expression} 的结果是 {result}。",
            tools_used=[record],
        )
    return AssistantReply(
        content=f"我尝试调用 calculator_tool 进行计算，但{result}",
        tools_used=[record],
    )


async def _call_calculator_tool_with_fallback(expression: str) -> str:
    try:
        return await call_mcp_tool('calculator_tool', {'expression': expression})
    except Exception as exc:
        LOGGER.warning(
            'MCP calculator_tool call failed. Falling back to direct function call: %s',
            exc,
        )
        return calculator_tool(expression)


async def _build_knowledge_reply(topic: str) -> AssistantReply:
    result = await _call_knowledge_tool_with_fallback(topic)
    record = _build_tool_record(
        tool_name='knowledge_tool',
        arguments={'topic': topic},
        result=result,
        status='error' if result.startswith('知识查询错误') else 'success',
    )
    if record['status'] == 'success':
        return AssistantReply(
            content=f"我用 knowledge_tool 查询了一下，下面是关于“{topic}”的知识摘要：\n{result}",
            tools_used=[record],
        )
    return AssistantReply(
        content=f"我尝试调用 knowledge_tool 查询资料，但{result}",
        tools_used=[record],
    )


async def _build_question_reply(topic: str) -> AssistantReply:
    result = await _call_question_tool_with_fallback(topic)
    status = 'error'
    content = f"我尝试调用 question_tool 出题，但{result}"

    if not result.startswith('出题错误'):
        try:
            payload = json.loads(result)
        except json.JSONDecodeError:
            payload = None
        else:
            status = 'success'
            content = _format_question_payload(topic, payload)

    record = _build_tool_record(
        tool_name='question_tool',
        arguments={'topic': topic},
        result=result,
        status=status,
    )
    return AssistantReply(content=content, tools_used=[record])


async def _call_knowledge_tool_with_fallback(topic: str) -> str:
    try:
        return await call_mcp_tool('knowledge_tool', {'topic': topic})
    except Exception as exc:
        LOGGER.warning(
            'MCP knowledge_tool call failed. Falling back to direct function call: %s',
            exc,
        )
        return knowledge_tool(topic)


async def _call_question_tool_with_fallback(topic: str) -> str:
    try:
        return await call_mcp_tool('question_tool', {'topic': topic})
    except Exception as exc:
        LOGGER.warning(
            'MCP question_tool call failed. Falling back to direct function call: %s',
            exc,
        )
        return question_tool(topic)


async def _build_mock_reply(user_message: str) -> AssistantReply:
    normalized = user_message.strip()
    direct_reply = await _build_direct_tool_reply(normalized)
    if direct_reply is not None:
        return direct_reply

    suggestion_reply = _build_tool_suggestion_reply(normalized)
    if suggestion_reply is not None:
        return suggestion_reply

    if not normalized:
        return AssistantReply(content="你好，我已经收到你的消息。")
    return AssistantReply(
        content=(
            f"你好，我已经收到你的问题：{normalized}。"
            "当前处于演示模式，我先返回一条可运行的示例回复。"
            "后续只要配置好真实大模型环境变量，就会自动切换到真实模型调用。"
        )
    )


async def _call_openai_compatible_api(
    settings: Dict[str, Any], conversation: List[Dict[str, Any]]
) -> AssistantReply:
    providers = _extract_provider_settings(settings)
    if not providers:
        raise ValueError('LLM provider settings are incomplete.')

    last_error: Optional[Exception] = None
    for provider in providers:
        try:
            return await _call_openai_compatible_api_with_provider(provider, conversation)
        except Exception as exc:
            last_error = exc
            if should_retry_provider_error(exc):
                LOGGER.warning(
                    'LLM provider %s failed, trying next provider: %s',
                    describe_provider(provider),
                    exc,
                )
                continue
            raise

    if last_error is not None:
        raise last_error
    raise ValueError('LLM provider settings are incomplete.')


async def _call_openai_compatible_api_stream(
    settings: Dict[str, Any], conversation: List[Dict[str, Any]]
) -> AsyncGenerator[Dict[str, Any], None]:
    providers = _extract_provider_settings(settings)
    if not providers:
        raise ValueError('LLM provider settings are incomplete.')

    last_error: Optional[Exception] = None
    for provider in providers:
        emitted_any_delta = False
        try:
            async for event in _call_openai_compatible_api_stream_with_provider(
                provider, conversation
            ):
                if event.get('type') == 'delta':
                    emitted_any_delta = True
                yield event
            return
        except Exception as exc:
            last_error = exc
            if should_retry_provider_error(exc) and not emitted_any_delta:
                LOGGER.warning(
                    'LLM streaming provider %s failed before output, trying next provider: %s',
                    describe_provider(provider),
                    exc,
                )
                continue
            raise

    if last_error is not None:
        raise last_error
    raise ValueError('LLM provider settings are incomplete.')


async def _call_openai_compatible_api_with_provider(
    provider: Dict[str, Any], conversation: List[Dict[str, Any]]
) -> AssistantReply:
    url = provider["base_url"].rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}, *conversation]
    tools_used: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=provider["timeout"], trust_env=False) as client:
        for _ in range(MAX_TOOL_ROUNDS + 1):
            payload = {
                "model": provider["model"],
                "stream": False,
                "messages": messages,
                "tools": TOOL_DEFINITIONS,
                "tool_choice": "auto",
            }
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            message = _extract_response_message(data)
            tool_calls = message.get("tool_calls")

            if isinstance(tool_calls, list) and tool_calls:
                assistant_msg = {
                    'role': 'assistant',
                    'content': message.get('content') or '',
                    'tool_calls': tool_calls,
                }
                reasoning = message.get('reasoning_content')
                if reasoning:
                    assistant_msg['reasoning_content'] = reasoning
                messages.append(assistant_msg)
                for tool_call in tool_calls:
                    tool_output, tool_record = await _execute_tool_call(tool_call)
                    tools_used.append(tool_record)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_record.get("tool_call_id", ""),
                            "content": tool_output,
                        }
                    )
                continue

            content = _extract_message_content(message)
            if not content:
                raise ValueError("The LLM API returned an empty response.")
            return AssistantReply(content=content, tools_used=tools_used)

    raise ValueError("Exceeded the maximum number of tool call rounds.")


async def _call_openai_compatible_api_stream_with_provider(
    provider: Dict[str, Any], conversation: List[Dict[str, Any]]
) -> AsyncGenerator[Dict[str, Any], None]:
    url = provider["base_url"].rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}, *conversation]
    tools_used: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=provider["timeout"], trust_env=False) as client:
        for _ in range(MAX_TOOL_ROUNDS + 1):
            payload = {
                "model": provider["model"],
                "stream": True,
                "messages": messages,
                "tools": TOOL_DEFINITIONS,
                "tool_choice": "auto",
            }
            content_parts: List[str] = []
            reasoning_parts: List[str] = []
            tool_call_buffers: Dict[int, Dict[str, Any]] = {}

            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    data_text = _extract_sse_data_text(line)
                    if data_text is None:
                        continue
                    if data_text == '[DONE]':
                        break
                    chunk = _parse_stream_chunk(data_text)
                    if chunk is None:
                        continue

                    delta = _extract_stream_delta(chunk)
                    if delta is None:
                        continue

                    content = _extract_delta_content(delta)
                    if content:
                        content_parts.append(content)
                        yield {'type': 'delta', 'content': content}

                    reasoning = delta.get('reasoning_content')
                    if reasoning:
                        reasoning_parts.append(reasoning)

                    _accumulate_tool_call_deltas(tool_call_buffers, delta.get('tool_calls'))

            tool_calls = _build_tool_calls_from_stream_buffers(tool_call_buffers)
            if tool_calls:
                assistant_msg = {
                    'role': 'assistant',
                    'content': ''.join(content_parts),
                    'tool_calls': tool_calls,
                }
                if reasoning_parts:
                    assistant_msg['reasoning_content'] = ''.join(reasoning_parts)
                messages.append(assistant_msg)
                for tool_call in tool_calls:
                    tool_output, tool_record = await _execute_tool_call(tool_call)
                    tools_used.append(tool_record)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_record.get("tool_call_id", ""),
                            "content": tool_output,
                        }
                    )
                continue

            if content_parts:
                yield {'type': 'done', 'tools_used': tools_used, 'tool_suggestion': None}
                return

            raise ValueError("The LLM API returned an empty streaming response.")

    raise ValueError("Exceeded the maximum number of tool call rounds.")


def _extract_provider_settings(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    providers = settings.get('providers')
    if isinstance(providers, list):
        normalized = [provider for provider in providers if isinstance(provider, dict)]
        if normalized:
            return normalized

    legacy_provider = {
        'name': 'primary',
        'base_url': settings.get('base_url') or '',
        'api_key': settings.get('api_key') or '',
        'model': settings.get('model') or '',
        'timeout': settings.get('timeout') or 30,
    }
    if legacy_provider['base_url'] and legacy_provider['api_key'] and legacy_provider['model']:
        return [legacy_provider]
    return []


def _extract_response_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Missing choices in LLM response payload.")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("Missing message in LLM response payload.")
    return message


def _extract_message_content(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts).strip()

    return ""


def _extract_sse_data_text(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped or not stripped.startswith('data:'):
        return None
    return stripped[len('data:'):].strip()


def _parse_stream_chunk(data_text: str) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(data_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_stream_delta(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    choices = payload.get('choices')
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    delta = first_choice.get('delta')
    return delta if isinstance(delta, dict) else None


def _extract_delta_content(delta: Dict[str, Any]) -> str:
    content = delta.get('content')
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'text':
                text = part.get('text')
                if isinstance(text, str):
                    parts.append(text)
        return ''.join(parts)

    return ''


def _accumulate_tool_call_deltas(
    buffers: Dict[int, Dict[str, Any]], tool_call_deltas: Any
) -> None:
    if not isinstance(tool_call_deltas, list):
        return

    for fallback_index, tool_call_delta in enumerate(tool_call_deltas):
        if not isinstance(tool_call_delta, dict):
            continue
        raw_index = tool_call_delta.get('index')
        try:
            index = int(raw_index) if raw_index is not None else fallback_index
        except (TypeError, ValueError):
            index = fallback_index
        buffer = buffers.setdefault(
            index,
            {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}},
        )
        if tool_call_delta.get('id'):
            buffer['id'] = str(tool_call_delta['id'])
        if tool_call_delta.get('type'):
            buffer['type'] = str(tool_call_delta['type'])

        function_delta = tool_call_delta.get('function')
        if not isinstance(function_delta, dict):
            continue
        function_buffer = buffer.setdefault('function', {'name': '', 'arguments': ''})
        if function_delta.get('name'):
            function_buffer['name'] = str(function_delta['name'])
        if function_delta.get('arguments'):
            function_buffer['arguments'] += str(function_delta['arguments'])


def _build_tool_calls_from_stream_buffers(
    buffers: Dict[int, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    return [buffers[index] for index in sorted(buffers)]


async def _execute_tool_call(tool_call: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    tool_call_id = str(tool_call.get('id') or '')
    function_payload = tool_call.get('function')
    if not isinstance(function_payload, dict):
        result = '工具调用错误：缺少 function 字段。'
        return result, _build_tool_record('unknown_tool', {}, result, 'error', tool_call_id)

    tool_name = str(function_payload.get('name') or 'unknown_tool')
    raw_arguments = function_payload.get('arguments') or '{}'
    arguments = _parse_tool_arguments(raw_arguments)

    if tool_name == 'calculator_tool':
        expression = str(arguments.get('expression') or '')
        LOGGER.info('Executing tool %s with expression=%s', tool_name, expression)
        result = await _call_calculator_tool_with_fallback(expression)
        status = 'error' if result.startswith('计算错误') else 'success'
        return result, _build_tool_record(tool_name, arguments, result, status, tool_call_id)

    if tool_name == 'knowledge_tool':
        topic = str(arguments.get('topic') or '')
        LOGGER.info('Executing tool %s with topic=%s', tool_name, topic)
        result = await _call_knowledge_tool_with_fallback(topic)
        status = 'error' if result.startswith('知识查询错误') else 'success'
        return result, _build_tool_record(tool_name, arguments, result, status, tool_call_id)

    if tool_name == 'question_tool':
        topic = str(arguments.get('topic') or '')
        LOGGER.info('Executing tool %s with topic=%s', tool_name, topic)
        result = await _call_question_tool_with_fallback(topic)
        status = 'error' if result.startswith('出题错误') else 'success'
        return result, _build_tool_record(tool_name, arguments, result, status, tool_call_id)

    result = f'工具调用错误：暂不支持工具 {tool_name}。'
    return result, _build_tool_record(tool_name, arguments, result, 'error', tool_call_id)


def _parse_tool_arguments(raw_arguments: Any) -> Dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not isinstance(raw_arguments, str):
        return {}

    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_tool_record(
    tool_name: str,
    arguments: Dict[str, Any],
    result: str,
    status: str,
    tool_call_id: str = '',
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        'tool_name': tool_name,
        'arguments': arguments,
        'result': result,
        'status': status,
    }
    if tool_call_id:
        record['tool_call_id'] = tool_call_id
    return record


def _extract_expression_from_text(user_message: str) -> Optional[str]:
    candidate = user_message.strip()
    if not candidate:
        return None

    candidate = _strip_math_prompt_prefix(candidate)
    candidate = candidate.strip('：:，,。！？!? ')
    for pattern in MATH_RESULT_SUFFIX_PATTERNS:
        candidate = re.sub(pattern, '', candidate).strip()

    if not candidate:
        return None

    normalized_candidate = _normalize_natural_language_expression(candidate)
    if re.fullmatch(r'[A-Za-z0-9_+\-*/%^().,\s]+', normalized_candidate) and any(
        character.isdigit() for character in normalized_candidate
    ):
        return normalized_candidate
    return None


def _strip_math_prompt_prefix(candidate: str) -> str:
    for prefix in MATH_PROMPT_PREFIXES:
        if candidate.lower().startswith(prefix.lower()):
            return candidate[len(prefix):].strip()
    return candidate


def _normalize_natural_language_expression(candidate: str) -> str:
    normalized = candidate.translate(MATH_SYMBOL_TRANSLATION)
    normalized = re.sub(r'\s*乘以\s*', ' * ', normalized)
    normalized = re.sub(r'(?<=\d|\))\s*乘\s*(?=\d|\()', ' * ', normalized)
    normalized = re.sub(r'\s*除以\s*', ' / ', normalized)
    normalized = re.sub(r'(?<=\d|\))\s*除\s*(?=\d|\()', ' / ', normalized)
    normalized = re.sub(r'\s*加上\s*', ' + ', normalized)
    normalized = re.sub(r'(?<=\d|\))\s*加\s*(?=\d|\()', ' + ', normalized)
    normalized = re.sub(r'\s*减去\s*', ' - ', normalized)
    normalized = re.sub(r'(?<=\d|\))\s*减\s*(?=\d|\()', ' - ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    power_phrase = re.fullmatch(
        r'(?P<base>[A-Za-z0-9_+\-*/%^().,\s]+?)\s*的\s*(?P<exponent>[+\-]?\d+(?:\.\d+)?)\s*次(?:方|幂)',
        normalized,
    )
    if power_phrase:
        base = power_phrase.group('base').strip()
        exponent = power_phrase.group('exponent').strip()
        if base:
            return f'({base})^({exponent})'

    return normalized


def _extract_knowledge_topic_from_text(user_message: str) -> Optional[str]:
    candidate = user_message.strip().strip('？?。！! ')
    if not candidate:
        return None

    patterns = (
        r'^什么是(?P<topic>.+)$',
        r'^什么叫(?P<topic>.+)$',
        r'^请解释(?P<topic>.+)$',
        r'^解释(?P<topic>.+)$',
        r'^请介绍(?P<topic>.+)$',
        r'^介绍(?P<topic>.+)$',
        r'^请问(?P<topic>.+)是什么$',
        r'^(?P<topic>.+)是什么$',
        r'^(?P<topic>.+)是$',
        r'^说说(?P<topic>.+)$',
        r'^聊聊(?P<topic>.+)$',
    )
    for pattern in patterns:
        match = re.match(pattern, candidate)
        if match:
            topic = _clean_topic_candidate(match.group('topic'))
            if topic and not _looks_like_math_expression(topic):
                return topic

    return None


def _extract_knowledge_suggestion_topic(user_message: str) -> Optional[str]:
    candidate = _clean_topic_candidate(user_message)
    if not candidate or _looks_like_math_expression(candidate):
        return None

    if any(keyword in candidate for keyword in KNOWLEDGE_TOPIC_KEYWORDS):
        return candidate

    return None


def _extract_question_topic_from_text(user_message: str) -> Optional[str]:
    candidate = user_message.strip().strip('？?。！! ')
    if not candidate:
        return None

    for pattern in QUESTION_REQUEST_PATTERNS:
        match = re.match(pattern, candidate)
        if not match:
            continue

        topic = _clean_question_topic(match.group('topic'))
        if topic:
            return topic

    return None


def _clean_question_topic(candidate: str) -> Optional[str]:
    topic = _clean_topic_candidate(candidate)
    if topic is None:
        return None

    topic = re.sub(r'(?:的)?(?:选择)?题$', '', topic).strip()
    topic = re.sub(r'^关于', '', topic).strip()
    return _clean_topic_candidate(topic)


def _clean_topic_candidate(candidate: str) -> Optional[str]:
    topic = candidate.strip().strip('“”"\'：:，,。！？!? ')
    if not topic or topic in GENERIC_TOPIC_WORDS:
        return None
    return topic


def _looks_like_math_expression(candidate: str) -> bool:
    normalized = _normalize_natural_language_expression(candidate)
    return bool(
        re.fullmatch(r'[A-Za-z0-9_+\-*/%^().,\s]+', normalized)
        and any(character.isdigit() for character in normalized)
    )


def _format_question_payload(topic: str, payload: Dict[str, Any]) -> str:
    question = str(payload.get('question') or '').strip() or f'下面是一道关于“{topic}”的题目。'
    options = payload.get('options')
    if not isinstance(options, dict):
        return f'我用 question_tool 出了一道关于“{topic}”的题，但题目结构不完整。'

    explanation = str(payload.get('explanation') or '').strip()
    source = str(payload.get('source') or '').strip()
    intro = f'我用 question_tool 为你准备了一道关于“{topic}”的练习题：'
    if source == 'ceval_subject_fallback':
        intro = f'我先从同学科题库里挑了一道接近“{topic}”的练习题：'
    lines = [
        intro,
        question,
        f"A. {str(options.get('A') or '').strip()}",
        f"B. {str(options.get('B') or '').strip()}",
        f"C. {str(options.get('C') or '').strip()}",
        f"D. {str(options.get('D') or '').strip()}",
    ]
    answer = str(payload.get('answer') or '').strip()
    if answer:
        lines.append(f'参考答案：{answer}')
    if explanation:
        lines.append(f'解析：{explanation}')
    return '\n'.join(lines)
