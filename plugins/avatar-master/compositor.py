# -*- coding: utf-8 -*-
"""
Compositor Module for Digital Human Studio
Handles video layer blending, PiP (Picture-in-Picture) for PPT/Lecture presentations,
Chroma key background replacement, and SRT subtitle burning via FFmpeg.
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("avatar.compositor")


def find_ffmpeg() -> str:
    """Locate the ffmpeg binary across common project and system locations."""
    # 1. Environment variable
    env_ffmpeg = os.environ.get("AI_CLIENT_FFMPEG_PATH")
    if env_ffmpeg and os.path.isfile(env_ffmpeg):
        return env_ffmpeg

    # 2. Project sidecars relative paths
    base_dir = Path(__file__).resolve().parent.parent.parent
    possible_paths = [
        base_dir / "sidecars" / "media" / "ffmpeg" / "bin" / "ffmpeg.exe",
        base_dir / "sidecars" / "media" / "ffmpeg" / "bin" / "ffmpeg",
        base_dir / "sidecars" / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]
    for p in possible_paths:
        if p.is_file():
            return str(p)

    # 3. System PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    raise FileNotFoundError("FFmpeg executable not found. Please install FFmpeg or configure AI_CLIENT_FFMPEG_PATH.")


def escape_ffmpeg_path(path: str) -> str:
    """Escapes file paths for ffmpeg filter arguments on Windows and POSIX."""
    # FFmpeg filter parser requires forward slashes, escaped colons and single quotes
    clean = str(Path(path).resolve()).replace("\\", "/")
    # Escape colons e.g. C: -> C\:
    clean = clean.replace(":", r"\:")
    # Escape single quotes
    clean = clean.replace("'", r"\'")
    return clean


def composite_standalone(
    avatar_video_path: str,
    audio_path: str,
    output_path: str,
    srt_path: Optional[str] = None,
    bg_preset_or_path: Optional[str] = None,
    chroma_key: bool = False,
    chroma_color: str = "0x00FF00",
    chroma_similarity: float = 0.28,
    chroma_blend: float = 0.1,
    resolution: Tuple[int, int] = (1920, 1080),
) -> str:
    """
    Composites standalone digital human video with background, audio, and subtitle overlay.
    """
    ffmpeg = find_ffmpeg()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    w, h = resolution

    # Preset backgrounds dictionary
    preset_colors = {
        "studio_blue": "0x111e38",
        "tech_dark": "0x0f172a",
        "minimal_white": "0xf8fafc",
        "warm_gray": "0x27272a",
        "cinema_black": "0x050505",
    }

    cmd = [ffmpeg, "-y"]

    # Background handling
    use_bg_file = False
    bg_color = None

    if bg_preset_or_path and bg_preset_or_path != "none":
        if os.path.isfile(bg_preset_or_path):
            use_bg_file = True
        elif bg_preset_or_path in preset_colors:
            bg_color = preset_colors[bg_preset_or_path]
        elif bg_preset_or_path.startswith("#"):
            bg_color = "0x" + bg_preset_or_path.lstrip("#")
        elif bg_preset_or_path.startswith("0x"):
            bg_color = bg_preset_or_path

    if use_bg_file:
        # Input 0: Background video/image
        # Check if background is image or video
        is_bg_video = bg_preset_or_path.lower().endswith((".mp4", ".mov", ".mkv", ".webm"))
        if is_bg_video:
            cmd.extend(["-stream_loop", "-1", "-i", bg_preset_or_path])
        else:
            cmd.extend(["-loop", "1", "-i", bg_preset_or_path])
        # Input 1: Avatar video
        cmd.extend(["-i", avatar_video_path])
        # Input 2: Master audio
        cmd.extend(["-i", audio_path])

        filter_parts = []
        filter_parts.append(f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[bg]")

        if chroma_key:
            filter_parts.append(
                f"[1:v]colorkey={chroma_color}:{chroma_similarity}:{chroma_blend},"
                f"scale={w}:{h}:force_original_aspect_ratio=decrease[fg]"
            )
            filter_parts.append("[bg][fg]overlay=(W-w)/2:(H-h)[comp]")
        else:
            filter_parts.append(
                f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease[fg]"
            )
            filter_parts.append("[bg][fg]overlay=(W-w)/2:(H-h)[comp]")

        last_v = "[comp]"

    elif bg_color:
        # Color background using lavfi color source
        cmd.extend(["-f", "lavfi", "-i", f"color=c={bg_color}:s={w}x{h}:r=25"])
        cmd.extend(["-i", avatar_video_path])
        cmd.extend(["-i", audio_path])

        filter_parts = []
        if chroma_key:
            filter_parts.append(
                f"[1:v]colorkey={chroma_color}:{chroma_similarity}:{chroma_blend},"
                f"scale={w}:{h}:force_original_aspect_ratio=decrease[fg]"
            )
            filter_parts.append("[0:v][fg]overlay=(W-w)/2:(H-h)[comp]")
        else:
            filter_parts.append(f"[1:v]scale={w}:{h}[fg]")
            filter_parts.append("[0:v][fg]overlay=0:0[comp]")

        last_v = "[comp]"

    else:
        # Avatar video directly as base
        cmd.extend(["-i", avatar_video_path])
        cmd.extend(["-i", audio_path])
        filter_parts = [f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[base]"]
        last_v = "[base]"

    # Subtitle burn-in
    if srt_path and os.path.isfile(srt_path):
        escaped_srt = escape_ffmpeg_path(srt_path)
        # Professional modern subtitle styling: clean white text, subtle semi-opaque black box / shadow
        sub_style = (
            "force_style="
            "'FontName=Microsoft YaHei,FontSize=22,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00111111,BackColour=&H60000000,BorderStyle=4,"
            "Outline=1,Shadow=1,MarginV=42,Alignment=2'"
        )
        filter_parts.append(f"{last_v}subtitles='{escaped_srt}':{sub_style}[vsub]")
        last_v = "[vsub]"

    filter_graph = ";".join(filter_parts)
    cmd.extend(["-filter_complex", filter_graph])
    cmd.extend(["-map", last_v])
    # The last input is the master audio
    audio_idx = 2 if (use_bg_file or bg_color) else 1
    cmd.extend(["-map", f"{audio_idx}:a"])

    # Video & audio encoding parameters
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_file)
    ])

    logger.info(f"Executing FFmpeg composition: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        logger.error(f"FFmpeg composite failed:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg composition failed with code {result.returncode}: {result.stderr[-400:]}")

    logger.info(f"Successfully composited standalone avatar video to: {out_file}")
    return str(out_file)


def composite_ppt_pip(
    ppt_video_path: str,
    avatar_video_path: str,
    output_path: str,
    audio_path: Optional[str] = None,
    pip_pos: str = "bottom_right",
    pip_style: str = "circle",
    pip_scale: float = 0.28,
    srt_path: Optional[str] = None,
) -> str:
    """
    Composites PPT video presentation with Picture-in-Picture (PiP) digital human speaker.
    pip_pos: 'bottom_right' | 'bottom_left' | 'top_right' | 'top_left'
    pip_style: 'circle' | 'rounded_rect' | 'rect'
    """
    ffmpeg = find_ffmpeg()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [ffmpeg, "-y"]
    # Input 0: PPT video
    cmd.extend(["-i", ppt_video_path])
    # Input 1: Avatar video
    cmd.extend(["-i", avatar_video_path])
    # Input 2 (Optional): Custom master audio track
    has_audio = False
    if audio_path and os.path.isfile(audio_path):
        cmd.extend(["-i", audio_path])
        has_audio = True

    # Calculate overlay dimensions and positions
    # PPT base is typically 1920x1080 (16:9)
    # Target avatar width = main_W * pip_scale
    filter_parts = []

    if pip_style == "circle":
        # Square crop then circular alpha mask with anti-aliasing
        filter_parts.append(
            f"[1:v]crop=w='min(iw,ih)':h='min(iw,ih)',"
            f"scale=trunc(main_w*{pip_scale}/2)*2:trunc(main_w*{pip_scale}/2)*2,"
            f"format=yuva420p,"
            f"geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':"
            f"alpha='if(lte(hypot(X-W/2,Y-H/2),min(W,H)/2-2),255,if(lte(hypot(X-W/2,Y-H/2),min(W,H)/2),140,0))'[av_pip]"
        )
    elif pip_style == "rounded_rect":
        filter_parts.append(
            f"[1:v]scale=trunc(main_w*{pip_scale}/2)*2:-2,"
            f"format=yuva420p,"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.9:t=3[av_pip]"
        )
    else:  # rect
        filter_parts.append(
            f"[1:v]scale=trunc(main_w*{pip_scale}/2)*2:-2,"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.8:t=2[av_pip]"
        )

    # Position coordinates with 28px margins
    pos_coords = {
        "bottom_right": "W-w-28:H-h-28",
        "bottom_left": "28:H-h-28",
        "top_right": "W-w-28:28",
        "top_left": "28:28",
    }
    coords = pos_coords.get(pip_pos, "W-w-28:H-h-28")

    filter_parts.append(f"[0:v][av_pip]overlay={coords}[vcomp]")
    last_v = "[vcomp]"

    # Subtitles
    if srt_path and os.path.isfile(srt_path):
        escaped_srt = escape_ffmpeg_path(srt_path)
        sub_style = (
            "force_style="
            "'FontName=Microsoft YaHei,FontSize=20,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00111111,BackColour=&H60000000,BorderStyle=4,"
            "Outline=1,Shadow=1,MarginV=30,Alignment=2'"
        )
        filter_parts.append(f"{last_v}subtitles='{escaped_srt}':{sub_style}[vsub]")
        last_v = "[vsub]"

    filter_graph = ";".join(filter_parts)
    cmd.extend(["-filter_complex", filter_graph])
    cmd.extend(["-map", last_v])

    if has_audio:
        cmd.extend(["-map", "2:a"])
    else:
        # Fallback to avatar audio (input 1)
        cmd.extend(["-map", "1:a?"])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_file)
    ])

    logger.info(f"Executing PPT PiP composition: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        logger.error(f"FFmpeg PiP composite failed:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg PiP failed with code {result.returncode}: {result.stderr[-400:]}")

    logger.info(f"Successfully generated PPT PiP video: {out_file}")
    return str(out_file)
