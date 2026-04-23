from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from backend import database
from backend.services.llm_provider_support import (
    describe_provider,
    load_provider_settings,
    should_retry_provider_error,
)


LOGGER = logging.getLogger(__name__)

TOPIC_ALIASES = {
    '二次函数': ('抛物线', '顶点', '开口方向', '配方法', '二次'),
    '一次函数': ('斜率', '截距', 'y=kx+b'),
    '勾股定理': ('商高定理', '直角三角形', '勾股'),
    '牛顿第一定律': ('惯性定律',),
    '牛顿第二定律': ('F=ma', '加速度', '受力', '牛顿第二'),
    '牛顿第三定律': ('作用力', '反作用力'),
    '光合作用': ('叶绿体', '光反应', '暗反应'),
    '热力学第一定律': ('内能', '做功', '热传递'),
    '热量守恒定律': ('内能守恒', '热力学第一定律'),
    '氧化还原反应': ('氧化剂', '还原剂', '得失电子'),
    '离子反应': ('离子方程式', '电解质'),
}

SUBJECT_HINTS = {
    '二次函数': ('high_school_mathematics', 'middle_school_mathematics'),
    '一次函数': ('high_school_mathematics', 'middle_school_mathematics'),
    '函数': ('high_school_mathematics', 'middle_school_mathematics'),
    '勾股': ('middle_school_mathematics', 'high_school_mathematics'),
    '抛物线': ('high_school_mathematics', 'middle_school_mathematics'),
    '牛顿': ('high_school_physics', 'middle_school_physics'),
    '力学': ('high_school_physics', 'middle_school_physics'),
    '热力学': ('high_school_physics', 'middle_school_physics'),
    '光合作用': ('high_school_biology',),
    '生物': ('high_school_biology',),
    '氧化还原': ('high_school_chemistry', 'middle_school_chemistry'),
    '离子': ('high_school_chemistry', 'middle_school_chemistry'),
    '化学': ('high_school_chemistry', 'middle_school_chemistry'),
}


