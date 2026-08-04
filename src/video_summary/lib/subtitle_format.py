"""字幕段到 SRT/VTT 文本的格式化。"""

from ..types import TranscriptSegment


def _pad2(n: int) -> str:
    return str(n).zfill(2)


def _pad3(n: int) -> str:
    return str(n).zfill(3)


def ms_to_srt_time(ms: int) -> str:
    t = max(0, int(ms))
    hh, rem = divmod(t, 3600000)
    mm, rem = divmod(rem, 60000)
    ss, mmm = divmod(rem, 1000)
    return f"{_pad2(hh)}:{_pad2(mm)}:{_pad2(ss)},{_pad3(mmm)}"


def ms_to_vtt_time(ms: int) -> str:
    t = max(0, int(ms))
    hh, rem = divmod(t, 3600000)
    mm, rem = divmod(rem, 60000)
    ss, mmm = divmod(rem, 1000)
    return f"{_pad2(hh)}:{_pad2(mm)}:{_pad2(ss)}.{_pad3(mmm)}"


def _clean(s: str) -> str:
    return str(s or "").replace("\r", "").strip()


def segments_to_srt(segments: list[TranscriptSegment]) -> str:
    blocks = []
    for idx, s in enumerate(segments):
        blocks.append(
            f"{idx + 1}\n{ms_to_srt_time(s['startMs'])} --> {ms_to_srt_time(s['endMs'])}\n{_clean(s['text'])}\n"
        )
    return "\n".join(blocks).rstrip() + "\n"


def segments_to_vtt(segments: list[TranscriptSegment]) -> str:
    blocks = []
    for s in segments:
        blocks.append(
            f"{ms_to_vtt_time(s['startMs'])} --> {ms_to_vtt_time(s['endMs'])}\n{_clean(s['text'])}\n"
        )
    return f"WEBVTT\n\n{''.join(blocks)}".rstrip() + "\n"
