# llama.cpp 本地推理运行时

用于运行 GGUF 模型并暴露 OpenAI 兼容 `/v1` 端点，核心引擎通过 `LlamaServerManager` 自动拉起。

## 获取 llama-server（构建期）
- 官方 release 提供预编译 `llama-server`（Windows/macOS/Linux x64/arm64）：
  https://github.com/ggml-org/llama.cpp/releases
- 解压后将 `llama-server(.exe)` 放到 `sidecars/llama.cpp/bin/<platform>/`。
- 核心引擎通过 `AI_CLIENT_LLAMA_SERVER` 环境变量或配置文件 `llama_server_bin` 定位。

## 运行参数（由核心引擎控制）
```
llama-server -m <model.gguf> --host 127.0.0.1 --port 18080 -c 4096 --n-gpu-layers 0
```

## 模型导入
- 用户在「大模型」页导入本地 `.gguf` 文件，核心引擎登记为 `local_gguf` 档案。
- 任务执行时自动启动对应模型服务，无网络依赖。
