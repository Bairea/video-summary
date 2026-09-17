"""OpenAI 兼容 API 调用（openai SDK + AsyncOpenAI）。与旧 TS openaiCompatible.ts 行为一致。

AI 入口统一走这里的 chat_complete / test_ai_connection，按 ai.provider 分发：
- openai_compatible：OpenAI Chat Completions（默认 DeepSeek）
- anthropic_compatible：Anthropic Messages（见 anthropic_compat）
"""

import asyncio
import os

from ..lib.ai_http import await_with_signal, normalize_base_url
from .settings_sync import load_settings_sync

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
PROVIDERS = ("openai_compatible", "anthropic_compatible")


def normalize_openai_base_url(input_url: str) -> str:
    return normalize_base_url(input_url)


def resolve_ai_settings(settings: dict) -> dict:
    """解析 AI 配置：apiKey 优先取环境变量（OpenAI 兼容取 DEEPSEEK_API_KEY，Anthropic 取 ANTHROPIC_API_KEY）。"""
    ai = settings.get("ai", {})
    provider = (ai.get("provider") or "").strip()
    if provider not in PROVIDERS:
        provider = "openai_compatible"

    if provider == "anthropic_compatible":
        from .anthropic_compat import DEFAULT_BASE_URL as ANTHROPIC_DEFAULT_BASE_URL
        from .anthropic_compat import DEFAULT_MODEL as ANTHROPIC_DEFAULT_MODEL
        from .anthropic_compat import normalize_anthropic_base_url
        api_key = os.environ.get("ANTHROPIC_API_KEY") or (ai.get("apiKey") or "").strip()
        base_url = normalize_anthropic_base_url(
            (ai.get("baseUrl") or "").strip() or ANTHROPIC_DEFAULT_BASE_URL
        )
        model = (ai.get("model") or "").strip() or ANTHROPIC_DEFAULT_MODEL
    else:
        api_key = os.environ.get("DEEPSEEK_API_KEY") or (ai.get("apiKey") or "").strip()
        base_url = normalize_openai_base_url((ai.get("baseUrl") or "").strip() or DEFAULT_BASE_URL)
        model = (ai.get("model") or "").strip() or DEFAULT_MODEL

    return {"provider": provider, "baseUrl": base_url, "apiKey": api_key, "model": model}


def _make_client(base_url: str, api_key: str, timeout: float = 120):
    from openai import AsyncOpenAI
    return AsyncOpenAI(base_url=f"{base_url}/v1", api_key=api_key, max_retries=0, timeout=timeout)


async def chat_complete(messages: list[dict], temperature: float = 0.2, signal: asyncio.Event | None = None) -> str:
    settings = await asyncio.to_thread(load_settings_sync)
    resolved = resolve_ai_settings(settings)
    base_url, api_key, model = resolved["baseUrl"], resolved["apiKey"], resolved["model"]

    if not base_url or not api_key or not model:
        raise RuntimeError("AI 未配置（需要 Base URL / API Key / Model）")

    if resolved["provider"] == "anthropic_compatible":
        from .anthropic_compat import chat_complete as anthropic_chat_complete
        return await anthropic_chat_complete(
            messages, temperature=temperature, signal=signal,
            api_key=api_key, base_url=base_url, model=model,
        )

    client = _make_client(base_url, api_key)
    request = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=False,
    )
    response = await await_with_signal(request, signal)

    if not response.choices:
        raise RuntimeError("AI 返回为空")
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("AI 返回为空")
    return content


async def test_ai_connection() -> dict:
    """设置页测试连通性：5 秒超时，返回 {ok, message}。"""
    settings = await asyncio.to_thread(load_settings_sync)
    resolved = resolve_ai_settings(settings)
    base_url, api_key, model = resolved["baseUrl"], resolved["apiKey"], resolved["model"]
    if not base_url or not api_key or not model:
        return {"ok": False, "message": "未配置 Base URL / API Key / Model"}

    try:
        if resolved["provider"] == "anthropic_compatible":
            from .anthropic_compat import test_connection as anthropic_test_connection
            await anthropic_test_connection(api_key=api_key, base_url=base_url, model=model, timeout=10.0)
        else:
            client = _make_client(base_url, api_key, timeout=5.0)
            await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                temperature=0,
                max_tokens=1,
                stream=False,
            )
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        status = getattr(e, "status_code", None)
        extra = ""
        if status == 404:
            extra = "（请确认 Base URL 不要重复包含 /v1，例如填 https://api.deepseek.com 而不是 https://api.deepseek.com/v1）"
        message = f"请求失败: {status} {extra} {str(e)}".strip()[:260]
        return {"ok": False, "message": message}
