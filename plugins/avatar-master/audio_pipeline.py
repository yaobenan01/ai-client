#!/usr/bin/env python3
"""纯离线语音生成、语义韵律断句、多级停顿注入、SRT 字幕生成与广播级人声母带增强流水线。
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"[音频母带] {msg}", flush=True)


def sh(cmd: list[str], timeout: float | None = 60, **kw) -> subprocess.CompletedProcess:
    cmd_str = " ".join(str(c) for c in cmd)
    try:
        res = subprocess.run(cmd, check=False, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"命令执行超时 (>{timeout}s): {cmd_str}")
    if res.returncode != 0:
        raise RuntimeError(f"执行失败 (退出码 {res.returncode}): {cmd_str}")
    return res


def format_srt_time(ms: int) -> str:
    """毫秒转换为 SRT 标准时间格式: HH:MM:SS,mmm"""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def split_into_semantic_chunks(text: str, max_chunk_len: int = 24) -> list[tuple[str, str]]:
    """将文本切分为符合人类自然呼吸节奏的语义短句与末尾标点符号。

    返回: [(短句内容, 结尾标点), ...]
    """
    # 规整空白与换行
    cleaned = re.sub(r"[\r\n]+", "。 ", text.strip())
    # 匹配标点断句
    pattern = r"([^，。！？、；：!?,;:]+)([，。！？、；：!?,;:]*)"
    matches = re.findall(pattern, cleaned)

    chunks: list[tuple[str, str]] = []
    for content, punct in matches:
        content = content.strip()
        if not content:
            continue
        # 如果单个无标点长句超过最大限制，进一步按并列连词切分
        if len(content) > max_chunk_len:
            sub_parts = re.split(r"(并且|而且|同时|以及|接着|然后|但是|然而)", content)
            accum = ""
            for sp in sub_parts:
                if len(accum) + len(sp) > max_chunk_len and accum:
                    chunks.append((accum, "，"))
                    accum = sp
                else:
                    accum += sp
            if accum:
                chunks.append((accum, punct or "。"))
        else:
            chunks.append((content, punct or "。"))

    return chunks


def get_punctuation_pause_duration(punct: str) -> float:
    """根据中文标点符号赋予真人朗读的生理换气停顿秒数。"""
    if "、" in punct:
        return 0.14
    elif "，" in punct or "," in punct:
        return 0.22
    elif "；" in punct or "：" in punct or ";" in punct or ":" in punct:
        return 0.30
    elif "。" in punct or "！" in punct or "？" in punct or "!" in punct or "?" in punct:
        return 0.42
    return 0.20


def generate_silence_wav(out_wav: Path, duration_sec: float, ffmpeg: str) -> None:
    """生成一段指定秒数的无底噪高精度纯静音 WAV (24kHz 16bit)。"""
    dur = max(duration_sec, 0.05)
    sh(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            f"{dur:.3f}",
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ],
        timeout=15,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def tts_synthesize_segment(
    text: str,
    out_wav: Path,
    voice: str,
    rate: str,
    pitch: str,
    piper_exe: str,
    piper_model: str,
    ffmpeg: str,
    cosy_cli: str = "",
) -> bool:
    """单句合成（优先纯离线 Piper / CosyVoice，自动回退微软神经或系统 SAPI）。"""
    # 1. 尝试 Piper 纯离线神经网络
    if piper_exe and piper_model and Path(piper_model).exists():
        try:
            # 语速调节换算
            scale = 1.05
            if rate:
                m = re.match(r"([+-]?\d+)%", rate)
                if m:
                    pct = int(m.group(1))
                    scale = max(0.65, min(1.6, 1.05 * (1.0 - pct / 100.0)))
            cmd = [
                piper_exe,
                "--model",
                piper_model,
                "--length_scale",
                str(round(scale, 3)),
                "--output_file",
                str(out_wav),
            ]
            sh(cmd, input=text.encode("utf-8"), timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out_wav.exists() and out_wav.stat().st_size > 400:
                return True
        except Exception as e:
            pass

    # 2. 尝试 CosyVoice 本地大模型（若配置）
    if cosy_cli and Path(cosy_cli).exists():
        try:
            sh([sys.executable, cosy_cli, "--text", text, "--output", str(out_wav)], timeout=45)
            if out_wav.exists() and out_wav.stat().st_size > 400:
                return True
        except Exception:
            pass

    # 3. 尝试 Edge-TTS 在线神经语音（有网时极富感情）
    try:
        import edge_tts

        temp_mp3 = out_wav.with_suffix(".tmp.mp3")

        async def _run_edge():
            v = voice or "zh-CN-YunxiNeural"
            c = edge_tts.Communicate(text, v, rate=rate or "+0%", pitch=pitch or "+0Hz")
            await c.save(str(temp_mp3))

        asyncio.run(_run_edge())
        if temp_mp3.exists() and temp_mp3.stat().st_size > 300:
            sh(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(temp_mp3),
                    "-ar",
                    "24000",
                    "-ac",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    str(out_wav),
                ],
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            temp_mp3.unlink(missing_ok=True)
            if out_wav.exists() and out_wav.stat().st_size > 400:
                return True
    except Exception:
        pass

    # 4. Windows 原生 SAPI5 系统兜底（全离线无依赖保底）
    if sys.platform == "win32":
        try:
            safe_text = text.replace("'", "''").replace("\r", " ").replace("\n", " ")
            ps = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Rate = 0; "
                f"$s.SetOutputToWaveFile('{str(out_wav)}'); "
                f"$s.Speak('{safe_text}'); "
                f"$s.Dispose()"
            )
            sh(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], timeout=30)
            if out_wav.exists() and out_wav.stat().st_size > 400:
                return True
        except Exception:
            pass

    # 5. 极端容灾：3 秒静音
    generate_silence_wav(out_wav, 3.0, ffmpeg)
    return False


def get_wav_duration_ms(wav_path: Path) -> int:
    """精确获取 WAV 音频文件毫秒时长。"""
    import wave

    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return int(round((frames / float(rate)) * 1000))


def apply_broadcast_mastering(
    raw_concat_wav: Path,
    out_master_wav: Path,
    out_16k_wav: Path,
    ffmpeg: str,
) -> None:
    """应用广播级人声母带滤镜链：

    - 75Hz 高通滤波（滤除呼吸风噪与机械底噪）
    - 220Hz 增益 2dB（增加胸腔共鸣厚度）
    - 3500Hz 增益 1.5dB（增加齿音与词尾清晰度）
    - 动态压缩器（使声音轻重均匀、富有力量感）
    - EBU R128 标准响度归一化 (-16 LUFS)
    """
    log("正在应用广播级人声母带滤镜链 (EQ均衡 + 动态压缩 + EBU R128 响度标准化)...")
    filter_chain = (
        "highpass=f=75,"
        "equalizer=f=220:width_type=o:width=1.2:g=2.0,"
        "equalizer=f=3500:width_type=o:width=1.5:g=1.5,"
        "acompressor=threshold=-18dB:ratio=2.5:attack=12:release=160:makeup=2dB,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    # 导出 24kHz 广播级母带
    sh(
        [
            ffmpeg,
            "-y",
            "-i",
            str(raw_concat_wav),
            "-af",
            filter_chain,
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out_master_wav),
        ],
        timeout=120,
    )
    # 导出 16kHz 唇形同步专用标准输入
    sh(
        [
            ffmpeg,
            "-y",
            "-i",
            str(out_master_wav),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out_16k_wav),
        ],
        timeout=60,
    )


def process_audio_pipeline(
    script_text: str,
    work_dir: Path,
    ffmpeg_exe: str,
    voice: str = "zh-CN-YunxiNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    piper_exe: str = "",
    piper_model: str = "",
    cosy_cli: str = "",
) -> tuple[Path, Path, Path, float]:
    """完整音频处理流水线：

    返回: (master_audio_24k_path, wav_16k_path, srt_subtitle_path, total_duration_sec)
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    chunks = split_into_semantic_chunks(script_text)
    log(f"剧本已智能分词为 {len(chunks)} 个呼吸语块，开始分句合成与停顿注入...")

    wav_parts: list[Path] = []
    srt_entries: list[str] = []
    current_ms = 0

    for idx, (content, punct) in enumerate(chunks, start=1):
        # 1. 合成主体语句
        part_wav = work_dir / f"seg_{idx:03d}_speech.wav"
        tts_synthesize_segment(
            content,
            part_wav,
            voice=voice,
            rate=rate,
            pitch=pitch,
            piper_exe=piper_exe,
            piper_model=piper_model,
            ffmpeg=ffmpeg_exe,
            cosy_cli=cosy_cli,
        )
        speech_dur_ms = get_wav_duration_ms(part_wav)
        wav_parts.append(part_wav)

        # 记录 SRT 字幕时间轴
        start_time_str = format_srt_time(current_ms)
        end_time_str = format_srt_time(current_ms + speech_dur_ms)
        srt_entries.append(f"{idx}\n{start_time_str} --> {end_time_str}\n{content}\n")
        current_ms += speech_dur_ms

        # 2. 注入标点停顿
        pause_sec = get_punctuation_pause_duration(punct)
        if pause_sec > 0.05 and idx < len(chunks):
            pause_wav = work_dir / f"seg_{idx:03d}_pause.wav"
            generate_silence_wav(pause_wav, pause_sec, ffmpeg_exe)
            pause_ms = get_wav_duration_ms(pause_wav)
            wav_parts.append(pause_wav)
            current_ms += pause_ms

    # 写入 SRT 字幕文件
    srt_path = work_dir / "subtitles.srt"
    srt_path.write_text("\n".join(srt_entries), encoding="utf-8")

    # 合并各片段
    concat_list = work_dir / "concat_audio.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in wav_parts), encoding="utf-8")
    raw_concat = work_dir / "raw_concat.wav"
    sh(
        [
            ffmpeg_exe,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(raw_concat),
        ],
        timeout=60,
    )

    # 母带处理
    master_wav = work_dir / "master_audio.wav"
    audio_16k = work_dir / "audio_16k.wav"
    apply_broadcast_mastering(raw_concat, master_wav, audio_16k, ffmpeg_exe)

    total_duration_sec = current_ms / 1000.0
    log(f"音频母带与 SRT 生成完毕！总时长: {total_duration_sec:.2f} 秒")
    return master_wav, audio_16k, srt_path, total_duration_sec


