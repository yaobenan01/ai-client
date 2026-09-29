# 本地一键打包桌面应用（CI 不可用时的备用路径）
# 前置：已安装 Rust 工具链（cargo/rustc）、Node + pnpm
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# 1) 目标三元组 —— Tauri v2 的 externalBin 要求文件名带 triple 后缀
$hostLine = (& rustc -vV | Select-String '^host:\s*(.+)$')
if (-not $hostLine) { throw "无法获取 rustc host 目标三元组，请先安装 Rust 工具链" }
$triple = $hostLine.Matches[0].Groups[1].Value.Trim()
Write-Host "==> 目标三元组：$triple" -ForegroundColor Cyan

# 2) 构建 core（release）
Write-Host "==> 构建 core（release）" -ForegroundColor Cyan
Push-Location "$root\core"
cargo build --release
Pop-Location

# 3) 暂存 core 为 Tauri externalBin（带 triple 后缀 + 无后缀各一份）
$isWindows = ($env:OS -eq "Windows_NT")
$coreName = if ($isWindows) { "ai-client.exe" } else { "ai-client" }
$src = Join-Path "$root\core\target\release" $coreName
if (-not (Test-Path $src)) { throw "未找到 core 产物：$src" }

$binDir = Join-Path $root "desktop\src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
$ext = [System.IO.Path]::GetExtension($coreName)
Copy-Item $src (Join-Path $binDir "ai-client-$triple$ext") -Force
Copy-Item $src (Join-Path $binDir "ai-client$ext") -Force
Get-ChildItem $binDir | Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,2)}} | Format-Table -AutoSize

# 4) 校验内置运行时 sidecars 是否齐备（保证「安装即用」目标）
Write-Host "==> 校验内置运行时" -ForegroundColor Cyan
$missing = @()
if (-not (Test-Path "$root\sidecars\llama.cpp\llama-server.exe")) { $missing += "llama.cpp" }
if (-not (Test-Path "$root\sidecars\python\runtime\python.exe")) { $missing += "python" }
if (-not (Test-Path "$root\sidecars\media\ffmpeg\bin\ffmpeg.exe")) { $missing += "ffmpeg" }
if (-not (Test-Path "$root\sidecars\media\libreoffice\program\soffice.exe")) { $missing += "libreoffice" }
if ($missing.Count -gt 0) {
    Write-Host "检测到部分内置运行时缺失：$($missing -join ', ')，自动拉取补齐..." -ForegroundColor Yellow
    & "$root\scripts\fetch-sidecars.ps1" -All
} else {
    Write-Host "内置运行时全部齐备（llama.cpp, python, ffmpeg, libreoffice），将被打入安装包。" -ForegroundColor Green
}

# 5) 打包（tauri.conf.json 的 beforeBuildCommand 会自动构建 web/dist）
Write-Host "==> Tauri 打包" -ForegroundColor Cyan
Push-Location "$root\desktop"
pnpm install
pnpm tauri build
Pop-Location

Write-Host "完成。安装包位于 desktop/src-tauri/target/release/bundle/" -ForegroundColor Green
Write-Host "安装包已完整内置 Python、FFmpeg、LibreOffice 及模型运行环境，支持目标机器离线开箱即用。" -ForegroundColor Cyan

