#!/usr/bin/env python3
"""ppt-master 驱动：生成专业、内容丰富、图文并茂的原生可编辑 PPTX。

核心设计能力：
  - 16:9 现代专业版式体系（封面、目录、多栏卡片、数据亮点大字、流程图解、对比分析、封底）；
  - 自适应多版式识别引擎：根据内容语义自动匹配「指标亮点卡片」、「横向流程步骤」、「多列卡片」、「图文混排」；
  - 原生矢量形状与排版：所有元素均由 python-pptx 原生矢量卡片渲染，用户可在 PowerPoint / WPS / LibreOffice 中随意修改；
  - 图文并茂增强：支持解析 Markdown 中的图片语法 `![alt](path)` 原生嵌入，未配图时自动辅以高质感装饰几何、胶囊徽标与类别标签；
  - 自动生成流畅自然的演讲者口播旁白，直接赋能后续视频合成。

环境变量支持：
  AI_CLIENT_PPT_FONT   正文字体（默认 微软雅黑）
  AI_CLIENT_PPT_THEME  主题：indigo(默认) / teal / amber / crimson / slate
"""
from __future__ import annotations

import argparse
import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- 主题系统

THEMES = {
    "indigo": {
        "primary": (0x4F, 0x46, 0xE5),        # 科技靛蓝
        "primary_dark": (0x31, 0x2E, 0x9B),
        "primary_light": (0x81, 0x8C, 0xF8),
        "accent": (0x06, 0xB6, 0xD4),         # 青空蓝
        "soft": (0xF8, 0xFA, 0xFC),           # 底色
        "soft2": (0xEE, 0xF2, 0xFF),          # 卡片高亮底色
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
    "teal": {
        "primary": (0x0D, 0x94, 0x88),        # 碧翠青绿
        "primary_dark": (0x0F, 0x76, 0x6E),
        "primary_light": (0x2D, 0xD4, 0xBF),
        "accent": (0x02, 0x84, 0xC7),         # 天空蓝
        "soft": (0xF0, 0xFD, 0xFA),
        "soft2": (0xEC, 0xFE, 0xFF),
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
    "amber": {
        "primary": (0xD9, 0x77, 0x06),        # 琥珀金橙
        "primary_dark": (0xB4, 0x53, 0x09),
        "primary_light": (0xFB, 0xBF, 0x24),
        "accent": (0x25, 0x63, 0xEB),         # 经典蓝
        "soft": (0xFF, 0xFB, 0xEB),
        "soft2": (0xFF, 0xF7, 0xED),
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
    "crimson": {
        "primary": (0xE1, 0x1D, 0x48),        # 经典绯红
        "primary_dark": (0x9F, 0x12, 0x39),
        "primary_light": (0xFB, 0x71, 0x85),
        "accent": (0xF5, 0x9E, 0x0B),         # 金色点缀
        "soft": (0xFF, 0xF1, 0xF2),
        "soft2": (0xFF, 0xE4, 0xE6),
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
    "slate": {
        "primary": (0x33, 0x41, 0x55),        # 极简岩灰
        "primary_dark": (0x0F, 0x17, 0x2A),
        "primary_light": (0x64, 0x74, 0x8B),
        "accent": (0x3B, 0x82, 0xF6),         # 极简蓝
        "soft": (0xF8, 0xFA, 0xFC),
        "soft2": (0xF1, 0xF5, 0xF9),
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
}

INK = (0x0F, 0x17, 0x2A)
INK_LIGHT = (0x33, 0x41, 0x55)
MUTED = (0x64, 0x74, 0x8B)
WHITE = (0xFF, 0xFF, 0xFF)
LINE = (0xE2, 0xE8, 0xF0)


def _font_name() -> str:
    return os.environ.get("AI_CLIENT_PPT_FONT", "微软雅黑")


def _rgb(v):
    from pptx.dml.color import RGBColor
    return RGBColor(*v)


# ---------------------------------------------------------------- Markdown 解析与语义识别

_MD_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_TOKENS = re.compile(r"(\*\*|__|\*|`|~~)")


class SlideSection:
    def __init__(self, title: str, bullets: list[str], images: list[str] = None):
        self.title = title
        self.bullets = bullets
        self.images = images or []
        self.layout_type = self._detect_layout()

    def _detect_layout(self) -> str:
        if self.images:
            return "image_text"

        text_corpus = " ".join(self.bullets)

        # 1. 检查是否为指标亮点数据页 (包含百分比、大数字、KPI 词汇)
        metric_matches = re.findall(r"(\d+(?:\.\d+)?%|\d+[xX倍]|\d{2,}\+?万?|\bTOP\s*\d+\b)", text_corpus)
        if len(metric_matches) >= 2 and len(self.bullets) in (2, 3, 4):
            return "stat_cards"

        # 2. 检查是否为流程步骤页 (步骤、阶段、Step、流程)
        step_matches = [b for b in self.bullets if re.search(r"^(?:步骤|阶段|Step|Phase|\d+[.、)])", b, re.IGNORECASE)]
        if len(step_matches) >= 3 or (len(step_matches) >= 2 and len(self.bullets) <= 4):
            return "process_steps"

        # 3. 检查是否适合多栏展示 (2~3 项，且字数较短均衡)
        if len(self.bullets) in (2, 3):
            avg_len = sum(len(b) for b in self.bullets) / len(self.bullets)
            if avg_len <= 120:
                return "column_cards"

        return "standard_cards"


def clean_inline(text: str) -> str:
    """去掉 Markdown 装饰符号，只保留文字内容。"""
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_TOKENS.sub("", text)
    return text.strip()


def parse_markdown_rich(text: str, base_dir: Path | None = None) -> tuple[str, str, list[SlideSection]]:
    deck_title = "演示文稿"
    subtitle = ""
    sections: list[SlideSection] = []

    cur_title = "概览"
    cur_bullets: list[str] = []
    cur_images: list[str] = []
    started = False
    seen_h2 = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # 提取图片路径
        img_match = _MD_IMG.search(stripped)
        if img_match:
            img_path = img_match.group(2)
            if base_dir and not Path(img_path).is_absolute():
                candidate = base_dir / img_path
                if candidate.exists():
                    img_path = str(candidate)
            cur_images.append(img_path)
            # 移除图片语法保留文字
            stripped = _MD_IMG.sub("", stripped).strip()
            if not stripped:
                continue

        # 一级标题：主标题
        if line.startswith("# ") and not line.startswith("## "):
            if not started:
                deck_title = clean_inline(line[2:])
                started = True
                continue
            cur_bullets.append(clean_inline(line[2:]))
            continue

        # 二级标题：幻灯片页面
        if line.startswith("## "):
            if seen_h2 or cur_bullets or cur_images:
                sections.append(SlideSection(cur_title, cur_bullets, cur_images))
                cur_bullets = []
                cur_images = []
            cur_title = clean_inline(line[3:]) or "核心内容"
            seen_h2 = True
            continue

        # 三级标题：要点小标题
        if line.startswith("### "):
            cur_bullets.append(clean_inline(line[4:]))
            continue

        # 副标题
        if not seen_h2 and not subtitle and not stripped.startswith(("-", "*", "•", "1.", "2.")):
            subtitle = clean_inline(stripped)
            continue

        # 列表要点
        clean_line = re.sub(r"^\s*(?:[-*•]|\d+[.、)]|[①-⑳])\s*", "", stripped)
        clean_line = clean_inline(clean_line)
        if clean_line:
            cur_bullets.append(clean_line)

    if cur_bullets or cur_images or seen_h2:
        sections.append(SlideSection(cur_title, cur_bullets, cur_images))

    if not sections:
        sections = [SlideSection("概览与要点", ["（暂无正文要点，请提供更丰富的大纲内容）"])]

    return deck_title, subtitle, sections


# ---------------------------------------------------------------- 底层原生矢量形状与文本封装


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
    l, t, w, h,
    text,
    size=15,
    bold=False,
    color=INK,
    align="left",
    line_spacing=1.2,
    anchor="top",
):
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches

    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
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


def add_header(slide, page_no: int, total: int, title: str, theme: dict):
    """绘制所有内容页统一的专业头部导航栏。"""
    # 顶部装饰微色条
    add_shape(slide, 0.0, 0.0, 13.334, 0.08, fill=theme["primary"], shape="rect")

    # 页码小徽标
    add_shape(slide, 0.8, 0.45, 0.65, 0.36, fill=theme["primary"], radius=0.35)
    add_text(slide, 0.8, 0.5, 0.65, 0.3, f"{page_no:02d}", size=12, bold=True, color=WHITE, align="center")

    # 页面标题
    add_text(slide, 1.6, 0.36, 9.5, 0.75, title, size=25, bold=True, color=INK)

    # 标题下的高光色块装饰
    add_shape(slide, 1.62, 1.15, 1.1, 0.05, fill=theme["accent"], radius=0.5)

    # 页眉右侧主题提示
    add_text(slide, 10.0, 0.48, 2.5, 0.3, "OFFLINE AGENT", size=9, bold=True, color=theme["primary_light"], align="right")


def add_footer(slide, page_no: int, total: int):
    """绘制统一规范的页脚。"""
    add_shape(slide, 0.8, 6.95, 11.734, 0.012, fill=LINE, shape="rect")
    add_text(slide, 0.8, 7.02, 6.0, 0.3, "AI 客户端 · 离线智能体  |  ppt-master 原生生成", size=9, color=MUTED)
    add_text(slide, 9.5, 7.02, 3.03, 0.3, f"{page_no:02d} / {total:02d}", size=9, color=MUTED, align="right")


# ---------------------------------------------------------------- 各种专业多样化版式构建


def build_cover(prs, deck_title: str, subtitle: str, theme: dict, total: int):
    """封面页：高端几何光影科技感设计。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 背景几何层次装饰
    add_shape(slide, 9.8, -0.8, 4.8, 4.8, fill=theme["soft2"], shape="oval")
    add_shape(slide, 11.5, 2.2, 1.6, 1.6, fill=theme["accent"], shape="oval")
    add_shape(slide, 8.5, 4.5, 2.5, 2.5, fill=theme["soft"], shape="oval")

    # 底部主色条
    add_shape(slide, 0.0, 6.5, 13.334, 1.0, fill=theme["primary"], shape="rect")

    # 类别标签
    add_shape(slide, 0.95, 1.45, 1.8, 0.36, fill=theme["soft2"], radius=0.5)
    add_text(slide, 0.95, 1.5, 1.8, 0.3, "* 离线 AI 演示", size=11, bold=True, color=theme["primary_dark"], align="center")

    # 大标题
    title_size = 38 if len(deck_title) <= 16 else (32 if len(deck_title) <= 28 else 26)
    add_text(slide, 0.92, 2.05, 10.2, 2.0, deck_title, size=title_size, bold=True, color=INK, line_spacing=1.08)

    # 副标题
    if subtitle:
        add_text(slide, 0.95, 4.15, 9.5, 1.0, subtitle, size=15, color=MUTED, line_spacing=1.3)

    # 分割线
    add_shape(slide, 0.95, 5.35, 3.2, 0.025, fill=theme["accent"], shape="rect")

    # 元信息
    date_str = datetime.now().strftime("%Y-%m-%d")
    add_text(slide, 0.95, 5.55, 8.0, 0.4, f"{date_str}   ·   共 {total} 页演示文稿   ·   原生可编辑", size=11, color=MUTED)

    # 底部白字标语
    add_text(slide, 0.95, 6.82, 11.0, 0.4, "全本地离线智能体驱动   ·   支持一键转口播视频", size=11, color=WHITE)
    return slide


def build_catalog(prs, page_no: int, total: int, sections: list[SlideSection], theme: dict):
    """目录导航页：当章节较多时自动生成。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, "内容结构与核心目录", theme)

    items = sections[:6]  # 最多取前6章
    cols = 2 if len(items) > 3 else 1

    if cols == 1:
        top, left, width, gap = 1.6, 1.5, 10.33, 0.22
        card_h = min(0.95, (5.0 - gap * (len(items) - 1)) / len(items))
        for i, s in enumerate(items):
            y = top + i * (card_h + gap)
            add_shape(slide, left, y, width, card_h, fill=theme["soft"], radius=0.12)
            add_shape(slide, left, y, 0.12, card_h, fill=theme["primary"], radius=0.5)

            # 编号
            add_text(slide, left + 0.35, y + 0.15, 0.8, 0.5, f"{i+1:02d}", size=20, bold=True, color=theme["primary"])
            # 标题
            add_text(slide, left + 1.25, y + 0.18, width - 2.0, 0.5, s.title, size=16, bold=True, color=INK)
    else:
        lefts = [0.8, 6.8]
        width = 5.7
        half = (len(items) + 1) // 2
        for i, s in enumerate(items):
            c = 0 if i < half else 1
            idx_in_col = i if c == 0 else (i - half)
            y = 1.65 + idx_in_col * 1.35
            add_shape(slide, lefts[c], y, width, 1.15, fill=theme["soft"], radius=0.14)
            add_shape(slide, lefts[c] + 0.2, y + 0.2, 0.7, 0.7, fill=theme["primary_dark"], shape="oval")
            add_text(slide, lefts[c] + 0.2, y + 0.32, 0.7, 0.5, f"{i+1:02d}", size=14, bold=True, color=WHITE, align="center")
            add_text(slide, lefts[c] + 1.1, y + 0.32, width - 1.3, 0.6, s.title, size=16, bold=True, color=INK)

    add_footer(slide, page_no, total)
    return slide


def build_stat_cards(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """指标亮点版式：超大高亮数值 + 说明卡片（极具视觉冲击力）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    count = min(len(bullets), 4)
    gap = 0.25
    total_w = 11.734
    w = (total_w - gap * (count - 1)) / count
    top = 1.7
    h = 4.8

    for i in range(count):
        text = bullets[i]
        x = 0.8 + i * (w + gap)

        # 提取数字与文字
        num_match = re.search(r"(\d+(?:\.\d+)?%|\d+[xX倍]|\d{2,}\+?万?|\bTOP\s*\d+\b)", text)
        highlight_num = num_match.group(1) if num_match else f"0{i+1}"
        desc = text.replace(highlight_num, "").strip(" :：-——,，") or text

        # 大卡片底色
        add_shape(slide, x, top, w, h, fill=theme["soft2"], radius=0.15)
        # 顶端装饰条
        add_shape(slide, x, top, w, 0.15, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="rect")

        # 序号徽章
        add_shape(slide, x + 0.3, top + 0.4, 0.7, 0.32, fill=theme["primary_dark"], radius=0.5)
        add_text(slide, x + 0.3, top + 0.43, 0.7, 0.3, f"KEY {i+1}", size=9, bold=True, color=WHITE, align="center")

        # 超大数值亮点
        add_text(slide, x + 0.2, top + 1.1, w - 0.4, 1.2, highlight_num, size=36, bold=True, color=theme["primary"], align="center")

        # 分割微线
        add_shape(slide, x + (w - 1.2)/2, top + 2.5, 1.2, 0.02, fill=LINE, shape="rect")

        # 说明文字
        add_text(slide, x + 0.25, top + 2.8, w - 0.5, 1.8, desc, size=13.5, color=INK_LIGHT, align="center", line_spacing=1.3)

    add_footer(slide, page_no, total)
    return slide


def build_process_steps(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """横向步骤流转版式：带箭头/指示连线的步骤体系。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    count = min(len(bullets), 4)
    gap = 0.35
    total_w = 11.734
    w = (total_w - gap * (count - 1)) / count
    top = 2.0
    h = 4.4

    for i in range(count):
        text = bullets[i]
        x = 0.8 + i * (w + gap)

        # 卡片框
        add_shape(slide, x, top, w, h, fill=theme["soft"], radius=0.14)
        # 卡片顶部的步骤圆球
        add_shape(slide, x + (w - 0.9)/2, top - 0.45, 0.9, 0.9, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="oval")
        add_text(slide, x + (w - 0.9)/2, top - 0.33, 0.9, 0.5, f"{i+1}", size=16, bold=True, color=WHITE, align="center")

        # 步骤标题与正文
        parts = re.split(r"[:：——\s-]", text, maxsplit=1)
        step_title = parts[0] if len(parts) > 1 else f"步骤 {i+1}"
        step_detail = parts[1] if len(parts) > 1 else text

        add_text(slide, x + 0.2, top + 0.7, w - 0.4, 0.6, step_title, size=16, bold=True, color=INK, align="center")
        add_shape(slide, x + (w - 0.8)/2, top + 1.4, 0.8, 0.02, fill=LINE, shape="rect")
        add_text(slide, x + 0.25, top + 1.6, w - 0.5, 2.5, step_detail, size=13, color=MUTED, line_spacing=1.35)

        # 步骤之间的流转指示箭头
        if i < count - 1:
            arrow_x = x + w + 0.08
            add_text(slide, arrow_x, top + 1.8, gap - 0.16, 0.6, "->", size=20, bold=True, color=theme["primary_light"], align="center")

    add_footer(slide, page_no, total)
    return slide


def build_column_cards(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """2~3 栏多列精美特色卡片版式。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    count = len(bullets)
    gap = 0.3
    total_w = 11.734
    w = (total_w - gap * (count - 1)) / count
    top = 1.65
    h = 4.9

    for i in range(count):
        text = bullets[i]
        x = 0.8 + i * (w + gap)

        add_shape(slide, x, top, w, h, fill=theme["soft"], radius=0.14)
        add_shape(slide, x, top, w, 0.1, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="rect")

        # 徽章胶囊
        add_shape(slide, x + 0.3, top + 0.35, 1.1, 0.36, fill=theme["soft2"], radius=0.5)
        add_text(slide, x + 0.3, top + 0.4, 1.1, 0.3, f"FEATURE {i+1}", size=9, bold=True, color=theme["primary"], align="center")

        # 文本
        parts = re.split(r"[:：\n]", text, maxsplit=1)
        sub_title = parts[0] if len(parts) > 1 else f"核心观点 {i+1}"
        sub_body = parts[1] if len(parts) > 1 else text

        add_text(slide, x + 0.3, top + 0.9, w - 0.6, 0.8, sub_title, size=18, bold=True, color=INK)
        add_shape(slide, x + 0.3, top + 1.8, 1.0, 0.02, fill=theme["accent"], shape="rect")
        add_text(slide, x + 0.3, top + 2.0, w - 0.6, 2.6, sub_body, size=13.5, color=INK_LIGHT, line_spacing=1.35)

    add_footer(slide, page_no, total)
    return slide


def build_image_text(prs, page_no: int, total: int, title: str, bullets: list[str], images: list[str], theme: dict):
    """图文混排版式：左文右图（或左图右文）。"""
    from pptx.util import Inches

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    # 左侧文字区域
    text_w = 6.2
    top = 1.6
    n = max(len(bullets), 1)
    gap = 0.18
    avail = 4.9
    card_h = min(1.2, (avail - gap * (n - 1)) / n)

    for i, text in enumerate(bullets):
        y = top + i * (card_h + gap)
        add_shape(slide, 0.8, y, text_w, card_h, fill=theme["soft"], radius=0.12)
        add_shape(slide, 0.8, y + 0.1, 0.08, card_h - 0.2, fill=theme["primary"] if i % 2 == 0 else theme["accent"], radius=0.5)
        add_text(slide, 1.05, y + 0.08, text_w - 0.35, card_h - 0.16, text, size=13, color=INK, anchor="middle", line_spacing=1.25)

    # 右侧图片放置
    img_x, img_y, img_w, img_h = 7.3, 1.6, 5.2, 4.9
    img_path = images[0] if images else ""

    if img_path and Path(img_path).exists():
        try:
            # 图片阴影底板
            add_shape(slide, img_x - 0.08, img_y - 0.08, img_w + 0.16, img_h + 0.16, fill=theme["soft2"], radius=0.12)
            slide.shapes.add_picture(img_path, Inches(img_x), Inches(img_y), width=Inches(img_w))
        except Exception as e:
            print(f"  ! 嵌入图片失败 {img_path}: {e}", file=sys.stderr)
            add_shape(slide, img_x, img_y, img_w, img_h, fill=theme["soft2"], radius=0.12)
            add_text(slide, img_x + 0.5, img_y + 2.0, img_w - 1.0, 1.0, "【图示与架构呈现】", size=16, bold=True, color=MUTED, align="center")
    else:
        # 无外部图片时生成精美矢量图解示意框
        add_shape(slide, img_x, img_y, img_w, img_h, fill=theme["soft2"], radius=0.12)
        add_shape(slide, img_x + 1.6, img_y + 1.2, 2.0, 2.0, fill=theme["primary_light"], shape="oval")
        add_text(slide, img_x + 1.6, img_y + 1.9, 2.0, 0.6, "VISUAL", size=18, bold=True, color=WHITE, align="center")
        add_text(slide, img_x + 0.5, img_y + 3.5, img_w - 1.0, 0.8, "系统架构与功能图解", size=14, bold=True, color=INK, align="center")

    add_footer(slide, page_no, total)
    return slide


def build_standard_cards(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """精美水平卡片列表（要点清晰，带彩色序号圆标与层次卡片）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    top, left, width = 1.62, 0.8, 11.734
    n = max(len(bullets), 1)
    gap = 0.16
    avail = 5.0
    card_h = min(1.15, (avail - gap * (n - 1)) / n)

    for i, text in enumerate(bullets):
        y = top + i * (card_h + gap)
        # 背景卡片
        add_shape(slide, left, y, width, card_h, fill=theme["soft"], radius=0.14)
        # 侧边彩条
        add_shape(slide, left + 0.04, y + 0.1, 0.08, card_h - 0.2, fill=theme["primary"] if i % 2 == 0 else theme["accent"], radius=0.5)

        # 序号徽章圆点
        badge_d = 0.38
        bx, by = left + 0.35, y + (card_h - badge_d) / 2
        add_shape(slide, bx, by, badge_d, badge_d, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="oval")
        add_text(slide, bx, by + 0.06, badge_d, 0.28, str(i + 1), size=12, bold=True, color=WHITE, align="center")

        # 文本
        size = 14.5 if len(text) <= 50 else (13 if len(text) <= 85 else 12)
        add_text(
            slide,
            left + 0.95,
            y + 0.08,
            width - 1.25,
            card_h - 0.16,
            text,
            size=size,
            color=INK,
            line_spacing=1.3,
            anchor="middle",
        )

    add_footer(slide, page_no, total)
    return slide


def build_end(prs, theme: dict, total: int):
    """封底页：大气总结致谢。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # 底部主色条
    add_shape(slide, 0.0, 6.5, 13.334, 1.0, fill=theme["primary"], shape="rect")

    # 装饰线与高光
    add_shape(slide, 5.85, 2.3, 1.6, 0.08, fill=theme["accent"], radius=0.5)
    add_text(slide, 1.5, 2.7, 10.334, 1.2, "谢谢观看", size=42, bold=True, color=INK, align="center")
    add_text(
        slide,
        1.5,
        4.0,
        10.334,
        0.8,
        "本演示文稿由 AI 客户端 · ppt-master 离线智能生成，内容全部可自由编辑",
        size=15,
        color=MUTED,
        align="center",
    )
    add_text(slide, 0.8, 6.85, 11.734, 0.4, f"共 {total} 页演示完成   ·   全离线无网络依赖", size=11, color=WHITE, align="center")
    return slide


# ---------------------------------------------------------------- 核心生成入口


def quick_markdown_pptx(text: str, out_path: Path) -> Path:
    from pptx import Presentation
    from pptx.util import Inches

    theme_name = os.environ.get("AI_CLIENT_PPT_THEME", "indigo").lower()
    theme = THEMES.get(theme_name, THEMES["indigo"])

    deck_title, subtitle, sections = parse_markdown_rich(text, base_dir=out_path.parent)

    prs = Presentation()
    prs.slide_width = Inches(13.334)  # 16:9 现代宽屏
    prs.slide_height = Inches(7.5)

    # 计算总页数：封面 + (目录页 if >=3) + 各章节正文 + 封底
    has_catalog = len(sections) >= 3
    total_pages = len(sections) + (3 if has_catalog else 2)

    # 1. 封面
    cover_slide = build_cover(prs, deck_title, subtitle, theme, total_pages)
    cover_slide.notes_slide.notes_text_frame.text = f"大家好，今天我为大家汇报的主题是《{deck_title}》。{subtitle}"

    cur_page = 1
    # 2. 目录页（章节多时呈现）
    if has_catalog:
        cur_page += 1
        cat_slide = build_catalog(prs, cur_page, total_pages, sections, theme)
        cat_slide.notes_slide.notes_text_frame.text = "首先让我们概览一下今天汇报的整体内容框架与核心篇章。"

    # 3. 逐页正文（智能语义版式选择）
    for sec in sections:
        cur_page += 1
        layout = sec.layout_type

        if layout == "image_text":
            slide = build_image_text(prs, cur_page, total_pages, sec.title, sec.bullets, sec.images, theme)
        elif layout == "stat_cards":
            slide = build_stat_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "process_steps":
            slide = build_process_steps(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "column_cards":
            slide = build_column_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        else:
            slide = build_standard_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)

        # 编写演讲者旁白备注（供口播视频朗读）
        narrative = f"接下来看这一页，{sec.title}。" + "。".join(sec.bullets) + "。"
        slide.notes_slide.notes_text_frame.text = narrative[:1500]

    # 4. 封底
    end_slide = build_end(prs, theme, total_pages)
    end_slide.notes_slide.notes_text_frame.text = "以上就是本次演示的全部汇报内容，感谢大家的聆听与观看！"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    print(f"[ppt-master] 成功生成高清 PPTX: {out_path}（共 {total_pages} 页，主题: {theme_name}，图文多版式排版就绪）")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="ppt-master 演示文稿生成引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--input", required=True, help="材料文件路径或大纲文本")
    g.add_argument("--out", required=True, help="输出目录")
    args = ap.parse_args()

    if args.cmd != "generate":
        print("[错误] 未知命令", file=sys.stderr)
        return 2

    src = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if src.suffix.lower() in {".md", ".txt", ".markdown"}:
        text = src.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        base_name = title_match.group(1).strip() if title_match else src.stem
        # 清理文件名非法字符
        safe_name = re.sub(r'[\\/:*?"<>|\r\n\t]', "", base_name).strip()[:40] or "presentation"
        out_path = out_dir / f"{safe_name}_{stamp}.pptx"

        quick_markdown_pptx(text, out_path)
        return 0

    print("[ppt-master] 当前输入格式需转换为 Markdown 后生成", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
