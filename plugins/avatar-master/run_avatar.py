# -*- coding: utf-8 -*-
"""
Master CLI Entrypoint for Digital Human Video Studio.
Orchestrates:
1. Speech Synthesis & Audio Mastering (AudioPipeline -> WAV + SRT)
2. Audio Mel-spectrogram extraction (MelExtractor)
3. Neural Lipsync Inference (LipsyncEngine)
4. Video Compositing & Subtitles (Compositor -> Standalone or PPT PiP)
"""

import os
import sys
import json
import time
import shutil
import tempfile
import argparse
import logging
from pathlib import Path

# Add current plugin directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audio_pipeline import AudioPipeline
from lipsync_onnx import LipsyncEngine, ensure_preset_assets, prepare_custom_avatar_assets
from compositor import composite_standalone, composite_ppt_pip

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("avatar.master")


def normalize_cli_args(argv):
    """Normalize negative rate/pitch args like ['--rate', '-4%'] to ['--rate=-4%']."""
    normalized = []
    skip = False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a in ("--rate", "--pitch") and i + 1 < len(argv):
            next_val = argv[i + 1]
            if not next_val.startswith("--"):
                normalized.append(f"{a}={next_val}")
                skip = True
                continue
        normalized.append(a)
    return normalized


def locate_default_dirs():
    """Locate preset directory, model directory, and project root."""
    proj_root = SCRIPT_DIR.parent.parent
    presets_dir = proj_root / "sidecars" / "avatar" / "presets"
    models_dir = proj_root / "sidecars" / "avatar" / "models"
    return proj_root, presets_dir, models_dir


def print_progress(percent: int, message: str):
    print(f"[PROGRESS] {percent}%: {message}", flush=True)
    logger.info(f"Progress {percent}%: {message}")


