from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import httpx


DEFAULT_BASE_URL = 'https://api.openai.com/v1'
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
ENABLED_VALUES = {'1', 'true', 'yes', 'on'}


def load_provider_settings() -> Dict[str, Any]:
    timeout = float(os.getenv('LLM_TIMEOUT_SECONDS', '30'))
    providers = _load_provider_configs(timeout)
    mock_mode = os.getenv('LLM_MOCK_MODE', '').lower() in ENABLED_VALUES
    return {
        'providers': providers,
        'mock_mode': mock_mode,
        'timeout': timeout,
    }


def should_retry_provider_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        return response is not None and response.status_code in RETRYABLE_STATUS_CODES

    return isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.ProtocolError,
            httpx.ProxyError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.ConnectError,
        ),
    )


def describe_provider(provider: Dict[str, Any]) -> str:
    return str(provider.get('name') or provider.get('base_url') or 'llm-provider')


def _load_provider_configs(timeout: float) -> List[Dict[str, Any]]:
    providers: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for provider in _load_json_provider_configs(timeout):
        key = _provider_identity(provider)
        if key in seen:
            continue
        seen.add(key)
        providers.append(provider)

    primary_provider = _load_primary_provider(timeout)
    if primary_provider is not None:
        key = _provider_identity(primary_provider)
        if key not in seen:
            seen.add(key)
            providers.append(primary_provider)

    for provider in _load_base_url_fallbacks(timeout):
        key = _provider_identity(provider)
        if key in seen:
            continue
        seen.add(key)
        providers.append(provider)

    return providers


def _load_json_provider_configs(timeout: float) -> List[Dict[str, Any]]:
    raw = os.getenv('LLM_PROVIDER_CONFIGS', '').strip()
    if not raw:
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    default_api_key = os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY') or ''
    default_model = os.getenv('LLM_MODEL') or os.getenv('OPENAI_MODEL') or ''
    providers: List[Dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue

        provider = _build_provider_config(
            name=str(item.get('name') or f'provider-{index}'),
            base_url=str(item.get('base_url') or item.get('baseUrl') or DEFAULT_BASE_URL),
            api_key=str(item.get('api_key') or item.get('apiKey') or default_api_key),
            model=str(item.get('model') or default_model),
            timeout=float(item.get('timeout') or timeout),
        )
        if _provider_is_complete(provider):
            providers.append(provider)

    return providers


def _load_base_url_fallbacks(timeout: float) -> List[Dict[str, Any]]:
    raw = os.getenv('LLM_BASE_URLS', '').strip()
    if not raw:
        return []

    api_key = os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY') or ''
    model = os.getenv('LLM_MODEL') or os.getenv('OPENAI_MODEL') or ''
    providers: List[Dict[str, Any]] = []
    for index, base_url in enumerate(raw.split(','), start=1):
        normalized = base_url.strip()
        if not normalized:
            continue
        provider = _build_provider_config(
            name=f'fallback-{index}',
            base_url=normalized,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )
        if _provider_is_complete(provider):
            providers.append(provider)

    return providers


def _load_primary_provider(timeout: float) -> Dict[str, Any] | None:
    provider = _build_provider_config(
        name='primary',
        base_url=os.getenv('LLM_BASE_URL') or os.getenv('OPENAI_BASE_URL') or DEFAULT_BASE_URL,
        api_key=os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY') or '',
        model=os.getenv('LLM_MODEL') or os.getenv('OPENAI_MODEL') or '',
        timeout=timeout,
    )
    return provider if _provider_is_complete(provider) else None


def _build_provider_config(
    *,
    name: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float,
) -> Dict[str, Any]:
    return {
        'name': name.strip() or 'provider',
        'base_url': base_url.strip() or DEFAULT_BASE_URL,
        'api_key': api_key.strip(),
        'model': model.strip(),
        'timeout': timeout,
    }


def _provider_is_complete(provider: Dict[str, Any]) -> bool:
    return bool(provider.get('base_url') and provider.get('api_key') and provider.get('model'))


def _provider_identity(provider: Dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(provider.get('base_url') or ''),
        str(provider.get('api_key') or ''),
        str(provider.get('model') or ''),
    )
