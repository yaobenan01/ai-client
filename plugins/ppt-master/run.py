#!/usr/bin/env python3
"""ppt-master 演示文稿引擎：专业排版、精炼聚焦、图文并茂，配备生动口播解说文案。

核心特性与设计规范：
  1. 严格精炼与分页原则：
     - 单页严格控制在 3~4 个核心要点以内，杜绝信息过载与文字堆砌；
     - 自动过滤 `--`、`---`、`> ` 等 Markdown 杂质；
     - 当单节内容超过 4 条时，自动进行主题分叶与智能分页。
  2. 顶级视觉排版架构（精简、突出重点、好看）：
     - 4 要点：现代四宫格聚焦矩阵（2x2 网格卡片，层次分明，信息张力强）；
     - 3 要点：三列立体特色卡片（并列架构，带分类徽标与重点大字）；
     - 2 要点：双栏对比与核心双翼布局；
     - 数据亮点：36pt 超大渐变对比度数值卡片（如 300%、99.8%、5000+）；
     - 流程流转：横向阶段步骤图（带步骤圆标与指示箭头）；
     - 要点分层：每个要点均自动拆解为「核心重点词（粗体大字）」与「精炼阐释说明」。
  3. 生动口播解说词引擎（拒绝照读 PPT）：
     - 自动根据页面内容、所处结构、核心亮点与业务价值生成生动、自然、口语化的现场讲解旁白；
     - 包含承上启下开场、深入浅出的痛点与价值剖析、自然过渡与升华收尾；
     - 写入幻灯片演讲者备注，直接驱动后续 Piper 离线语音合成口播视频。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------- 专业多套系主题

THEMES = {
    "indigo": {
        "primary": (0x4F, 0x46, 0xE5),        # 科技靛蓝
        "primary_dark": (0x31, 0x2E, 0x9B),
        "primary_light": (0x81, 0x8C, 0xF8),
        "accent": (0x06, 0xB6, 0xD4),         # 青空蓝
        "soft": (0xF8, 0xFA, 0xFC),           # 极浅灰底
        "soft2": (0xEE, 0xF2, 0xFF),          # 高光卡片底
        "card_bg": (0xFF, 0xFF, 0xFF),        # 纯白卡片
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

INK = (0x0F, 0x17, 0x2A)           # 标题高对比深黑
INK_LIGHT = (0x33, 0x41, 0x55)     # 正文深灰
MUTED = (0x64, 0x74, 0x8B)         # 辅助次级灰
WHITE = (0xFF, 0xFF, 0xFF)
LINE = (0xE2, 0xE8, 0xF0)          # 边框与微细线


def _font_name() -> str:
    return os.environ.get("AI_CLIENT_PPT_FONT", "微软雅黑")


def _rgb(v):
    from pptx.dml.color import RGBColor
    return RGBColor(*v)


# ---------------------------------------------------------------- 文本解析与要点提炼


_MD_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_TOKENS = re.compile(r"(\*\*|__|\*|`|~~)")


def clean_markdown_artifacts(text: str) -> str:
    """彻底清除 Markdown 标记，保留纯净文本。"""
    t = _MD_LINK.sub(r"\1", text)
    t = _MD_TOKENS.sub("", t)
    # 清理行首引用符号
    t = re.sub(r"^>\s*", "", t)
    # 清理多余序号和项目符
    t = re.sub(r"^[\s\-*•\d.、)①-⑳]+\s*", "", t)
    return t.strip()


def extract_point_parts(bullet: str) -> tuple[str, str]:
    """将一条要点智能拆解为 (标题/关键词, 阐述说明)。

    例如：
      'All-in-One 工作台: 对话、写作、翻译一站式完成' -> ('All-in-One 工作台', '对话、写作、翻译一站式完成')
      '隐私优先 - 敏感数据本地处理' -> ('隐私优先', '敏感数据本地处理')
    """
    clean = clean_markdown_artifacts(bullet)
    # 仅按中英文冒号、全角破折号或带空格的破折号拆分，绝不能破坏 All-in-One 这种英文单词连字符
    m = re.split(r"(?:[:：]|(?:\s+[-——]\s+)|(?:——))\s*", clean, maxsplit=1)
    if len(m) == 2 and 2 <= len(m[0]) <= 25 and len(m[1]) >= 2:
        return m[0].strip(), m[1].strip()

    # 无明确分隔符时，如果前面几个字包含专有名词或较短，取前10个字作为重点，后面作为展开
    if len(clean) > 22:
        # 寻找第一个标点或空格
        match_punc = re.search(r"[,，\s]", clean[4:18])
        if match_punc:
            split_idx = 4 + match_punc.start()
            return clean[:split_idx].strip(), clean[split_idx+1:].strip()

    return clean[:16], clean


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

        # 1. 指标亮点数据页 (如 99.8%、300%、5000+、TOP 1)
        metric_matches = re.findall(r"(\d+(?:\.\d+)?%|\d+[xX倍]|\d{2,}\+?万?|\bTOP\s*\d+\b)", text_corpus)
        if len(metric_matches) >= 2 and len(self.bullets) <= 4:
            return "stat_cards"

        # 2. 流程流转步骤页 (步骤、阶段、Step、流程)
        step_matches = [b for b in self.bullets if re.search(r"^(?:步骤|阶段|Step|Phase|\d+[.、)])", b, re.IGNORECASE)]
        if len(step_matches) >= 2 and len(self.bullets) <= 4:
            return "process_steps"

        # 3. 恰好 4 项：使用极具专业感的 2x2 四宫格卡片矩阵
        if len(self.bullets) == 4:
            return "quad_grid"

        # 4. 2 或 3 项：三列/双栏立体特色卡片
        if len(self.bullets) in (2, 3):
            return "column_cards"

        return "standard_cards"


def parse_and_paginate_markdown(text: str, base_dir: Path | None = None) -> tuple[str, str, list[SlideSection]]:
    """解析 Markdown 并执行严格的分页限制：单页要点不超过 4 条。"""
    deck_title = "演示文稿"
    subtitle = ""
    raw_sections: list[tuple[str, list[str], list[str]]] = []

    cur_title = "核心概览"
    cur_bullets: list[str] = []
    cur_images: list[str] = []
    started = False
    seen_h2 = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # 过滤 Markdown 纯分隔线 (如 --, ---, ***, ___)
        if re.match(r"^[-*_]{2,}$", stripped):
            continue

        # 提取图片
        img_match = _MD_IMG.search(stripped)
        if img_match:
            img_path = img_match.group(2)
            if base_dir and not Path(img_path).is_absolute():
                candidate = base_dir / img_path
                if candidate.exists():
                    img_path = str(candidate)
            cur_images.append(img_path)
            stripped = _MD_IMG.sub("", stripped).strip()
            if not stripped:
                continue

        # 一级标题：主标题
        if line.startswith("# ") and not line.startswith("## "):
            if not started:
                deck_title = clean_markdown_artifacts(line[2:])
                started = True
                continue
            cur_bullets.append(clean_markdown_artifacts(line[2:]))
            continue

        # 二级标题：幻灯片页面
        if line.startswith("## "):
            if seen_h2 or cur_bullets or cur_images:
                raw_sections.append((cur_title, cur_bullets, cur_images))
                cur_bullets = []
                cur_images = []
            cur_title = clean_markdown_artifacts(line[3:]) or "核心内容"
            seen_h2 = True
            continue

        # 三级标题：视为小章节或卡片重点
        if line.startswith("### "):
            sub_title = clean_markdown_artifacts(line[4:])
            if sub_title:
                cur_bullets.append(f"{sub_title}: 重点推进与落地实施")
            continue

        # 副标题判断
        if not seen_h2 and not subtitle and not stripped.startswith(("-", "*", "•", "1.", "2.")):
            subtitle = clean_markdown_artifacts(stripped)
            continue

        # 列表要点
        clean = clean_markdown_artifacts(stripped)
        # 排除无意义的空行或纯短符号
        if clean and len(clean) >= 2 and not re.match(r"^[-*_]+$", clean):
            cur_bullets.append(clean)

    if cur_bullets or cur_images or seen_h2:
        raw_sections.append((cur_title, cur_bullets, cur_images))

    if not raw_sections:
        raw_sections = [("核心概览", ["全功能离线智能体: 本地运算与极致安全", "开箱即用体验: 无需繁琐配置环境"], [])]

    # 执行智能分页：任何单节如果超过 4 条要点，自动拆分为多页！
    MAX_PER_PAGE = 4
    final_sections: list[SlideSection] = []

    for title, bullets, images in raw_sections:
        if not bullets:
            final_sections.append(SlideSection(title, ["（本篇章包含架构要点分析）"], images))
            continue

        if len(bullets) <= MAX_PER_PAGE:
            final_sections.append(SlideSection(title, bullets, images))
        else:
            # 智能拆分
            chunks = [bullets[i:i + MAX_PER_PAGE] for i in range(0, len(bullets), MAX_PER_PAGE)]
            sub_labels = ["核心定位", "功能全景", "应用落地", "延展探索"]
            for idx, chunk in enumerate(chunks):
                label = sub_labels[idx] if idx < len(sub_labels) else f"第 {idx+1} 部分"
                page_title = f"{title} · {label}"
                # 图片只放在第一分节
                page_imgs = images if idx == 0 else []
                final_sections.append(SlideSection(page_title, chunk, page_imgs))

    return deck_title, subtitle, final_sections


# ---------------------------------------------------------------- 生动口播解说词生成引擎


def generate_lively_speaker_script(
    title: str,
    bullets: list[str],
    layout_type: str,
    page_no: int,
    total_pages: int,
    deck_title: str
) -> str:
    """生成自然生动、富有感染力、现场感十足的演讲者口播稿（拒绝机械照读）。"""
    parts = []

    # 1. 现场感承上启下引入
    if page_no == 1:
        return f"大家好！今天我非常荣幸能向大家分享《{deck_title}》。在接下来的汇报中，我们将全方位解析这一方案的核心架构、关键突破与实践价值。让我们正式开始。"
    elif "目录" in title:
        return "在深入展开之前，我们先整体浏览一下今天汇报的核心篇章结构。整个内容由浅入深，涵盖了关键定位、核心功能以及落地成果，让我们逐一深入探讨。"
    elif page_no == 2:
        parts.append(f"首先，让我们把目光投向《{title}》这一核心篇章。")
    elif page_no == total_pages:
        return "以上就是本次汇报的全部核心内容。我们始终坚信，只有真正贴近用户需求、兼顾安全与效率的方案，才能创造持久的价值。非常感谢大家的聆听与支持，欢迎随时交流探讨！"
    elif layout_type == "stat_cards":
        parts.append(f"大家请看屏幕上这组亮眼的数据，它非常直观地展现了在《{title}》方面所取得的突破性成效。")
    elif layout_type == "process_steps":
        parts.append(f"在具体实施落地的路径上，《{title}》被拆解为了清晰有序、环环相扣的几个推进阶段。")
    else:
        intros = [
            f"接下来，请大家重点关注《{title}》，这也是整个体系中最具分量的一部分。",
            f"进一步深入来看，《{title}》为我们解决实际痛点提供了坚实的支点。",
            f"紧接着，我们来看《{title}》，它在整个业务流转中起到了至关重要的承载作用。",
        ]
        parts.append(intros[page_no % len(intros)])

    # 2. 逐点生动口语化阐释
    point_openers = [
        "第一点，也是最关键的基石，在于【{}】。",
        "紧接着第二点，我们重点发力于【{}】。",
        "第三点，在【{}】方面，我们做了深度的打磨与升级。",
        "第四点，【{}】则构成了整个体验闭环不可或缺的保障。",
    ]

    for i, b in enumerate(bullets):
        p_title, p_desc = extract_point_parts(b)
        opener = point_openers[i] if i < len(point_openers) else "另外，在【{}】上，"
        opener_text = opener.format(p_title)

        # 组织生动阐释：结合用户痛点与价值
        explanation = p_desc
        if not explanation.endswith(("。", "！", "？")):
            explanation += "。"

        # 加入口语化延伸修辞
        if i == 0:
            exp_spoken = f"{opener_text}正如大家所见，{explanation}这不仅极大地优化了传统繁琐的链路，更为用户带来了真正流畅的一站式操作体验。"
        elif i == 1:
            exp_spoken = f"{opener_text}针对实际场景中最严苛的要求，{explanation}切实做到了把数据安全与主动权牢牢把握在用户自己手中。"
        elif i == 2:
            exp_spoken = f"{opener_text}在这里，{explanation}使得整体系统无论在离线环境还是重度任务下，都能保持高水准的稳定性。"
        else:
            exp_spoken = f"{opener_text}{explanation}从而让全套能力真正做到即开即用、零门槛覆盖。"

        parts.append(exp_spoken)

    # 3. 页面升华小结
    closers = [
        "正是这几项特性的协同并进，使我们在这一维度建立起了非常扎实的技术与体验壁垒。",
        "可以说，这项设计的落地，彻底免去了用户的后顾之忧，实现了效率的成倍跃升。",
        "这也正是我们产品理念的核心体现——用最纯粹的极简设计，承载最强大的生产力赋能。",
    ]
    parts.append(closers[page_no % len(closers)])

    full_script = "".join(parts)
    return full_script[:1200]


# ---------------------------------------------------------------- 原生形状与文本排版原语


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
    tf.margin_left = Inches(0.06)
    tf.margin_right = Inches(0.06)
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
    """统一高端页眉：带色条、页码徽章、大标题与分类标志。"""
    # 顶部装饰色条
    add_shape(slide, 0.0, 0.0, 13.334, 0.08, fill=theme["primary"], shape="rect")

    # 页码小徽标
    add_shape(slide, 0.8, 0.45, 0.65, 0.36, fill=theme["primary"], radius=0.35)
    add_text(slide, 0.8, 0.5, 0.65, 0.3, f"{page_no:02d}", size=12, bold=True, color=WHITE, align="center")

    # 页面标题
    add_text(slide, 1.6, 0.36, 9.5, 0.75, title, size=24, bold=True, color=INK)

    # 标题下的高光色块装饰
    add_shape(slide, 1.62, 1.15, 1.1, 0.05, fill=theme["accent"], radius=0.5)

    # 页眉右侧主题提示
    add_text(slide, 10.0, 0.48, 2.5, 0.3, "OFFLINE AGENT", size=9, bold=True, color=theme["primary_light"], align="right")


def add_footer(slide, page_no: int, total: int):
    """统一规范页脚。"""
    add_shape(slide, 0.8, 6.95, 11.734, 0.012, fill=LINE, shape="rect")
    add_text(slide, 0.8, 7.02, 6.0, 0.3, "AI 客户端 · 离线智能体  |  ppt-master 原生生成", size=9, color=MUTED)
    add_text(slide, 9.5, 7.02, 3.03, 0.3, f"{page_no:02d} / {total:02d}", size=9, color=MUTED, align="right")


# ---------------------------------------------------------------- 全新高端版式渲染体系


def build_cover(prs, deck_title: str, subtitle: str, theme: dict, total: int):
    """封面页：高端几何层次设计。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_shape(slide, 9.8, -0.8, 4.8, 4.8, fill=theme["soft2"], shape="oval")
    add_shape(slide, 11.5, 2.2, 1.6, 1.6, fill=theme["accent"], shape="oval")
    add_shape(slide, 8.5, 4.5, 2.5, 2.5, fill=theme["soft"], shape="oval")

    add_shape(slide, 0.0, 6.5, 13.334, 1.0, fill=theme["primary"], shape="rect")

    # 类别标签
    add_shape(slide, 0.95, 1.45, 1.8, 0.36, fill=theme["soft2"], radius=0.5)
    add_text(slide, 0.95, 1.5, 1.8, 0.3, "* 离线 AI 演示", size=11, bold=True, color=theme["primary_dark"], align="center")

    title_size = 38 if len(deck_title) <= 16 else (32 if len(deck_title) <= 28 else 26)
    add_text(slide, 0.92, 2.05, 10.2, 2.0, deck_title, size=title_size, bold=True, color=INK, line_spacing=1.08)

    if subtitle:
        add_text(slide, 0.95, 4.15, 9.5, 1.0, subtitle, size=15, color=MUTED, line_spacing=1.3)

    add_shape(slide, 0.95, 5.35, 3.2, 0.025, fill=theme["accent"], shape="rect")
    date_str = datetime.now().strftime("%Y-%m-%d")
    add_text(slide, 0.95, 5.55, 8.0, 0.4, f"{date_str}   ·   共 {total} 页演示文稿   ·   原生可编辑", size=11, color=MUTED)
    add_text(slide, 0.95, 6.82, 11.0, 0.4, "全本地离线智能体驱动   ·   支持一键转口播视频", size=11, color=WHITE)
    return slide


