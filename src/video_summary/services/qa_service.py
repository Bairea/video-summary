"""引用式问答。与旧 TS qaService.ts 行为一致。"""

import asyncio
import json
import re

from .openai_compat import chat_complete

QA_SYSTEM_PROMPT = (
    '你是一个基于字幕的问答助手。只使用提供的字幕上下文回答；不确定就明确说明证据不足。输出严格 JSON：{"answer": "...", "insufficientEvidence": false, "citations": [{"startMs":0,"endMs":0,"text":"..."}]}。当无法确认时，insufficientEvidence 必须为 true，且 citations 可以为空。'
)


def tokenize(s: str) -> list[str]:
    return [t for t in re.sub(r"[^\w一-鿿]+", " ", s.lower()).split() if len(t) >= 2][:50]


def score_segment(q_tokens: list[str], seg: dict) -> int:
    t = seg["text"].lower()
    return sum(1 for tok in q_tokens if tok in t)


def pick_context(question: str, segments: list[dict]) -> list[dict]:
    q_tokens = tokenize(question)
    scored = [s for s in segments if score_segment(q_tokens, s) > 0]
    scored.sort(key=lambda s: score_segment(q_tokens, s), reverse=True)
    if scored:
        return scored[:10]
    return segments[:10]


def safe_json_parse(s: str):
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, TypeError):
            return None


async def answer_question(question: str, segments: list[dict], mode: str | None = None,
                          signal: asyncio.Event | None = None) -> dict:
    ctx = pick_context(question, segments)
    ctx_text = "\n".join(f"[{s['startMs']}-{s['endMs']}] {s['text']}" for s in ctx)

    raw = await chat_complete([
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"问题：{question}\n\n回答风格：{'详细' if mode == 'detailed' else '简洁'}\n\n字幕上下文：\n{ctx_text}",
        },
    ], signal=signal)

    parsed = safe_json_parse(raw)
    answer = (parsed.get("answer") if isinstance(parsed, dict) else None) or raw.strip()
    citations = []
    if isinstance(parsed, dict) and isinstance(parsed.get("citations"), list):
        citations = [c for c in parsed["citations"] if isinstance(c, dict) and isinstance(c.get("text"), str)][:8]
    insufficient_evidence = isinstance(parsed, dict) and parsed.get("insufficientEvidence") is True or len(citations) == 0

    return {"answer": answer, "citations": citations, "insufficientEvidence": insufficient_evidence}
