"""cookies 格式转换：Cookie 请求头 <-> Netscape 格式文件。"""

import time

HEADER_PREFIX = "# Netscape HTTP Cookie File"


def is_probably_netscape_cookies(content: str) -> bool:
    s = str(content or "")
    if not s.strip():
        return False
    if HEADER_PREFIX in s:
        return True
    lines = [l for l in s.splitlines() if l]
    return any(len(l.split("\t")) >= 7 for l in lines)


def _parse_cookie_header(header: str) -> list[dict]:
    parts = [p.strip() for p in str(header or "").split(";") if p.strip()]
    cookies = []
    for part in parts:
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name:
            cookies.append({"name": name, "value": value})
    return cookies


def cookie_header_to_netscape(header: str, domain: str = ".bilibili.com", secure: bool = True) -> str:
    now = int(time.time())
    expires = now + 365 * 24 * 60 * 60
    lines = [
        HEADER_PREFIX,
        "# https://curl.se/docs/http-cookies.html",
        "# This file was generated from Cookie header string.",
        "",
    ]
    for c in _parse_cookie_header(header):
        lines.append("\t".join([
            domain, "TRUE", "/", "TRUE" if secure else "FALSE", str(expires), c["name"], c["value"],
        ]))
    return "\n".join(lines) + "\n"