def _find_binaries():
    root = Path(__file__).resolve().parent.parent.parent
    ffmpeg_exe = os.environ.get("AI_CLIENT_FFMPEG_PATH")
    if not ffmpeg_exe or not Path(ffmpeg_exe).is_file():
        candidates = [
            root / "sidecars" / "media" / "ffmpeg" / "bin" / "ffmpeg.exe",
            root / "sidecars" / "ffmpeg" / "bin" / "ffmpeg.exe",
        ]
        for c in candidates:
            if c.is_file():
                ffmpeg_exe = str(c)
                break
    if not ffmpeg_exe:
        ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"

    piper_exe = os.environ.get("AI_CLIENT_PIPER_PATH")
    if not piper_exe or not Path(piper_exe).is_file():
        p_cand = root / "sidecars" / "tts" / "piper" / "piper.exe"
        if p_cand.is_file():
            piper_exe = str(p_cand)
        else:
            piper_exe = shutil.which("piper") or ""

    piper_model = os.environ.get("AI_CLIENT_PIPER_MODEL")
    if not piper_model or not Path(piper_model).is_file():
        m_cand = root / "sidecars" / "tts" / "models" / "zh_CN-huayan-medium.onnx"
        if m_cand.is_file():
            piper_model = str(m_cand)
        else:
            piper_model = ""

    return str(ffmpeg_exe), str(piper_exe), str(piper_model)


