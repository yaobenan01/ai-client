# 离线 AI 智能体客户端 —— 需求实现方案与计划

> 项目代号：`ai-client`　工作目录：`D:\ai_workspace\ai-client`
> 文档版本：v0.1（方案评审稿）　日期：2026-09-27

---

## 一、项目概述

构建一个**全离线、可跨平台打包**的 AI 客户端：用户本机登录、本地配置大模型、以任务方式驱动 AI 完成工作，并内置 `ppt-master` 插件实现「可编辑 PPT 生成」与「PPT → 口播视频」。产品在形态与能力上融合三类优秀实践的优点：

| 参考对象 | 取其优势 |
| --- | --- |
| `docker-headless` | 核心引擎与 UI 解耦，可无头/容器化运行，提供本地 HTTP/CLI 接口 |
| `codex` | 成熟的 Agent 循环（规划-执行-反思）、工具调用协议、上下文/沙箱管理 |
| `豆包/豆包任务` | 面向普通用户的「任务/工作流」体验、多模态输入、业务流程编排 |

核心承诺：
1. **全离线**：登录、模型推理、PPT 生成、口播视频全链路在本机完成，无强制联网依赖。
2. **可编辑 PPT**：不是导出图片，而是原生可编辑的 `.pptx`（形状/图表/表格/动画均可继续编辑）。
3. **口播视频**：PPT + 演讲者备注 → 本地 TTS 语音 → 合成带旁白的 MP4。
4. **跨平台**：Windows / macOS / Linux / 麒麟 / 信创（统信等）/ 鸿蒙。

---

## 二、需求清单与优先级

### 2.1 功能需求

| 编号 | 需求 | 说明 | 优先级 |
| --- | --- | --- | --- |
| F1 | 本地用户登录 | 本地账号库、密码哈希、会话管理、多用户、数据隔离 | P0 |
| F2 | 大模型配置 | 导入本地模型(GGUF/ONNX)、配置本地 OpenAI 兼容端点、模型参数/系统提示词/工具开关、模型测试 | P0 |
| F3 | 任务执行 | 创建任务、进度/状态展示、日志、停止/重试/恢复 | P0 |
| F4 | 核心执行算法 | Agent 循环、工具调用、上下文管理、反思与重规划 | P0 |
| F5 | 业务逻辑执行 | 可编排工作流（步骤/条件/循环/输入输出），复用核心引擎 | P1 |
| F6 | 插件/技能系统 | 插件安装、启用、沙箱执行、`SKILL.md` 兼容 | P0 |
| F7 | ppt-master 插件 | 集成开源 `ppt-master`，生成可编辑 PPTX | P0 |
| F8 | PPT→口播视频 | 本地 TTS + 渲染 + FFmpeg 合成 MP4 | P0 |
| F9 | 离线打包 | 各平台安装包/便携包，麒麟/信创/鸿蒙适配 | P0 |

### 2.2 非功能需求

| 类别 | 要求 |
| --- | --- |
| 离线 | 无网可用；联网能力默认关闭、可显式开启 |
| 安全 | 模型/数据本地存储、密码 Argon2id、插件沙箱、命令白名单 |
| 性能 | 模型推理异步化、UI 不阻塞、大文件流式处理 |
| 可扩展 | 模型 Provider、工具、插件、TTS 引擎均为可插拔接口 |
| 可维护 | 核心与 UI 解耦，核心可独立作为 headless 服务/CLI 运行 |

---

## 三、参考方案分析与取舍

### 3.1 docker-headless
- 优势：引擎容器化、无头运行、API 化，便于服务器/信创环境部署。
- 采纳：本项目的 **core 引擎独立成 crate**，同时提供 `headless`（CLI + 本地 HTTP）与 `desktop`（Tauri 壳）两种形态；保留 Docker 化能力。

### 3.2 codex
- 优势：Agent 循环成熟、工具调用协议规范、上下文与沙箱管理完善。
- 采纳：核心执行算法参考其「规划→执行→反思」循环与工具/上下文抽象（自研实现，不复制代码）。

### 3.3 豆包 / 豆包任务
- 优势：任务化交互、工作流编排、面向普通用户。
- 采纳：前端以「任务面板 + 对话执行」为核心交互；F5 工作流引擎面向业务编排。

### 3.4 ppt-master（重点集成对象）
- 事实：`hugohe3/ppt-master` 是开源 Agent Skill，依赖 Python 3.10+，通过 `SKILL.md` 工作流 + Python 脚本（SVG → 原生 DrawingML PPTX）运行；支持「材料→PPT」「模板/填充现有 PPT」「旁白→MP4」等路径；官方要求宿主具备读写文件 + 执行命令 + 多轮对话能力。
- 结论：本项目**原生内置一个 Skill 运行时来托管 ppt-master**，将其 Python 依赖与脚本作为插件资产打包；旁白 TTS 由本地引擎替换官方默认的网络 TTS，以满足全离线。

