#!/usr/bin/env python3
"""PPTX -> 口播 MP4（全离线）。

流水线：
  PPTX --LibreOffice--> PDF --PyMuPDF--> 逐页 PNG
  演讲者备注 --TTS(CosyVoice/Piper)--> 逐页 WAV
  PNG + WAV --FFmpeg--> 口播 MP4

用法：
  python render_video.py --pptx deck.pptx --out out.mp4 --tts cosyvoice
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def find_exe(name: str, env: str) -> str:
    p = os.environ.get(env)
    if p and Path(p).exists():
        return p
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"未找到 {name}（请设置 {env} 或加入 PATH）")
    return found


def pptx_to_pdf(pptx: Path, out_dir: Path) -> Path:
    lo = find_exe("soffice", "AI_CLIENT_LIBREOFFICE")
    sh([lo, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)])
    pdf = out_dir / (pptx.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError("LibreOffice 未能导出 PDF")
    return pdf


def pdf_to_pngs(pdf: Path, out_dir: Path, dpi: int = 160) -> list[Path]:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf)
    paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        p = out_dir / f"slide_{i + 1:03d}.png"
        pix.save(p)
        paths.append(p)
    return paths


def extract_notes(pptx: Path) -> list[str]:
    from pptx import Presentation

    prs = Presentation(str(pptx))
    notes = []
    for slide in prs.slides:
        if slide.has_notes_slide:
            notes.append(slide.notes_slide.notes_text_frame.text.strip())
        else:
            notes.append("")
    return notes


def tts_piper(text: str, out: Path, model: str) -> None:
    piper = find_exe("piper", "AI_CLIENT_PIPER")
    sh([piper, "--model", model, "--output_file", str(out)], input=text.encode())


def tts_cosyvoice(text: str, out: Path) -> None:
    # 接入内嵌 CosyVoice 运行时：CLI 或本地 HTTP 服务。
    # 参考 sidecars/tts/README.md；此处调用约定的 CLI。
    cli = os.environ.get("AI_CLIENT_COSYVOICE_CLI", "cosyvoice")
    sh([cli, "--text", text, "--output", str(out)])


def synthesize(notes: list[str], engine: str, work: Path) -> list[Path]:
    wavs = []
    for i, text in enumerate(notes):
        out = work / f"audio_{i + 1:03d}.wav"
        if not text:
            out = None
        elif engine == "piper":
            model = os.environ.get("PIPER_MODEL", "zh_CN-huayan-medium.onnx")
            tts_piper(text, out, model)
        elif engine == "cosyvoice":
            tts_cosyvoice(text, out)
        else:
            raise ValueError(f"未知 TTS 引擎: {engine}")
        wavs.append(out)
    return wavs


def make_clip(slide: Path, wav: Path | None, clip: Path, ffmpeg: str) -> None:
    cmd = [ffmpeg, "-y", "-loop", "1", "-i", str(slide)]
    if wav:
        cmd += ["-i", str(wav), "-shortest"]
    else:
        cmd += ["-t", "3"]
    cmd += ["-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", str(clip)]
    sh(cmd)


def concat(clips: list[Path], out: Path, ffmpeg: str) -> None:
    lst = out.with_suffix(".txt")
    lst.write_text("\n".join(f"file '{c.resolve()}'" for c in clips), encoding="utf-8")
    sh([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def main() -> int:
    ap = argparse.ArgumentParser(description="PPTX -> narrated MP4")
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tts", default="cosyvoice", choices=["cosyvoice", "piper"])
    args = ap.parse_args()

    pptx = Path(args.pptx)
    out = Path(args.out)
    if out.suffix.lower() != ".mp4":
        out = out / (pptx.stem + ".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_exe("ffmpeg", "AI_CLIENT_FFMPEG")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        pdf = pptx_to_pdf(pptx, work)
        slides = pdf_to_pngs(pdf, work)
        notes = extract_notes(pptx)
        wavs = synthesize(notes, args.tts, work)
        clips = []
        for i, slide in enumerate(slides):
            clip = work / f"clip_{i + 1:03d}.mp4"
            make_clip(slide, wavs[i], clip, ffmpeg)
            clips.append(clip)
        concat(clips, out, ffmpeg)

    print(f"[ppt-master] 已生成口播视频 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
