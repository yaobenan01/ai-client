#!/usr/bin/env bash
# Linux/macOS：拉取/准备离线附件运行时（构建期在开发机执行）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIDE="$ROOT/sidecars"
mkdir -p "$SIDE/llama.cpp/bin" "$SIDE/tts/models" "$SIDE/media/ffmpeg" "$SIDE/python/runtime"

echo "==> 提示：请按平台获取以下运行时（离线分发，目标机免安装）"
echo "  llama.cpp  : https://github.com/ggml-org/llama.cpp/releases -> sidecars/llama.cpp/bin/<platform>/"
echo "  FFmpeg     : 静态构建 -> sidecars/media/ffmpeg/"
echo "  LibreOffice: 系统包或便携版 -> sidecars/media/libreoffice/  (Linux 优先检测 soffice)"
echo "  Piper      : https://github.com/rhasspy/piper/releases + zh_CN-huayan-medium.onnx -> sidecars/tts/"
echo "  CosyVoice  : git clone https://github.com/FunAudioLLM/CosyVoice.git + CosyVoice2-0.5B 模型"
echo "  Python     : python-build-standalone -> sidecars/python/runtime/"
