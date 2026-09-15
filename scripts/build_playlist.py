#!/usr/bin/env python3
"""Build a deterministic M3U playlist from public upstream playlists."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = "carplay-iptv/1.0 (+https://github.com/BinDoooo/carplay-iptv)"


@dataclass(frozen=True)
class Entry:
    metadata: tuple[str, ...]
    stream_url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("sources.json"))
    parser.add_argument("--output", type=Path, default=Path("carplay.m3u"))
    parser.add_argument("--timeout", type=float, default=25.0)
    return parser.parse_args()


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def decode_playlist(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def download(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=timeout) as response:
        return decode_playlist(response.read())


def parse_m3u(text: str) -> Iterable[Entry]:
    metadata: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            continue
        if line.startswith("#"):
            if line.startswith("#EXTINF"):
                metadata = [line]
            elif metadata:
                metadata.append(line)
            continue
        if metadata and is_http_url(line):
            yield Entry(tuple(metadata), line)
        metadata = []


def load_sources(config_path: Path) -> list[dict[str, object]]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise ValueError("sources.json 必须包含 sources 数组")

    enabled: list[dict[str, object]] = []
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise ValueError(f"第 {index} 个来源必须是对象")
        if not source.get("enabled", True):
            continue
        name = source.get("name")
        url = source.get("url")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"第 {index} 个来源缺少有效 name")
        if not isinstance(url, str) or not is_http_url(url):
            raise ValueError(f"来源 {name!r} 缺少有效的 HTTP(S) URL")
        enabled.append(source)
    if not enabled:
        raise ValueError("没有启用的频道源")
    return enabled


def build(config_path: Path, output_path: Path, timeout: float) -> int:
    sources = load_sources(config_path)
    entries: list[Entry] = []
    seen_urls: set[str] = set()
    failures: list[str] = []

    for source in sources:
        name = str(source["name"])
        url = str(source["url"])
        try:
            source_entries = list(parse_m3u(download(url, timeout)))
            if not source_entries:
                raise ValueError("未找到有效频道")
            added = 0
            for entry in source_entries:
                if entry.stream_url in seen_urls:
                    continue
                seen_urls.add(entry.stream_url)
                entries.append(entry)
                added += 1
            print(f"[成功] {name}: 读取 {len(source_entries)}，新增 {added}")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            failures.append(f"{name}: {exc}")
            print(f"[失败] {name}: {exc}", file=sys.stderr)

    if not entries:
        details = "; ".join(failures) if failures else "未知错误"
        raise RuntimeError(f"所有频道源均不可用，未覆盖现有播放列表：{details}")

    lines = ["#EXTM3U"]
    for entry in entries:
        lines.extend(entry.metadata)
        lines.append(entry.stream_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[完成] 写入 {len(entries)} 个去重频道到 {output_path}")
    if failures:
        print(f"[警告] {len(failures)} 个来源读取失败，其余来源已正常生成", file=sys.stderr)
    return len(entries)


def main() -> int:
    args = parse_args()
    try:
        build(args.config, args.output, args.timeout)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
