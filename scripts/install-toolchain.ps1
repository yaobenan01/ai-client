# 安装本地 Rust + C 工具链（极速国内镜像源加速）
$ErrorActionPreference = "Stop"

function Has-Cmd($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host "==> [第 1/3 步] 检测系统已安装 Rust 环境..." -ForegroundColor Cyan
if (Has-Cmd cargo) { Write-Host "✓ 检测到系统已就绪: $(cargo --version)" -ForegroundColor Green; exit 0 }

# 极速国内镜像配置（提升 10 倍以上安装与更新速度）
$env:RUSTUP_DIST_SERVER = "https://rsproxy.cn"
$env:RUSTUP_UPDATE_ROOT = "https://rsproxy.cn/rustup"
Write-Host "==> 已配置 rsproxy 国内极速源加速 (RUSTUP_DIST_SERVER: https://rsproxy.cn)" -ForegroundColor Green

$vs = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vs) {
  Write-Host "✓ 检测到 MSVC Build Tools，使用 MSVC 主机安装 rustup" -ForegroundColor Green
  $hostTriple = "x86_64-pc-windows-msvc"
} elseif (Has-Cmd gcc) {
  Write-Host "✓ 检测到 MinGW gcc，使用 GNU 主机安装 rustup" -ForegroundColor Green
  $hostTriple = "x86_64-pc-windows-gnu"
} else {
  Write-Host "ℹ️ 未检测到 MSVC / MinGW，将使用 GNU 主机（rustup 自带 rust-mingw 组件，含 gcc/binutils）。" -ForegroundColor Yellow
  $hostTriple = "x86_64-pc-windows-gnu"
}

$u = "$env:TEMP\rustup-init.exe"
if (-not (Test-Path $u)) {
  Write-Host "==> [第 2/3 步] 极速下载 rustup-init 安装器..." -ForegroundColor Cyan
  $ProgressPreference = 'SilentlyContinue'
  $urls = @(
    "https://rsproxy.cn/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe",
    "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe"
  )
  $downloaded = $false
  foreach ($url in $urls) {
    try {
      Write-Host "  -> 尝试从 $url 下载..." -ForegroundColor Gray
      Invoke-WebRequest -Uri $url -OutFile $u -UseBasicParsing -TimeoutSec 15
      if ((Test-Path $u) -and ((Get-Item $u).Length -gt 500000)) {
        $downloaded = $true
        Write-Host "  ✓ 下载完成 ($([math]::Round((Get-Item $u).Length / 1MB, 2)) MB)" -ForegroundColor Green
        break
      }
    } catch {
      Write-Warning "从 $url 下载超时或失败，尝试备用地址..."
    }
  }
  if (-not $downloaded) {
    throw "无法下载 rustup-init，请检查网络设置。"
  }
}

Write-Host "==> [第 3/3 步] 正在安装 Rust 工具链（默认主机 $hostTriple，极速精简模式）..." -ForegroundColor Cyan
& $u -y --default-host $hostTriple --profile minimal --component rustfmt,clippy
Write-Host "rustup 安装执行完成，退出码: $LASTEXITCODE"

# 让当前会话与后续脚本能找到 cargo（写入用户 PATH）
$cargoBin = "$env:USERPROFILE\.cargo\bin"
if (Test-Path "$cargoBin\cargo.exe") {
  $env:Path = "$cargoBin;$env:Path"
  Write-Host "✓ Rust 工具链安装成功！当前版本：$(cargo --version)" -ForegroundColor Green
} else {
  Write-Host "⚠️ 安装未完成，请检查网络后重试，或改用 CI（.github/workflows/build.yml）编译。" -ForegroundColor Yellow
}
