# CarPlay IPTV 自动更新订阅

这是一个完全免费的 IPTV 播放列表聚合项目。GitHub Actions 每 6 小时读取 `sources.json` 中启用的公开频道源，去重后生成 `carplay.m3u`，可直接作为 APTV 的远程订阅。

## APTV 订阅地址

```text
https://raw.githubusercontent.com/BinDoooo/carplay-iptv/main/carplay.m3u
```

在 APTV 中新建订阅，类型选择 M3U/远程播放列表，粘贴上面的地址即可。首次提交后若暂时无法访问，请等待约 1 分钟再刷新。

## 自动更新

- 默认每 6 小时运行一次，也可在仓库的 **Actions → Update IPTV playlist → Run workflow** 手动运行。
- 只有播放列表内容变化时才会自动提交，避免无意义的提交记录。
- 单个来源暂时失效不会阻止其他来源更新；如果所有来源均失效，脚本会失败并保留上一版订阅。
- 不需要服务器、域名、数据库或付费服务。

## 自定义频道源

编辑 `sources.json`，按下面的格式增加、关闭或删除来源：

```json
{
  "sources": [
    {
      "name": "示例频道源",
      "url": "https://example.com/playlist.m3u",
      "enabled": true
    }
  ]
}
```

只支持公开的 `http://` 或 `https://` M3U/M3U8 播放列表地址。请确保你有权访问和使用所添加的频道源。

## 本地生成

项目只使用 Python 标准库，无需安装依赖：

```bash
python3 scripts/build_playlist.py
```

可选参数：

```bash
python3 scripts/build_playlist.py --config sources.json --output carplay.m3u --timeout 25
```

## 文件说明

- `sources.json`：上游公开频道源配置。
- `scripts/build_playlist.py`：下载、解析、校验和去重脚本。
- `carplay.m3u`：供 APTV 订阅的最终播放列表。
- `.github/workflows/update.yml`：定时与手动更新任务。

## 使用提醒

本项目只整理上游公开链接，不托管视频内容，也不保证频道永久可用。请遵守频道版权、当地法律及服务条款。驾驶过程中请勿操作或观看视频，仅在安全停车后使用。
