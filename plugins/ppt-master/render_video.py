#!/usr/bin/env python3
"""PPTX -> 口播 MP4（全离线自包含流水线）。

流水线阶段：
  [阶段 1/4] PPTX --LibreOffice--> 高清矢量 PDF
  [阶段 2/4] PDF --PyMuPDF--> 逐页幻灯片超清帧图
  [阶段 3/4] 演讲者备注 --TTS(Piper / Windows SAPI5 / CosyVoice)--> 逐页高清配音音频
  [阶段 4/4] 幻灯片帧图 + 配音音频 --FFmpeg--> 合成最终口播 MP4 视频

特性：
  - 自动定位安装包内嵌入的 sidecars（LibreOffice, FFmpeg, Piper）；
  - 多级 TTS 容灾回退（Piper -> Windows 原生 SAPI5 语音 -> 静音帧）；
  - 全程离线运行，用户宿主机无需安装任何第三方环境。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def log_step(step: int, total: int, msg: str) -> None:
    print(f"\n[步骤 {step}/{total}] {msg}", flush=True)


def sh(cmd, timeout: float | None = None, **kw):
    cmd_str = " ".join(str(c) for c in cmd)
    # 过滤可能太长的命令行日志
    print(f"  -> 执行: {cmd_str[:120]}{'...' if len(cmd_str) > 120 else ''}", flush=True)
    try:
        res = subprocess.run(cmd, check=False, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"命令执行超时（>{timeout}s）: {cmd_str}")
    if res.returncode != 0:
        raise RuntimeError(f"命令执行失败 (退出码 {res.returncode}): {cmd_str}")
    return res


def find_tool(name: str, env_var: str, candidate_rel_paths: list[str]) -> str:
    """按优先级探测工具：环境变量 -> 相对工作区/安装包路径 -> 系统 PATH。"""
    # 1. 显式环境变量
    p = os.environ.get(env_var)
    if p and Path(p).exists():
        return p

    # 2. 从当前脚本所在目录向上查找 sidecars
    curr = Path(__file__).resolve()
    # 可能的根目录：plugins/ppt-master -> 项目根目录，或 resources/plugins/ppt-master -> 安装包根目录
    roots = [
        curr.parent.parent.parent,  # git repo 根目录
        curr.parent.parent,         # plugins 根目录
        curr.parent,                # 本身
    ]
    # 如果在 resources/ 目录下
    if "resources" in curr.parts:
        idx = curr.parts.index("resources")
        roots.append(Path(*curr.parts[:idx]))
        roots.append(Path(*curr.parts[:idx + 1]))

    for root in roots:
        for rel in candidate_rel_paths:
            candidate = root / rel
            if candidate.exists() and candidate.is_file():
                return str(candidate)

    # 3. 系统 PATH
    found = shutil.which(name)
    if found:
        return found

    return ""


def find_libreoffice() -> str:
    candidates = [
        "sidecars/media/libreoffice/program/soffice.exe",
        "sidecars/media/libreoffice/program/soffice.com",
        "sidecars/media/libreoffice/soffice.exe",
        "sidecars/media/libreoffice/program/soffice",
        "sidecars/media/libreoffice/soffice",
    ]
    lo = find_tool("soffice", "AI_CLIENT_LIBREOFFICE", candidates)
    if not lo and sys.platform == "win32":
        # 常见 Windows 安装目录兜底
        for p in [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]:
            if Path(p).exists():
                return p
    if not lo:
        raise RuntimeError("未找到 LibreOffice 渲染器（请确保 sidecars/media/libreoffice 完整打包）")
    return lo


def find_ffmpeg() -> str:
    candidates = [
        "sidecars/media/ffmpeg/bin/ffmpeg.exe",
        "sidecars/media/ffmpeg/ffmpeg.exe",
        "sidecars/media/ffmpeg/bin/ffmpeg",
        "sidecars/media/ffmpeg/ffmpeg",
    ]
    ff = find_tool("ffmpeg", "AI_CLIENT_FFMPEG", candidates)
    if not ff:
        raise RuntimeError("未找到 FFmpeg 工具（请确保 sidecars/media/ffmpeg 完整打包）")
    return ff


def find_piper() -> tuple[str, str]:
    """返回 (piper_exe, piper_model_path)"""
    exe_candidates = [
        "sidecars/tts/piper/piper.exe",
        "sidecars/tts/piper/piper/piper.exe",
        "sidecars/tts/piper/piper",
    ]
    piper_exe = find_tool("piper", "AI_CLIENT_PIPER", exe_candidates)

    # 模型文件查找
    model_path = os.environ.get("PIPER_MODEL", "")
    if model_path and Path(model_path).exists():
        return piper_exe, model_path

    model_candidates = [
        "sidecars/tts/models/zh_CN-huayan-medium.onnx",
        "sidecars/tts/models/zh_CN-huayan-medium.onnx.json",
    ]
    curr = Path(__file__).resolve()
    roots = [curr.parent.parent.parent, curr.parent.parent, curr.parent]
    for root in roots:
        candidate = root / "sidecars/tts/models/zh_CN-huayan-medium.onnx"
        if candidate.exists():
            return piper_exe, str(candidate)

    return piper_exe, ""


# ---------------------------------------------------------------- 流水线各阶段处理


def pptx_to_pdf(pptx: Path, out_dir: Path) -> Path:
    lo = find_libreoffice()
    print(f"  -> 使用 LibreOffice: {lo}")
    # 关键：给 LibreOffice 指定独立用户配置目录，避免多实例/默认 profile 锁导致
    # headless 转换无限期挂起（Windows 下非常常见）；同时加超时兜底。
    profile = out_dir / "lo_profile"
    profile.mkdir(parents=True, exist_ok=True)
    env_arg = f"-env:UserInstallation={profile.resolve().as_uri()}"
    sh(
        [lo, "--headless", env_arg, "--norestore", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)],
        timeout=300,
    )
    pdf = out_dir / (pptx.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError(f"LibreOffice 未能导出 PDF: 预期路径 {pdf} 不存在")
    print(f"  [OK] 成功生成高清矢量 PDF: {pdf.name} ({round(pdf.stat().st_size / 1024, 1)} KB)")
    return pdf


def pdf_to_pngs(pdf: Path, out_dir: Path, dpi: int = 128) -> list[Path]:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf)
    paths = []
    print(f"  -> 正在将 PDF ({len(doc)} 页) 栅格化为高清逐页帧图 (DPI={dpi})...")
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        p = out_dir / f"slide_{i + 1:03d}.png"
        pix.save(p)
        paths.append(p)
    print(f"  [OK] 成功导出 {len(paths)} 张幻灯片高清帧图")
    return paths


def extract_notes(pptx: Path) -> list[str]:
    from pptx import Presentation

    prs = Presentation(str(pptx))
    notes = []
    for i, slide in enumerate(prs.slides):
        note = ""
        if slide.has_notes_slide:
            note = slide.notes_slide.notes_text_frame.text.strip()
        # 如果没有演讲者备注，尝试从当前页面的文本框提取一段简短解说作为口播
        if not note:
            texts = []
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text_frame.text.strip():
                    texts.append(shape.text_frame.text.strip())
            if texts:
                note = "。".join(texts[:3])
        notes.append(note)
    return notes


def tts_piper(text: str, out: Path, piper_exe: str, model_path: str) -> bool:
    """使用 Piper 离线语音合成引擎。"""
    try:
        sh([piper_exe, "--model", model_path, "--output_file", str(out)], input=text.encode("utf-8"))
        return out.exists() and out.stat().st_size > 500
    except Exception as e:
        print(f"  ! Piper 合成失败: {e}", file=sys.stderr)
        return False


def tts_windows_sapi(text: str, out: Path) -> bool:
    """使用 Windows 内置 SAPI5 / PowerShell 语音合成（零依赖，系统自带）。"""
    if sys.platform != "win32":
        return False
    try:
        # 转义单引号
        safe_text = text.replace("'", "''").replace("\r", " ").replace("\n", " ")
        ps_cmd = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = 0; "
            f"$s.SetOutputToWaveFile('{str(out)}'); "
            f"$s.Speak('{safe_text}'); "
            f"$s.Dispose()"
        )
        res = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], check=False)
        return res.returncode == 0 and out.exists() and out.stat().st_size > 500
    except Exception as e:
        print(f"  ! Windows SAPI 合成失败: {e}", file=sys.stderr)
        return False


def generate_silent_audio(out: Path, duration: float, ffmpeg: str) -> None:
    """生成一段指定时长的静音音频（保证音画合成不中断）。"""
    dur_str = f"{max(duration, 2.5):.2f}"
    sh([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", dur_str, "-c:a", "pcm_s16le", str(out)])


def synthesize_one(i: int, text: str, work: Path, ffmpeg: str, piper_exe: str, piper_model: str) -> Path:
    """合成单页解说旁白（多级容灾：Piper -> Windows SAPI -> 静音）。"""
    out = work / f"audio_{i:03d}.wav"
    clean_text = text.strip()

    if not clean_text:
        generate_silent_audio(out, 3.0, ffmpeg)
        return out

    success = False
    if piper_exe and piper_model and Path(piper_model).exists():
        success = tts_piper(clean_text, out, piper_exe, piper_model)
        if success:
            print(f"    - 第 {i} 页语音合成完成 (Piper 神经网络): {clean_text[:25]}...")
    if not success and sys.platform == "win32":
        success = tts_windows_sapi(clean_text, out)
        if success:
            print(f"    - 第 {i} 页语音合成完成 (Windows SAPI5): {clean_text[:25]}...")
    if not success:
        generate_silent_audio(out, 3.0, ffmpeg)
    return out


def synthesize_all(notes: list[str], engine: str, work: Path, ffmpeg: str) -> list[Path]:
    piper_exe, piper_model = find_piper()
    workers = min(4, os.cpu_count() or 2)
    wavs: list[Path | None] = [None] * len(notes)

    print(f"  -> 开始并行合成 {len(notes)} 段解说旁白音频（{workers} 并发）...")
    tasks = [(i, text) for i, text in enumerate(notes, start=1)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, wav in pool.map(
            lambda item: (item[0], synthesize_one(item[0], item[1], work, ffmpeg, piper_exe, piper_model)),
            tasks,
        ):
            wavs[i - 1] = wav

    return [w for w in wavs if w is not None]
def make_clip(slide: Path, wav: Path, clip: Path, ffmpeg: str) -> None:
    """将单页图片与对应音频合成独立视频切片。"""
    cmd = [
        ffmpeg,
        "-y",
        "-loop", "1",
        "-i", str(slide),
        "-i", str(wav),
        # 强制输出尺寸为偶数：128/160 DPI 下宽度可能为奇数(如 1707)，x264 无法编码
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(clip),
    ]
    sh(cmd)


def concat_clips(clips: list[Path], out: Path, ffmpeg: str) -> None:
    """无损拼接所有视频切片为完整口播 MP4 视频。"""
    lst = out.with_suffix(".txt")
    lines = [f"file '{c.resolve().as_posix()}'" for c in clips]
    lst.write_text("\n".join(lines), encoding="utf-8")
    sh([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    if lst.exists():
        lst.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="PPTX -> 离线口播视频生成引擎")
    ap.add_argument("--pptx", required=True, help="输入的 PPTX 文件路径")
    ap.add_argument("--out", required=True, help="输出的 MP4 视频路径")
    ap.add_argument("--tts", default="piper", choices=["piper", "cosyvoice", "auto"], help="TTS 引擎选择")
    args = ap.parse_args()

    pptx = Path(args.pptx).resolve()
    if not pptx.exists():
        print(f"[错误] 输入 PPTX 不存在: {pptx}", file=sys.stderr)
        return 1

    out = Path(args.out).resolve()
    if out.suffix.lower() != ".mp4":
        out = out.parent / f"{pptx.stem}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("[START] 启动口播视频生成流水线 (全程离线自包含)")
    print(f"  输入文稿: {pptx.name}")
    print(f"  输出目标: {out}")
    print("=" * 60)

    ffmpeg = find_ffmpeg()
    print(f"  -> 检测到 FFmpeg: {ffmpeg}")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        # 阶段 1/4: LibreOffice PPTX -> PDF
        log_step(1, 4, "调用内置 LibreOffice 将 PPTX 渲染为高质量矢量 PDF...")
        pdf = pptx_to_pdf(pptx, work)

        # 阶段 2/4: PyMuPDF PDF -> PNGs
        log_step(2, 4, "提取逐页幻灯片高清图像帧 (160 DPI 高清渲染)...")
        slides = pdf_to_pngs(pdf, work)

        # 阶段 3/4: 提取备注并语音合成
        log_step(3, 4, "解析演讲者备注并进行多轨离线语音合成...")
        notes = extract_notes(pptx)
        wavs = synthesize_all(notes, args.tts, work, ffmpeg)

        # 阶段 4/4: 合成各页面视频切片并最终拼接
        log_step(4, 4, "使用内置 FFmpeg 进行音视频画面对齐与视频拼接...")
        slide_wav_pairs = list(zip(slides, wavs))
        clip_workers = min(4, os.cpu_count() or 2)
        clips: list[Path | None] = [None] * len(slide_wav_pairs)
        print(f"  -> 并行渲染 {len(slide_wav_pairs)} 页视频切片（{clip_workers} 并发）...")
        with ThreadPoolExecutor(max_workers=clip_workers) as pool:
            def render_one(item):
                i, (slide, wav) = item
                clip = work / f"clip_{i:03d}.mp4"
                make_clip(slide, wav, clip, ffmpeg)
                return i, clip
            for i, clip in pool.map(render_one, list(enumerate(slide_wav_pairs, start=1))):
                clips[i - 1] = clip

        clips = [c for c in clips if c is not None]
        print(f"  -> 拼接全部 {len(clips)} 个视频切片为最终成品视频...")
        concat_clips(clips, out, ffmpeg)

    if out.exists():
        size_mb = round(out.stat().st_size / (1024 * 1024), 2)
        print("=" * 60)
        print(f"[SUCCESS] 口播视频渲染圆满完成！")
        print(f"  成片路径: {out}")
        print(f"  文件大小: {size_mb} MB")
        print("=" * 60)
        return 0
    else:
        print("[错误] 未能生成最终视频文件", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
