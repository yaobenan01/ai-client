#!/usr/bin/env python3
"""Build publication-grade White Paper HTML, compile vector PDF via LibreOffice,
and generate the corresponding PPTX presentation deck.
"""
import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "plugins/ppt-master"))

from run import quick_markdown_pptx

ASSETS_DIR = ROOT_DIR / "docs/whitepaper/assets"
OUTPUT_DIR = ROOT_DIR / "docs/whitepaper"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_whitepaper_html() -> Path:
    html_file = OUTPUT_DIR / "ai_client_whitepaper.html"

    # Base64 embedded assets for 100% self-contained LibreOffice vector PDF compilation
    def asset_uri(name: str) -> str:
        p = (ASSETS_DIR / name).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Whitepaper asset not found: {p}")
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>AI-Client 全离线智能体工作站 · 技术白皮书与产品完整功能手册</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 14mm 16mm 14mm 16mm;
    @bottom-center {{
      content: "AI-Client 全离线智能体工作站技术白皮书 | 第 " counter(page) " 页";
      font-size: 8pt;
      color: #94a3b8;
    }}
  }}

  *, *:before, *:after {{
    box-sizing: border-box;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "Segoe UI", Roboto, "PingFang SC", sans-serif;
    line-height: 1.48;
    color: #1e293b;
    background-color: #ffffff;
    font-size: 8.8pt;
    margin: 0;
    padding: 0;
  }}

  /* Page Break Utilities */
  .page-break {{
    page-break-before: always;
    break-before: page;
  }}

  .avoid-break {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  /* Cover Page */
  .cover-container {{
    padding-top: 50px;
    padding-bottom: 20px;
    text-align: center;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .cover-badge {{
    display: inline-block;
    padding: 4px 14px;
    font-size: 9.5pt;
    font-weight: 700;
    color: #4f46e5;
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    border-radius: 9999px;
    margin-bottom: 18px;
    letter-spacing: 0.5px;
  }}

  .cover-title {{
    font-size: 24pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.25;
    margin: 0 0 12px 0;
    letter-spacing: -0.5px;
  }}

  .cover-subtitle {{
    font-size: 11.5pt;
    color: #475569;
    max-width: 620px;
    margin: 0 auto 18px auto;
    line-height: 1.45;
  }}

  .cover-desc {{
    font-size: 9.5pt;
    color: #64748b;
    font-weight: 500;
    margin-bottom: 26px;
  }}

  .cover-meta-table {{
    width: 92%;
    margin: 0 auto 30px auto;
    border-collapse: collapse;
    border: 1px solid #e2e8f0;
    background: #f8fafc;
    border-radius: 6px;
    font-size: 8.5pt;
  }}

  .cover-meta-table td {{
    padding: 9px 12px;
    border: 1px solid #e2e8f0;
    text-align: left;
    color: #475569;
  }}

  .cover-meta-table td strong {{
    color: #0f172a;
  }}

  /* Executive Highlight Box */
  .exec-summary {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 5px solid #4f46e5;
    padding: 12px 16px;
    border-radius: 6px;
    margin-bottom: 14px;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .exec-summary h3 {{
    margin: 0 0 6px 0;
    font-size: 10.5pt;
    color: #1e1b4b;
  }}

  .exec-summary p {{
    margin: 0 0 6px 0;
    font-size: 8.5pt;
    color: #334155;
    line-height: 1.48;
  }}

  .exec-summary p:last-child {{
    margin-bottom: 0;
  }}

  /* Table of Contents */
  .toc-box {{
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 14px;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .toc-title {{
    font-size: 11pt;
    font-weight: 800;
    color: #1e1b4b;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 2px solid #4f46e5;
  }}

  .toc-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0;
    font-size: 8.5pt;
  }}

  .toc-table tr td {{
    border: none !important;
    padding: 4.5px 0 !important;
    background: transparent !important;
  }}

  .toc-name {{
    white-space: nowrap;
    color: #1e293b;
  }}

  .toc-leader {{
    border-bottom: 1px dotted #94a3b8 !important;
    width: 100%;
    height: 0;
    padding: 0 6px !important;
  }}

  .toc-page {{
    text-align: right;
    white-space: nowrap;
    font-weight: 700;
    color: #4f46e5;
    font-family: Consolas, monospace;
    padding-left: 8px !important;
  }}

  /* Headings */
  h1.section-title {{
    font-size: 13.5pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 2px solid #4f46e5;
    padding-bottom: 4px;
    margin-top: 4px;
    margin-bottom: 10px;
    page-break-before: always;
    break-before: page;
    page-break-after: avoid;
    break-after: avoid;
  }}

  h2.subsection-title {{
    font-size: 10pt;
    font-weight: 700;
    color: #1e293b;
    margin-top: 8px;
    margin-bottom: 5px;
    padding-left: 6px;
    border-left: 4px solid #06b6d4;
    page-break-after: avoid;
    break-after: avoid;
  }}

  h3 {{
    font-size: 9pt;
    font-weight: 600;
    color: #334155;
    margin-top: 6px;
    margin-bottom: 3px;
    page-break-after: avoid;
    break-after: avoid;
  }}

  p {{
    margin: 0 0 5px 0;
    text-align: justify;
    line-height: 1.48;
  }}

  /* Table-based Grid layout for rock-solid LibreOffice rendering */
  table.layout-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 8px;
    margin: 6px 0;
    border: none;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  table.layout-table td {{
    vertical-align: top;
    border: none;
    padding: 0;
    background: transparent;
  }}

  .card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 7px 9px;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .card-header {{
    font-size: 8.5pt;
    font-weight: 700;
    color: #4f46e5;
    margin-bottom: 2px;
  }}

  .card p {{
    font-size: 7.8pt;
    color: #475569;
    margin: 0;
    line-height: 1.38;
  }}

  /* Data Metric Card */
  .metric-card {{
    text-align: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .metric-num {{
    font-size: 16pt;
    font-weight: 800;
    color: #4f46e5;
    line-height: 1.1;
  }}

  .metric-label {{
    font-size: 7.8pt;
    font-weight: 600;
    color: #64748b;
    margin-top: 2px;
  }}

  /* Tables */
  table.data-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 6px 0;
    font-size: 7.8pt;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  table.data-table th {{
    background: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
    text-align: left;
    padding: 5px 7px;
    border: 1px solid #cbd5e1;
  }}

  table.data-table td {{
    padding: 5px 7px;
    border: 1px solid #e2e8f0;
    color: #334155;
    vertical-align: top;
    line-height: 1.38;
  }}

  table.data-table tr:nth-child(even) td {{
    background: #f8fafc;
  }}

  /* Code & Mono */
  code {{
    font-family: Consolas, Monaco, "Courier New", monospace;
    font-size: 7.8pt;
    background: #f1f5f9;
    padding: 1px 4px;
    border-radius: 3px;
    color: #0f172a;
    border: 1px solid #e2e8f0;
  }}

  /* Image Figure Box */
  .figure-box {{
    margin: 6px auto;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    overflow: hidden;
    background: #f8fafc;
    text-align: center;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .figure-box img {{
    display: block;
    margin: 0 auto;
    border-bottom: 1px solid #e2e8f0;
  }}

  .figure-caption {{
    padding: 4px 8px;
    font-size: 7.8pt;
    font-weight: 600;
    color: #475569;
    background: #f1f5f9;
  }}

  /* Architecture Diagram Styles */
  .arch-container {{
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 7px;
    background: #ffffff;
    margin: 4px 0;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .arch-layer {{
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 4px 5px;
    margin-bottom: 3px;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .arch-title-bar {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 2px;
  }}

  .arch-title-bar td {{
    border: none;
    padding: 0;
    background: transparent;
  }}

  .arch-badge-num {{
    display: inline-block;
    padding: 1px 4px;
    color: #ffffff;
    border-radius: 3px;
    font-size: 7.2pt;
    font-weight: 700;
    margin-right: 4px;
  }}

  .arch-cards-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 3px;
    margin: 0;
  }}

  .arch-card-td {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 3px 5px;
    vertical-align: top;
  }}

  .arch-card-h {{
    font-weight: 700;
    font-size: 7.5pt;
    margin-bottom: 1px;
  }}

  .arch-card-p {{
    font-size: 6.6pt;
    color: #475569;
    margin: 0;
    line-height: 1.25;
  }}

  .arch-conn {{
    text-align: center;
    color: #64748b;
    font-size: 6.6pt;
    font-weight: bold;
    margin: 1px 0;
    letter-spacing: 0.5px;
  }}

  /* Callouts */
  .callout {{
    padding: 6px 10px;
    border-radius: 5px;
    margin: 6px 0;
    font-size: 7.8pt;
    line-height: 1.4;
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  .callout-info {{
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    color: #1e40af;
  }}

  .callout-success {{
    background: #f0fdf4;
    border-left: 4px solid #22c55e;
    color: #166534;
  }}

  .callout-warning {{
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    color: #92400e;
  }}

  ul, ol {{
    margin: 0 0 5px 0;
    padding-left: 16px;
  }}

  li {{
    margin-bottom: 2px;
    line-height: 1.4;
  }}
</style>
</head>
<body>

<!-- ==================== 第 01 页：白皮书正式封面 ==================== -->
<div class="cover-container avoid-break">
  <div class="cover-badge">★ 2026 企业级高安全与全离线智能体标杆工程</div>
  <div class="cover-title">AI-Client 离线智能体工作站</div>
  <div class="cover-subtitle">
    全离线自主可控 · 原生 DrawingML 矢量演示文稿 · 音画同步口播视频 · 国产信创全生态适配
  </div>
  <div class="cover-desc">
    产品功能全景深度剖析与工程实现技术白皮书（Release v2.0）
  </div>

  <table class="cover-meta-table">
    <tr>
      <td style="width: 50%;"><strong>研发机构：</strong>AI-Client 核心工程组</td>
      <td style="width: 50%;"><strong>运行模式：</strong>物理隔离 / 100% 纯本地运行</td>
    </tr>
    <tr>
      <td><strong>适配架构：</strong>x86_64 / ARM64 / 龙芯 LoongArch / 鲲鹏 / 飞腾</td>
      <td><strong>操作系统：</strong>Windows / macOS / 银河麒麟 / 统信 UOS / 方德</td>
    </tr>
    <tr>
      <td><strong>发布版本：</strong>Enterprise Release v2.0 (全自包含安装版)</td>
      <td><strong>发布日期：</strong>2026 年技术发布版</td>
    </tr>
  </table>

  <table class="layout-table" style="width: 92%; margin: 0 auto;">
    <tr>
      <td style="width: 33.3%;">
        <div class="metric-card">
          <div class="metric-num">100%</div>
          <div class="metric-label">全本地离线运算 · 核心资产零外流</div>
        </div>
      </td>
      <td style="width: 33.3%;">
        <div class="metric-card">
          <div class="metric-num">0 配置</div>
          <div class="metric-label">内嵌完整工具链 · 用户解压即用</div>
        </div>
      </td>
      <td style="width: 33.4%;">
        <div class="metric-card">
          <div class="metric-num">原生矢量</div>
          <div class="metric-label">DrawingML 排版 · 100% 自由二次编辑</div>
        </div>
      </td>
    </tr>
  </table>
</div>

<!-- ==================== 第 02 页：执行摘要与目录大纲 ==================== -->
<h1 class="section-title" style="margin-top: 0;">执行摘要与目录大纲 (Executive Summary & Contents)</h1>

<div class="exec-summary">
  <h3>✦ 执行摘要 (Executive Summary)</h3>
  <p>
    随着生成式人工智能向各行各业深度渗透，政务涉密、国防军工、金融核心与高端工业制造领域面临着前所未有的<strong>「数据主权与物理断网安全」</strong>矛盾：公网大模型存在不可控的敏感资产出域泄密风险；常规离线工具部署极其繁重、依赖复杂；开源生成式 PPT 方案大多采用不可二次编辑的“图片拼贴”，且配音视频制作成本高昂。
  </p>
  <p>
    <strong>AI-Client</strong> 专为彻底解决上述痛点而生。项目以 <strong>Rust 独立核心引擎（core）</strong>为中枢，深度融合 <strong>React 现代化任务工作台（web）</strong>与 <strong>Tauri 跨平台桌面壳（desktop）</strong>，全面内嵌 <strong>llama.cpp、Python、LibreOffice、Piper 神经网络语音与 FFmpeg</strong> 等全套附件运行时（sidecars）。系统交付即包含完整的开箱即用能力，做到“双击即用、物理断网零依赖、原生矢量 PPTX 自由修改、音画同步口播视频一键成片”。
  </p>
</div>

<div class="toc-box">
  <div class="toc-title">目 录 (Table of Contents)</div>
  <table class="toc-table">
    <tr>
      <td class="toc-name"><strong>执行摘要 (Executive Summary)</strong> · 全景价值与核心指标</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 02 页</td>
    </tr>
    <tr>
      <td class="toc-name"><strong>第一章：产品定位与核心痛点破局</strong> · 涉密安全与四大约束解耦</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 03 页</td>
    </tr>
    <tr>
      <td class="toc-name"><strong>第二章：顶层设计与分层技术架构</strong> · 四层解耦架构与 Rust 强安全中枢</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 04 页</td>
    </tr>
    <tr>
      <td class="toc-name"><strong>第三章：核心功能模块深度解析（图文全览）</strong> · 智能步骤合并与离线编排</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 05 页</td>
    </tr>
    <tr>
      <td class="toc-name"><strong>第四章：原生矢量演示文稿与智能口播视频引擎</strong> · DrawingML 排版与演说级配音</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 07 页</td>
    </tr>
    <tr>
      <td class="toc-name"><strong>第五章：插件与技能生态体系 (SKILL.md)</strong> · 运行时环境自检与动态装配</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 09 页</td>
    </tr>
    <tr>
      <td class="toc-name"><strong>第六章：国产信创生态与跨平台适配全景</strong> · 麒麟/统信/龙芯/鲲鹏全生态</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 10 页</td>
    </tr>
    <tr>
      <td class="toc-name"><strong>第七章：总结与展望</strong> · 筑造坚不可摧的政企自主可控数智化基座</td>
      <td class="toc-leader"></td>
      <td class="toc-page">第 11 页</td>
    </tr>
  </table>
</div>

<div class="callout callout-info" style="margin-top: 10px;">
  <strong>✦ 白皮书阅读指引：</strong>
  本手册系统剖析 AI-Client 的离线运行中枢、原生矢量排版体系、音画同步口播流水线及国产信创底座。读者可根据上方目录各章节编号，精准翻阅对应的技术方案与落地指引。
</div>

<!-- ==================== 第 03 页：第一章 产品定位与核心痛点破局 ==================== -->
<h1 class="section-title">第一章：产品定位与核心痛点破局</h1>

<p>
  在数字化政务与企业数字化转型进程中，日常办公、政务公文研报、技术方案汇报与培训课件的制作占据了大量业务骨干的宝贵时间。现有市场方案普遍存在四大约束瓶颈，AI-Client 创新架构给出了体系化的破局解答：
</p>

<table class="data-table">
  <thead>
    <tr>
      <th style="width: 18%;">维度挑战</th>
      <th style="width: 41%;">传统方案 / 在线云端平台劣势</th>
      <th style="width: 41%;">AI-Client 创新解决方案</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>数据安全与保密</strong></td>
      <td>必须联网调用云端 API，核心战略规划、财务数据、未公开技术面临云端审查、网络监听与出域泄密风险。</td>
      <td><strong>物理级断网安全</strong>：模型权重、向量检索、思维推理与文件生成均物理闭环在宿主机本地内存，零网络依赖。</td>
    </tr>
    <tr>
      <td><strong>环境部署与门槛</strong></td>
      <td>各类开源 Agent 要求宿主机自行安装配置 Python、Node、CUDA、C++ 编译工具链，环境冲突与报错频繁。</td>
      <td><strong>附件运行时整包自包含</strong>：安装包内置免配 Python 3.10+、LibreOffice、FFmpeg 及 Piper 语音模型，开箱即用。</td>
    </tr>
    <tr>
      <td><strong>PPT 呈现与复用</strong></td>
      <td>多数 AI 工具输出只读图片或简陋 Markdown，排版凌乱文字堆砌，用户无法进行字号、配色与形状微调。</td>
      <td><strong>原生 DrawingML 矢量排版</strong>：严格控制单页 &le; 4 条要点，语义自适应匹配四宫格、步骤图、对比卡片等现代版式。</td>
    </tr>
    <tr>
      <td><strong>口播视频与宣讲</strong></td>
      <td>需人工录制或调用昂贵商业数字人；现有转口播工具死板念读 PPT 页面文字，听感机械单调无感情。</td>
      <td><strong>现场演讲家级口播引擎</strong>：为每页深度剖析痛点、机制与价值，输出自然生动解说词，离线合成音画同步 MP4。</td>
    </tr>
  </tbody>
</table>

<table class="layout-table">
  <tr>
    <td style="width: 33.3%;">
      <div class="card" style="text-align: center;">
        <div class="card-header">100% 物理隔离</div>
        <p>全要素闭环运行，满足国防涉密与金融强监管合规要求。</p>
      </div>
    </td>
    <td style="width: 33.3%;">
      <div class="card" style="text-align: center;">
        <div class="card-header">0 环境门槛</div>
        <p>完整内嵌附件运行时，彻底杜绝 Python/C++ 依赖缺失故障。</p>
      </div>
    </td>
    <td style="width: 33.4%;">
      <div class="card" style="text-align: center;">
        <div class="card-header">100% 原生矢量</div>
        <p>原生 DrawingML 渲染，兼容 Office 与信创办公套件二次精调。</p>
      </div>
    </td>
  </tr>
</table>

<div class="callout callout-info">
  <strong>✦ 破局核心总结：</strong>
  AI-Client 并非简单的大模型外壳封装，而是一套将<strong>端侧算力、自动化工作流、原生文档排版与多媒体渲染</strong>深度融合的单机自主可控生产力系统，彻底打破“能看不能改”、“机械读稿”、“断网即瘫痪”的三重困境。
</div>

<!-- ==================== 第 04 页：第二章 顶层设计与分层技术架构 ==================== -->
<h1 class="section-title">第二章：顶层设计与分层技术架构</h1>

<p>
  AI-Client 采用高内聚、松耦合的<strong>「分层解耦架构」</strong>。核心引擎与表现层彻底分离，既能作为单机桌面软件运行，亦支持在无显示设备的服务器/信创节点中以 Headless 无头模式运行。
</p>

<!-- 现代化全彩卡片式架构图 -->
<div class="arch-container">
  <!-- 层级 01 -->
  <div class="arch-layer" style="border-left: 4px solid #4f46e5; background: #f5f3ff;">
    <table class="arch-title-bar">
      <tr>
        <td style="text-align: left; font-weight: 800; font-size: 8pt; color: #4338ca;">
          <span class="arch-badge-num" style="background: #4f46e5;">层级 01</span>客户端表现交互层 (Presentation Layer)
        </td>
        <td style="text-align: right; font-size: 7pt; color: #4f46e5;">轻量响应 · 双模式交互</td>
      </tr>
    </table>
    <table class="arch-cards-table">
      <tr>
        <td class="arch-card-td" style="width: 33.3%;">
          <div class="arch-card-h" style="color: #4f46e5;">React 18 现代化工作台</div>
          <p class="arch-card-p">TypeScript + Vite 响应式，支持实时任务流与动态状态树可视化。</p>
        </td>
        <td class="arch-card-td" style="width: 33.3%;">
          <div class="arch-card-h" style="color: #4f46e5;">Tauri v2 跨平台桌面壳</div>
          <p class="arch-card-p">Rust 宿主轻量化深度绑定，常驻内存 &lt; 80MB，物理隔绝云端外联。</p>
        </td>
        <td class="arch-card-td" style="width: 33.4%;">
          <div class="arch-card-h" style="color: #4f46e5;">PWA 离线应用支持</div>
          <p class="arch-card-p">集成 Service Worker，支持鸿蒙/信创平板在断网环境下脱网免安装运行。</p>
        </td>
      </tr>
    </table>
  </div>

  <div class="arch-conn">↕ 高效 IPC 二进制通信通道 (Tauri Command / JSON-RPC 异步事件流) ↕</div>

  <!-- 层级 02 -->
  <div class="arch-layer" style="border-left: 4px solid #0284c7; background: #f0f9ff;">
    <table class="arch-title-bar">
      <tr>
        <td style="text-align: left; font-weight: 800; font-size: 8pt; color: #0369a1;">
          <span class="arch-badge-num" style="background: #0284c7;">层级 02</span>核心执行引擎层 (Core Engine Layer · Rust 原生强安全中枢)
        </td>
        <td style="text-align: right; font-size: 7pt; color: #0284c7;">高可靠 · 零内存泄漏</td>
      </tr>
    </table>
    <table class="arch-cards-table">
      <tr>
        <td class="arch-card-td" style="width: 25%;">
          <div class="arch-card-h" style="color: #0284c7;">自主 Agent 调度</div>
          <p class="arch-card-p">ReAct 循环：意图解析 &rarr; 任务拆解 &rarr; 工具调用 &rarr; 反思校验。</p>
        </td>
        <td class="arch-card-td" style="width: 25%;">
          <div class="arch-card-h" style="color: #0284c7;">步骤智能合并器</div>
          <p class="arch-card-p">Step Collapsing 聚合连续同名日志，消除视觉噪音。</p>
        </td>
        <td class="arch-card-td" style="width: 25%;">
          <div class="arch-card-h" style="color: #0284c7;">人文化诊断 & 免API</div>
          <p class="arch-card-p">识别 402/401 额度异常，提供一键切换离线直出 PPT 通道。</p>
        </td>
        <td class="arch-card-td" style="width: 25%;">
          <div class="arch-card-h" style="color: #0284c7;">SQLite 事务存储</div>
          <p class="arch-card-p">本地持久化任务快照、审计日志与产物索引，断电不丢。</p>
        </td>
      </tr>
    </table>
  </div>

  <div class="arch-conn">↕ 标准进程沙箱管道总线 (Sidecars Process Bus) ↕</div>

  <!-- 层级 03 -->
  <div class="arch-layer" style="border-left: 4px solid #059669; background: #ecfdf5;">
    <table class="arch-title-bar">
      <tr>
        <td style="text-align: left; font-weight: 800; font-size: 8pt; color: #047857;">
          <span class="arch-badge-num" style="background: #059669;">层级 03</span>附件运行时总线 (Bundled Sidecars Layer · 全离线开箱即用)
        </td>
        <td style="text-align: right; font-size: 7pt; color: #059669;">0 环境依赖 · 绿色便携</td>
      </tr>
    </table>
    <table class="arch-cards-table">
      <tr>
        <td class="arch-card-td" style="width: 20%;">
          <div class="arch-card-h" style="color: #059669;">llama.cpp 引擎</div>
          <p class="arch-card-p">自动拉起本地 GGUF 推理，按需释放显存。</p>
        </td>
        <td class="arch-card-td" style="width: 20%;">
          <div class="arch-card-h" style="color: #059669;">内嵌 Python 3.10+</div>
          <p class="arch-card-p">免配置环境，内置 python-pptx, PyMuPDF 等。</p>
        </td>
        <td class="arch-card-td" style="width: 20%;">
          <div class="arch-card-h" style="color: #059669;">LibreOffice 总线</div>
          <p class="arch-card-p">Headless 模式高保真矢量转换输出出版级 PDF。</p>
        </td>
        <td class="arch-card-td" style="width: 20%;">
          <div class="arch-card-h" style="color: #059669;">Piper 神经网络语音</div>
          <p class="arch-card-p">纯离线 zh_CN 自然中英文混读发音人。</p>
        </td>
        <td class="arch-card-td" style="width: 20%;">
          <div class="arch-card-h" style="color: #059669;">FFmpeg 音画中枢</div>
          <p class="arch-card-p">毫秒级逐页对齐合成专业高画质 MP4 视频。</p>
        </td>
      </tr>
    </table>
  </div>

  <div class="arch-conn">↕ 操作系统系统调用与硬件指令集抽象 ↕</div>

  <!-- 层级 04 -->
  <div class="arch-layer" style="border-left: 4px solid #d97706; background: #fffbeb;">
    <table class="arch-title-bar">
      <tr>
        <td style="text-align: left; font-weight: 800; font-size: 8pt; color: #b45309;">
          <span class="arch-badge-num" style="background: #d97706;">层级 04</span>数据安全沙箱与信创生态底座 (Security & Domestic Platform Base)
        </td>
        <td style="text-align: right; font-size: 7pt; color: #d97706;">自主可控 · 信创全适配</td>
      </tr>
    </table>
    <table class="arch-cards-table">
      <tr>
        <td class="arch-card-td" style="width: 33.3%;">
          <div class="arch-card-h" style="color: #d97706;">物理断网安全沙箱</div>
          <p class="arch-card-p">100% 数据不出域，禁止外部未授权网络调用，符合涉密与金融强监管合规。</p>
        </td>
        <td class="arch-card-td" style="width: 33.3%;">
          <div class="arch-card-h" style="color: #d97706;">国产信创操作系统</div>
          <p class="arch-card-p">银河麒麟 (KylinOS V10)、统信 UOS、中科方德 原生 deb/rpm/AppImage 包。</p>
        </td>
        <td class="arch-card-td" style="width: 33.4%;">
          <div class="arch-card-h" style="color: #d97706;">国产芯片原生编译</div>
          <p class="arch-card-p">龙芯 LoongArch64、飞腾 Phytium、华为鲲鹏、海光 x86 等多架构原生指令支持。</p>
        </td>
      </tr>
    </table>
  </div>
</div>
<div class="figure-caption" style="text-align: center; margin-top: -2px; margin-bottom: 5px;">图 2-1：AI-Client 分层系统架构与附件运行时协同拓扑</div>

<h2 class="subsection-title">2.1 为什么选择 Rust 构建核心引擎？</h2>
<ul>
  <li><strong>零垃圾回收停顿与极低常驻内存</strong>：Rust 核心在维持长时间大模型交互与并发任务调度时，常驻内存仅需几十兆，彻底杜绝 Electron 类软件的卡顿与内存膨胀。</li>
  <li><strong>信创 CPU 架构原生跨平台编译</strong>：基于 LLVM 后端，Rust 能够无缝编译为 x86_64、aarch64 以及龙芯 <code>loongarch64</code> 原生机器码，完美契合国产信创战略。</li>
  <li><strong>强类型安全与进程沙箱管理</strong>：Rust 严格的借用检查器与并发所有权模型，确保在频繁拉起多子进程（llama-server、Python、FFmpeg）时绝无内存泄露与僵尸进程。</li>
</ul>

<!-- ==================== 第 05 页：第三章 核心功能模块深度解析（图文全览） ==================== -->
<h1 class="section-title">第三章：核心功能模块深度解析（图文全览）</h1>

<h2 class="subsection-title">3.1 目标驱动型任务执行中枢</h2>
<p>
  AI-Client 摒弃了传统大模型客户端“仅提供单一对话气泡”的简易范式，全面升级为<strong>「目标驱动的任务工作台」</strong>。用户输入业务需求后，Agent 执行引擎会自动开启多阶段推进闭环：
</p>
<ol>
  <li><strong>阶段 1/4（需求分析与大纲架构）</strong>：分析材料、拆解逻辑脉络、提炼核心版式方案；</li>
  <li><strong>阶段 2/4（原生 PPTX 矢量生成）</strong>：调用矢量排版引擎生成高质感 16:9 原生幻灯片；</li>
  <li><strong>阶段 3/4（音画同步视频渲染）</strong>：调用视频流水线执行矢量提取、TTS 配音与流媒体合成；</li>
  <li><strong>阶段 4/4（交付总结与产物归档）</strong>：归纳产物清单，提供后续编辑建议与本地打开通道。</li>
</ol>

<div class="figure-box" style="width: 440px;">
  <img src="{asset_uri('ui_task_detail.png')}" alt="任务执行详情与产物交付界面" width="440" height="230">
  <div class="figure-caption">图 3-1：AI-Client 目标驱动型任务工作台全景（展示规划推进、状态流转与产物交付卡片）</div>
</div>

<p>
  系统提供<strong>阶段级进度追溯</strong>，实时显示“规划中、执行中、已完成、异常中断”等清晰状态；任务产物即时卡片化输出，支持一键在操作系统原生程序中定位与打开。
</p>

<!-- ==================== 第 06 页：第三章 续：智能步骤合并与端侧编排 ==================== -->
<h2 class="subsection-title" style="page-break-before: always; break-before: page; margin-top: 0;">3.2 独家创新：相同步骤智能合并算法 (Step Collapsing)</h2>
<p>
  传统智能体在处理批处理操作或多步重试时，UI 往往被刷入几十条重复的“调用工具”与“工具返回”日志，导致关键业务结论被严重淹没。AI-Client 在前端 <code>LogViewer</code> 组件中引入了步骤拓扑折叠机制：对同一 Step 内的连续同名工具操作（如连续调用 <code>read_file</code> 或 <code>write_file</code>），系统自动将其折叠聚合为一个整洁的状态卡片，并在徽标上实时显示子操作执行计数（如 <code>read_file (4次操作)</code>），既保持极简视觉，又支持点击展开微观调试。
</p>

<div class="figure-box" style="width: 460px;">
  <img src="{asset_uri('ui_step_merge.png')}" alt="相同步骤合并与状态诊断" width="460" height="85">
  <div class="figure-caption">图 3-2：相同步骤智能合并算法执行实拍（消除多重工具重复调用噪音）</div>
</div>

<h2 class="subsection-title">3.3 大模型纳管与端侧 llama.cpp 自动化编排</h2>
<p>
  AI-Client 提供了高度弹性、多模态的模型纳管层，覆盖端侧离线推理与局域网服务器全场景：
</p>
<ul>
  <li><strong>本地 GGUF 离线模型导入与动态编排</strong>：用户仅需在界面指定本地 <code>.gguf</code> 文件路径，系统内的 <code>LlamaServerManager</code> 将在任务触发时自动探测空闲端口，按需拉起高性能 <code>llama-server</code>，任务结束后自动回收显存；</li>
  <li><strong>本地局域网 OpenAI 兼容端点接入</strong>：支持直接对接内网部署的 Ollama、vLLM、Xinference 等大模型服务；</li>
  <li><strong>402 余额耗尽人文化诊断与免 API 离线直出</strong>：当配置的外部接口由于账户欠费返回 HTTP 402/401 时，系统弹出友好诊断卡片，并提供<strong>「⚡ 使用内置离线引擎直接生成 PPT (免 API 额度)」</strong>快捷按钮，保障应急交付不中断。</li>
</ul>

<!-- ==================== 第 07 页：第四章 原生矢量演示文稿与智能口播视频引擎 ==================== -->
<h1 class="section-title">第四章：原生矢量演示文稿与智能口播视频引擎</h1>

<h2 class="subsection-title">4.1 原生 DrawingML 矢量排版体系（告别图片拼接与杂乱堆砌）</h2>
<p>
  与市场上大部分“将 HTML/Markdown 截图贴进 PPT”的假课件工具不同，AI-Client 内置的原生矢量演示文稿引擎生成的是<strong>100% 原生矢量 DrawingML 幻灯片</strong>。文档中的每个矩形卡片、圆角高光底板、立体阴影、文本框与字号层级，在 Microsoft PowerPoint、WPS Office 或 LibreOffice 中均可自由选中、移动、换色或修改文字。
</p>

<div class="figure-box" style="width: 440px;">
  <img src="{asset_uri('ppt_slide_preview.png')}" alt="原生矢量演示文稿排版实拍" width="440" height="202">
  <div class="figure-caption">图 4-1：原生矢量演示文稿生成实机效果（层次分明、高对比重点大字、优雅现代）</div>
</div>

<p>
  为彻底解决用户痛感最强烈的“文字堆砌、排版凌乱、主次不分”问题，引擎确立了严格的<strong>排版设计规范</strong>：
</p>
<ul>
  <li><strong>单页要点严格控制在 3~4 条以内</strong>：若原始材料单节超过 4 条，算法自动启用主题分叶，严禁信息过载；</li>
  <li><strong>该简介简介，该详细详细</strong>：标题精炼醒目（4~10字）大字高对比呈现；正文详细展开（20~50字）把背后的工作机制与价值介绍清楚，严禁粗暴截断关键句；</li>
  <li><strong>专业多套系主题色彩</strong>：支持科技靛蓝、碧翠青绿、琥珀金橙、兵工复古红与党建中国红等丰富调色方案。</li>
</ul>

<!-- ==================== 第 08 页：第四章 续：自适应核心版式矩阵与演说级口播视频 ==================== -->
<h2 class="subsection-title" style="page-break-before: always; break-before: page; margin-top: 0;">4.2 内容感知自适应版式矩阵</h2>
<p>
  引擎通过语义解析输入文本的结构特征，自适应调度最佳视觉容器组件：
</p>

<table style="width: 100%; border-collapse: separate; border-spacing: 6px; margin: 3px 0 6px 0; border: none; page-break-inside: avoid; break-inside: avoid;">
  <tr>
    <td style="border: 1px solid #cbd5e1; border-radius: 5px; padding: 3px; background: #f8fafc; text-align: center; width: 50%;">
      <img src="{asset_uri('ppt_quad_grid.png')}" alt="四宫格聚焦矩阵" width="220" height="124" style="display: block; margin: 0 auto;">
      <div style="font-size: 7.2pt; font-weight: 700; color: #475569; padding: 2px 0;">四宫格聚焦矩阵 (4 要点矩阵)</div>
    </td>
    <td style="border: 1px solid #cbd5e1; border-radius: 5px; padding: 3px; background: #f8fafc; text-align: center; width: 50%;">
      <img src="{asset_uri('ppt_stat_cards.png')}" alt="36pt 数据亮点卡片" width="220" height="124" style="display: block; margin: 0 auto;">
      <div style="font-size: 7.2pt; font-weight: 700; color: #475569; padding: 2px 0;">36pt 超大数值亮点卡片</div>
    </td>
  </tr>
  <tr>
    <td style="border: 1px solid #cbd5e1; border-radius: 5px; padding: 3px; background: #f8fafc; text-align: center; width: 50%;">
      <img src="{asset_uri('ppt_steps.png')}" alt="横向流程流转步骤" width="220" height="124" style="display: block; margin: 0 auto;">
      <div style="font-size: 7.2pt; font-weight: 700; color: #475569; padding: 2px 0;">横向流程流转步骤图</div>
    </td>
    <td style="border: 1px solid #cbd5e1; border-radius: 5px; padding: 3px; background: #f8fafc; text-align: center; width: 50%;">
      <img src="{asset_uri('ppt_columns.png')}" alt="三列立体特色卡片" width="220" height="124" style="display: block; margin: 0 auto;">
      <div style="font-size: 7.2pt; font-weight: 700; color: #475569; padding: 2px 0;">三列立体特色架构卡片</div>
    </td>
  </tr>
</table>

<h2 class="subsection-title">4.3 现场演说家级口播文案与全离线视频流水线</h2>
<p>
  传统“PPT 转视频”软件最大的硬伤在于直接念读屏幕上的干瘪文字。AI-Client 推行<strong>「屏幕负责要点精简展示，口播负责深度剖析讲解」</strong>的双轨设计：
</p>

<table style="width: 100%; border-collapse: collapse; margin: 5px 0; background: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 5px;">
  <tr>
    <td style="padding: 7px 10px; font-size: 7.8pt; color: #1e40af; line-height: 1.4;">
      <strong>✦ 演讲家级解说词设计三要素（拒绝机械读 PPT）：</strong><br>
      <strong>1. 情境代入与痛点设问：</strong>从受众现实痛点切入，建立现场共鸣；<br>
      <strong>2. 核心逻辑与机理解剖：</strong>对要点进行深层次因果分析与业务价值阐发；<br>
      <strong>3. 生动口语与情感充沛：</strong>使用自然流畅、富有感染力的现场演说口吻，自动注入演讲者备注（Speaker Notes）。
    </td>
  </tr>
</table>

<div class="card" style="background: #f8fafc; margin-top: 5px;">
  <div class="card-header" style="color: #0f172a;">全离线音画同步视频合成流水线</div>
  <p style="font-size: 7.2pt; color: #334155; line-height: 1.4;">
    <code>PPTX 矢量文件</code> &rarr; [LibreOffice Headless] &rarr; <code>出版级矢量 PDF</code> &rarr; [PyMuPDF 160DPI 栅格化] &rarr; <code>逐页极清帧图</code><br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&rarr; [演讲者备注提取 &rarr; Piper 神经网络语音合成] &rarr; <code>逐页高保真旁白音频</code><br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&rarr; [FFmpeg 毫秒级时间戳精确对齐流媒体合成] &rarr; <code>专业高画质 MP4 视频成片</code>
  </p>
</div>

<!-- ==================== 第 09 页：第五章 插件与技能生态体系 (SKILL.md) ==================== -->
<h1 class="section-title">第五章：插件与技能生态体系 (SKILL.md)</h1>

<p>
  AI-Client 原生兼容开源 <strong>Agent Skill</strong> 规范。系统支持从本地磁盘直接扫描与装载插件，所有启用的插件技能指令与参数规范将自动编译装配至 Agent 系统提示词（System Prompt）中，赋予智能体无限扩展的能力边界。
</p>

<div class="figure-box" style="width: 480px;">
  <img src="{asset_uri('ui_plugins.png')}" alt="插件与技能生态中心" width="480" height="52">
  <div class="figure-caption">图 5-1：AI-Client 离线插件与技能中心（支持 SKILL.md 动态导入与运行时自检）</div>
</div>

<h2 class="subsection-title">5.1 运行时环境自检仪表盘</h2>
<p>
  在插件与技能管理中心，系统不仅能够对演示文稿生成等内置功能插件进行状态监控，还提供了<strong>本地附件运行时环境自检仪表盘</strong>，一目了然显示 Python 3.10+、LibreOffice、FFmpeg、llama.cpp 与 Piper 的就绪状态，确保用户在任何极端离线环境下均能直观掌握系统的健康状态与算力配置。
</p>

<div class="callout callout-success">
  <strong>✦ 绿色免配置保障：</strong>
  所有依赖项均由安装包自包含携带，软件启动时执行自动化路径探测与端口可用性检查，彻底免除了传统开源项目冗长且易失败的环境配置过程。
</div>

<!-- ==================== 第 10 页：第六章 国产信创生态与跨平台适配全景 ==================== -->
<h1 class="section-title">第六章：国产信创生态与跨平台适配全景</h1>

<p>
  AI-Client 深度响应国产自主可控战略，在架构设计之初即完成了对国内主流软硬件体系的全面适配支持：
</p>

<table class="data-table">
  <thead>
    <tr>
      <th style="width: 20%;">体系类别</th>
      <th style="width: 38%;">支持平台 / 架构</th>
      <th style="width: 42%;">适配策略与技术保障</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>商用通用系统</strong></td>
      <td>Windows 10 / 11 (x64), macOS (Intel & Apple Silicon M系列)</td>
      <td>原生 Tauri v2 打包，NSIS 便携安装程序，全自动注册系统关联。</td>
    </tr>
    <tr>
      <td><strong>国产信创操作系统</strong></td>
      <td>银河麒麟 (KylinOS V10), 统信 UOS, 中科方德</td>
      <td>提供 <code>.deb</code>、<code>.rpm</code> 原生安装包与沙箱便携 AppImage，完美适配国产桌面环境。</td>
    </tr>
    <tr>
      <td><strong>国产信创硬件架构</strong></td>
      <td>飞腾 (Phytium/ARM64), 鲲鹏 (Kunpeng/ARM64), 龙芯 (LoongArch64), 海光 (x86)</td>
      <td>Rust 核心层支持跨架构源码编译；内嵌 llama.cpp 支持 CPU 纯指令集优化运行。</td>
    </tr>
    <tr>
      <td><strong>移动端与泛终端</strong></td>
      <td>华为鸿蒙 (HarmonyOS), 统信平板, 移动政务终端</td>
      <td>前端集成标准 PWA 离线清单与 Service Worker，支持在断网浏览器内一键固化为本地应用。</td>
    </tr>
  </tbody>
</table>

<div class="card" style="margin-top: 8px;">
  <div class="card-header">信创软硬件全栈闭环验证</div>
  <p>经过实机联调测试，系统在龙芯 3A6000、飞腾 FT-2000+、统信 UOS 桌面操作系统等典型国产信创平台上，均实现了推理调度、矢量 PPT 生成与语音合成的全链路流畅跑通，具备高度实战价值。</p>
</div>

<!-- ==================== 第 11 页：第七章 总结与展望 ==================== -->
<h1 class="section-title">第七章：总结与展望</h1>

<p>
  AI-Client 的诞生，代表着企业级 AI 应用从“依赖外部云端公网的玩具型对话”迈向了<strong>“自主可控、全栈闭环、业务强交付的生产力中枢”</strong>。
</p>
<p>
  它不仅守住了政企高安全场景下<strong>数据资产绝不出域</strong>的底线，更在工程细节上实现了<strong>可自由二次编辑的 DrawingML 原生排版</strong>与<strong>极具现场感和感染力的全离线口播视频生成</strong>。未来，AI-Client 将持续演进端侧多模态视觉感知、离线多智能体协同（Teamwork）以及本地语音双向实时对话等前沿能力，为各行各业的数智化建设筑造坚不可摧、高效敏捷的智能基座。
</p>

<table class="layout-table" style="margin: 10px 0;">
  <tr>
    <td style="width: 33.3%;">
      <div class="card" style="text-align: center;">
        <div class="card-header" style="color: #4f46e5;">支柱一：全离线零泄露</div>
        <p>物理断网闭环，守住政企核心资产与商业机密安全的绝对红线。</p>
      </div>
    </td>
    <td style="width: 33.3%;">
      <div class="card" style="text-align: center;">
        <div class="card-header" style="color: #0284c7;">支柱二：原生矢量强交付</div>
        <p>拒绝死板截图拼贴，DrawingML 语义排版支持自由二次编辑。</p>
      </div>
    </td>
    <td style="width: 33.4%;">
      <div class="card" style="text-align: center;">
        <div class="card-header" style="color: #059669;">支柱三：音画同步全自控</div>
        <p>演说家级生动解说词结合内置神经网络语音与 FFmpeg 毫秒级对齐。</p>
      </div>
    </td>
  </tr>
</table>

<div style="margin-top: 18px; padding: 10px 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; text-align: center; font-size: 8pt; color: #64748b; page-break-inside: avoid; break-inside: avoid;">
  <strong>AI-Client 全离线智能体工作站核心工程组 · 版权所有</strong><br>
  技术白皮书交付路径：<code>docs/whitepaper/ai_client_whitepaper.pdf</code> | 配套演示文稿：<code>docs/whitepaper/ai_client_presentation.pptx</code>
</div>

</body>
</html>
"""
    html_file.write_text(html_content, encoding="utf-8")
    print(f"[Whitepaper] 成功生成出版级 HTML 文档: {html_file.name}")
    return html_file


def compile_html_to_pdf(html_file: Path) -> Path:
    lo = ROOT_DIR / "sidecars/media/libreoffice/program/soffice.exe"
    if not lo.exists():
        lo = ROOT_DIR / "sidecars/media/libreoffice/soffice.exe"
    if not lo.exists():
        raise RuntimeError("未在 sidecars 中找到 LibreOffice 可执行文件")

    profile_dir = OUTPUT_DIR / "lo_prof"
    profile_dir.mkdir(parents=True, exist_ok=True)
    env_arg = f"-env:UserInstallation={profile_dir.resolve().as_uri()}"

    print(f"[Whitepaper] 正在调用内置 LibreOffice 编译高保真矢量 PDF...")
    cmd = [
        str(lo.resolve()),
        "--headless",
        env_arg,
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(OUTPUT_DIR.resolve()),
        str(html_file.resolve()),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise RuntimeError(f"LibreOffice PDF 转换失败 (code {res.returncode}): {res.stderr}")

    pdf_file = OUTPUT_DIR / (html_file.stem + ".pdf")
    if not pdf_file.exists():
        raise RuntimeError(f"PDF 目标文件未找到: {pdf_file}")

    print(f"[Whitepaper] 成功编译高保真矢量 PDF: {pdf_file.name} ({round(pdf_file.stat().st_size / 1024, 1)} KB)")
    return pdf_file


def generate_presentation_deck() -> Path:
    deck_md = """# AI-Client 全离线智能体工作站
面向政企与信创环境的零泄露、开箱即用自主可控生产力中枢

<!-- 口播文案: 各位领导、各位行业同仁，大家下午好！非常荣幸今天能向大家系统汇报《AI-Client 全离线智能体工作站》。在当前大模型席卷全球的浪潮下，很多核心政企与涉密单位都面临着一个两难抉择：既想享受 AI 带来的效能跃升，又苦于公网调用带来的数据出域和失控风险。今天我们带来的 AI-Client，就是为了彻底打破这一僵局。我们做到了物理级纯离线、真正可编辑的 DrawingML 原生排版、以及音画同步口播视频的一站式交付。下面让我们进入正题。 -->

## 核心痛点与时代破局
<!-- 口播文案: 首先让我们直面核心痛点。目前很多团队在尝试引入大模型时，普遍困扰于四座大山：公网 API 随时有泄密红线；开源方案安装配置如同天书；市面上的 PPT 插件生成的居然是不可二次修改的死板图片；而配音视频更是要面对机械念经式的尴尬。面对这些顽疾，屏幕上的这组对比极其鲜明地展示了 AI-Client 的破局之道——我们把所有的计算闭环在用户本机，真正实现零泄露、零门槛与全自主。 -->
- **物理断网零泄露**: 核心数据与思维推理全闭环在本地内存，从根源杜绝数据出域。
- **开箱即用免配置**: 预装 Python、LibreOffice、FFmpeg 与离线语音，双击解压即用。
- **原生 DrawingML 矢量**: 告别图片拼接，所有形状、文本与图表 100% 自由二次编辑。
- **生动现场口播引擎**: 深度解构页面逻辑与业务价值，拒绝机械照读，让宣讲富有感染力。

## 关键核心成效指标
<!-- 口播文案: 衡量一套生产力体系的成色，最有说服力的始终是硬核事实与成效数据。请大家看屏幕上的这组关键指标：从资产安全的百分之百本地闭环，到多步骤复杂任务交付提效三倍以上，这每一项数字背后，都凝结着我们在端侧轻量化推理与工程全流程上的深度打磨。它证明了一件事：在完全物理隔离的环境下，AI 不仅能用，而且能产生立竿见影的颠覆性价值。 -->
- 100% 本地运算，核心资产物理隔离零泄露
- 0 门槛部署，内置附件运行时开箱即用
- 3倍 交付提效，复杂任务分钟级自动化直出
- 100% 矢量可编辑，原生支持 Office 与信创办公套件

## 分层架构与技术矩阵
<!-- 口播文案: 接下来这一页至关重要——我们来看 AI-Client 的底层骨架。一个优秀的系统必须做到动静分离、稳如泰山。我们采用了 Rust 作为整个系统的核心引擎，以单二进制实现任务状态机与 Agent 调度，常驻内存仅需几十兆；外层搭配现代化 React 任务工作台；而底层则通过强大的 Sidecars 附件运行时，无缝纳管了包括 llama.cpp、LibreOffice 和 Piper 语音在内的完整流水线。这种分层设计，赋予了它极强的稳健度与扩展性。 -->
- **Rust 核心执行引擎**: 任务状态机、ReAct 自主 Agent 循环调度与进程沙箱管理。
- **现代化响应式工作台**: 基于 React 18 与 TypeScript，支持 Tauri 桌面壳与移动端 PWA。
- **自动化端侧模型编排**: 自动拉起 llama-server 托管 GGUF，显存自适应按需释放。
- **完整自包含 Sidecars**: 内置 Python 3.10+、LibreOffice、FFmpeg 与 Piper 神经网络语音。

## 独家创新执行体验
<!-- 口播文案: 大家在实际操作智能体时，最头疼的往往是界面被几十行密密麻麻的重复工具调用刷屏，找不着核心结论；或者遇到在线模型余额耗尽时程序直接报错崩溃。AI-Client 在这些交互细节上做了深度的工匠级打磨。我们自研了相同步骤智能合并算法，让日志瞬间清爽；同时开发了人文化异常诊断与离线直出兜底按钮。这些微小而坚实的创新，构成了极致顺滑的生产力体验。 -->
- **相同步骤智能合并**: 同一阶段内连续同名工具操作合二为一，消除多重调用视觉噪音。
- **余额不足人文化诊断**: 智能识别 402/401 错误，提供一键更换密钥与充值指引。
- **免 API 离线直出兜底**: 云端不可用时一键切换内置离线引擎直接生成 PPT，保障应急交付。
- **状态全透明进度追溯**: 实时可视化展示规划中、执行中、已完成与异常各阶段状态。

## 原生 PPT 核心排版体系
<!-- 口播文案: 很多人问我：AI-Client 生成的 PPT 到底好在哪里？大家请看屏幕上的这四项设计准则。第一，我们坚决杜绝文字堆砌，单页严格控制在三到四条要点以内；第二，我们把大字重点和详细阐释彻底解耦，该简介的地方大字醒目，该展开的地方把原理讲透；第三，四宫格、步骤图、对比卡片等现代版式内容感知自适应；第四，完全原生 DrawingML，交付给用户的永远是一份能够随时修改的活文档。 -->
- **单页精简聚焦原则**: 严格控制每页 3~4 条核心要点，杜绝信息过载与疲劳堆砌。
- **大字重点与阐释分层**: 核心标题 4~10 字粗体突出，正文 20~50 字详细介绍机制与成效。
- **语义内容感知版式**: 自适应切换四宫格矩阵、三列立体卡片、双栏对比与流转步骤图。
- **专业多套系主题色彩**: 支持科技靛蓝、碧翠青绿、琥珀金橙、兵工复古红与党建中国红。

## 音画同步全离线口播流水线
<!-- 口播文案: 演示文稿生成之后，我们如何让它变成一部引人入胜的口播视频？大家请看这条严丝合缝的全离线自包含流水线。从 PPTX 导出高清矢量 PDF 开始，PyMuPDF 逐页提取 160DPI 极清帧；与此同时，演讲者备注被送入内置的 Piper 离线神经网络语音引擎，合成富有情感起伏的高保真音频；最后由 FFmpeg 完成音画的毫秒级对齐与转码。全程无需任何外部环境配置，几分钟即可直出成片。 -->
- **步骤 1: 矢量 PDF 导出**: 调用内嵌 LibreOffice Headless 导出高保真矢量 PDF。
- **步骤 2: 逐页极清帧提取**: 使用 PyMuPDF 以 160DPI 超高清栅格化生成幻灯片图像。
- **步骤 3: 离线神经网络语音**: 提取每页专属演讲者备注，通过 Piper 离线合成高清旁白。
- **步骤 4: 音画对齐流媒体合成**: 调用 FFmpeg 毫秒级对齐图片帧与音频，输出专业 MP4 视频。

## 国产信创生态全适配
<!-- 口播文案: 作为面向高安全与政企市场的基石产品，信创生态适配是我们最核心的底色。AI-Client 深度支持包括银河麒麟、统信 UOS 在内的全部主流国产操作系统，并对飞腾、鲲鹏、龙芯 LoongArch 等国产 CPU 架构进行了原生编译优化。无论用户是在传统的 Windows 办公电脑，还是在涉密物理隔离的信创专用终端，AI-Client 都能提供完全一致、开箱即用的卓越体验。 -->
- **国产信创操作系统**: 深度适配银河麒麟 KylinOS V10、统信 UOS 及中科方德。
- **国产 CPU 硬件架构**: 全面支持飞腾 Phytium、华为鲲鹏、龙芯 LoongArch64 与海光。
- **跨平台绿色分发**: 提供 Windows NSIS 便携安装包、Linux deb/rpm/AppImage 及 macOS dmg。
- **鸿蒙终端协同模式**: 前端深度支持离线 PWA 标准，移动平板浏览器即可独立离线安装使用。

## 典型应用落地场景
<!-- 口播文案: 最后，我们来看看 AI-Client 已经在哪些领域发挥了不可替代的作用。在国防军工与涉密单位，它是涉密汇报与研报课件的安全盾牌；在各级党政机关，它是政策宣传、微党课视频的自动化量产流水线；在大型金融与高新技术企业，它是保护核心商业秘密、快速赋能员工培训的高效引擎。一套软件，全面覆盖文案编写、排版美化与视频讲解的全流程闭环。 -->
- **国防军工与涉密汇报**: 零网络依赖与物理隔离保障，内部研报与技术总结秒级成稿。
- **政务党建与政策宣讲**: 自动匹配红色党建视觉主题，一键产出政策解读与微党课视频。
- **企业知识培训与微课**: 自动解析企业内部技术文档，批量生产带旁白音画课件视频。
- **科研院所方案宣讲**: 复杂学术成果与工业技术指标大字图文并茂，提升对外汇报质感。
"""

    md_file = OUTPUT_DIR / "ai_client_presentation.md"
    md_file.write_text(deck_md, encoding="utf-8")
    print(f"[Presentation] 成功写入 PPT 大纲 Markdown: {md_file.name}")

    out_pptx = OUTPUT_DIR / "ai_client_presentation.pptx"
    try:
        quick_markdown_pptx(deck_md, out_pptx)
        print(f"[Presentation] 成功编译高质量 16:9 演示文稿: {out_pptx.name}")
    except PermissionError:
        print(f"[Presentation] 提示: {out_pptx.name} 当前已被外部软件（如 Office/WPS）打开锁定，跳过覆盖，保留现有生成版本。")
    return out_pptx


def main():
    print("=" * 60)
    print("正在启动 AI-Client 技术白皮书与 PPT 演示文稿构建流水线...")
    print("=" * 60)

    html_file = build_whitepaper_html()
    pdf_file = compile_html_to_pdf(html_file)
    pptx_file = generate_presentation_deck()

    print("=" * 60)
    print("🎉 构建流水线全部执行成功！交付物清单：")
    print(f"  1. 白皮书 HTML 源码: {html_file}")
    print(f"  2. 白皮书矢量 PDF:    {pdf_file} ({round(pdf_file.stat().st_size / 1024, 1)} KB)")
    print(f"  3. 介绍大纲 Markdown: {OUTPUT_DIR / 'ai_client_presentation.md'}")
    print(f"  4. 介绍演示 PPTX:     {pptx_file} ({round(pptx_file.stat().st_size / 1024, 1)} KB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
