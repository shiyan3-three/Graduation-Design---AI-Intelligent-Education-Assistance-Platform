from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from backend.services.llm_provider_support import (
    describe_provider,
    load_provider_settings,
    should_retry_provider_error,
)


LOGGER = logging.getLogger(__name__)
MAX_TAGS = 3
TAG_EXTRACTION_PROMPT = """请从以下 AI 辅导助手的回复中提取 1-3 个核心知识点标签。
要求：
1. 使用标准化的学科术语，例如"一元二次方程"、"勾股定理"、"牛顿第二定律"
2. 仅返回 JSON 数组，不要解释，不要 Markdown
3. 如果回复不涉及明确知识点，返回空数组 []

示例输出：["一元二次方程", "配方法"]

助手回复：
{content}
"""

KNOWN_TAGS = (
    '一元二次方程',
    '二次函数',
    '配方法',
    '因式分解',
    '勾股定理',
    '直角三角形',
    '概率统计',
    '函数图像',
    '导数',
    '积分',
    '牛顿第一定律',
    '牛顿第二定律',
    '牛顿第三定律',
    '光合作用',
    '化学反应',
    '能量守恒定律',
    '热力学第一定律',
    '热量守恒',
)


async def extract_message_tags(content: str) -> List[str]:
    normalized_content = content.strip()
    if not normalized_content:
        return []

    llm_tags = await _extract_tags_with_llm(normalized_content)
    if llm_tags:
        return llm_tags
    return _extract_tags_with_keywords(normalized_content)


async def _extract_tags_with_llm(content: str) -> List[str]:
    settings = load_provider_settings()
    if settings.get('mock_mode'):
        return []

    providers = _extract_provider_settings(settings)
    if not providers:
        return []

    messages = [
        {'role': 'system', 'content': '你只负责抽取学习知识点标签，并且必须返回 JSON 数组。'},
        {'role': 'user', 'content': TAG_EXTRACTION_PROMPT.format(content=content[:4000])},
    ]
    last_error: Optional[Exception] = None
    for provider in providers:
        try:
            raw_content = await _call_provider_for_tags(provider, messages)
            return _parse_tag_array(raw_content)
        except Exception as exc:
            last_error = exc
            if should_retry_provider_error(exc):
                LOGGER.warning(
                    'Tag extraction provider %s failed, trying next provider: %s',
                    describe_provider(provider),
                    exc,
                )
                continue
            LOGGER.warning('Tag extraction failed without retry: %s', exc)
            return []

    if last_error is not None:
        LOGGER.warning('All tag extraction providers failed: %s', last_error)
    return []


async def _call_provider_for_tags(
    provider: Dict[str, Any], messages: List[Dict[str, str]]
) -> str:
    url = str(provider['base_url']).rstrip('/') + '/chat/completions'
    headers = {
        'Authorization': f"Bearer {provider['api_key']}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': provider['model'],
        'stream': False,
        'messages': messages,
        'temperature': 0,
    }
    async with httpx.AsyncClient(timeout=provider['timeout'], trust_env=False) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    return _extract_message_content(data)


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


def _extract_message_content(payload: Dict[str, Any]) -> str:
    choices = payload.get('choices')
    if not isinstance(choices, list) or not choices:
        return ''

    message = choices[0].get('message')
    if not isinstance(message, dict):
        return ''

    content = message.get('content')
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'text':
                text = part.get('text')
                if isinstance(text, str):
                    parts.append(text)
        return ''.join(parts).strip()

    return ''


def _parse_tag_array(raw_content: str) -> List[str]:
    text = raw_content.strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    if not isinstance(parsed, list):
        return []
    return _deduplicate_tags([str(item) for item in parsed])


def _extract_tags_with_keywords(content: str) -> List[str]:
    candidates = [tag for tag in KNOWN_TAGS if tag in content]
    return _deduplicate_tags(candidates)


def _deduplicate_tags(tags: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for tag in tags:
        normalized = tag.strip().strip('“”"\'：:，,。！？!? ')
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= MAX_TAGS:
            break
    return result
