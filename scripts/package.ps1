# 打包桌面应用（需先执行 build.ps1，并把 core 二进制放到 desktop/src-tauri/binaries/）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$binDir = "$root\desktop\src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
$coreExe = if ($env:OS -eq "Windows_NT") { "ai-client.exe" } else { "ai-client" }
Copy-Item "$root\core\target\release\$coreExe" "$binDir\ai-client" -Force

Write-Host "==> Tauri 打包" -ForegroundColor Cyan
Push-Location "$root\desktop"
pnpm install
pnpm tauri build
Pop-Location

Write-Host "完成。安装包位于 desktop/src-tauri/target/release/bundle/" -ForegroundColor Green
