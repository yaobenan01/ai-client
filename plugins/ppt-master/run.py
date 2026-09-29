#!/usr/bin/env python3
"""ppt-master 驱动：生成美观、可编辑的原生 PPTX。

用法：
  python run.py generate --input <材料> --out <输出目录>

设计说明：
  - 16:9 现代扁平风格，统一色板与栅格，标题/卡片/页脚分层清晰；
  - 全部使用原生形状与文本框，产出为**可编辑** PPTX（非图片）；
  - 每条要点渲染为独立卡片，自动分页，避免文字挤在一起；
  - 同时写入演讲者备注，供 render_video.py 生成口播视频时朗读。

环境变量：
  AI_CLIENT_PPT_FONT   正文字体（默认 微软雅黑）
  AI_CLIENT_PPT_THEME  主题：indigo(默认) / teal / amber
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- 主题

THEMES = {
    "indigo": {
        "primary": (0x4F, 0x46, 0xE5),
        "primary_dark": (0x31, 0x2E, 0x9B),
        "accent": (0x06, 0xB6, 0xD4),
        "soft": (0xF1, 0xF5, 0xF9),
        "soft2": (0xEE, 0xF2, 0xFF),
    },
    "teal": {
        "primary": (0x0D, 0x94, 0x88),
        "primary_dark": (0x0F, 0x76, 0x6E),
        "accent": (0x38, 0xBD, 0xF8),
        "soft": (0xF0, 0xFD, 0xFA),
        "soft2": (0xEC, 0xFE, 0xFF),
    },
    "amber": {
        "primary": (0xD9, 0x77, 0x06),
        "primary_dark": (0xB4, 0x53, 0x09),
        "accent": (0x0E, 0xA5, 0xE9),
        "soft": (0xFF, 0xFB, 0xEB),
        "soft2": (0xFF, 0xF7, 0xED),
    },
}

INK = (0x0F, 0x17, 0x2A)
MUTED = (0x64, 0x74, 0x8B)
WHITE = (0xFF, 0xFF, 0xFF)
LINE = (0xE2, 0xE8, 0xF0)


def _font_name() -> str:
    return os.environ.get("AI_CLIENT_PPT_FONT", "微软雅黑")


def _rgb(v):
    from pptx.dml.color import RGBColor

    return RGBColor(*v)


# ---------------------------------------------------------------- Markdown 解析

_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_TOKENS = re.compile(r"(\*\*|__|\*|`|~~)")


def clean_inline(text: str) -> str:
    """去掉 Markdown 装饰，只保留可读文本。"""
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_TOKENS.sub("", text)
    return text.strip()


def parse_markdown(text: str):
    """解析为 (deck_title, subtitle, [(section_title, [bullet, ...]), ...])。"""
    deck_title = "演示文稿"
    subtitle = ""
    sections: list[tuple[str, list[str]]] = []
    cur_title = "概览"
    cur_bullets: list[str] = []
    started = False
    seen_h2 = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith("# ") and not line.startswith("## "):
            if not started:
                deck_title = clean_inline(line[2:])
                started = True
                continue
            cur_bullets.append(clean_inline(line[2:]))
            continue
        if line.startswith("## "):
            if seen_h2 or cur_bullets:
                sections.append((cur_title, cur_bullets))
                cur_bullets = []
            cur_title = clean_inline(line[3:]) or "概览"
            seen_h2 = True
            continue
        if line.startswith("### "):
            cur_bullets.append(clean_inline(line[4:]))
            continue
        if not seen_h2 and not subtitle and not stripped.startswith(("-", "*", "•")):
            # 第一个二级标题之前的说明文字，作为副标题
            subtitle = clean_inline(stripped)
            continue
        stripped = re.sub(r"^\s*(?:[-*•]|\d+[.、)]|[①-⑳])\s*", "", stripped)
        stripped = clean_inline(stripped)
        if stripped:
            cur_bullets.append(stripped)

    if cur_bullets or seen_h2:
        sections.append((cur_title, cur_bullets))
    if not sections:
        sections = [("概览", ["（空演示文稿，请补充材料）"])]
    return deck_title, subtitle, sections


MAX_PER_SLIDE = 6


def safe_filename(name: str, fallback: str) -> str:
    """把幻灯片标题转成安全的文件名。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]', "", name).strip().strip(".")
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:60] or fallback


