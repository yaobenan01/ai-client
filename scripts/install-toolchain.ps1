# 安装本地 Rust + C 工具链（一次性，便于编译 core/desktop）
$ErrorActionPreference = "Stop"

function Has-Cmd($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host "==> 检测 Rust" -ForegroundColor Cyan
if (Has-Cmd cargo) { Write-Host "已安装: $(cargo --version)"; exit 0 }

$vs = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vs) {
  Write-Host "检测到 MSVC Build Tools，使用 MSVC 主机安装 rustup" -ForegroundColor Green
  $hostTriple = "x86_64-pc-windows-msvc"
} elseif (Has-Cmd gcc) {
  Write-Host "检测到 MinGW gcc，使用 GNU 主机安装 rustup" -ForegroundColor Green
  $hostTriple = "x86_64-pc-windows-gnu"
} else {
  Write-Host "未检测到 MSVC / MinGW。将使用 GNU 主机（rustup 自带 rust-mingw 组件，含 gcc/binutils）。" -ForegroundColor Yellow
  $hostTriple = "x86_64-pc-windows-gnu"
}

$u = "$env:TEMP\rustup-init.exe"
if (-not (Test-Path $u)) {
  Write-Host "==> 下载 rustup-init" -ForegroundColor Cyan
  $ProgressPreference = 'SilentlyContinue'
  Invoke-WebRequest -Uri "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe" -OutFile $u -UseBasicParsing
}

Write-Host "==> 安装 Rust（默认主机 $hostTriple）" -ForegroundColor Cyan
& $u -y --default-host $hostTriple --profile minimal --component rustfmt,clippy
Write-Host "rustup exit=$LASTEXITCODE"

# 让当前会话与后续脚本能找到 cargo（写入用户 PATH）
$cargoBin = "$env:USERPROFILE\.cargo\bin"
if (Test-Path "$cargoBin\cargo.exe") {
  $env:Path = "$cargoBin;$env:Path"
  Write-Host "已安装 cargo：$(cargo --version)" -ForegroundColor Green
} else {
  Write-Host "安装未完成，请检查网络后重试，或改用 CI（.github/workflows/build.yml）编译。" -ForegroundColor Yellow
}
