# 准备 ppt-master：拉取官方主线 + 用内嵌 Python 安装依赖（构建期在开发机执行）
param(
  [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$plugin = "$root\plugins\ppt-master"

if (-not $Python) {
  $Python = $env:AI_CLIENT_PYTHON
}
if (-not $Python -and (Test-Path "$root\sidecars\python\runtime\python.exe")) {
  $Python = "$root\sidecars\python\runtime\python.exe"
}
if (-not $Python) {
  $Python = "python"
}

# 1) 拉取官方主线（仅 skill 文件即可，脚本与 SKILL.md）
Write-Host "==> 拉取官方 ppt-master 主线" -ForegroundColor Cyan
if (Test-Path "$plugin\src\.git") {
  Push-Location "$plugin\src"; git pull; Pop-Location
} else {
  git clone --depth 1 https://github.com/hugohe3/ppt-master.git "$plugin\src"
}

# 2) 创建内嵌 venv 并安装依赖
Write-Host "==> 创建内嵌 venv 并安装依赖" -ForegroundColor Cyan
$venv = "$root\sidecars\python\runtime\venv"
if (-not (Test-Path $venv)) {
  & $Python -m venv $venv
}
$py = "$venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "$venv\bin\python" }
& $py -m pip install --upgrade pip
& $py -m pip install -r "$plugin\requirements.txt"
if (Test-Path "$plugin\src\requirements.txt") {
  & $py -m pip install -r "$plugin\src\requirements.txt"
}

Write-Host "完成。内嵌运行时：$py" -ForegroundColor Green