def split_sections(sections):
    """要点过多时自动分页，避免单页拥挤。"""
    out = []
    for title, bullets in sections:
        if not bullets:
            out.append((title, []))
            continue
        for i in range(0, len(bullets), MAX_PER_SLIDE):
            chunk = bullets[i : i + MAX_PER_SLIDE]
            part = title if i == 0 else f"{title}（续）"
            out.append((part, chunk))
    return out


# ---------------------------------------------------------------- 绘图原语


def _style_run(run, size: float, bold: bool, color, font: str):
    from pptx.oxml.ns import qn
    from pptx.util import Pt

    f = run.font
    f.name = font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = _rgb(color)
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", font)


def add_text(
    slide,
    l,
    t,
    w,
    h,
    text,
    size=16,
    bold=False,
    color=INK,
    align="left",
    line_spacing=1.15,
    anchor="top",
):
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches

    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = {
        "top": MSO_ANCHOR.TOP,
        "middle": MSO_ANCHOR.MIDDLE,
        "bottom": MSO_ANCHOR.BOTTOM,
    }[anchor]
    p = tf.paragraphs[0]
    p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}[align]
    p.line_spacing = line_spacing
    run = p.add_run()
    run.text = text
    _style_run(run, size, bold, color, _font_name())
    return box


