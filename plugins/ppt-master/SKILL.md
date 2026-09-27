---
name: ppt-master
description: >-
  将 PDF / DOCX / Markdown / 文本材料生成原生可编辑 PPTX，并把 PPTX + 演讲者备注
  渲染为带本地 TTS 旁白的 MP4 口播视频。使用 python-pptx 与 PyMuPDF、本地 CosyVoice/Piper、
  LibreOffice 与 FFmpeg，全程离线。
---
# ppt-master（内置插件）

- 生成：`python run.py generate --input <材料> --out <目录>`
- 视频：`python render_video.py --pptx <文件> --out <输出> --tts cosyvoice`
