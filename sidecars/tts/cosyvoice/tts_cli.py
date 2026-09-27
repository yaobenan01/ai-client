#!/usr/bin/env python3
"""CosyVoice 本地 TTS CLI（离线中文口播，高质量）。

用法：
  python tts_cli.py --text "大家好" --output out.wav [--model CosyVoice2-0.5B]

依赖 CosyVoice 运行时，见 sidecars/tts/cosyvoice/README.md。
render_video.py 通过环境变量 AI_CLIENT_COSYVOICE_CLI 调用本脚本。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def via_official_cli(text: str, out: Path, repo: Path) -> bool:
    cli = repo / "cosyvoice" / "cli" / "cosyvoice.py"
    if not cli.exists():
        return False
    cmd = [
        sys.executable, str(cli),
        "--mode", "sft",
        "--tts_text", text,
        "--output", str(out),
    ]
    subprocess.run(cmd, check=True)
    return True


def via_api(text: str, out: Path) -> None:
    repo = os.environ.get("COSYVOICE_REPO", "third_party/CosyVoice")
    sys.path.insert(0, repo)
    import torchaudio  # noqa: F401
    from cosyvoice.cli.cosyvoice import CosyVoice2

    model = os.environ.get("COSYVOICE_MODEL", "CosyVoice2-0.5B")
    cosyvoice = CosyVoice2(model, load_jit=False, load_trt=False, fp16=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    for result in cosyvoice.inference_sft(text, "中文女", stream=False, speed=1.0):
        torchaudio.save(str(out), result["tts_speech"], cosyvoice.sample_rate)
        break


def main() -> int:
    ap = argparse.ArgumentParser(description="CosyVoice TTS CLI")
    ap.add_argument("--text", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", default=os.environ.get("COSYVOICE_MODEL", "CosyVoice2-0.5B"))
    args = ap.parse_args()

    out = Path(args.output)
    repo = Path(os.environ.get("COSYVOICE_REPO", "third_party/CosyVoice"))
    if via_official_cli(args.text, out, repo):
        pass
    else:
        via_api(args.text, out)

    print(f"[cosyvoice] 已生成 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
