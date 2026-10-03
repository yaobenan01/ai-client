# 拉取/准备离线附件运行时（在开发机构建期执行，产物随应用分发）
# 目标机器无需安装 Python / FFmpeg / LibreOffice / 模型。
param(
  [switch]$LlamaCpp,
  [switch]$Ffmpeg,
  [switch]$LibreOffice,
  [switch]$Piper,
  [switch]$CosyVoice,
  [switch]$PythonStandalone,
  [switch]$All
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$side = "$root\sidecars"

if ($All) {
  $LlamaCpp = $true
  $Ffmpeg = $true
  $LibreOffice = $true
  $Piper = $true
  $CosyVoice = $true
  $PythonStandalone = $true
}

function FetchWithFallback($urls, $dest) {
  $dir = Split-Path -Parent $dest
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
  $ProgressPreference = 'SilentlyContinue'
  foreach ($url in $urls) {
    try {
      Write-Host "==> 下载 $url" -ForegroundColor Cyan
      Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
      if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 1000)) {
        Write-Host "==> 下载成功: $url ($([math]::Round((Get-Item $dest).Length / 1MB, 2)) MB)" -ForegroundColor Green
        return
      }
    } catch {
      Write-Warning "从 $url 下载失败: $_"
    }
  }
  throw "未能从任何镜像源下载成功: $($urls -join ', ')"
}

function Fetch($url, $dest) {
  FetchWithFallback @($url) $dest
}

# 1) llama.cpp llama-server
if ($LlamaCpp) {
  $targetExe = "$side\llama.cpp\llama-server.exe"
  if (-not (Test-Path $targetExe)) {
    Write-Host "==> 准备 llama-server..." -ForegroundColor Cyan
    $zip = "$env:TEMP\llama.zip"
    Fetch "https://github.com/ggml-org/llama.cpp/releases/download/b4372/llama-b4372-bin-win-avx2-x64.zip" $zip
    $targetDir = "$side\llama.cpp"
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    tar -xf $zip -C $targetDir
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
  } else {
    Write-Host "llama-server 已存在，跳过拉取。" -ForegroundColor Green
  }
}

