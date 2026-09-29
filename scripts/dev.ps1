﻿# 开发模式：启动 headless 核心 + 前端 dev server
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "==> 构建核心引擎（debug）" -ForegroundColor Cyan
Push-Location "$root\core"
cargo build
if ($LASTEXITCODE -ne 0) { throw "cargo build 失败" }
Pop-Location

Write-Host "==> 启动核心引擎 http://127.0.0.1:8787" -ForegroundColor Cyan
$core = Start-Process -FilePath "$root\core\target\debug\ai-client.exe" -ArgumentList "serve","--data-dir","$root\.dev-data" -PassThru -WindowStyle Hidden

Write-Host "==> 启动前端 http://localhost:5173" -ForegroundColor Cyan
Push-Location "$root\web"
pnpm install
pnpm dev
Pop-Location

# Ctrl+C 后清理
if ($core -and !$core.HasExited) { Stop-Process -Id $core.Id -Force }
