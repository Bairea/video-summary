"""OpenAI 兼容 API 调用（openai SDK + AsyncOpenAI）。与旧 TS openaiCompatible.ts 行为一致。"""

import asyncio

from .settings_sync import load_settings_sync


def normalize_openai_base_url(input_url: str) -> str:
    s = str(input_url or "").strip()
    if not s:
        return ""
    no_slash = s.rstrip("/")
    import re
    return re.sub(r"/v1$", "", no_slash, flags=re.IGNORECASE)


def _make_client(base_url: str, api_key: str, timeout: float = 120):
    from openai import AsyncOpenAI
    return AsyncOpenAI(base_url=f"{base_url}/v1", api_key=api_key, max_retries=0, timeout=timeout)


async def chat_complete(messages: list[dict], temperature: float = 0.2, signal: asyncio.Event | None = None) -> str:
    settings = await asyncio.to_thread(load_settings_sync)
    base_url = normalize_openai_base_url(settings["ai"].get("baseUrl") or "")
    api_key = settings["ai"].get("apiKey")
    model = settings["ai"].get("model")

    if not base_url or not api_key or not model:
        raise RuntimeError("AI 未配置（需要 Base URL / API Key / Model）")

    client = _make_client(base_url, api_key)
    request = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=False,
    )

    if signal is None:
        response = await request
    else:
        task = asyncio.create_task(request)

        async def _watch() -> None:
            await signal.wait()
            task.cancel()

        watcher = asyncio.create_task(_watch())
        try:
            response = await task
        finally:
            watcher.cancel()

    if not response.choices:
        raise RuntimeError("AI 返回为空")
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("AI 返回为空")
    return content


async def test_ai_connection() -> dict:
    """设置页测试连通性：5 秒超时，返回 {ok, message}。"""
    settings = await asyncio.to_thread(load_settings_sync)
    base_url = normalize_openai_base_url(settings["ai"].get("baseUrl") or "")
    api_key = settings["ai"].get("apiKey")
    model = settings["ai"].get("model")
    if not base_url or not api_key or not model:
        return {"ok": False, "message": "未配置 Base URL / API Key / Model"}

    try:
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
        import re
        status = getattr(e, "status_code", None)
        extra = ""
        if status == 404:
            extra = "（请确认 Base URL 不要重复包含 /v1，例如填 https://api.openai.com 而不是 https://api.openai.com/v1）"
        message = f"请求失败: {status} {extra} {str(e)}".strip()[:260]
        return {"ok": False, "message": message}
