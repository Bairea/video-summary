"""Anthropic Messages API 调用（httpx 直连 POST {base}/v1/messages）。

兼容 Anthropic Messages 形式的网关：x-api-key 鉴权、anthropic-version 头、
system 与 messages 分离、content 为分块数组。
"""

import asyncio

from ..lib.ai_http import await_with_signal, normalize_base_url

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "grok-4.6"
DEFAULT_MAX_TOKENS = 8192


def normalize_anthropic_base_url(input_url: str) -> str:
    return normalize_base_url(input_url)


def split_system_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """OpenAI 风格消息转 Anthropic 格式：system 抽出拼接，连续同角色合并。"""
    system_parts: list[str] = []
    rest: list[dict] = []
    for m in messages:
        role = m.get("role") or "user"
        content = m.get("content") or ""
        if role == "system":
            system_parts.append(content)
        else:
            rest.append({"role": role, "content": content})

    merged: list[dict] = []
    for m in rest:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] = f"{merged[-1]['content']}\n\n{m['content']}"
        else:
            merged.append(dict(m))
    # Messages API 要求首条为 user 角色
    if merged and merged[0]["role"] != "user":
        merged.insert(0, {"role": "user", "content": "请继续。"})
    return "\n\n".join(system_parts), merged


def _headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }


def _error_message(status: int, body_text: str) -> str:
    import json
    detail = body_text[:200]
    try:
        body = json.loads(body_text)
        detail = (body.get("error") or {}).get("message") or str(body)
    except (json.JSONDecodeError, AttributeError):
        pass
    extra = ""
    if status == 404:
        extra = "（请确认网关支持 Anthropic Messages 协议，即 POST {base}/v1/messages）"
    return f"Anthropic API 请求失败: {status} {extra} {detail}".strip()[:300]


async def chat_complete(
    messages: list[dict],
    temperature: float = 0.2,
    signal: asyncio.Event | None = None,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    timeout: float = 300.0,
) -> str:
    import httpx

    system, api_messages = split_system_messages(messages)
    if not api_messages:
        raise RuntimeError("AI 消息为空")

    payload: dict = {
        "model": model,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "temperature": temperature,
        "stream": False,
        "messages": api_messages,
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=timeout) as client:
        request = client.post(f"{base_url}/v1/messages", headers=_headers(api_key), json=payload)
        response = await await_with_signal(request, signal)

    if response.status_code >= 400:
        raise RuntimeError(_error_message(response.status_code, response.text))

    try:
        body = response.json()
    except ValueError:
        raise RuntimeError("AI 返回为空")
    text = "".join(
        b.get("text", "") for b in body.get("content", [])
        if isinstance(b, dict) and b.get("type") == "text"
    )
    if not text.strip():
        raise RuntimeError("AI 返回为空")
    return text


async def test_connection(api_key: str, base_url: str, model: str, timeout: float = 8.0) -> None:
    """连通性测试（max_tokens=1）：成功静默返回，失败抛 RuntimeError。"""
    import httpx

    payload = {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{base_url}/v1/messages", headers=_headers(api_key), json=payload)
    if response.status_code >= 400:
        raise RuntimeError(_error_message(response.status_code, response.text))
