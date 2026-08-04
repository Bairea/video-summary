"""服务层纯逻辑测试（对应旧 mindmapService.test.ts / qaService.test.ts）。"""

from video_summary.services.mindmap_service import normalize_markmap_markdown
from video_summary.services.qa_service import pick_context, safe_json_parse, tokenize

SEGMENTS = [
    {"startMs": 0, "endMs": 1000, "text": "今天讲的是机器学习的基础概念"},
    {"startMs": 1000, "endMs": 2000, "text": "模型训练需要大量数据"},
    {"startMs": 2000, "endMs": 3000, "text": "推理阶段关注速度"},
]


def test_normalize_markmap_with_heading():
    out = normalize_markmap_markdown("# 主题\n\n## 章节\n- 要点")
    assert out == "# 主题\n\n## 章节\n- 要点"


def test_normalize_markmap_fenced():
    out = normalize_markmap_markdown("```markdown\n# 主题\n\n- a\n- b\n```")
    assert out == "# 主题\n\n- a\n- b"


def test_normalize_markmap_plain_lines():
    out = normalize_markmap_markdown("1. 第一点\n- 第二点\n第三点")
    assert out == "# 视频要点\n\n- 第一点\n- 第二点\n- 第三点"


def test_normalize_markmap_keeps_existing_heading_lines():
    # 与旧实现一致：任何以 # 开头的行存在时原样返回
    out = normalize_markmap_markdown("1. 第一点\n### 第三点")
    assert out == "1. 第一点\n### 第三点"


def test_normalize_markmap_empty():
    assert normalize_markmap_markdown("") == "# 视频要点\n\n- 暂无内容"


def test_tokenize():
    tokens = tokenize("机器学习 训练 数据？")
    assert "机器学习" in tokens
    assert "训练" in tokens
    assert len([t for t in tokens if len(t) < 2]) == 0


def test_pick_context_ranks():
    picked = pick_context("机器学习 数据", SEGMENTS)
    assert picked[0]["startMs"] == 0  # 匹配 2 个词
    assert len(picked) <= 10


def test_pick_context_empty_question_falls_back():
    picked = pick_context("???", SEGMENTS)
    assert picked == SEGMENTS[:10]


def test_safe_json_parse():
    assert safe_json_parse('{"answer": "ok"}')["answer"] == "ok"
    assert safe_json_parse('前缀{"answer": "ok"}后缀')["answer"] == "ok"
    assert safe_json_parse("不是 json") is None
