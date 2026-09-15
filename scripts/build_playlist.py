#!/usr/bin/env python3
"""Build a small, health-checked APTV playlist with per-channel fallbacks."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (AppleTV; carplay-iptv health check)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("sources.json"))
    parser.add_argument("--output", type=Path, default=Path("carplay.m3u"))
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def fetch(url: str, timeout: float, limit: int = 131072) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=timeout) as response:
        return response.read(limit), response.geturl()


def playlist_links(payload: bytes) -> list[str]:
    text = payload.decode("utf-8", errors="replace")
    if "#EXTM3U" not in text[:1024]:
        return []
    return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]


def probe_hls(url: str, timeout: float) -> None:
    payload, final_url = fetch(url, timeout)
    links = playlist_links(payload)
    if not links:
        raise ValueError("不是有效的 HLS 播放列表")
    child_payload, child_url = fetch(urljoin(final_url, links[0]), timeout, 32768)
    if child_payload.startswith(b"#EXTM3U"):
        segments = playlist_links(child_payload)
        if not segments:
            raise ValueError("子播放列表中没有视频片段")
        fetch(urljoin(child_url, segments[0]), timeout, 32768)


def validate_channel(channel: object, index: int) -> dict[str, object]:
    if not isinstance(channel, dict):
        raise ValueError(f"第 {index} 个频道必须是对象")
    for field in ("name", "tvg_id", "group"):
        if not isinstance(channel.get(field), str) or not str(channel[field]).strip():
            raise ValueError(f"第 {index} 个频道缺少有效 {field}")
    urls = channel.get("urls")
    if not isinstance(urls, list) or not urls:
        raise ValueError(f"频道 {channel['name']!r} 缺少备用地址列表")
    if any(not isinstance(url, str) or not is_http_url(url) for url in urls):
        raise ValueError(f"频道 {channel['name']!r} 包含无效 HTTP(S) 地址")
    return channel


def select_stream(channel: dict[str, object], timeout: float) -> tuple[dict[str, object], str | None, list[str]]:
    failures: list[str] = []
    for url in channel["urls"]:
        try:
            probe_hls(str(url), timeout)
            return channel, str(url), failures
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            failures.append(f"{url}: {type(exc).__name__}")
    return channel, None, failures


def escape_attribute(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build(config_path: Path, output_path: Path, timeout: float, workers: int) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    raw_channels = config.get("channels")
    minimum_channels = config.get("minimum_channels", 1)
    if not isinstance(raw_channels, list) or not raw_channels:
        raise ValueError("sources.json 必须包含非空 channels 数组")
    if not isinstance(minimum_channels, int) or minimum_channels < 1:
        raise ValueError("minimum_channels 必须是正整数")
    channels = [validate_channel(channel, index) for index, channel in enumerate(raw_channels, 1)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        selected = list(pool.map(lambda channel: select_stream(channel, timeout), channels))

    available = [(channel, url) for channel, url, _ in selected if url]
    for channel, url, failures in selected:
        if url:
            fallback_note = "（使用备用源）" if url != channel["urls"][0] else ""
            print(f"[可用] {channel['name']}{fallback_note}")
        else:
            print(f"[跳过] {channel['name']}: {'; '.join(failures)}", file=sys.stderr)

    if len(available) < minimum_channels:
        raise RuntimeError(
            f"仅 {len(available)} 个频道通过健康检查，低于安全阈值 {minimum_channels}；未覆盖上一版播放列表"
        )

    lines = ["#EXTM3U"]
    for channel, url in available:
        tvg_id = escape_attribute(str(channel["tvg_id"]))
        group = escape_attribute(str(channel["group"]))
        name = str(channel["name"]).replace("\n", " ").strip()
        lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{group}",{name}')
        lines.append(str(url))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[完成] 写入 {len(available)} 个已实测频道到 {output_path}")
    return len(available)


def main() -> int:
    args = parse_args()
    try:
        build(args.config, args.output, args.timeout, args.workers)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
