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
    "retro": {
        "primary": (0x8C, 0x4A, 0x2F),        # 复古砖红（兵工/历史/文旅）
        "primary_dark": (0x5C, 0x2E, 0x12),
        "primary_light": (0xC0, 0x7A, 0x50),
        "accent": (0x5B, 0x6B, 0x3A),         # 军旅橄榄绿
        "soft": (0xF7, 0xF2, 0xEA),
        "soft2": (0xF0, 0xE6, 0xD4),
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
    "forest": {
        "primary": (0x2F, 0x7D, 0x4F),        # 森林绿（自然/生态/农业/文旅）
        "primary_dark": (0x1B, 0x4D, 0x31),
        "primary_light": (0x6F, 0xB0, 0x82),
        "accent": (0xE0, 0xA8, 0x3D),         # 麦田金
        "soft": (0xF2, 0xF8, 0xF2),
        "soft2": (0xE5, 0xF1, 0xE7),
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
    "royal": {
        "primary": (0x9F, 0x1D, 0x1D),        # 中国红（政务/党建）
        "primary_dark": (0x6E, 0x12, 0x12),
        "primary_light": (0xD4, 0x6A, 0x6A),
        "accent": (0xC9, 0x9A, 0x2E),         # 鎏金
        "soft": (0xFB, 0xF4, 0xF0),
        "soft2": (0xF7, 0xE8, 0xDE),
        "card_bg": (0xFF, 0xFF, 0xFF),
    },
}

# 主题关键词规则（按优先级顺序匹配，先命中者生效）
_THEME_RULES = [
    ("royal", ["党建", "政务", "政府", "廉政", "纪念", "长征", "红色文化"]),
    ("retro", ["兵工", "军工", "历史", "革命", "抗战", "小镇", "古镇", "遗址", "三线", "文物", "博物馆", "老工业"]),
    ("forest", ["生态", "自然", "农业", "乡村", "田园", "森林", "绿色", "环保", "景区", "旅游", "文旅"]),
    ("teal", ["医疗", "健康", "生命", "医药", "生物", "临床"]),
    ("amber", ["金融", "商业", "投资", "财经", "增长", "市场", "营销"]),
    ("indigo", ["科技", "AI", "智能", "算法", "数据", "互联网", "数字", "软件", "技术", "系统", "离线"]),
]


def choose_theme(text: str) -> str:
    """根据任务主题与内容自动选择配色主题；可用 AI_CLIENT_PPT_THEME 显式覆盖。"""
    env = os.environ.get("AI_CLIENT_PPT_THEME", "").strip().lower()
    if env and env in THEMES:
        return env
    corpus = text[:3000]
    for name, kws in _THEME_RULES:
        for kw in kws:
            if kw.lower() in corpus.lower():
                return name
    return "indigo"

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
    # 清理项目符号 / 破折号
    t = re.sub(r"^[\s\-*•]+\s*", "", t)
    # 清理 1~2 位序号（如 "1. " "12、" "③"）；保留 4 位年份（如 1938年）
    t = re.sub(r"^\d{1,2}[.、)）]\s*", "", t)
    t = re.sub(r"^[①-⑳]\s*", "", t)
    return t.strip()


def extract_point_parts(bullet: str) -> tuple[str, str]:
    """将一条要点智能拆解为 (标题/关键词, 阐述说明)。

    设计原则：
      - 该简介简介：大字重点词精炼醒目（4~10字），大字展示；
      - 该详细的详细：正文阐释充分清晰（介绍清楚，把机制和收益讲透，绝不丢失关键信息）。
    """
    raw = bullet.strip()
    if not raw:
        return "", ""

    # 1) 优先识别 Markdown 加粗重点词（如 **核心定位**: 详细说明 或 **极致安全** 详细说明）
    m_bold = re.match(r"^[\s\-*•]*\*{2}([^\*]+)\*{2}[:：\s]*(.*)$", raw)
    if m_bold:
        k = clean_markdown_artifacts(m_bold.group(1))
        v = clean_markdown_artifacts(m_bold.group(2))
        if k:
            return k, v

    # 2) 优先识别中括号或中文括号包裹的核心重点词（如 【端侧部署】详细说明 或 [全功能集成] 详细说明）
    m_bracket = re.match(r"^[\s\-*•]*[【\[]([^】\]]+)[】\]][:：\s]*(.*)$", raw)
    if m_bracket:
        k = clean_markdown_artifacts(m_bracket.group(1))
        v = clean_markdown_artifacts(m_bracket.group(2))
        if k:
            return k, v

    clean = clean_markdown_artifacts(raw)
    if not clean:
        return "", ""

    # 3) 按中英文冒号、全角破折号或带空格的破折号拆分
    m = re.split(r"(?:[:：]|(?:\s+[-——]\s+)|(?:——))\s*", clean, maxsplit=1)
    if len(m) == 2 and 2 <= len(m[0]) <= 28 and len(m[1]) >= 2:
        return m[0].strip(), m[1].strip()

    # 4) 较长文本（> 18字）无冒号时：智能寻找自然断句标点，不粗暴截断
    if len(clean) > 18:
        m2 = re.search(r"[,，、;；\s]", clean[4:20])
        if m2:
            idx = 4 + m2.start()
            head = clean[:idx].strip()
            tail = clean[idx + 1:].strip()
            if len(head) >= 2 and len(tail) >= 2:
                return head, tail
        # 若未找到标点，提取前 6~10 个字为重点标题，整句保留为详细说明（保证介绍清楚）
        short_title = clean[:8].rstrip("的与和在对此从以")
        return short_title, clean

    # 5) 短句（<= 18字）：整句即重点词，阐述留空（排版时自适应居中）
    return clean, ""


class SlideSection:
    def __init__(self, title: str, bullets: list[str], images: list[str] = None, notes: str = ""):
        self.title = title
        self.bullets = bullets
        self.images = images or []
        self.notes = notes.strip()
        self.layout_type = self._detect_layout()

    def _detect_layout(self) -> str:
        """根据内容语义智能选择版式（而非只看要点数量）。"""
        if self.images:
            return "image_text"

        text_corpus = " ".join(self.bullets)
        full = self.title + " " + text_corpus

        # 1. 金句 / 愿景 / 使命（单条短句，或标题命中）
        if len(self.bullets) == 1 and len(self.bullets[0]) <= 24:
            return "quote"
        if any(k in self.title for k in ("愿景", "使命", "理念", "口号", "目标", "展望")):
            return "quote"

        # 2. 时间线 / 历史沿革
        if any(k in self.title for k in ("历史", "历程", "沿革", "大事记", "时间线", "发展", "演进", "里程碑", "征程")):
            return "timeline"
        if len(re.findall(r"\b(?:19|20)\d{2}\s*年", full)) >= 2:
            return "timeline"

        # 3. 指标亮点数据页
        metric_matches = re.findall(r"(\d+(?:\.\d+)?%|\d+[xX倍]|\d+\+|\bTOP\s*\d+\b|\d{2,}\s*万?)", text_corpus)
        if len(metric_matches) >= 2 and len(self.bullets) <= 4:
            return "stat_cards"

        # 4. 流程步骤页
        step_matches = [b for b in self.bullets if re.search(r"^(?:步骤|阶段|Step|Phase|\d+[.、)])", b, re.IGNORECASE)]
        if len(step_matches) >= 2 and len(self.bullets) <= 4:
            return "process_steps"

        # 5. 双栏对比（两条要点，或内容命中对比词）
        if len(self.bullets) == 2:
            return "comparison"

        # 6. 四宫格聚焦矩阵
        if len(self.bullets) == 4:
            return "quad_grid"

        # 7. 多列立体卡片
        if len(self.bullets) in (2, 3):
            return "column_cards"

        return "standard_cards"


def parse_and_paginate_markdown(text: str, base_dir: Path | None = None) -> tuple[str, str, list[SlideSection], str, str]:
    """解析 Markdown，提取专属演讲者口播备注文案，并执行严格的分页限制：单页要点不超过 4 条。"""
    deck_title = "演示文稿"
    subtitle = ""
    cover_notes = ""
    end_notes = ""
    raw_sections: list[tuple[str, list[str], list[str], str]] = []

    cur_title = "核心概览"
    cur_bullets: list[str] = []
    cur_images: list[str] = []
    cur_notes: list[str] = []
    started = False
    seen_h2 = False
    in_note_comment = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # 1. 跨行 HTML 备注注释提取
        if in_note_comment:
            if "-->" in stripped:
                part = stripped.split("-->", 1)[0].strip()
                if part:
                    cur_notes.append(part)
                in_note_comment = False
            else:
                cur_notes.append(stripped)
            continue

        # 2. 单行/起首 HTML 口播备注识别：<!-- 口播文案: ... --> / <!-- 演讲备注: ... --> / <!-- note: ... -->
        note_comment_match = re.search(
            r"<!--\s*(?:口播文案|演讲备注|口播|旁白|演讲稿|解说词|note|notes)[:：\s]*(.*?)(?:-->|$)",
            stripped,
            re.IGNORECASE,
        )
        if note_comment_match:
            note_content = note_comment_match.group(1).strip()
            if "-->" in stripped:
                if note_content:
                    cur_notes.append(note_content)
            else:
                if note_content:
                    cur_notes.append(note_content)
                in_note_comment = True
            continue

        # 3. 引用块口播标注识别：> **口播文案**：... 或 > 口播：...
        note_quote_match = re.match(
            r"^>\s*(?:\*\*)?(?:口播文案|演讲备注|口播|旁白|解说词)(?:\*\*)?[:：\s]*(.*)",
            stripped,
        )
        if note_quote_match:
            c = note_quote_match.group(1).strip()
            if c:
                cur_notes.append(c)
            continue

        # 4. 中括号口播标注识别：【口播文案】... 或 [演讲备注] ...
        note_bracket_match = re.match(
            r"^[【\[](?:口播文案|演讲备注|口播|旁白|解说词)[】\]][:：\s]*(.*)",
            stripped,
        )
        if note_bracket_match:
            c = note_bracket_match.group(1).strip()
            if c:
                cur_notes.append(c)
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
            if not seen_h2:
                # 第一页二级标题之前收集到的 notes 归属于封面
                if cur_notes:
                    cover_notes = " ".join(cur_notes).strip()
                    cur_notes = []
            if seen_h2 or cur_bullets or cur_images or cur_notes:
                raw_sections.append((cur_title, cur_bullets, cur_images, " ".join(cur_notes).strip()))
                cur_bullets = []
                cur_images = []
                cur_notes = []
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
        if clean and len(clean) >= 2 and not re.match(r"^[-*_]+$", clean):
            cur_bullets.append(clean)

    if cur_bullets or cur_images or seen_h2 or cur_notes:
        raw_sections.append((cur_title, cur_bullets, cur_images, " ".join(cur_notes).strip()))

    if not raw_sections:
        raw_sections = [("核心概览", ["全功能离线智能体: 本地运算与极致安全", "开箱即用体验: 无需繁琐配置环境"], [], "")]

    # 执行智能分页：任何单节如果超过 4 条要点，自动拆分为多页！
    MAX_PER_PAGE = 4
    final_sections: list[SlideSection] = []

    for title, bullets, images, notes in raw_sections:
        if not bullets:
            final_sections.append(SlideSection(title, ["（本篇章包含架构要点分析）"], images, notes=notes))
            continue

        if len(bullets) <= MAX_PER_PAGE:
            final_sections.append(SlideSection(title, bullets, images, notes=notes))
        else:
            chunks = [bullets[i:i + MAX_PER_PAGE] for i in range(0, len(bullets), MAX_PER_PAGE)]
            sub_labels = ["核心定位", "功能全景", "应用落地", "延展探索"]
            for idx, chunk in enumerate(chunks):
                label = sub_labels[idx] if idx < len(sub_labels) else f"第 {idx+1} 部分"
                page_title = f"{title} · {label}"
                page_imgs = images if idx == 0 else []
                # 原始备注由首个分节使用，后续分节独立生成
                page_note = notes if idx == 0 else ""
                final_sections.append(SlideSection(page_title, chunk, page_imgs, notes=page_note))

    # 检查最后一节是否为专门的致谢/总结页
    if final_sections and any(k in final_sections[-1].title for k in ("致谢", "谢谢", "总结与致谢", "结束")):
        end_sec = final_sections.pop()
        if end_sec.notes:
            end_notes = end_sec.notes

    return deck_title, subtitle, final_sections, cover_notes, end_notes


# ---------------------------------------------------------------- 生动口播解说词生成引擎


def generate_lively_speaker_script(
    title: str,
    bullets: list[str],
    layout_type: str,
    page_no: int,
    total_pages: int,
    deck_title: str
) -> str:
    """生成富有感染力、感情充沛、深入剖析核心逻辑的现场宣讲稿（拒绝机械化照读 PPT）。"""

    # 1. 封面开场
    if page_no == 1 or layout_type == "cover":
        return (
            f"各位同仁、各位朋友，大家好！非常荣幸今天能和大家聚在一起。在当前数字化与智能化快速演进的浪潮下，"
            f"我们每天都在思考一个根本命题：如何让前沿技术真正转化为稳定、可靠且具有深度价值的生产力？"
            f"今天，我们将紧扣《{deck_title}》这一主题，从战略构想、核心突破到落地实践，展开全方位的深入剖析。"
            "话不多说，让我们正式启程！"
        )

    # 2. 目录概览
    if "目录" in title or layout_type == "catalog":
        clean_titles = [clean_markdown_artifacts(b) for b in bullets if b][:4]
        joined = "、".join(clean_titles)
        path_str = f"沿着【{joined}】这条主线层层递进、抽丝剥茧" if joined else "沿着几大核心战略篇章层层推进"
        return (
            "在正式切入各个业务细节之前，我们先花一分钟登高望远，看清本次分享的沙盘全景。"
            f"今天的分享我们将{path_str}。"
            "这套脉络旨在为大家搭建起从底层逻辑到顶层应用的完整闭环，让大家既能看清全局方位，又能把握关键抓手。"
        )

    # 3. 封底收束
    if page_no == total_pages or layout_type == "end":
        return (
            "行而不辍，履践致远。到这里，今天的核心分享就告一段落了。"
            f"但《{deck_title}》所展现的蓝图与探索，才刚刚拉开序幕。"
            "技术的终极价值在于解决真实世界的痛点，在于赋能每一个人的成长与创造。"
            "由衷感谢大家的专注聆听与支持，期待接下来与大家携手共进、深化落地，谢谢大家！"
        )

    parts: list[str] = []

    # 4. 情境代入与设问开场（根据版式与主题定制现场感引导）
    if layout_type == "comparison":
        openers = [
            f"面对《{title}》，很多团队在技术选型或业务推进时都会陷入两难抉择。屏幕上的这组对照，极其尖锐地呈现了两种不同路径带来的深层差距。",
            f"在《{title}》的考量上，传统做法往往存在不少暗坑。通过将两种方案并置对比，优劣边界一目了然。",
        ]
    elif layout_type == "stat_cards":
        openers = [
            f"用事实说话，最有力量的往往是数据。在屏幕上《{title}》这一组亮眼指标的背后，凝结着我们在关键瓶颈上的全力攻坚突破。",
            f"衡量一套方案的成色，核心看成效。《{title}》展现的这一组硬核数据，正是我们交给市场和业务的最有说服力的答卷。",
        ]
    elif layout_type == "process_steps":
        openers = [
            f"天下大事，必作于细。要把《{title}》的宏大构想落到实处，离不开一套条理清晰、环环相扣的实施路径。",
            f"在推进落地层面，《{title}》被拆解为几个循序渐进的战略阶段，每一步都承前启后、有的放矢。",
        ]
    elif layout_type == "timeline":
        openers = [
            f"回望《{title}》的波澜历程，每一个时间刻度，都见证了一次关键的思维迭代与战略跃升。",
            f"时间是最好的试金石。沿着《{title}》的发展轨迹，我们能清晰看懂这一体系是如何一步步沉淀并厚积薄发的。",
        ]
    elif layout_type == "quote":
        openers = [
            f"屏幕上这句凝练而铿锵有力的话语，正是我们在《{title}》中始终秉持的初心与最高准则。",
            f"如果用一句话来概括《{title}》的精神内核，那就是屏幕上的这段宣言，它指引着我们所有的探索与前行。",
        ]
    elif layout_type == "image_text":
        openers = [
            f"大家请结合右侧直观的图解架构来看。图文呼应之下，《{title}》的整体运转机理与核心脉络清晰可见。",
            f"在《{title}》这一环，我们通过可视化的全景架构，将复杂的机制化繁为简地呈现出来。",
        ]
    else:
        openers = [
            f"现在让我们把焦点对准《{title}》。很多朋友在初次接触时最关心的往往是：它到底解决了什么核心痛点？其支撑底座又是什么？",
            f"紧接着，我们深入到《{title}》的核心腹地。如果说前文搭建了框架，那么这一部分，则是为整个体系注入了强劲的运转动能。",
            f"大家请看《{title}》。这不仅是业务落地的关键枢纽，更是直接决定最终用户体验与交付效能的核心胜负手。",
            f"接下来这一页至关重要——《{title}》。我们在这里构建了一个多维协同、稳健自洽的闭环体系。",
        ]
    parts.append(openers[(page_no - 1) % len(openers)])

    # 5. 核心要点现场演讲式深度拆解（告别机械重复的模板句式）
    item_starters = [
        ("首先映入眼帘、也是最根本的支柱，正是【{title}】。",
         "它的破局点在于：{desc}。这直接化解了以往推进中的最大断点，让底盘扎得足够稳固。",
         "这正是整个体系的立足之本，确保在复杂严苛的实际环境下依然能稳如磐石。"),
        ("在打牢底座之后，第二项关键抓手在于【{title}】。",
         "正如大家所见，{desc}。这彻底打通了原本相互割裂的环节，实现了跨越式的效能跃升。",
         "这一环重在赋能提效，让原本繁琐耗时的流程实现真正意义上的降维与提速。"),
        ("更进一步来看，【{title}】同样极具战略价值。",
         "通过{desc}，不仅大幅增强了系统韧性，更为未来的持续拓展留足了空间与弹性。",
         "它赋予了整体架构极强的敏捷度与自适应力，让每一次协作流转都能做到从容自如。"),
        ("最后，作为至关重要的闭环防线，【{title}】同样不可或缺。",
         "它严密确保了{desc}，真正筑牢了一道坚不可摧的安全、合规与品质屏障。",
         "它形成了最后的护城河，让整体方案真正做到闭环无死角、运行无后顾之忧。"),
    ]

    for i, b in enumerate(bullets):
        p_title, p_desc = extract_point_parts(b)
        if not p_title:
            continue
        template_idx = min(i, len(item_starters) - 1)
        lead_fmt, with_desc_fmt, no_desc_fmt = item_starters[template_idx]

        lead_txt = lead_fmt.format(title=p_title)
        if p_desc and p_desc != p_title and p_title not in p_desc:
            body_txt = with_desc_fmt.format(title=p_title, desc=p_desc)
        else:
            body_txt = no_desc_fmt.format(title=p_title)

        parts.append(f"{lead_txt}{body_txt}")

    # 6. 价值升华结语
    closers = [
        "把这几个维度串联起来，大家会发现，这绝非散点功能的简单拼凑，而是一个有机协同、相互赋能的高效战斗力矩阵。",
        "可以说，把握住这几项核心支柱，我们就真正握住了这一板块的主动权，让落地实施有的放矢、水到渠成。",
        "正是得益于这套严密而富有弹性的机制设计，我们才能在多变的环境中始终保持领先的响应力与可靠性。",
    ]
    parts.append(closers[(page_no - 1) % len(closers)])

    return "".join(parts)[:1500]

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

        if p_desc:
            # 核心亮点标题 (大字突出重点)
            add_text(slide, x + 0.3, y + 0.68, w - 0.6, 0.45, p_title, size=16, bold=True, color=INK)
            # 阐述正文 (多行优雅排版，该详细的详细，把机制和收益介绍清楚)
            desc_size = 12.0 if len(p_desc) > 45 else 13.0
            add_text(slide, x + 0.3, y + 1.15, w - 0.6, h - 1.25, p_desc, size=desc_size, color=INK_LIGHT, line_spacing=1.3)
        else:
            # 纯重点词：居中大字，简洁有力
            add_text(slide, x + 0.3, y + 0.95, w - 0.6, 0.8, p_title, size=18, bold=True, color=INK, align="left")

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

        if p_desc:
            # 核心标题
            add_text(slide, x + 0.3, top + 1.2, w - 0.6, 0.7, p_title, size=18, bold=True, color=INK)
            # 分割线
            add_shape(slide, x + 0.3, top + 1.95, 1.2, 0.02, fill=theme["accent"], shape="rect")
            # 阐述说明 (介绍清楚)
            desc_size = 12.5 if len(p_desc) > 60 else 13.5
            add_text(slide, x + 0.3, top + 2.15, w - 0.6, h - 2.35, p_desc, size=desc_size, color=INK_LIGHT, line_spacing=1.35)
        else:
            add_text(slide, x + 0.3, top + 1.8, w - 0.6, 1.2, p_title, size=20, bold=True, color=INK, align="center")

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

        num_match = re.search(r"(\d+(?:\.\d+)?%|\d+[xX倍]|\d+\+|\bTOP\s*\d+\b|\d{2,}\s*万?)", text)
        highlight_num = num_match.group(1) if num_match else f"0{i+1}"
        desc = text.replace(highlight_num, "").strip(" :：-——,，") or text

        add_shape(slide, x, top, w, h, fill=theme["card_bg"], line=LINE, line_w=1.0, radius=0.15)
        add_shape(slide, x, top, w, 0.12, fill=theme["primary"] if i % 2 == 0 else theme["accent"], shape="rect")

        add_shape(slide, x + 0.3, top + 0.38, 0.75, 0.32, fill=theme["soft2"], radius=0.5)
        add_text(slide, x + 0.3, top + 0.42, 0.75, 0.3, f"KEY 0{i+1}", size=9, bold=True, color=theme["primary"], align="center")

        add_text(slide, x + 0.2, top + 1.1, w - 0.4, 1.2, highlight_num, size=36, bold=True, color=theme["primary"], align="center")
        add_shape(slide, x + (w - 1.2)/2, top + 2.45, 1.2, 0.02, fill=LINE, shape="rect")
        desc_size = 12.0 if len(desc) > 50 else 13.5
        add_text(slide, x + 0.25, top + 2.7, w - 0.5, 1.9, desc, size=desc_size, color=INK_LIGHT, align="center", line_spacing=1.3)

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
        desc_size = 12.0 if len(p_desc) > 50 else 13.0
        add_text(slide, x + 0.25, top + 1.55, w - 0.5, 2.5, p_desc, size=desc_size, color=INK_LIGHT, line_spacing=1.35)

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

        if p_desc:
            add_text(slide, 1.05, y + 0.12, text_w - 0.35, 0.38, p_title, size=15, bold=True, color=INK)
            desc_size = 11.5 if len(p_desc) > 50 else 12.5
            add_text(slide, 1.05, y + 0.52, text_w - 0.35, card_h - 0.6, p_desc, size=desc_size, color=INK_LIGHT, line_spacing=1.25)
        else:
            add_text(slide, 1.05, y + (card_h - 0.4) / 2, text_w - 0.35, 0.4, p_title, size=16, bold=True, color=INK)

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
    """水平卡片排版（控制在 3 条以内，大卡片，大字重点与详细说明）。"""
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

        if p_desc:
            # 核心重点标题 (粗体大字，一目了然)
            add_text(slide, left + 0.95, y + 0.18, width - 1.25, 0.42, p_title, size=16.5, bold=True, color=INK)
            # 阐述说明正文 (详细介绍)
            desc_size = 12.0 if len(p_desc) > 60 else 13.0
            add_text(slide, left + 0.95, y + 0.62, width - 1.25, card_h - 0.72, p_desc, size=desc_size, color=INK_LIGHT, line_spacing=1.3)
        else:
            add_text(slide, left + 0.95, y + (card_h - 0.45) / 2, width - 1.25, 0.45, p_title, size=17.5, bold=True, color=INK)

    add_footer(slide, page_no, total)
    return slide


def build_quote(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """金句/愿景大标题版式：居中大字，极简有力。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    statement = bullets[0] if bullets else title
    size = 36 if len(statement) <= 18 else (30 if len(statement) <= 30 else 24)

    add_shape(slide, 5.45, 1.9, 2.45, 0.08, fill=theme["accent"], radius=0.5)
    add_text(slide, 1.3, 2.25, 10.73, 2.5, statement, size=size, bold=True, color=INK, align="center", line_spacing=1.35)
    add_shape(slide, 5.45, 4.95, 2.45, 0.08, fill=theme["accent"], radius=0.5)
    add_text(slide, 1.3, 5.25, 10.73, 0.6, f"—— {title}", size=15, bold=True, color=theme["primary_dark"], align="center")

    add_footer(slide, page_no, total)
    return slide


def build_timeline(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """横向时间线版式：节点年份 + 上下说明，适合历史沿革/发展历程。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    n = max(min(len(bullets), 5), 2)
    y_line = 3.75
    xs = [1.1 + i * (11.1 / max(n - 1, 1)) for i in range(n)]

    add_shape(slide, 1.0, y_line, 11.3, 0.045, fill=theme["primary_light"], shape="rect")

    for i, (x, b) in enumerate(zip(xs, bullets[:n])):
        p_title, p_desc = extract_point_parts(b)
        node_fill = theme["primary"] if i % 2 == 0 else theme["accent"]
        add_shape(slide, x - 0.17, y_line - 0.15, 0.36, 0.36, fill=node_fill, shape="oval")
        add_text(slide, x - 1.05, y_line - 1.55, 2.1, 0.5, p_title, size=15, bold=True, color=INK, align="center")
        desc_size = 11.0 if len(p_desc) > 40 else 12.0
        add_text(slide, x - 1.1, y_line + 0.4, 2.2, 1.5, p_desc, size=desc_size, color=INK_LIGHT, align="center", line_spacing=1.25)

    add_footer(slide, page_no, total)
    return slide


def build_comparison(prs, page_no: int, total: int, title: str, bullets: list[str], theme: dict):
    """双栏对比版式：左右两栏 + 中间 VS，用于优劣/方案对比。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, page_no, total, title, theme)

    left_b = bullets[0] if len(bullets) > 0 else ""
    right_b = bullets[1] if len(bullets) > 1 else ""

    col_w = 5.55
    x1, x2 = 0.8, 7.0
    top, h = 1.7, 4.55

    add_shape(slide, x1, top, col_w, h, fill=theme["soft"], radius=0.14)
    add_shape(slide, x1, top, col_w, 0.08, fill=theme["primary_light"], shape="rect")
    l_title, l_desc = extract_point_parts(left_b)
    add_text(slide, x1 + 0.3, top + 0.35, col_w - 0.6, 0.7, l_title or "方案 A", size=20, bold=True, color=theme["primary_light"], line_spacing=1.2)
    add_shape(slide, x1 + 0.3, top + 1.2, 1.0, 0.04, fill=theme["primary_light"], shape="rect")
    desc_size_l = 12.0 if len(l_desc) > 60 else 13.0
    add_text(slide, x1 + 0.3, top + 1.45, col_w - 0.6, h - 1.7, l_desc, size=desc_size_l, color=INK_LIGHT, line_spacing=1.4)

    add_shape(slide, x2, top, col_w, h, fill=theme["card_bg"], line=theme["primary"], line_w=1.5, radius=0.14)
    add_shape(slide, x2, top, col_w, 0.08, fill=theme["primary"], shape="rect")
    r_title, r_desc = extract_point_parts(right_b)
    add_text(slide, x2 + 0.3, top + 0.35, col_w - 0.6, 0.7, r_title or "方案 B", size=20, bold=True, color=theme["primary_dark"], line_spacing=1.2)
    add_shape(slide, x2 + 0.3, top + 1.2, 1.0, 0.04, fill=theme["accent"], shape="rect")
    desc_size_r = 12.0 if len(r_desc) > 60 else 13.0
    add_text(slide, x2 + 0.3, top + 1.45, col_w - 0.6, h - 1.7, r_desc, size=desc_size_r, color=INK_LIGHT, line_spacing=1.4)

    add_shape(slide, 6.08, top + 1.85, 0.9, 0.9, fill=theme["primary"], shape="oval")
    add_text(slide, 6.08, top + 2.08, 0.9, 0.5, "VS", size=16, bold=True, color=WHITE, align="center")

    add_footer(slide, page_no, total)
    return slide


def alternate_layout(layout: str, sec) -> str:
    """版式去重：若连续两页撞版式，换成另一种适配该页内容的版式。"""
    n = len(sec.bullets)
    if layout == "quad_grid":
        return "column_cards" if n <= 3 else "standard_cards"
    if layout == "column_cards":
        return "standard_cards"
    if layout == "standard_cards":
        return "quad_grid" if n == 4 else "column_cards"
    if layout == "process_steps":
        return "quad_grid" if n == 4 else "standard_cards"
    return layout


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

    theme = THEMES[choose_theme(text)]

    deck_title, subtitle, sections, cover_notes, end_notes = parse_and_paginate_markdown(text, base_dir=out_path.parent)

    prs = Presentation()
    prs.slide_width = Inches(13.334)  # 16:9
    prs.slide_height = Inches(7.5)

    has_catalog = len(sections) >= 3
    total_pages = len(sections) + (3 if has_catalog else 2)

    # 1. 封面
    cover_slide = build_cover(prs, deck_title, subtitle, theme, total_pages)
    cover_slide.notes_slide.notes_text_frame.text = (
        cover_notes if cover_notes else generate_lively_speaker_script(
            deck_title, [], "cover", 1, total_pages, deck_title
        )
    )

    cur_page = 1
    # 2. 目录页
    if has_catalog:
        cur_page += 1
        cat_slide = build_catalog(prs, cur_page, total_pages, sections, theme)
        cat_slide.notes_slide.notes_text_frame.text = generate_lively_speaker_script(
            "核心目录概览", [s.title for s in sections[:4]], "catalog", cur_page, total_pages, deck_title
        )

    # 3. 逐页生成核心内容（内容感知版式 + 连续去重，避免单调）
    prev_layout = None
    for sec in sections:
        cur_page += 1
        layout = sec.layout_type
        if layout == prev_layout:
            layout = alternate_layout(layout, sec)
        prev_layout = layout

        if layout == "quad_grid":
            slide = build_quad_grid(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "image_text":
            slide = build_image_text(prs, cur_page, total_pages, sec.title, sec.bullets, sec.images, theme)
        elif layout == "stat_cards":
            slide = build_stat_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "process_steps":
            slide = build_process_steps(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "timeline":
            slide = build_timeline(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "comparison":
            slide = build_comparison(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "quote":
            slide = build_quote(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        elif layout == "column_cards":
            slide = build_column_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)
        else:
            slide = build_standard_cards(prs, cur_page, total_pages, sec.title, sec.bullets, theme)

        # 写入生动、富有感染力的口播演讲稿（优先使用显式备注，无显式备注时由演说引擎深度分析生成）
        if sec.notes:
            lively_notes = sec.notes
        else:
            lively_notes = generate_lively_speaker_script(
                sec.title, sec.bullets, layout, cur_page, total_pages, deck_title
            )
        slide.notes_slide.notes_text_frame.text = lively_notes

    # 4. 封底
    end_slide = build_end(prs, theme, total_pages)
    end_slide.notes_slide.notes_text_frame.text = (
        end_notes if end_notes else generate_lively_speaker_script(
            "致谢与总结", [], "end", total_pages, total_pages, deck_title
        )
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