def load_question_from_bank_impl(topic: str) -> Optional[Dict[str, Any]]:
    normalized_topic = topic.strip()
    if not normalized_topic:
        return None

    connection = None
    try:
        connection = database.get_connection()
        rows = connection.execute(
            """
            SELECT subject, topic, question, option_a, option_b, option_c, option_d, answer, explanation, source
            FROM question_bank
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    finally:
        if connection is not None:
            connection.close()

    if not rows:
        return None

    search_terms = _build_search_terms(normalized_topic)
    subject_hints = _resolve_subject_hints(normalized_topic)
    best_row, best_score = _pick_best_row(rows, search_terms, subject_hints)
    if best_row is not None and best_score > 0:
        return _serialize_question_row(best_row)

    subject_row = _pick_subject_fallback(rows, subject_hints)
    if subject_row is None:
        return None

    return _serialize_question_row(subject_row, source_override='ceval_subject_fallback')


def generate_question_with_llm_impl(topic: str) -> Dict[str, Any]:
    settings = load_provider_settings()
    if settings['mock_mode'] or not settings['providers']:
        return build_mock_question_impl(topic)

    payload = {
        'stream': False,
        'messages': [
            {
                'role': 'system',
                'content': (
                    '你是一名教育出题助手。请围绕用户给出的知识点生成一道中文单选题。'
                    '必须严格返回 JSON，不要输出任何额外文本。'
                ),
            },
            {
                'role': 'user',
                'content': (
                    f'知识点：{topic}\n'
                    '请输出 JSON：'
                    '{"question":"题目文本","options":{"A":"选项A","B":"选项B","C":"选项C","D":"选项D"},'
                    '"answer":"正确选项字母","explanation":"解题思路","source":"llm_generated"}'
                ),
            },
        ],
    }

    last_error: Optional[Exception] = None
    for provider in settings['providers']:
        try:
            return _generate_question_with_provider(provider, payload)
        except Exception as exc:  # noqa: BLE001 - provider failover handled here
            last_error = exc
            if should_retry_provider_error(exc):
                LOGGER.warning(
                    'question_tool provider %s failed, trying next provider: %s',
                    describe_provider(provider),
                    exc,
                )
                continue
            raise

    if last_error is not None:
        raise last_error
    return build_mock_question_impl(topic)


def build_mock_question_impl(topic: str) -> Dict[str, Any]:
    return {
        'question': f'关于“{topic}”的下列说法中，哪一项最准确？',
        'options': {
            'A': f'{topic}只适用于极少数特殊情形',
            'B': f'{topic}是一个需要结合定义理解的基础知识点',
            'C': f'{topic}与任何已学公式都无关',
            'D': f'{topic}无法用于解题分析',
        },
        'answer': 'B',
        'explanation': f'这是 mock/兜底生成的示例题，强调先理解“{topic}”的核心定义再解题。',
        'source': 'llm_generated',
    }


def extract_content_impl(response_payload: Dict[str, Any]) -> str:
    choices = response_payload.get('choices')
    if not isinstance(choices, list) or not choices:
        raise ValueError('LLM 返回缺少 choices。')

    message = choices[0].get('message')
    if not isinstance(message, dict):
        raise ValueError('LLM 返回缺少 message。')

    content = message.get('content')
    if not isinstance(content, str) or not content.strip():
        raise ValueError('LLM 返回缺少内容。')
    return content.strip()


def parse_json_payload_impl(content: str) -> Dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith('```'):
        stripped = stripped.strip('`')
        if stripped.startswith('json'):
            stripped = stripped[4:].strip()
    start = stripped.find('{')
    end = stripped.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ValueError('LLM 未返回有效 JSON。')
    return json.loads(stripped[start:end + 1])


def normalize_generated_payload_impl(payload: Dict[str, Any]) -> Dict[str, Any]:
    options = payload.get('options')
    if not isinstance(options, dict):
        raise ValueError('LLM 返回缺少 options。')

    normalized_options = {
        'A': str(options.get('A') or ''),
        'B': str(options.get('B') or ''),
        'C': str(options.get('C') or ''),
        'D': str(options.get('D') or ''),
    }
    answer = str(payload.get('answer') or '').strip()
    if answer not in normalized_options:
        raise ValueError('LLM 返回了非法答案选项。')

    return {
        'question': str(payload.get('question') or '').strip(),
        'options': normalized_options,
        'answer': answer,
        'explanation': str(payload.get('explanation') or '').strip(),
        'source': str(payload.get('source') or 'llm_generated'),
    }


def _generate_question_with_provider(provider: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    request_payload = dict(payload)
    request_payload['model'] = provider['model']
    url = provider['base_url'].rstrip('/') + '/chat/completions'
    headers = {
        'Authorization': f"Bearer {provider['api_key']}",
        'Content-Type': 'application/json',
    }

    with httpx.Client(timeout=provider['timeout'], trust_env=False) as client:
        response = client.post(url, json=request_payload, headers=headers)
        response.raise_for_status()
        response_payload = response.json()

    content = extract_content_impl(response_payload)
    return normalize_generated_payload_impl(parse_json_payload_impl(content))


def _build_search_terms(topic: str) -> List[Tuple[str, int]]:
    seen: set[str] = set()
    terms: List[Tuple[str, int]] = []

    def add(term: str, weight: int) -> None:
        normalized = _normalize_search_text(term)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        terms.append((normalized, weight))

    add(topic, 160)

    for key, aliases in TOPIC_ALIASES.items():
        normalized_key = _normalize_search_text(key)
        normalized_topic = _normalize_search_text(topic)
        if normalized_key in normalized_topic or normalized_topic in normalized_key:
            add(key, 140)
            for alias in aliases:
                add(alias, 120)

    for fragment in _derive_topic_fragments(topic):
        add(fragment, 60)

    return terms


def _derive_topic_fragments(topic: str) -> Iterable[str]:
    fragments: List[str] = []
    stripped = topic.strip()
    for suffix in ('函数', '定理', '定律', '方程', '反应', '守恒'):
        if stripped.endswith(suffix):
            fragments.append(suffix)
    if '牛顿' in stripped:
        fragments.append('牛顿')
    if '热力学' in stripped:
        fragments.append('热力学')
    return fragments


def _resolve_subject_hints(topic: str) -> List[str]:
    hints: List[str] = []
    normalized = _normalize_search_text(topic)
    for keyword, subjects in SUBJECT_HINTS.items():
        if _normalize_search_text(keyword) in normalized:
            for subject in subjects:
                if subject not in hints:
                    hints.append(subject)
    return hints


def _pick_best_row(
    rows: Iterable[sqlite3.Row],
    search_terms: List[Tuple[str, int]],
    subject_hints: List[str],
) -> Tuple[Optional[sqlite3.Row], int]:
    best_row: Optional[sqlite3.Row] = None
    best_score = 0

    for row in rows:
        score = _score_row(row, search_terms, subject_hints)
        if score > best_score:
            best_row = row
            best_score = score

    return best_row, best_score


def _pick_subject_fallback(
    rows: Iterable[sqlite3.Row],
    subject_hints: List[str],
) -> Optional[sqlite3.Row]:
    if not subject_hints:
        return None

    for subject in subject_hints:
        for row in rows:
            if str(row['subject']) == subject:
                return row
    return None


def _score_row(
    row: sqlite3.Row,
    search_terms: List[Tuple[str, int]],
    subject_hints: List[str],
) -> int:
    row_topic = _normalize_search_text(str(row['topic'] or ''))
    row_question = _normalize_search_text(str(row['question'] or ''))
    row_explanation = _normalize_search_text(str(row['explanation'] or ''))

    score = 0
    for term, weight in search_terms:
        if not term:
            continue
        if row_topic == term:
            score += weight + 60
        elif term in row_topic:
            score += weight + 30
        if term in row_question:
            score += max(weight - 20, 20)
        if term in row_explanation:
            score += max(weight - 50, 10)

    if score > 0 and str(row['subject']) in subject_hints:
        score += 15

    return score


def _serialize_question_row(
    row: sqlite3.Row,
    *,
    source_override: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        'question': str(row['question']),
        'options': {
            'A': str(row['option_a'] or ''),
            'B': str(row['option_b'] or ''),
            'C': str(row['option_c'] or ''),
            'D': str(row['option_d'] or ''),
        },
        'answer': str(row['answer']),
        'explanation': str(row['explanation'] or ''),
        'source': str(source_override or row['source'] or 'ceval'),
    }


def _normalize_search_text(value: str) -> str:
    translation = str.maketrans(
        {
            '（': '(',
            '）': ')',
            '，': ',',
            '。': '.',
            '：': ':',
            '；': ';',
            '？': '?',
            '！': '!',
            '“': '"',
            '”': '"',
            '‘': "'",
            '’': "'",
            ' ': '',
            '\n': '',
            '\r': '',
            '\t': '',
        }
    )
    return value.translate(translation).lower()
