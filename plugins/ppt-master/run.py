#!/usr/bin/env python3
"""ppt-master 驱动：生成可编辑 PPTX。

用法：
  python run.py generate --input <材料> --out <输出目录>

说明：
  1) 优先委托完整 ppt-master 工作流（见 src/ 内的 SKILL.md 与脚本）。
  2) 对 Markdown/文本提供零依赖的「快速生成」兜底，产出原生可编辑 PPTX。
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


def quick_markdown_pptx(text: str, out_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    title = "演示文稿"
    slides = []  # (title, bullets)
    cur_title, cur_bullets = title, []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            if cur_title or cur_bullets:
                slides.append((cur_title, cur_bullets))
            cur_title, cur_bullets = line[3:].strip(), []
        elif line.startswith("- "):
            cur_bullets.append(line[2:].strip())
        else:
            cur_bullets.append(line.strip())
    if cur_title or cur_bullets:
        slides.append((cur_title, cur_bullets))
    if not slides:
        slides = [(title, ["（空演示文稿，请补充材料）"])]

    blank = prs.slide_layouts[6]
    for idx, (t, bullets) in enumerate(slides):
        slide = prs.slides.add_slide(blank)
        if idx == 0:
            box = slide.shapes.add_textbox(Inches(0.9), Inches(2.6), Inches(11.5), Inches(2.0))
            tf = box.text_frame
            tf.text = t
            tf.paragraphs[0].font.size = Pt(44)
            tf.paragraphs[0].font.bold = True
        else:
            box = slide.shapes.add_textbox(Inches(0.9), Inches(0.6), Inches(11.5), Inches(1.0))
            tf = box.text_frame
            tf.text = t
            tf.paragraphs[0].font.size = Pt(32)
            tf.paragraphs[0].font.bold = True

        body = slide.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(5.0))
        btf = body.text_frame
        for i, b in enumerate(bullets[:8]):
            p = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
            p.text = b
            p.font.size = Pt(20)

    prs.save(str(out_path))
    print(f"[ppt-master] 已生成 {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="ppt-master driver")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--input", required=True)
    g.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.cmd != "generate":
        print("unknown command", file=sys.stderr)
        return 2

    src = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{src.stem}_{stamp}.pptx"

    if src.suffix.lower() in {".md", ".txt", ".markdown"}:
        quick_markdown_pptx(src.read_text(encoding="utf-8"), out_path)
        return 0

    # 文档类输入（PDF/DOCX/URL）委托完整 ppt-master 工作流。
    # 完整工作流由核心 Agent 读取 src/SKILL.md 并驱动其脚本执行；
    # 这里保留明确的接入点。
    print("[ppt-master] 文档输入需由 Agent 驱动完整工作流（或调用 src 内脚本）", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
