# 内嵌 Python 运行时（免安装）

目标：用户机器**不装 Python**，开箱即用。

## 方案
使用 [python-build-standalone](https://github.com/astral-sh/python-build-standalone)（或 `uv python install` 的独立发行版），
它是一份免安装、自包含、可重定位的 CPython，支持 Windows / macOS / Linux x64 / arm64。

## 构建期（在开发机执行，产物随应用分发）
1. 下载对应平台的 python-build-standalone 包，解压到 `runtime/`。
2. 用它创建独立 venv，并安装 `../plugins/ppt-master/requirements.txt` 到 `runtime/venv`。
3. 将 `runtime/` 打进安装包（Tauri `bundle.resources`）。

## 运行时
核心引擎通过 `AI_CLIENT_PYTHON` 或自动探测 `runtime/<platform>/python` 调用该解释器，
执行 ppt-master 的 `run.py` / `render_video.py`。

## 离线依赖
依赖 wheel 在构建期一次性下载并固化（wheelhouse），离线环境无需再次联网。
