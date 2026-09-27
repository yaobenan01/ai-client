# CosyVoice 运行时（默认口播 TTS）

## 模型与依赖（构建期准备，离线分发）
1. 克隆 CosyVoice：`git clone https://github.com/FunAudioLLM/CosyVoice.git`
2. 安装依赖（PyTorch + 依赖），见其 README（`pip install -r requirements.txt`）。
3. 下载模型 `CosyVoice2-0.5B`，放到 `models/CosyVoice2-0.5B/`。
4. 设置环境变量：
   - `COSYVOICE_REPO` → CosyVoice 源码目录
   - `COSYVOICE_MODEL` → 模型名（默认 CosyVoice2-0.5B）

## 调用
- CLI：`python tts_cli.py --text "..." --output out.wav`
- 被 `render_video.py` 自动调用（`AI_CLIENT_COSYVOICE_CLI=python <path>/tts_cli.py`）。

## 兜底
- 低配/信创设备可切换 Piper（`--tts piper`），见 `sidecars/tts/README.md`。
