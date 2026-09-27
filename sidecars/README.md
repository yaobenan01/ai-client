# 附件运行时（sidecars）

为保证「全离线、开箱即用」，以下运行时随应用一起分发，用户**无需**在目标机器安装 Python / FFmpeg / LibreOffice。

| 目录 | 内容 | 说明 |
| --- | --- | --- |
| `python/` | 内嵌 Python 运行时 | 用 python-build-standalone 或 uv 内嵌 Python，替代系统 Python |
| `tts/` | CosyVoice（默认）+ Piper（兜底） | 本地 TTS，中文口播 |
| `media/` | LibreOffice + FFmpeg | PPT 渲染与视频合成 |

打包策略：Linux 优先检测系统已装组件，缺失时回退内置版本；Windows/macOS 一律内置便携版。