def build_catalog(prs, page_no: int, total: int, sections: list[SlideSection], theme: dict):
    """目录导航页：章节概览卡片。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, "内容结构与核心目录", theme)

    items = sections[:6]
    lefts = [0.8, 6.8] if len(items) > 3 else [1.5]
    width = 5.7 if len(items) > 3 else 10.33
    half = (len(items) + 1) // 2 if len(items) > 3 else len(items)

    for i, s in enumerate(items):
        col = 0 if i < half else 1
        x = lefts[col]
        idx_in_col = i if col == 0 else (i - half)
        y = 1.65 + idx_in_col * 1.35

        add_shape(slide, x, y, width, 1.15, fill=theme["soft"], radius=0.14)
        add_shape(slide, x + 0.2, y + 0.2, 0.7, 0.7, fill=theme["primary_dark"], shape="oval")
        add_text(slide, x + 0.2, y + 0.32, 0.7, 0.5, f"{i+1:02d}", size=14, bold=True, color=WHITE, align="center")
        add_text(slide, x + 1.1, y + 0.32, width - 1.3, 0.6, s.title, size=16, bold=True, color=INK)

    add_footer(slide, page_no, total)
    return slide


def build_quad_grid(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """四宫格聚焦矩阵 (2x2 卡片)：专为 4 条要点打造的绝佳现代化版式！"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    # 2x2 布局参数
    w = 5.65
    h = 2.22
    gap_x = 0.43
    gap_y = 0.32
    lefts = [0.8, 0.8 + w + gap_x]
    tops = [1.62, 1.62 + h + gap_y]

    for i in range(min(len(bullets), 4)):
        col = i % 2
        row = i // 2
        x = lefts[col]
        y = tops[row]

        p_title, p_desc = extract_point_parts(bullets[i])

        # 卡片纯净底板
        add_shape(slide, x, y, w, h, fill=theme["card_bg"], line=LINE, line_w=1.0, radius=0.12)
        # 顶端彩色高光条
        add_shape(slide, x, y, w, 0.08, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="rect")

        # 胶囊序号徽章
        badge_w, badge_h = 0.95, 0.32
        add_shape(slide, x + 0.3, y + 0.25, badge_w, badge_h, fill=theme["soft2"], radius=0.5)
        add_text(slide, x + 0.3, y + 0.29, badge_w, 0.28, f"POINT 0{i+1}", size=9.5, bold=True, color=theme["primary"], align="center")

        # 核心亮点标题 (大字突出重点)
        add_text(slide, x + 0.3, y + 0.68, w - 0.6, 0.45, p_title, size=17, bold=True, color=INK)

        # 阐述正文 (多行优雅排版)
        add_text(slide, x + 0.3, y + 1.18, w - 0.6, 0.92, p_desc, size=13, color=INK_LIGHT, line_spacing=1.3)

    add_footer(slide, page_no, total)
    return slide


