# 构建指南

## 环境要求

| 组件 | 版本 | 用途 | 说明 |
| --- | --- | --- | --- |
| Node.js | 20+ | 前端/桌面壳 | 或使用内置运行时 |
| pnpm | 9+ | 前端依赖 | 也可用 npm |
| Rust (rustup) | stable | 核心引擎 + Tauri | https://rustup.rs/ |
| C 工具链 | — | 编译 rusqlite(bundled) 与链接 | Windows: MSVC Build Tools 或 MinGW-w64；Linux/macOS: gcc/clang |

> 核心引擎使用 `rusqlite` 的 `bundled` 特性（内置 SQLite 源码），需要 C 编译器；
> 同时 Rust 的 proc-macro 依赖（serde derive 等）需要链接器。因此 **Windows 必须安装
> MSVC Build Tools（含 C++ 工作负载）或 MinGW-w64**，仅装 rustup 是不够的。

## 前端（已验证可编译）

```powershell
cd web
pnpm install          # 若 pnpm 拦截 esbuild 构建脚本：
# 手动补一次：node node_modules/.pnpm/esbuild@*/node_modules/esbuild/install.js
# 并复制 @esbuild/win32-x64/esbuild.exe 到 esbuild/bin/
pnpm run build        # 产物 web/dist
```

> 说明：本机已用 `tsc --noEmit` 通过类型检查、`vite build` 成功产出 dist（55 模块）。

## 核心引擎（headless）

```powershell
cd core
cargo build --release      # 产物 core/target/release/ai-client(.exe)
./target/release/ai-client serve --data-dir .dev-data   # 监听 127.0.0.1:8787
```

## 桌面壳（Tauri）

```powershell
# 1) 先把 core 二进制放到期望位置
scripts/package.ps1        # 内部会复制并执行 tauri build
# 或手动：
cd desktop && pnpm install && pnpm tauri build
```

Tauri 打包前需补齐 `desktop/src-tauri/icons/` 的 `icon.icns`（macOS）、各平台图标。

## 离线附件运行时（开箱即用）

见 `sidecars/README.md` 与 `scripts/setup-ppt-master.ps1`（在开发机构建，产物随应用分发，
目标机器无需安装 Python / FFmpeg / LibreOffice）。


> 提示：若使用 `x86_64-pc-windows-gnu` 主机（rustup 默认附带 `rust-mingw` 组件，内含 gcc/binutils），
> 可免装 MSVC Build Tools；MSVC 主机则需安装 MSVC Build Tools（含 C++ 工作负载）。