# 2) FFmpeg 静态构建（仅保留 ffmpeg.exe；ffprobe 当前无调用方，且避免重复存放）
if ($Ffmpeg) {
  $destExe = "$side\media\ffmpeg\bin\ffmpeg.exe"
  if (-not (Test-Path $destExe)) {
    Write-Host "==> 准备 FFmpeg..." -ForegroundColor Cyan
    $zip = "$env:TEMP\ffmpeg-release-essentials.zip"
    Fetch "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" $zip
    $tempExtract = "$env:TEMP\ffmpeg_unpack"
    if (Test-Path $tempExtract) { Remove-Item -Recurse -Force $tempExtract }
    New-Item -ItemType Directory -Force -Path $tempExtract | Out-Null
    tar -xf $zip -C $tempExtract

    $destBin = "$side\media\ffmpeg\bin"
    New-Item -ItemType Directory -Force -Path $destBin | Out-Null

    $ffExe = Get-ChildItem -Path $tempExtract -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
    if (-not $ffExe) { throw "未在压缩包中找到 ffmpeg.exe" }
    Copy-Item $ffExe.FullName "$destBin\ffmpeg.exe" -Force

    Remove-Item -Recurse -Force $tempExtract -ErrorAction SilentlyContinue
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
  } else {
    Write-Host "FFmpeg 已存在，跳过拉取。" -ForegroundColor Green
  }
  # 清理历史遗留的重复/无用文件，减小最终包体
  foreach ($legacy in @(
      "$side\media\ffmpeg\ffmpeg.exe",
      "$side\media\ffmpeg\ffprobe.exe",
      "$side\media\ffmpeg\bin\ffprobe.exe")) {
    if (Test-Path $legacy) { Remove-Item -Force $legacy -ErrorAction SilentlyContinue }
  }
}
# 3) LibreOffice（自动拉取并解包为自包含绿色渲染器，清理语言包体积）
if ($LibreOffice) {
  $sofficeExe = "$side\media\libreoffice\program\soffice.exe"
  if (-not (Test-Path $sofficeExe)) {
    Write-Host "==> 准备 LibreOffice..." -ForegroundColor Cyan
    $msi = "$env:TEMP\libreoffice.msi"
    $loUrls = @(
      "https://download.documentfoundation.org/libreoffice/stable/26.8.0/win/x86_64/LibreOffice_26.8.0_Win_x86-64.msi",
      "https://mirrors.ustc.edu.cn/tdf/libreoffice/stable/26.8.0/win/x86_64/LibreOffice_26.8.0_Win_x86-64.msi"
    )
    FetchWithFallback $loUrls $msi
    $target = "$env:TEMP\lo_unpack"
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
    Write-Host "==> 解包 LibreOffice MSI 提取绿色文件..." -ForegroundColor Cyan
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/a `"$msi`" /qn TARGETDIR=`"$target`"" -Wait
    $loRoot = "$side\media\libreoffice"
    New-Item -ItemType Directory -Force -Path $loRoot | Out-Null
    $found = Get-ChildItem -Path $target -Filter "soffice.exe" -Recurse | Select-Object -First 1
    if ($found) {
      Copy-Item "$($found.Directory.Parent.FullName)\*" $loRoot -Recurse -Force
      # 清理多余语言包，减小最终安装包体积
      if (Test-Path "$loRoot\share\extensions") {
        Get-ChildItem "$loRoot\share\extensions" -Exclude "*dict-en*", "*dict-zh*" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
      }
    } else {
      throw "解包 LibreOffice 失败：未找到 soffice.exe"
    }
    Remove-Item -Recurse -Force $target -ErrorAction SilentlyContinue
    Remove-Item $msi -Force -ErrorAction SilentlyContinue
  } else {
    Write-Host "LibreOffice 已存在，跳过拉取。" -ForegroundColor Green
  }
}

# 4) Piper TTS（Windows：piper.exe + 基础中文语音模型与配置文件）
if ($Piper) {
  $piperExe = "$side\tts\piper\piper.exe"
  if (-not (Test-Path $piperExe)) {
    Write-Host "==> 准备 Piper TTS..." -ForegroundColor Cyan
    Fetch "https://github.com/rhasspy/piper/releases/latest/download/piper_windows_amd64.zip" "$env:TEMP\piper.zip"
    Expand-Archive "$env:TEMP\piper.zip" "$side\tts\piper" -Force
    if (Test-Path "$side\tts\piper\piper\piper.exe") {
      Copy-Item "$side\tts\piper\piper\*" "$side\tts\piper\" -Recurse -Force
    }
    Remove-Item "$env:TEMP\piper.zip" -Force -ErrorAction SilentlyContinue
  } else {
    Write-Host "Piper TTS 已存在，跳过拉取。" -ForegroundColor Green
  }
  $modelDest = "$side\tts\models\zh_CN-huayan-medium.onnx"
  $jsonDest = "$side\tts\models\zh_CN-huayan-medium.onnx.json"
  if (-not (Test-Path $modelDest)) {
    try {
      Write-Host "==> 准备 Piper 中文模型权重..." -ForegroundColor Cyan
      Fetch "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx" $modelDest
    } catch {
      Write-Warning "下载 Piper 模型失败: $_"
    }
  }
  if (-not (Test-Path $jsonDest)) {
    try {
      Write-Host "==> 准备 Piper 中文模型配置..." -ForegroundColor Cyan
      Fetch "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json" $jsonDest
    } catch {
      Write-Warning "下载 Piper 模型配置失败: $_"
    }
  }
}

# 5) Python standalone（免安装，CPython 3.10 + 依赖预置）
if ($PythonStandalone) {
  $pythonExe = "$side\python\runtime\python.exe"
  if (-not (Test-Path $pythonExe)) {
    Write-Host "==> 准备 Python 独立免安装运行时..." -ForegroundColor Cyan
    $pyTar = "$env:TEMP\python-standalone.tar.gz"
    Fetch "https://github.com/astral-sh/python-build-standalone/releases/download/20260924/cpython-3.10.21%2B20260924-x86_64-pc-windows-msvc-install_only.tar.gz" $pyTar
    $dest = "$side\python\runtime"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    tar -xzf $pyTar -C $dest --strip-components 1
    Remove-Item $pyTar -Force -ErrorAction SilentlyContinue
    
    # 预装依赖
    Write-Host "==> 预装 ppt-master Python 依赖..." -ForegroundColor Cyan
    & "$dest\python.exe" -m pip install --upgrade pip
    if (Test-Path "$root\plugins\ppt-master\requirements.txt") {
      & "$dest\python.exe" -m pip install -r "$root\plugins\ppt-master\requirements.txt"
    }
  } else {
    Write-Host "Python 已存在，跳过拉取。" -ForegroundColor Green
  }
}

# 6) CosyVoice（模型 + 源码，体积较大）
if ($CosyVoice) {
  Write-Host "CosyVoice：git clone https://github.com/FunAudioLLM/CosyVoice.git 并下载 CosyVoice2-0.5B 模型" -ForegroundColor Yellow
}

Write-Host "完成。请核对 sidecars/ 下各运行时是否就绪。" -ForegroundColor Green
