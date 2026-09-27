# ppt-master 插件集成

集成官方开源主线 `hugohe3/ppt-master`（Skill 工作流），并由本项目内置 Python 运行时执行。

- 官方主线克隆到 `plugins/ppt-master/src/`（gitignored，构建期拉取）。
- 本项目额外提供两个驱动脚本，供核心引擎直接调用：
  - `run.py`：生成可编辑 PPTX（含 Markdown/文本快速生成兜底）
  - `render_video.py`：PPTX → 口播 MP4（本地 TTS + FFmpeg）
- 官方默认的网络 TTS 已替换为本地 CosyVoice / Piper，满足全离线。