def main():
    raw_args = sys.argv[1:]
    normalized_args = normalize_cli_args(raw_args)

    proj_root, default_presets_dir, default_models_dir = locate_default_dirs()

    parser = argparse.ArgumentParser(description="Digital Human Video Studio Engine")
    parser.add_argument("--mode", choices=["standalone", "ppt_pip"], default="standalone",
                        help="Synthesis mode: standalone anchor video or PPT PiP overlay")
    parser.add_argument("--avatar-id", default="boyang",
                        help="Anchor preset identifier (e.g. boyang, wanqing, zhiming, xinyue, custom)")
    parser.add_argument("--custom-avatar-media", default="",
                        help="Custom anchor video or portrait photo file path (.mp4, .mov, .jpg, .png)")
    parser.add_argument("--presets-dir", default=str(default_presets_dir),
                        help="Directory containing anchor preset folders")
    parser.add_argument("--model-path", default=str(default_models_dir / "wav2lip.onnx"),
                        help="Path to wav2lip.onnx model weight")
    parser.add_argument("--text", default="",
                        help="Narration script text")
    parser.add_argument("--audio", default="",
                        help="Optional existing speech audio path (if provided, skips TTS)")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural",
                        help="TTS voice model identifier")
    parser.add_argument("--rate", default="+0%",
                        help="Speech rate offset (e.g. -4%%, +0%%, +10%%)")
    parser.add_argument("--pitch", default="+0Hz",
                        help="Speech pitch offset")
    parser.add_argument("--tts-engine", default="auto", choices=["auto", "piper", "edge", "system"],
                        help="TTS synthesis engine strategy")
    parser.add_argument("--background", default="studio_blue",
                        help="Background preset name or custom image/video path or 'none'")
    parser.add_argument("--chroma-key", action="store_true",
                        help="Enable green-screen removal for anchor footage")
    parser.add_argument("--no-subtitles", action="store_true",
                        help="Do not burn subtitles into the output video")
    parser.add_argument("--pptx", default="",
                        help="PPTX presentation path for PPT PiP mode")
    parser.add_argument("--ppt-video", default="",
                        help="Pre-rendered PPT video path for PPT PiP mode")
    parser.add_argument("--pip-pos", default="bottom_right",
                        choices=["bottom_right", "bottom_left", "top_right", "top_left"],
                        help="Anchor position in PPT PiP mode")
    parser.add_argument("--pip-style", default="circle",
                        choices=["circle", "rounded_rect", "rect"],
                        help="Anchor window shape in PPT PiP mode")
    parser.add_argument("--pip-scale", type=float, default=0.28,
                        help="Anchor relative scale (0.15 to 0.45)")
    parser.add_argument("--out", default="",
                        help="Destination output MP4 video path")
    parser.add_argument("--device", default="auto",
                        choices=["auto", "directml", "cuda", "cpu"],
                        help="Inference acceleration provider")

    args = parser.parse_args(normalized_args)

    if not args.text and not args.audio:
        logger.error("Either --text or --audio must be specified.")
        sys.exit(1)

    # Determine destination output path safely
    if args.out:
        out_path = Path(args.out).resolve()
    else:
        try:
            out_dir = proj_root / "workspace" / "exports"
            out_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            out_dir = Path(tempfile.gettempdir()) / "ai_client_avatar_exports"
            out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"avatar_{args.avatar_id}_{args.mode}_{int(time.time())}.mp4"
        out_path = out_dir / filename

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = out_path.parent / f"_temp_avatar_{args.avatar_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        work_dir = Path(tempfile.gettempdir()) / f"ai_client_temp_{args.avatar_id}"
        work_dir.mkdir(parents=True, exist_ok=True)

    try:
        print_progress(5, "初始化数字人渲染沙箱与参数配置...")
        # Step 1: Voice Narration Pipeline
        logger.info(">>> [Phase 1/4] Processing Speech Narration Pipeline...")
        print_progress(15, "正在进行语义断句、标点生理停顿注入与高保真语音母带合成...")
        audio_pipe = AudioPipeline(sample_rate=16000)

        if args.audio and os.path.isfile(args.audio):
            master_audio, srt_file = audio_pipe.generate_from_audio(
                audio_input_path=args.audio,
                output_dir=str(work_dir),
                source_text=args.text or None
            )
        else:
            master_audio, srt_file = audio_pipe.generate_from_text(
                text=args.text,
                output_dir=str(work_dir),
                voice=args.voice,
                rate=args.rate,
                pitch=args.pitch,
                engine=args.tts_engine
            )

        if args.no_subtitles:
            srt_file = None

        logger.info(f"Master audio ready: {master_audio}")
        print_progress(30, "语音母带合成完毕 (已对齐 EBU R128 标准)，正在核验人物底模...")

        # Step 2: Ensure Preset Assets or Process Custom Avatar
        logger.info(">>> [Phase 2/4] Verifying Digital Human Preset Assets...")
        if args.avatar_id == "custom" or args.custom_avatar_media:
            if args.custom_avatar_media and os.path.isfile(args.custom_avatar_media):
                logger.info(f"Using custom avatar media: {args.custom_avatar_media}")
                print_progress(35, "正在提取自定义人物视频/照片素材特征与 25FPS 底模循环...")
                custom_dir = work_dir / "custom_avatar"
                preset_dir = prepare_custom_avatar_assets(args.custom_avatar_media, str(custom_dir))
            else:
                logger.warning("未检测到有效自定义素材文件，自动降级至精选内置主播「伯洋」...")
                args.avatar_id = "boyang"
                preset_dir = Path(args.presets_dir) / "boyang"
                preset_dir = ensure_preset_assets(str(preset_dir), "boyang")
        else:
            preset_dir = Path(args.presets_dir) / args.avatar_id
            preset_dir = ensure_preset_assets(str(preset_dir), args.avatar_id)

        print_progress(45, "人物底模素材与面部嘴周关键坐标核验通过...")

        # Step 3: Neural Lipsync Synthesis
        logger.info(">>> [Phase 3/4] Synthesizing Lipsync Frame Sequence...")
        print_progress(55, "正在进行神经网络逐帧声画动态唇形重构 (25 FPS)...")
        lipsync_engine = LipsyncEngine(
            model_path=args.model_path if os.path.isfile(args.model_path) else None,
            device=args.device,
            enable_enhancer=False
        )

        synced_avatar_video = str(work_dir / "avatar_synced.mp4")
        lipsync_engine.synthesize(
            preset_dir=preset_dir,
            audio_path=master_audio,
            output_video_path=synced_avatar_video,
            fps=25
        )
        print_progress(75, "神经网络动态唇形重构完成，进入最终音画与字幕合成...")

        # Step 4: Final Layer Blending & Presentation Compositing
        logger.info(f">>> [Phase 4/4] Final Compositing (Mode: {args.mode})...")
        print_progress(85, "正在进行音画流编码封装与微黑底白字字幕烧录...")

        if args.mode == "standalone":
            target_res = (1920, 1080)
            try:
                import cv2
                cap = cv2.VideoCapture(synced_avatar_video)
                if cap.isOpened():
                    vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    if vh > vw:
                        # 竖屏人像 (例如 720x1280 或 1080x1920)：严禁强行拉伸成 16:9 横屏
                        target_res = (1080, 1920) if (vh >= 1200 or vw >= 720) else (vw, vh)
                    else:
                        target_res = (1920, 1080)
            except Exception:
                pass

            final_video = composite_standalone(
                avatar_video_path=synced_avatar_video,
                audio_path=master_audio,
                output_path=str(out_path),
                srt_path=srt_file,
                bg_preset_or_path=args.background,
                chroma_key=args.chroma_key,
                resolution=target_res
            )
        else:
            # Mode: ppt_pip
            ppt_video = args.ppt_video
            if not ppt_video or not os.path.isfile(ppt_video):
                # Check if pptx is provided and rendered video exists nearby
                if args.pptx and os.path.isfile(args.pptx):
                    potential_vid = Path(args.pptx).with_suffix(".mp4")
                    if potential_vid.is_file():
                        ppt_video = str(potential_vid)
                    else:
                        raise FileNotFoundError(f"Rendered PPT video not found for {args.pptx}. Please render PPT to video first.")
                else:
                    raise ValueError("PPT PiP mode requires either --ppt-video or a valid --pptx with rendered video.")

            final_video = composite_ppt_pip(
                ppt_video_path=ppt_video,
                avatar_video_path=synced_avatar_video,
                output_path=str(out_path),
                audio_path=master_audio,
                pip_pos=args.pip_pos,
                pip_style=args.pip_style,
                pip_scale=args.pip_scale,
                srt_path=srt_file
            )

        print_progress(100, "数字人成片渲染与字幕封装完成！")

        # Emit JSON result to stdout for client parsing
        result_payload = {
            "success": True,
            "output_path": str(out_path),
            "mode": args.mode,
            "avatar_id": args.avatar_id,
            "srt_path": srt_file,
            "master_audio": master_audio
        }
        print(f"__RESULT_JSON__{json.dumps(result_payload)}__END_RESULT__")
        logger.info(f"Digital human synthesis completed successfully: {out_path}")

    finally:
        # Cleanup temporary scratch files
        if work_dir.exists():
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Could not cleanly remove temp directory {work_dir}: {e}")


if __name__ == "__main__":
    main()
