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

# llama.cpp llama-server
if ($LlamaCpp) {
  $targetExe = "$side\llama.cpp\llama-server.exe"
  if (-not (Test-Path $targetExe)) {
    $zip = "$env:TEMP\llama.zip"
    Fetch "https://github.com/ggml-org/llama.cpp/releases/download/b4372/llama-b4372-bin-win-avx2-x64.zip" $zip
    $targetDir = "$side\llama.cpp"
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    tar -xf $zip -C $targetDir "llama-server.exe" "*.dll"
  }
}

# FFmpeg 静态构建（Windows 示例；Linux/macOS 请用对应构建）
if ($Ffmpeg) {
  $zip = "$env:TEMP\ffmpeg-release-essentials.zip"
  Fetch "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" $zip
  $destBin = "$side\media\ffmpeg\bin"
  $destRoot = "$side\media\ffmpeg"
  New-Item -ItemType Directory -Force -Path $destBin | Out-Null
  tar -xf $zip --strip-components 2 -C $destBin "*/bin/ffmpeg.exe" "*/bin/ffprobe.exe"
  Copy-Item "$destBin\ffmpeg.exe" "$destRoot\" -Force
  Copy-Item "$destBin\ffprobe.exe" "$destRoot\" -Force
}

# LibreOffice（Windows 示例：自动拉取并解包为自包含绿色渲染器）
if ($LibreOffice) {
  $msi = "$env:TEMP\libreoffice.msi"
  Fetch "https://mirrors.ustc.edu.cn/tdf/libreoffice/stable/26.8.0/win/x86_64/LibreOffice_26.8.0_Win_x86-64.msi" $msi
  $target = "$env:TEMP\lo_unpack"
  if (Test-Path $target) { Remove-Item -Recurse -Force $target }
  Start-Process -FilePath "msiexec.exe" -ArgumentList "/a `"$msi`" /qn TARGETDIR=`"$target`"" -Wait
  $loRoot = "$side\media\libreoffice"
  New-Item -ItemType Directory -Force -Path $loRoot | Out-Null
  $found = Get-ChildItem -Path $target -Filter "soffice.exe" -Recurse | Select-Object -First 1
  if ($found) {
    Copy-Item "$($found.Directory.Parent.FullName)\*" $loRoot -Recurse -Force
  }
  Remove-Item -Recurse -Force $target
}

# Piper TTS（Windows 示例：piper_windows_amd64.zip + 中文模型）
if ($Piper) {
  Fetch "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_amd64.zip" "$env:TEMP\piper.zip"
  Expand-Archive "$env:TEMP\piper.zip" "$side\tts\piper" -Force
  Fetch "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx" "$side\tts\models\zh_CN-huayan-medium.onnx"
}

# Python standalone（免安装，CPython 3.10 + 依赖预置）
if ($PythonStandalone) {
  $pyTar = "$env:TEMP\python-standalone.tar.gz"
  Fetch "https://github.com/astral-sh/python-build-standalone/releases/download/20260924/cpython-3.10.21%2B20260924-x86_64-pc-windows-msvc-install_only.tar.gz" $pyTar
  $dest = "$side\python\runtime"
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  tar -xzf $pyTar -C $dest --strip-components 1
  & "$dest\python.exe" -m pip install -r "$root\plugins\ppt-master\requirements.txt"
}

# CosyVoice（模型 + 源码，体积较大）
if ($CosyVoice) {
  Write-Host "CosyVoice：git clone https://github.com/FunAudioLLM/CosyVoice.git 并下载 CosyVoice2-0.5B 模型" -ForegroundColor Yellow
}

Write-Host "完成。请核对 sidecars/ 下各运行时是否就绪。" -ForegroundColor Green
