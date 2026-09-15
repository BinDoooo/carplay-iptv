# CarPlay IPTV 自动更新订阅

这是一个“小而精”的免费 IPTV 播放列表。它不再塞入大量地方台，而是保留纪录片、自然、汽车、户外、搞笑、美食旅行、经典影视、少儿和亚洲资讯等精选频道，可直接作为 APTV 的远程订阅。

## APTV 订阅地址

```text
https://raw.githubusercontent.com/BinDoooo/carplay-iptv/main/carplay.m3u
```

在 APTV 中新建订阅，类型选择 M3U/远程播放列表，粘贴上面的地址即可。首次提交后若暂时无法访问，请等待约 1 分钟再刷新。

## 自动更新

- 默认每 6 小时运行一次，也可在仓库的 **Actions → Update IPTV playlist → Run workflow** 手动运行。
- 每次更新都会实际读取 HLS 清单和首个视频片段，只写入当时通过健康检查的频道。
- 多数频道配置了备用 CDN，主地址失效时自动切换。
- 只有播放列表内容变化时才会提交；如果可用频道少于安全阈值，则保留上一版订阅。
- 不需要服务器、域名、数据库或付费服务。

## 自定义频道源

编辑 `sources.json`，按下面的格式增加、删除频道或设置备用地址：

```json
{
  "minimum_channels": 1,
  "channels": [
    {
      "name": "示例频道",
      "tvg_id": "Example.tv",
      "group": "精选·示例",
      "urls": [
        "https://example.com/primary.m3u8",
        "https://example.com/fallback.m3u8"
      ]
    }
  ]
}
```

只支持公开的 `http://` 或 `https://` HLS 播放列表。地址按顺序尝试，第一个通过清单与视频片段检查的地址会写入最终订阅。

## 本地生成

项目只使用 Python 标准库，无需安装依赖：

```bash
python3 scripts/build_playlist.py
```

可选参数：

```bash
python3 scripts/build_playlist.py --config sources.json --output carplay.m3u --timeout 8 --workers 8
```

## 文件说明

- `sources.json`：精选频道、分类和备用地址配置。
- `scripts/build_playlist.py`：并发健康检查与自动备用源选择脚本。
- `carplay.m3u`：供 APTV 订阅的最终播放列表。
- `.github/workflows/update.yml`：定时与手动更新任务。

## 使用提醒

本项目只整理上游公开链接，不托管视频内容，也不保证频道永久可用。请遵守频道版权、当地法律及服务条款。驾驶过程中请勿操作或观看视频，仅在安全停车后使用。
