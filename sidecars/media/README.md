# 媒体运行时（LibreOffice + FFmpeg）

## LibreOffice headless
- 作用：PPTX → PDF（原生渲染，保留版式）。
- 命令：`soffice --headless --convert-to pdf --outdir <dir> <file>.pptx`
- 打包：内置便携版（Windows/macOS）；Linux 优先检测系统 `soffice`/`libreoffice`。

## FFmpeg
- 作用：图片序列 + 音频 → MP4；转场、字幕烧录、背景音乐。
- 打包：内置静态构建（`ffmpeg` / `ffmpeg.exe`）。

## PDF → PNG
- 使用 PyMuPDF(fitz)，随 ppt-master 依赖一起安装，无需额外二进制。