class AudioPipeline:
    """音频母带与唇形对齐流水线封装类"""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.ffmpeg_exe, self.piper_exe, self.piper_model = _find_binaries()

    def generate_from_text(
        self,
        text: str,
        output_dir: str,
        voice: str = "zh-CN-YunxiNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        engine: str = "auto",
    ) -> tuple[str, str]:
        work_dir = Path(output_dir).resolve()
        master_wav, audio_16k, srt_path, _ = process_audio_pipeline(
            script_text=text,
            work_dir=work_dir,
            ffmpeg_exe=self.ffmpeg_exe,
            voice=voice,
            rate=rate,
            pitch=pitch,
            piper_exe=self.piper_exe,
            piper_model=self.piper_model,
        )
        return str(master_wav), str(srt_path)

    def generate_from_audio(
        self,
        audio_input_path: str,
        output_dir: str,
        source_text: str | None = None,
    ) -> tuple[str, str | None]:
        work_dir = Path(output_dir).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)
        inp = Path(audio_input_path).resolve()
        master_wav = work_dir / "master_audio.wav"
        audio_16k = work_dir / "audio_16k.wav"

        apply_broadcast_mastering(inp, master_wav, audio_16k, self.ffmpeg_exe)

        srt_path = None
        if source_text:
            srt_path = work_dir / "subtitles.srt"
            dur_ms = get_wav_duration_ms(master_wav)
            start_time = format_srt_time(0)
            end_time = format_srt_time(dur_ms)
            srt_content = f"1\n{start_time} --> {end_time}\n{source_text.strip()}\n"
            srt_path.write_text(srt_content, encoding="utf-8")
            srt_path = str(srt_path)

        return str(master_wav), srt_path

