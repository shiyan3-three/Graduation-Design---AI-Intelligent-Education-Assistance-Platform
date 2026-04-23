from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from backend.env import load_backend_env


load_backend_env()


SEARCH_URL = 'https://qianfan.baidubce.com/v2/ai_search/chat/completions'
DEFAULT_TIMEOUT_SECONDS = 30
MAX_REFERENCE_COUNT = 5
DEFAULT_SEARCH_MODEL = ''


def knowledge_tool(topic: str) -> str:
    normalized_topic = topic.strip()
    if not normalized_topic:
        return '知识查询错误：查询主题不能为空。'

    api_key = os.getenv('BAIDU_SEARCH_API_KEY', '').strip()
    if not api_key:
        return '知识查询错误：未配置 BAIDU_SEARCH_API_KEY。'

    try:
        payload = {
            'messages': [{'content': normalized_topic, 'role': 'user'}],
            'search_source': 'baidu_search_v2',
            'resource_type_filter': [{'type': 'web', 'top_k': MAX_REFERENCE_COUNT}],
            'search_mode': 'required',
            'response_format': 'text',
            'enable_corner_markers': False,
            'stream': False,
        }
        search_model = os.getenv('BAIDU_SEARCH_MODEL', DEFAULT_SEARCH_MODEL).strip()
        if search_model:
            payload['model'] = search_model

        response = requests.post(
            SEARCH_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        answer = _extract_generated_answer(payload)
        references = payload.get('references')
        if answer:
            return _format_generated_answer(answer, references)
        if not isinstance(references, list) or not references:
            return '知识查询错误：搜索结果为空。'
        return _format_references(references[:MAX_REFERENCE_COUNT])
    except Exception as exc:  # noqa: BLE001 - tool must never crash the service
        return f'知识查询错误：{exc}'


def _extract_generated_answer(payload: Dict[str, Any]) -> str:
    choices = payload.get('choices')
    if not isinstance(choices, list) or not choices:
        return ''

    message = choices[0].get('message')
    if not isinstance(message, dict):
        return ''

    content = message.get('content')
    if not isinstance(content, str):
        return ''

    return content.strip()


def _format_generated_answer(answer: str, references: Any) -> str:
    lines = [answer]
    if isinstance(references, list) and references:
        for index, item in enumerate(references[:3], start=1):
            title = str(item.get('title') or '未命名结果').strip()
            source = str(item.get('website') or item.get('url') or '未知来源').strip()
            lines.append(f'来源{index}：{title}（{source}）')
    return '\n'.join(lines)


def _format_references(references: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for index, item in enumerate(references, start=1):
        title = str(item.get('title') or '未命名结果').strip()
        summary = str(item.get('snippet') or item.get('content') or '暂无摘要').strip()
        source = str(item.get('website') or item.get('url') or '未知来源').strip()
        lines.append(f'{index}. {title}')
        lines.append(f'摘要：{summary}')
        lines.append(f'来源：{source}')

    return '\n'.join(lines)
