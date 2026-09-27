# 拉取/准备离线附件运行时（在开发机构建期执行，产物随应用分发）
# 目标机器无需安装 Python / FFmpeg / LibreOffice / 模型。
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$side = "$root\sidecars"

param(
  [switch]$LlamaCpp,
  [switch]$Ffmpeg,
  [switch]$LibreOffice,
  [switch]$Piper,
  [switch]$CosyVoice,
  [switch]$PythonStandalone,
  [switch]$All
)
if ($All) { $LlamaCpp=$true; $Ffmpeg=$true; $LibreOffice=$true; $Piper=$true; $CosyVoice=$true; $PythonStandalone=$true }

function Fetch($url, $dest) {
  $dir = Split-Path -Parent $dest
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Write-Host "==> 下载 $url" -ForegroundColor Cyan
  $ProgressPreference = 'SilentlyContinue'
  Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

# llama.cpp llama-server（按平台选择 release 压缩包）
if ($LlamaCpp) {
  Write-Host "llama.cpp：请从 https://github.com/ggml-org/llama.cpp/releases 下载对应平台的 llama-server"
  Write-Host "  并解压到 sidecars/llama.cpp/bin/<platform>/" -ForegroundColor Yellow
}

# FFmpeg 静态构建（Windows 示例；Linux/macOS 请用对应构建）
if ($Ffmpeg) {
  Fetch "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" "$env:TEMP\ffmpeg.zip"
  Expand-Archive "$env:TEMP\ffmpeg.zip" "$side\media\ffmpeg" -Force
}

# LibreOffice portable（Windows 示例）
if ($LibreOffice) {
  Write-Host "LibreOffice：请下载 Portable 版本解压到 sidecars/media/libreoffice/" -ForegroundColor Yellow
}

# Piper TTS（Windows 示例：piper_windows_amd64.zip + 中文模型）
if ($Piper) {
  Fetch "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_amd64.zip" "$env:TEMP\piper.zip"
  Expand-Archive "$env:TEMP\piper.zip" "$side\tts\piper" -Force
  Fetch "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx" "$side\tts\models\zh_CN-huayan-medium.onnx"
}

# Python standalone（免安装，跨平台）
if ($PythonStandalone) {
  Write-Host "python-build-standalone：请按平台下载并解压到 sidecars/python/runtime/" -ForegroundColor Yellow
}

# CosyVoice（模型 + 源码，体积较大）
if ($CosyVoice) {
  Write-Host "CosyVoice：git clone https://github.com/FunAudioLLM/CosyVoice.git 并下载 CosyVoice2-0.5B 模型" -ForegroundColor Yellow
}

Write-Host "完成。请核对 sidecars/ 下各运行时是否就绪。" -ForegroundColor Green
