from __future__ import annotations

import json
from typing import Any, Dict, Optional

from backend.env import load_backend_env
from backend.services.llm_provider_support import load_provider_settings
from backend.tools.question_tool_impl import (
    build_mock_question_impl,
    extract_content_impl,
    generate_question_with_llm_impl,
    load_question_from_bank_impl,
    normalize_generated_payload_impl,
    parse_json_payload_impl,
)


load_backend_env()


def question_tool(topic: str) -> str:
    normalized_topic = topic.strip()
    if not normalized_topic:
        return '出题错误：知识点不能为空。'

    local_question = load_question_from_bank(normalized_topic)
    if local_question is not None:
        return json.dumps(local_question, ensure_ascii=False)

    try:
        generated = generate_question_with_llm(normalized_topic)
        return json.dumps(generated, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001 - tool must never crash the service
        return f'出题错误：{exc}'


def load_question_from_bank(topic: str) -> Optional[Dict[str, Any]]:
    return load_question_from_bank_impl(topic)


def generate_question_with_llm(topic: str) -> Dict[str, Any]:
    return generate_question_with_llm_impl(topic)


def load_generation_settings() -> Dict[str, Any]:
    return load_provider_settings()


def build_mock_question(topic: str) -> Dict[str, Any]:
    return build_mock_question_impl(topic)


def extract_content(response_payload: Dict[str, Any]) -> str:
    return extract_content_impl(response_payload)


def parse_json_payload(content: str) -> Dict[str, Any]:
    return parse_json_payload_impl(content)


def normalize_generated_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return normalize_generated_payload_impl(payload)