def add_shape(slide, l, t, w, h, fill=None, shape="rounded", radius=0.12, line=None, line_w=1.0):
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    kind = {
        "rounded": MSO_SHAPE.ROUNDED_RECTANGLE,
        "rect": MSO_SHAPE.RECTANGLE,
        "oval": MSO_SHAPE.OVAL,
    }[shape]
    shp = slide.shapes.add_shape(kind, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = _rgb(line)
        shp.line.width = Pt(line_w)
    # 去掉主题样式引用，否则 LibreOffice/PowerPoint 会渲染出默认阴影
    try:
        from pptx.oxml.ns import qn

        sp = shp._element
        style = sp.find(qn("p:style"))
        if style is not None:
            sp.remove(style)
        shp.shadow.inherit = False
    except Exception:
        pass
    if shape == "rounded":
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    return shp


# ---------------------------------------------------------------- 版式


def build_cover(prs, deck_title, subtitle, theme, total):
    from pptx.util import Inches

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    W, H = prs.slide_width, prs.slide_height

    # 装饰（先画，位于文字下层）
    add_shape(slide, 10.6, 0.9, 3.6, 3.6, fill=theme["soft2"], shape="oval")
    add_shape(slide, 11.9, 3.4, 1.15, 1.15, fill=theme["accent"], shape="oval")
    add_shape(slide, 0.0, 6.55, 13.334, 0.96, fill=theme["primary"], shape="rect")

    add_shape(slide, 0.92, 1.62, 0.92, 0.09, fill=theme["accent"], radius=0.5)
    add_text(slide, 0.9, 1.95, 9.9, 2.2, deck_title, size=40, bold=True, color=INK, line_spacing=1.06)

    if subtitle:
        add_text(slide, 0.93, 4.15, 9.0, 0.9, subtitle, size=15, color=MUTED, line_spacing=1.3)

    add_shape(slide, 0.93, 5.35, 2.6, 0.02, fill=LINE, shape="rect")
    add_text(
        slide,
        0.93,
        5.55,
        8.0,
        0.4,
        datetime.now().strftime("%Y-%m-%d") + f"   ·   共 {total} 页",
        size=11,
        color=MUTED,
    )
    add_text(
        slide,
        0.92,
        6.83,
        10.0,
        0.4,
        "AI 客户端 · 离线智能体   |   由 ppt-master 生成",
        size=11,
        color=WHITE,
    )
    add_text(slide, 11.6, 5.55, 0.9, 0.4, "COVER", size=10, bold=True, color=theme["primary_dark"], align="right")
    return slide


def build_content(prs, page_no, total, title, bullets, theme):
    from pptx.util import Inches

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 页码徽标 + 标题 + 下划线
    add_shape(slide, 0.75, 0.52, 0.66, 0.36, fill=theme["primary"], radius=0.35)
    add_text(
        slide,
        0.75,
        0.575,
        0.66,
        0.3,
        f"{page_no:02d}",
        size=12,
        bold=True,
        color=WHITE,
        align="center",
    )
    add_text(slide, 1.58, 0.45, 11.0, 0.75, title, size=26, bold=True, color=INK)
    add_shape(slide, 1.60, 1.20, 1.05, 0.065, fill=theme["accent"], radius=0.5)

    # 要点卡片
    top, bottom, left, width = 1.62, 6.78, 0.75, 11.84
    n = max(len(bullets), 1)
    gap = 0.16
    avail = bottom - top
    card_h = min(1.15, (avail - gap * (n - 1)) / n)

    if not bullets:
        add_text(slide, left + 0.25, top + 0.2, width - 0.5, 0.6, "（本页无正文）", size=15, color=MUTED)
    for i, text in enumerate(bullets):
        y = top + i * (card_h + gap)
        add_shape(slide, left, y, width, card_h, fill=theme["soft"], radius=0.14)
        add_shape(
            slide,
            left + 0.03,
            y + 0.1,
            0.08,
            card_h - 0.2,
            fill=theme["primary"] if i % 2 == 0 else theme["accent"],
            radius=0.5,
        )

        # 序号圆点
        badge = 0.34
        bx, by = left + 0.32, y + (card_h - badge) / 2
        add_shape(slide, bx, by, badge, badge, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="oval")
        add_text(slide, bx, by + 0.055, badge, 0.24, str(i + 1), size=11, bold=True, color=WHITE, align="center")

        size = 15 if len(text) <= 46 else (13.5 if len(text) <= 78 else 12)
        add_text(
            slide,
            left + 0.82,
            y + 0.1,
            width - 1.1,
            card_h - 0.2,
            text,
            size=size,
            color=INK,
            line_spacing=1.28,
            anchor="middle",
        )

    # 页脚
    add_shape(slide, 0.75, 6.95, 11.84, 0.012, fill=LINE, shape="rect")
    add_text(slide, 0.75, 7.03, 6.0, 0.3, "AI 客户端 · 离线智能体", size=9, color=MUTED)
    add_text(slide, 9.5, 7.03, 3.09, 0.3, f"{page_no:02d} / {total:02d}", size=9, color=MUTED, align="right")
    return slide


def build_end(prs, theme, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_shape(slide, 0.0, 6.55, 13.334, 0.96, fill=theme["primary"], shape="rect")
    add_shape(slide, 5.85, 2.55, 1.6, 0.075, fill=theme["accent"], radius=0.5)
    add_text(slide, 1.5, 2.9, 10.33, 1.2, "谢谢观看", size=40, bold=True, color=INK, align="center")
    add_text(
        slide,
        1.5,
        4.15,
        10.33,
        0.8,
        "本演示文稿由 AI 客户端 · ppt-master 生成，全部内容可自由编辑",
        size=14,
        color=MUTED,
        align="center",
    )
    add_text(slide, 0.75, 7.03, 11.84, 0.3, f"共 {total} 页", size=9, color=MUTED, align="right")
    return slide


# ---------------------------------------------------------------- 入口


def quick_markdown_pptx(text: str, out_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    theme = THEMES.get(os.environ.get("AI_CLIENT_PPT_THEME", "indigo"), THEMES["indigo"])
    deck_title, subtitle, sections = parse_markdown(text)
    sections = split_sections(sections)

    total = len(sections) + 2  # 封面 + 正文 + 封底
    prs = Presentation()
    prs.slide_width = Inches(13.334)
    prs.slide_height = Inches(7.5)

    build_cover(prs, deck_title, subtitle, theme, total)
    for idx, (title, bullets) in enumerate(sections, start=1):
        slide = build_content(prs, idx, total, title, bullets, theme)
        # 写入演讲者备注，供 render_video.py 生成口播旁白
        note = f"{title}。" + "".join(f"{b}。" for b in bullets)
        slide.notes_slide.notes_text_frame.text = note[:1500]
    build_end(prs, theme, total)

    prs.save(str(out_path))
    print(f"[ppt-master] 已生成 {out_path}（{total} 页，主题 {os.environ.get('AI_CLIENT_PPT_THEME', 'indigo')}）")


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
        text = src.read_text(encoding="utf-8")
        # Agent 生成时输入是 content_xxx.md 这类临时名，用幻灯片标题替代更友好
        if src.stem.startswith("content_"):
            deck_title, _, _ = parse_markdown(text)
            out_path = out_dir / f"{safe_filename(deck_title, src.stem)}_{stamp}.pptx"
        quick_markdown_pptx(text, out_path)
        return 0

    print("[ppt-master] 文档输入需由 Agent 驱动完整工作流（或调用 src 内脚本）", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