---

## 四、总体架构

采用「**核心引擎（core）+ 前端（web UI）+ 桌面壳（Tauri）+ 附件运行时（sidecar）**」分层，核心与 UI 解耦，既能打包成桌面应用，也能以 headless 方式运行。

```
┌─────────────────────────────────────────────────────────────────┐
│  桌面壳 (Tauri v2, Rust)  —  可选；headless 模式无此层             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  前端 UI (React + TS + Vite)                               │  │
│  │  登录 · 模型配置 · 任务面板 · 对话/执行 · 插件 · PPT/视频      │  │
│  └───────────────────────────────────────────────────────────┘  │
│        │ IPC / 本地 HTTP (localhost, 127.0.0.1)                 │
│  ┌─────▼────────────────────────────────────────────────────┐  │
│  │  核心引擎 core (Rust crate)                                │  │
│  │  ┌────────────┬──────────────┬────────────┬────────────┐  │  │
│  │  │ 任务状态机  │ Agent 循环    │ 工具执行器  │ 上下文管理  │  │  │
│  │  ├────────────┼──────────────┼────────────┼────────────┤  │  │
│  │  │ 模型抽象    │ 工作流引擎    │ 插件运行时  │ 权限/沙箱   │  │  │
│  │  └────────────┴──────────────┴────────────┴────────────┘  │  │
│  │  存储: SQLite (rusqlite) · 账号/任务/配置/插件注册表        │  │
│  └─────┬──────────────────────────────────────────────────────┘  │
│        │ sidecar 子进程（按需启动）                               │
│  ┌─────▼──────────────────────────────────────────────────────┐  │
│  │  附件运行时                                                   │  │
│  │  · llama.cpp / llama-server   (GGUF 本地推理)                │  │
│  │  · ONNX Runtime               (embedding/视觉/部分模型)      │  │
│  │  · Python(内嵌) + ppt-master  (PPT 生成)                     │  │
│  │  · LibreOffice headless + FFmpeg + Piper/CosyVoice (视频/TTS)│  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**数据流（一次任务执行）**：
用户创建任务 → 前端 IPC → core 任务状态机 → 模型抽象层选模型 → Agent 循环（规划→工具执行→反思）→ 工具执行器调用内置/插件工具（含 ppt-master 脚本、TTS、FFmpeg）→ 结果/日志回传前端 → 产物（.pptx/.mp4）写入用户工作区。

---

## 五、技术选型与理由

| 层 | 选型 | 理由 |
| --- | --- | --- |
| 核心引擎 | **Rust** | 性能、内存安全、单二进制、`loongarch64-unknown-linux-gnu` 可交叉/源码编译，信创友好 |
| 桌面壳 | **Tauri v2** | 体积小、跨平台（Win/macOS/Linux）、webview 在麒麟/UOS 可用；比 Electron 更利于信创与源码构建 |
| 前端 | React 18 + TypeScript + Vite + Tailwind；Monaco 编辑器 | 生态成熟、离线打包简单 |
| 本地模型 | **llama.cpp**(GGUF) + **ONNX Runtime**(ort) | 覆盖主流开源模型与量化格式，跨平台/跨架构最好 |
| 存储 | SQLite (rusqlite + 迁移) | 嵌入式、零运维、单文件 |
| 进程通信 | 桌面走 Tauri IPC；headless 走本地 HTTP/JSON-RPC | 两种形态共享同一 core 接口 |
| PPT 生成 | **ppt-master**（Python 3.10+，内嵌运行） | 原生可编辑 PPTX，符合需求；本机运行保证离线 |
| PPT 渲染 | LibreOffice headless + pdftoppm | PPTX→PDF→PNG，全平台可用 |
| 视频合成 | FFmpeg | 图片序列 + 音频 + 字幕/转场，事实标准 |
| 口播 TTS | 默认 **Piper**（轻量跨平台）；可选 **CosyVoice/F5-TTS/XTTS**、本地 OpenAI 兼容 TTS | 全离线，Piper 起步快，高质量中文可插拔扩展 |
| 打包 | Tauri bundler（NSIS/MSI、dmg、deb/rpm/AppImage）+ 附件运行时 | 一键产出各平台安装包 |

> 说明：核心与 UI 解耦后，若某目标平台（如 LoongArch 或鸿蒙）无法运行 Tauri 壳，仍可运行 `core(headless)` + Web 前端，保证能力可用。

---

## 六、核心模块设计

### 6.1 F1 本地用户登录
- 账号存 SQLite：`users(id, username, pass_hash, salt, role, created_at)`。
- 密码用 **Argon2id** 哈希；支持可选 PIN/手势（本地解锁）。
- 登录后签发本地会话 token（随机 token 或本地签名 JWT），有效期与自动锁定策略可配。
- 多用户 + 角色（admin/user）；用户数据、任务、模型配置、插件按用户隔离。
- 完全本地校验，不联网。

### 6.2 F2 大模型配置
- **ModelProvider 抽象 trait**：`LocalGGUF` / `LocalONNX` / `OpenAICompat(local)` / `Remote(默认关闭)`。
- 模型档案：模型名、路径/端点、量化、上下文长度、temperature/top_p、系统提示词、工具开关、是否默认。
- **离线导入**：本地选择 `.gguf`/`.onnx` 文件或目录，自动探测与登记；内置模型下载器默认关闭，仅当用户显式联网时可用。
- 提供「模型测试对话」快速验证配置；支持多模型并存与任务级选型。
- 本地推理优先 `llama-server` 子进程（OpenAI 兼容本地端口），天然支持 function calling 的模型走结构化输出。

### 6.3 F3 任务执行
- 任务实体：`tasks(id, user_id, title, input, status, progress, model_id, workflow_id, result, logs, timestamps)`。
- 状态机：`pending → planning → running → awaiting_input → done/failed/cancelled`，支持暂停/停止/重试/恢复。
- 前端任务面板：列表 + 详情 + 实时日志流 + 进度条 + 产物列表（点击打开 .pptx/.mp4）。

### 6.4 F4 核心执行算法（Agent 循环）
参考 codex/豆包的 Agent 模式，自研实现：

```
loop {
  1. 规划    : 解析任务 → 生成子任务图/步骤计划
  2. 装配    : system prompt + skill 文档 + 记忆 + 工具定义 + 历史 → 按 token 预算裁剪
  3. 推理    : 调用模型（function calling / 结构化输出 / 文本协议）
  4. 执行    : 解析工具调用 → 工具执行器执行（文件/命令/检索/PPT/视频/代码…）
  5. 反思    : 结果回填 → 是否达成？→ 修正计划或补充信息
  6. 判定    : 满足终止条件则 done，否则回到 3
}
```

关键点：
- **工具协议**：JSON Schema 定义工具，统一 `ToolExecutor` 接口；内置工具 + 插件工具 + 预留 MCP 客户端。
- **上下文管理**：滑动窗口 + 摘要压缩 + 本地 embedding 向量检索（RAG 记忆），控制 token 成本。
- **沙箱**：进程级沙箱（文件系统只读白名单、命令白名单、超时、资源上限）；可选 Docker 容器（对应 docker-headless 形态）。

### 6.5 F5 业务逻辑执行（工作流引擎）
- 用户可用 JSON/YAML（或可视化表单）定义工作流：`输入 → 步骤(LLM/工具/条件/循环/并行) → 输出`。
- 工作流节点复用核心引擎的模型抽象与工具执行器，类似豆包「任务/工作流」。
- 运行实例落库、可中断续跑、可导出/导入工作流定义。

### 6.6 F6 插件/技能系统
- **Skill 运行时**：兼容 `SKILL.md` 约定（description / 触发条件 / 工作流说明），插件以目录形式安装。
- 插件生命周期：安装、启用/禁用、更新、卸载；注册表落 SQLite。
- 沙箱执行：插件脚本在受限环境运行，命令/文件访问走白名单；PPT 类插件开放 `.pptx`/`.svg`/`.png` 工作区。
- 内置「插件市场」离线包：ppt-master 作为首款内置插件预置。

### 6.7 F7 ppt-master 插件（可编辑 PPT 生成）
- 集成 `hugohe3/ppt-master`：内置其 `skills/ppt-master` 工作流 + Python 脚本 + `requirements.txt` 依赖。
- 内嵌 Python 运行时（python-build-standalone / uv 内嵌），首次使用或安装器阶段解压依赖，无需用户装 Python。
- 输入：PDF / DOCX / Markdown / URL / 纯文本 / 大纲；输出：`exports/<name>_<timestamp>.pptx`（原生 DrawingML 可编辑）+ `svg_final/` 预览。
- 支持路径：材料→新 PPT、模板抽取、填充现有 PPT、加转场/动画/旁白。
- 由 core 的 Agent 循环驱动（core 充当 ppt-master 所需的「有 Agent 能力的宿主」），或直接由插件暴露「一键生成」命令。

### 6.8 F8 PPT → 口播视频
流水线（全离线）：

```
PPTX → LibreOffice headless → PDF → pdftoppm → 逐页 PNG
演讲者备注 → 本地 TTS (Piper/CosyVoice/XTTS) → 逐页 WAV 旁白
PNG 序列 + WAV + 可选字幕/转场(Ken Burns) → FFmpeg → 口播 MP4
```

- TTS 引擎接口可插拔：默认 Piper（轻量），可选 CosyVoice/F5-TTS/XTTS（高质量中文）、本地 OpenAI 兼容 TTS 端点、用户自定义音色。
- 每页语音时长与页面停留时间对齐，支持背景音乐（本地音频）与字幕烧录。
- 视频参数可配：分辨率（16:9 默认）、帧率、码率、转场。

---

## 七、全离线策略

| 环节 | 离线方案 |
| --- | --- |
| 登录 | 本地 SQLite + Argon2id，不联网 |
| 模型推理 | 本地 GGUF/ONNX 推理；OpenAI 兼容端点仅指本地服务 |
| 模型获取 | 用户从本地文件导入 `.gguf`；下载器默认关闭 |
| PPT 生成 | ppt-master 全在本机 Python 运行 |
| PPT 渲染 | LibreOffice headless 本地渲染 |
| 口播 TTS | Piper/CosyVoice 等本地引擎，替换官方网络 TTS |
| 视频合成 | 本地 FFmpeg |
| 更新 | 离线安装包/离线补丁；联网更新默认关闭 |

联网能力作为「显式开启的选配」，仅用于用户主动需要时（如远程模型、网页素材、云端更新），并在 UI 上明确标识。

---

## 八、跨平台与打包方案

### 8.1 构建矩阵

| 平台 | 架构 | 打包格式 | 说明 |
| --- | --- | --- | --- |
| Windows | x64 | NSIS `.exe` / MSI / 便携版 | 附件运行时内置 |
| macOS | x64 / arm64 | `.dmg` | 附件运行时内置 |
| Linux 通用 | x64 / arm64 | AppImage + deb + rpm | 依赖 webkit2gtk |
| 麒麟 V10（银河麒麟/中标麒麟/优麒麟） | x64 / arm64（飞腾/鲲鹏） | deb / rpm / AppImage | Debian/Ubuntu 系，webview 可用 |
| 信创（统信 UOS 等） | x64（海光/兆芯）/ arm64（飞腾/鲲鹏）/ **LoongArch64（龙芯）** | deb / rpm | LoongArch 需源码构建或 headless+Web |
| 鸿蒙（HarmonyOS NEXT / OpenHarmony） | 通用 | **Web(PWA) + ArkTS 壳** | 桌面/平板浏览器运行 Web 版 |

### 8.2 各平台落地策略
- **Windows/macOS/Linux(麒麟/统信 x64、arm64)**：Tauri 壳 + 内置附件运行时，一键打包。
- **LoongArch64**：Rust 核心源码构建（`loongarch64-unknown-linux-gnu`）；若 webview 不可用，降级为 `core(headless) + 本地 Web 前端`。
- **鸿蒙**：核心以 headless 服务 + Web 前端（PWA，可离线安装）运行在系统浏览器/Web 组件；另提供 OpenHarmony ArkTS 壳包裹 Web 页面；PPT/TTS/FFmpeg 由鸿蒙端能力或 headless 服务提供（阶段实现）。
- **附件运行时打包**：Python(内嵌)+ppt-master、LibreOffice、FFmpeg、Piper/TTS 按平台分发；Linux 优先检测系统已装组件，缺失时使用内置版本。

### 8.3 CI/CD
- 统一 Git 仓库 + 多平台 CI（Windows/macOS/Linux x64、arm64），LoongArch 用 QEMU/真机构建。
- 产物签名与校验（防止离线环境篡改），发布离线安装包与 sha256 清单。

---

## 九、目录结构（规划）

```
ai-client/
├─ docs/PLAN.md                  # 本方案
├─ core/                         # Rust 核心引擎 crate
│  ├─ src/
│  │  ├─ agent/                  # 任务状态机、Agent 循环
│  │  ├─ models/                 # ModelProvider 抽象与实现
│  │  ├─ tools/                  # 工具执行器、内置工具
│  │  ├─ workflow/               # 工作流引擎
│  │  ├─ plugins/                # 插件/技能运行时
│  │  ├─ auth/                   # 本地登录
│  │  ├─ storage/                # SQLite 仓储
│  │  └─ server/                 # headless HTTP/CLI
├─ web/                          # 前端 React+TS
│  └─ src/{auth,models,tasks,plugins,ppt,video,ui}
├─ desktop/                      # Tauri 壳
│  └─ src-tauri/                 # 打包配置、能力权限
├─ sidecars/                     # 附件运行时清单与下载/构建脚本
│  ├─ python/                    # 内嵌 Python 构建
│  ├─ llama.cpp / onnxruntime
│  ├─ libreoffice / ffmpeg
│  └─ tts/                       # Piper / CosyVoice
├─ plugins/ppt-master/           # 内置 ppt-master 技能(源码/依赖清单)
├─ scripts/                      # 构建、打包、平台适配脚本
└─ installers/                   # 各平台安装包产物
```

---

## 十、实施计划（里程碑与任务拆解）

| 阶段 | 周期 | 目标 | 关键任务 | 验收标准 |
| --- | --- | --- | --- | --- |
| P0 基础设施 | 第 1 周 | 骨架 + 构建矩阵 | 仓库初始化、core/web/desktop 骨架、CI、空壳打包各平台 | 各平台能产出并启动空壳应用 |
| P1 核心引擎 | 第 2-3 周 | Agent 能力闭环 | 模型抽象、Agent 循环、工具系统、任务状态机、SQLite、登录 | 本地 GGUF 模型下能完成文件类任务 |
| P2 前端 UI | 第 4-5 周 | 可交互客户端 | 登录页、模型配置、任务面板、对话/执行视图、日志流 | 用户可登录并跑通一个任务 |
| P3 插件与 PPT | 第 6-7 周 | ppt-master 落地 | 插件运行时、内嵌 Python、ppt-master 集成、可编辑 PPT 生成 | 输入 Markdown/PDF 产出可编辑 .pptx |
| P4 口播视频 | 第 8-9 周 | PPT→MP4 | 本地 TTS 接入、LibreOffice/FFmpeg 流水线、字幕/转场 | 产出带旁白的 MP4，时长与页面对齐 |
| P5 打包与适配 | 第 10-11 周 | 跨平台交付 | 全离线打包、麒麟/信创适配、鸿蒙 Web 版、安装器、文档 | 麒麟/统信可安装运行，鸿蒙浏览器可运行 Web 版 |
| P6 加固发布 | 第 12 周 | 质量与安全 | 测试、安全审计、离线补丁、发布 v1.0 | 发布可交付安装包 + 校验清单 |

**总体估期**：MVP（P0-P4）约 9 周；完整版（P0-P6）约 12 周。

> 并行建议：P1 核心引擎与 P2 前端可并行；P4 的 TTS/FFmpeg 调研可在 P1 期间提前启动。

---

## 十一、风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| LoongArch/鸿蒙原生工具链不完整 | 无法完整打包桌面壳 | 核心 headless + Web 前端降级方案，优先保能力可用 |
| 本地 TTS 中文质量不足 | 口播视频体验差 | Piper 兜底 + CosyVoice/XTTS 可插拔高质量引擎 |
| 离线模型体积大、适配成本高 | 安装包臃肿 | 附件运行时按需下载/内置可选，模型由用户导入 |
| ppt-master 依赖网络 TTS/素材 | 全离线目标破口 | 替换为本地 TTS，联网素材默认关闭 |
| LibreOffice/FFmpeg 在信创缺包 | 视频链路不可用 | 内置便携版 + 系统组件检测兜底 |
| 插件/命令安全 | 恶意脚本风险 | 白名单沙箱、权限最小化、可审计日志 |

---

## 十二、待确认事项

1. **项目命名**：是否沿用 `ai-client`，还是采用正式产品名？
2. **核心语言确认**：默认 Rust 核心 + Tauri 壳；是否接受？（替代：Electron+Node，体积大但 LoongArch 支持更差）
3. **鸿蒙形态**：优先「Web(PWA) 版」还是「OpenHarmony 原生 ArkTS 应用」？
4. **默认模型**：是否内置一个默认 GGUF 模型，还是全部由用户导入？
5. **口播 TTS 音色**：默认 Piper 轻量，还是优先集成高质量中文（CosyVoice，体积更大）？
6. **ppt-master 版本**：集成官方 `hugohe3/ppt-master` 主线，还是 `macrochen/ppt-master-skill` 的 Codex 封装？

---

## 十三、下一步

方案确认后，即从 **P0 基础设施** 开始：初始化仓库骨架、打通 Windows/Linux 构建与空壳打包，随后进入 P1 核心引擎实现。
