# ai-client · 离线 AI 智能体客户端

全离线、跨平台（Windows / macOS / Linux / 麒麟 / 信创 / 鸿蒙）的 AI 客户端。
本地登录、本地配置大模型、任务驱动执行，内置 `ppt-master` 插件实现「可编辑 PPT 生成」与「PPT → 口播视频」。

> 方案：[`docs/PLAN.md`](docs/PLAN.md) · 构建：[`docs/BUILD.md`](docs/BUILD.md) · 打包：[`docs/PACKAGING.md`](docs/PACKAGING.md)

## 目录结构

```
core/         Rust 核心引擎（Agent 循环 / 模型抽象 / llama.cpp 管理 / 工具 / 工作流 / 插件 / headless HTTP）
web/          React + TS 前端（登录 / 模型 / 任务 / 插件 / PPT-视频）+ PWA（鸿蒙浏览器离线可装）
desktop/      Tauri v2 桌面壳（可选）
sidecars/     附件运行时（内嵌 Python / llama.cpp / LibreOffice / FFmpeg / CosyVoice+Piper）
plugins/      内置插件（ppt-master：run.py + render_video.py）
scripts/      开发 / 构建 / 打包 / 附件拉取脚本
.github/      CI（多平台编译 + 打包）
Dockerfile    无头（headless）容器化运行
```

## 当前进度

- ✅ 方案与计划、跨平台打包方案、构建/打包文档
- ✅ Rust 核心：登录、模型抽象（含 llama.cpp `LlamaServerManager` 自动拉起 GGUF）、模型导入、Agent 循环、工具、工作流、插件运行时、PPT/视频运行时、headless HTTP API
- ✅ React 前端：登录/大模型（导入 GGUF + 端点）/任务/插件/PPT-视频；TS 类型检查通过、vite 构建通过
- ✅ Tauri 桌面壳 + 图标 + capability
- ✅ ppt-master 插件：`run.py`（可编辑 PPTX）+ `render_video.py`（PPT→口播 MP4）
- ✅ PWA（manifest + service worker），鸿蒙浏览器可离线安装
- ✅ Docker headless + GitHub Actions 多平台 CI（Windows/macOS/Linux x64+arm64）
- ⏳ 待：Rust+C 工具链编译验证、CosyVoice/llama.cpp/FFmpeg 附件实体打包、真机适配

## 快速开始

前置：Node.js 20+、pnpm、Rust stable（含 C 工具链，见 `docs/BUILD.md`）。

```bash
cd web && pnpm install && pnpm dev                 # 1) 前端
cd core && cargo run -- serve                      # 2) 核心引擎（127.0.0.1:8787）
cd desktop && pnpm install && pnpm tauri dev       # 3) 桌面壳（可选）
docker compose up --build                          # 或：无头容器化运行
```
