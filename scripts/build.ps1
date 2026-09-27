# 构建 web + core（release）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "==> 构建前端" -ForegroundColor Cyan
Push-Location "$root\web"
pnpm install
pnpm build
Pop-Location

Write-Host "==> 构建核心引擎（release）" -ForegroundColor Cyan
Push-Location "$root\core"
cargo build --release
Pop-Location

Write-Host "完成。产物：web/dist 与 core/target/release/ai-client" -ForegroundColor Green