def build_column_cards(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """2~3 栏多列特色卡片版式。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    count = len(bullets)
    gap = 0.35
    total_w = 11.734
    w = (total_w - gap * (count - 1)) / count
    top = 1.65
    h = 4.9

    for i in range(count):
        p_title, p_desc = extract_point_parts(bullets[i])
        x = 0.8 + i * (w + gap)

        # 卡片底板
        add_shape(slide, x, top, w, h, fill=theme["card_bg"], line=LINE, line_w=1.0, radius=0.14)
        add_shape(slide, x, top, w, 0.1, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="rect")

        # 顶部圆球序号
        add_shape(slide, x + 0.3, top + 0.35, 0.65, 0.65, fill=theme["soft2"], shape="oval")
        add_text(slide, x + 0.3, top + 0.46, 0.65, 0.45, f"{i+1}", size=14, bold=True, color=theme["primary"], align="center")

        # 核心标题
        add_text(slide, x + 0.3, top + 1.2, w - 0.6, 0.7, p_title, size=18, bold=True, color=INK)
        # 分割线
        add_shape(slide, x + 0.3, top + 1.95, 1.2, 0.02, fill=theme["accent"], shape="rect")
        # 阐述说明
        add_text(slide, x + 0.3, top + 2.15, w - 0.6, 2.45, p_desc, size=13.5, color=INK_LIGHT, line_spacing=1.35)

    add_footer(slide, page_no, total)
    return slide


def build_stat_cards(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """指标亮点版式：超大数值 + 说明卡片。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    count = min(len(bullets), 4)
    gap = 0.28
    total_w = 11.734
    w = (total_w - gap * (count - 1)) / count
    top = 1.68
    h = 4.85

    for i in range(count):
        text = bullets[i]
        x = 0.8 + i * (w + gap)

        num_match = re.search(r"(\d+(?:\.\d+)?%|\d+[xX倍]|\d{2,}\+?万?|\bTOP\s*\d+\b)", text)
        highlight_num = num_match.group(1) if num_match else f"0{i+1}"
        desc = text.replace(highlight_num, "").strip(" :：-——,，") or text

        add_shape(slide, x, top, w, h, fill=theme["card_bg"], line=LINE, line_w=1.0, radius=0.15)
        add_shape(slide, x, top, w, 0.12, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="rect")

        add_shape(slide, x + 0.3, top + 0.38, 0.75, 0.32, fill=theme["soft2"], radius=0.5)
        add_text(slide, x + 0.3, top + 0.42, 0.75, 0.3, f"KEY 0{i+1}", size=9, bold=True, color=theme["primary"], align="center")

        add_text(slide, x + 0.2, top + 1.1, w - 0.4, 1.2, highlight_num, size=36, bold=True, color=theme["primary"], align="center")
        add_shape(slide, x + (w - 1.2)/2, top + 2.45, 1.2, 0.02, fill=LINE, shape="rect")
        add_text(slide, x + 0.25, top + 2.7, w - 0.5, 1.9, desc, size=13.5, color=INK_LIGHT, align="center", line_spacing=1.3)

    add_footer(slide, page_no, total)
    return slide


def build_process_steps(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """横向步骤流转版式。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    count = min(len(bullets), 4)
    gap = 0.35
    total_w = 11.734
    w = (total_w - gap * (count - 1)) / count
    top = 2.0
    h = 4.4

    for i in range(count):
        p_title, p_desc = extract_point_parts(bullets[i])
        x = 0.8 + i * (w + gap)

        add_shape(slide, x, top, w, h, fill=theme["card_bg"], line=LINE, line_w=1.0, radius=0.14)
        add_shape(slide, x + (w - 0.9)/2, top - 0.45, 0.9, 0.9, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="oval")
        add_text(slide, x + (w - 0.9)/2, top - 0.33, 0.9, 0.5, f"{i+1}", size=16, bold=True, color=WHITE, align="center")

        add_text(slide, x + 0.2, top + 0.7, w - 0.4, 0.6, p_title, size=16, bold=True, color=INK, align="center")
        add_shape(slide, x + (w - 0.8)/2, top + 1.35, 0.8, 0.02, fill=LINE, shape="rect")
        add_text(slide, x + 0.25, top + 1.55, w - 0.5, 2.5, p_desc, size=13, color=INK_LIGHT, line_spacing=1.35)

        if i < count - 1:
            arrow_x = x + w + 0.08
            add_text(slide, arrow_x, top + 1.8, gap - 0.16, 0.6, "->", size=20, bold=True, color=theme["primary_light"], align="center")

    add_footer(slide, page_no, total)
    return slide


def build_image_text(prs, page_no: int, total: int, title: str, bullets: list[str], images: list[str], theme: dict):
    """图文混排版式。"""
    from pptx.util import Inches

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    text_w = 6.2
    top = 1.6
    n = max(len(bullets), 1)
    gap = 0.2
    card_h = min(1.35, (4.9 - gap * (n - 1)) / n)

    for i, bullet in enumerate(bullets):
        p_title, p_desc = extract_point_parts(bullet)
        y = top + i * (card_h + gap)
        add_shape(slide, 0.8, y, text_w, card_h, fill=theme["card_bg"], line=LINE, line_w=1.0, radius=0.12)
        add_shape(slide, 0.8, y + 0.12, 0.08, card_h - 0.24, fill=theme["primary"] if i % 2 == 0 else theme["accent"], radius=0.5)

        add_text(slide, 1.05, y + 0.12, text_w - 0.35, 0.38, p_title, size=15, bold=True, color=INK)
        add_text(slide, 1.05, y + 0.52, text_w - 0.35, card_h - 0.6, p_desc, size=12.5, color=INK_LIGHT, line_spacing=1.25)

    img_x, img_y, img_w, img_h = 7.3, 1.6, 5.2, 4.9
    img_path = images[0] if images else ""

    if img_path and Path(img_path).exists():
        try:
            add_shape(slide, img_x - 0.08, img_y - 0.08, img_w + 0.16, img_h + 0.16, fill=theme["soft2"], radius=0.12)
            slide.shapes.add_picture(img_path, Inches(img_x), Inches(img_y), width=Inches(img_w))
        except Exception as e:
            add_shape(slide, img_x, img_y, img_w, img_h, fill=theme["soft2"], radius=0.12)
            add_text(slide, img_x + 0.5, img_y + 2.0, img_w - 1.0, 1.0, "【图解呈现】", size=16, bold=True, color=MUTED, align="center")
    else:
        add_shape(slide, img_x, img_y, img_w, img_h, fill=theme["soft2"], radius=0.12)
        add_shape(slide, img_x + 1.6, img_y + 1.2, 2.0, 2.0, fill=theme["primary_light"], shape="oval")
        add_text(slide, img_x + 1.6, img_y + 1.9, 2.0, 0.6, "VISUAL", size=18, bold=True, color=WHITE, align="center")
        add_text(slide, img_x + 0.5, img_y + 3.5, img_w - 1.0, 0.8, "系统架构与功能图解", size=14, bold=True, color=INK, align="center")

    add_footer(slide, page_no, total)
    return slide


def build_standard_cards(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """水平卡片排版（控制在 3 条以内，大卡片，大字重点）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    top, left, width = 1.65, 0.8, 11.734
    n = max(len(bullets), 1)
    gap = 0.22
    card_h = min(1.4, (5.0 - gap * (n - 1)) / n)

    for i, bullet in enumerate(bullets):
        p_title, p_desc = extract_point_parts(bullet)
        y = top + i * (card_h + gap)

        # 卡片底板
        add_shape(slide, left, y, width, card_h, fill=theme["card_bg"], line=LINE, line_w=1.0, radius=0.14)
        # 侧边彩条
        add_shape(slide, left + 0.04, y + 0.12, 0.08, card_h - 0.24, fill=theme["primary"] if i % 2 == 0 else theme["accent"], radius=0.5)

        # 序号徽章圆点
        badge_d = 0.42
        bx, by = left + 0.35, y + 0.2
        add_shape(slide, bx, by, badge_d, badge_d, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="oval")
        add_text(slide, bx, by + 0.07, badge_d, 0.3, str(i + 1), size=13, bold=True, color=WHITE, align="center")

        # 核心重点标题 (粗体大字，一目了然)
        add_text(slide, left + 0.95, y + 0.18, width - 1.25, 0.42, p_title, size=16, bold=True, color=INK)

        # 阐述说明正文
        add_text(slide, left + 0.95, y + 0.62, width - 1.25, card_h - 0.72, p_desc, size=13, color=INK_LIGHT, line_spacing=1.3)

    add_footer(slide, page_no, total)
    return slide


def build_end(prs, theme: dict, total: int):
    """封底页：大气总结致谢。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_shape(slide, 0.0, 6.5, 13.334, 1.0, fill=theme["primary"], shape="rect")
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

    deck_title, subtitle, sections = parse_and_paginate_markdown(text, base_dir=out_path.parent)

    prs = Presentation()
    prs.slide_width = Inches(13.334)  # 16:9
    prs.slide_height = Inches(7.5)

    has_catalog = len(sections) >= 3
    total_pages = len(sections) + (3 if has_catalog else 2)

    # 1. 封面
    cover_slide = build_cover(prs, deck_title, subtitle, theme, total_pages)
    cover_slide.notes_slide.notes_text_frame.text = generate_lively_speaker_script(
        deck_title, [], "cover", 1, total_pages, deck_title
    )

    cur_page = 1
    # 2. 目录页
    if has_catalog:
        cur_page += 1
        cat_slide = build_catalog(prs, cur_page, total_pages, sections, theme)
        cat_slide.notes_slide.notes_text_frame.text = generate_lively_speaker_script(
            "核心目录概览", [s.title for s in sections[:4]], "catalog", cur_page, total_pages, deck_title
        )

    # 3. 逐页生成核心内容
    for sec in sections:
        cur_page += 1
        layout = sec.layout_type

        if layout == "quad_grid":
            slide = build_quad_grid(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "image_text":
            slide = build_image_text(prs, cur_page, total_pages, sec.title, sec.bullets, sec.images, theme)
        elif layout == "stat_cards":
            slide = build_stat_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "process_steps":
            slide = build_process_steps(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "column_cards":
            slide = build_column_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        else:
            slide = build_standard_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)

        # 写入生动、富有感染力的口播演讲稿（非死读 PPT）
        lively_notes = generate_lively_speaker_script(
            sec.title, sec.bullets, layout, cur_page, total_pages, deck_title
        )
        slide.notes_slide.notes_text_frame.text = lively_notes

    # 4. 封底
    end_slide = build_end(prs, theme, total_pages)
    end_slide.notes_slide.notes_text_frame.text = generate_lively_speaker_script(
        "致谢与总结", [], "end", total_pages, total_pages, deck_title
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    print(f"[ppt-master] 成功生成高质量 16:9 PPTX: {out_path.name}（共 {total_pages} 页，精简多版式排版与生动口播备注已就绪）")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="ppt-master 专业演示文稿生成引擎")
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
        safe_name = re.sub(r'[\\/:*?"<>|\r\n\t]', "", base_name).strip()[:40] or "presentation"
        out_path = out_dir / f"{safe_name}_{stamp}.pptx"

        quick_markdown_pptx(text, out_path)
        return 0

    print("[ppt-master] 当前输入格式需转换为 Markdown 后生成", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
