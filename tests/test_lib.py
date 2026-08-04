"""字幕解析/格式化与 cookies 转换测试（对应旧 subtitleService.test.ts / ytdlpService.test.ts 相关用例）。"""

from video_summary.lib.cookies import cookie_header_to_netscape, is_probably_netscape_cookies
from video_summary.lib.subtitle_format import segments_to_srt, segments_to_vtt
from video_summary.lib.subtitle_parse import parse_srt, parse_vtt, segments_to_text

SRT_SAMPLE = """1
00:00:01,000 --> 00:00:03,500
Hello <b>world</b>

2
00:00:04,000 --> 00:00:06,000
Second line
still second
"""

VTT_SAMPLE = """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello world

00:00:04.000 --> 00:00:06.000
Second line
"""


def test_parse_srt():
    segments = parse_srt(SRT_SAMPLE)
    assert len(segments) == 2
    assert segments[0]["startMs"] == 1000
    assert segments[0]["endMs"] == 3500
    assert segments[0]["text"] == "Hello world"
    assert segments[1]["text"] == "Second line still second"


def test_parse_srt_millisecond_formats():
    segments = parse_srt("1\n00:00:01,234 --> 00:00:02,567\ntext\n")
    assert segments[0]["startMs"] == 1234
    assert segments[0]["endMs"] == 2567


def test_parse_vtt():
    segments = parse_vtt(VTT_SAMPLE)
    assert len(segments) == 2
    assert segments[0]["startMs"] == 1000
    assert segments[1]["text"] == "Second line"


def test_segments_to_text():
    assert segments_to_text([{"startMs": 0, "endMs": 1, "text": "a"}, {"startMs": 1, "endMs": 2, "text": "b"}]) == "a\nb"


def test_srt_round_trip():
    segments = [{"startMs": 1000, "endMs": 3500, "text": "Hello world"}]
    srt = segments_to_srt(segments)
    assert parse_srt(srt) == segments


def test_vtt_round_trip():
    segments = [{"startMs": 1000, "endMs": 3500, "text": "Hello world"}]
    vtt = segments_to_vtt(segments)
    assert vtt.startswith("WEBVTT")
    assert parse_vtt(vtt) == segments


def test_is_probably_netscape_cookies():
    assert is_probably_netscape_cookies("# Netscape HTTP Cookie File\n")
    assert is_probably_netscape_cookies(".bilibili.com\tTRUE\t/\tTRUE\t0\tsessdata\tabc")
    assert not is_probably_netscape_cookies("name=value; other=2")
    assert not is_probably_netscape_cookies("")


def test_cookie_header_to_netscape():
    out = cookie_header_to_netscape("SESSDATA=abc; bili_jct=xyz")
    assert out.startswith("# Netscape HTTP Cookie File")
    assert ".bilibili.com\tTRUE\t/\tTRUE\t" in out
    assert "SESSDATA\tabc" in out
    assert "bili_jct\txyz" in out
