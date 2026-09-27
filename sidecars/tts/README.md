# 本地 TTS（口播配音）

## 默认：CosyVoice（高质量中文）
- 阿里开源 CosyVoice（如 CosyVoice2-0.5B），中文音质好，支持音色克隆。
- 以 ONNX 或 PyTorch 运行时内嵌，模型置于 `models/`。
- 由 `render_video.py` 通过 `tts_cosyvoice()` 调用（CLI / 本地服务）。

## 兜底：Piper（轻量、跨平台）
- 体积小、CPU 实时，适合低配/信创设备。
- 模型：`zh_CN-huayan-medium.onnx` 等，置于 `models/`。
- 调用：`echo 文本 | piper --model models/zh_CN-huayan-medium.onnx --output_file out.wav`

## 扩展
支持用户配置「本地 OpenAI 兼容 TTS 端点」或自定义音色，通过环境变量/配置切换引擎。
