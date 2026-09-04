#!/usr/bin/env python3
"""Build the Simplified Chinese Splendor rulebook PDF from Markdown."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "RULEBOOK.md"
OUTPUT = ROOT / "output" / "pdf" / "splendor-rulebook-zh-CN.pdf"

INK = colors.HexColor("#20292D")
MUTED = colors.HexColor("#5B686B")
PAPER = colors.HexColor("#F7F3EA")
PAPER_ALT = colors.HexColor("#ECE5D8")
TABLE = colors.HexColor("#173B3A")
TABLE_DARK = colors.HexColor("#102426")
BRASS = colors.HexColor("#B78A3F")
BRASS_LIGHT = colors.HexColor("#E8BD62")
BLUE = colors.HexColor("#3A739A")
GREEN = colors.HexColor("#4E8068")
RED = colors.HexColor("#A8524B")
WHITE = colors.HexColor("#FAF8F2")
GRID = colors.HexColor("#C8BEAD")


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc")),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf")),
        (Path("C:/Windows/Fonts/simsun.ttc"), Path("C:/Windows/Fonts/simsun.ttc")),
        (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        ),
    ]
    for regular, bold in candidates:
        if not regular.is_file() or not bold.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont("SplendorCJK", str(regular), subfontIndex=0))
            pdfmetrics.registerFont(TTFont("SplendorCJKBold", str(bold), subfontIndex=0))
            pdfmetrics.registerFontFamily(
                "SplendorCJK",
                normal="SplendorCJK",
                bold="SplendorCJKBold",
                italic="SplendorCJK",
                boldItalic="SplendorCJKBold",
            )
            return "SplendorCJK", "SplendorCJKBold"
        except Exception:
            continue
    raise RuntimeError("No usable Chinese TrueType/OpenType font was found.")


FONT, FONT_BOLD = register_fonts()


def inline_markup(value: str) -> str:
    escaped = html.escape(value.strip(), quote=False)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda match: f'<a href="{match.group(2)}" color="#2D6E83"><u>{match.group(1)}</u></a>',
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", rf'<font name="{FONT_BOLD}" color="#8C5533">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


class GemNetwork(Flowable):
    """Original abstract gem-and-engine motif for the cover."""

    def __init__(self, width: float, height: float) -> None:
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        width, height = self.width, self.height
        canvas.saveState()
        nodes = [
            (0.10, 0.30, colors.HexColor("#E8E3D8"), "W"),
            (0.28, 0.67, BLUE, "B"),
            (0.50, 0.37, GREEN, "G"),
            (0.70, 0.72, RED, "R"),
            (0.90, 0.34, colors.HexColor("#353A3D"), "K"),
        ]
        canvas.setLineCap(1)
        for index in range(len(nodes) - 1):
            x1, y1, _, _ = nodes[index]
            x2, y2, _, _ = nodes[index + 1]
            canvas.setStrokeColor(colors.HexColor("#496866"))
            canvas.setLineWidth(10)
            canvas.line(x1 * width, y1 * height, x2 * width, y2 * height)
            canvas.setStrokeColor(BRASS_LIGHT)
            canvas.setLineWidth(2)
            canvas.line(x1 * width, y1 * height, x2 * width, y2 * height)
        for x, y, fill, symbol in nodes:
            cx, cy = x * width, y * height
            canvas.setFillColor(fill)
            canvas.setStrokeColor(BRASS_LIGHT)
            canvas.setLineWidth(2.3)
            canvas.circle(cx, cy, 18, fill=1, stroke=1)
            canvas.setFillColor(TABLE_DARK if fill != colors.HexColor("#353A3D") else WHITE)
            canvas.setFont(FONT_BOLD, 15)
            canvas.drawCentredString(cx, cy - 5, symbol)
        canvas.setFillColor(BRASS)
        canvas.setStrokeColor(BRASS_LIGHT)
        canvas.circle(width * 0.50, height * 0.37, 8, fill=1, stroke=0)
        canvas.restoreState()


class RulebookTemplate(BaseDocTemplate):
    def __init__(self, filename: str) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=17 * mm,
            title="《璀璨宝石》规则说明书",
            author="game-hall 非官方数字化建模包",
            subject="Splendor 2024 十周年新版基础规则原创中文摘要",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="content",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="rulebook", frames=[frame], onPage=draw_page))
        self.heading_index = 0

    def beforeDocument(self) -> None:
        self.heading_index = 0

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        if flowable.style.name not in {"RuleH1", "RuleH2"}:
            return
        level = 0 if flowable.style.name == "RuleH1" else 1
        label = flowable.getPlainText()
        key = f"heading-{self.heading_index}"
        self.heading_index += 1
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(label, key, level=level, closed=False)
        self.notify("TOCEntry", (level, label, self.page, key))


def draw_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setTitle("《璀璨宝石》规则说明书")
    canvas.setAuthor("game-hall 非官方数字化建模包")
    if doc.page == 1:
        canvas.setFillColor(TABLE_DARK)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(TABLE)
        canvas.circle(width + 18 * mm, height - 28 * mm, 64 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#16302F"))
        canvas.circle(-14 * mm, 20 * mm, 60 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(BRASS)
        canvas.setLineWidth(1.4)
        canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(colors.HexColor("#BFCAC8"))
        canvas.drawString(18 * mm, 9.5 * mm, "NON-OFFICIAL · ORIGINAL RULE SUMMARY · v1.0")
    else:
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(TABLE)
        canvas.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
        canvas.setFont(FONT_BOLD, 7.5)
        canvas.setFillColor(WHITE)
        canvas.drawString(18 * mm, height - 5.8 * mm, "璀璨宝石 · 2024 十周年新版基础规则")
        canvas.setStrokeColor(BRASS)
        canvas.setLineWidth(0.8)
        canvas.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
        canvas.setFont(FONT, 7.3)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 7.5 * mm, "非官方数字化整理稿 · 不含扩展与官方美术")
        canvas.drawRightString(width - 18 * mm, 7.5 * mm, f"第 {doc.page - 1} 页")
    canvas.restoreState()


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle("CoverKicker", parent=base["Normal"], fontName=FONT_BOLD, fontSize=9.5, leading=14, textColor=colors.HexColor("#BFD0CD"), spaceAfter=8),
        "cover_title": ParagraphStyle("CoverTitle", parent=base["Title"], fontName=FONT_BOLD, fontSize=36, leading=45, alignment=TA_LEFT, textColor=WHITE, spaceAfter=6),
        "cover_subtitle": ParagraphStyle("CoverSubtitle", parent=base["Normal"], fontName=FONT, fontSize=12.5, leading=19, textColor=colors.HexColor("#D7E0DE")),
        "cover_meta": ParagraphStyle("CoverMeta", parent=base["Normal"], fontName=FONT, fontSize=8.8, leading=13.5, textColor=colors.HexColor("#DFE5E2"), alignment=TA_CENTER),
        "h1": ParagraphStyle("RuleH1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=15.5, leading=21, textColor=TABLE, spaceBefore=10, spaceAfter=6, keepWithNext=True),
        "h2": ParagraphStyle("RuleH2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=11.3, leading=16, textColor=BLUE, spaceBefore=7, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("RuleBody", parent=base["BodyText"], fontName=FONT, fontSize=9.0, leading=14.5, textColor=INK, spaceAfter=5, wordWrap="CJK", allowWidows=0, allowOrphans=0),
        "list": ParagraphStyle("RuleList", parent=base["BodyText"], fontName=FONT, fontSize=8.8, leading=14, textColor=INK, spaceAfter=1.5, wordWrap="CJK"),
        "table": ParagraphStyle("RuleTable", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11.3, textColor=INK, wordWrap="CJK"),
        "table_header": ParagraphStyle("RuleTableHeader", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=7.7, leading=11.2, textColor=WHITE, wordWrap="CJK"),
        "callout": ParagraphStyle("RuleCallout", parent=base["BodyText"], fontName=FONT, fontSize=8.5, leading=13.5, textColor=INK, wordWrap="CJK"),
        "toc_heading": ParagraphStyle("TocHeading", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=22, leading=28, textColor=TABLE, spaceAfter=12),
        "toc0": ParagraphStyle("TOC0", parent=base["Normal"], fontName=FONT, fontSize=9.2, leading=15, leftIndent=0, firstLineIndent=0, textColor=INK),
        "toc1": ParagraphStyle("TOC1", parent=base["Normal"], fontName=FONT, fontSize=8.2, leading=12.5, leftIndent=12, firstLineIndent=0, textColor=MUTED),
    }


def cover_story(styles: dict[str, ParagraphStyle], width: float) -> list[Flowable]:
    stats = Table(
        [[
            Paragraph("<b>2-4</b><br/><font size=7>玩家</font>", styles["cover_meta"]),
            Paragraph("<b>30</b><br/><font size=7>分钟</font>", styles["cover_meta"]),
            Paragraph("<b>90</b><br/><font size=7>发展卡</font>", styles["cover_meta"]),
            Paragraph("<b>15</b><br/><font size=7>终局分</font>", styles["cover_meta"]),
        ]],
        colWidths=[width / 4] * 4,
        rowHeights=[18 * mm],
    )
    stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A3434")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#496866")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#496866")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [
        Spacer(1, 19 * mm),
        Paragraph("GAME HALL · DIGITAL DESIGN DOSSIER", styles["cover_kicker"]),
        Paragraph("《璀璨宝石》<br/>规则说明书", styles["cover_title"]),
        Paragraph("Splendor 基础游戏<br/>2024 十周年新版 · 简体中文整理稿", styles["cover_subtitle"]),
        Spacer(1, 9 * mm),
        GemNetwork(width, 64 * mm),
        Spacer(1, 6 * mm),
        stats,
        Spacer(1, 8 * mm),
        Paragraph("完整准备 · 四种行动 · 精确黄金支付 · 贵族拜访 · 最终轮<br/>依据当前官方规则重新组织；不包含扩展、官方美术或可印刷复刻组件。", styles["cover_meta"]),
        PageBreak(),
    ]


def toc_story(styles: dict[str, ParagraphStyle], width: float) -> list[Flowable]:
    quick = Table(
        [
            [Paragraph("每回合", styles["table_header"]), Paragraph("资源限制", styles["table_header"]), Paragraph("终局", styles["table_header"])],
            [Paragraph("四项主要行动中选一项", styles["table"]), Paragraph("棋子回合末 ≤ 10；保留牌 ≤ 3", styles["table"]), Paragraph("回合末达到 15 分，完成当前轮", styles["table"])],
        ],
        colWidths=[width / 3] * 3,
    )
    quick.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER_ALT]),
        ("BOX", (0, 0), (-1, -1), 0.7, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    toc = TableOfContents()
    toc.levelStyles = [styles["toc0"], styles["toc1"]]
    return [
        Paragraph("目录与速查", styles["toc_heading"]),
        Paragraph("本说明先介绍组件与准备，再逐项解释回合行动、支付、贵族和最终轮，最后给出示例、常见疑问与数字版信息边界。", styles["body"]),
        Spacer(1, 2 * mm),
        quick,
        Spacer(1, 7 * mm),
        toc,
        PageBreak(),
    ]


def list_flowable(items: list[str], ordered: bool, styles: dict[str, ParagraphStyle]) -> Flowable:
    children = [ListItem(Paragraph(inline_markup(item), styles["list"]), leftIndent=7) for item in items]
    options = {
        "bulletType": "1" if ordered else "bullet",
        "leftIndent": 16,
        "bulletFontName": FONT_BOLD,
        "bulletFontSize": 8.3,
        "bulletColor": BRASS if ordered else BLUE,
        "spaceAfter": 5,
    }
    if ordered:
        options["start"] = 1
    else:
        options["bulletChar"] = "•"
    return ListFlowable(children, **options)


def table_flowable(rows: list[list[str]], styles: dict[str, ParagraphStyle], width: float) -> Flowable:
    column_count = len(rows[0])
    prepared = []
    for row_index, row in enumerate(rows):
        style = styles["table_header"] if row_index == 0 else styles["table"]
        prepared.append([Paragraph(inline_markup(cell), style) for cell in row])
    if column_count == 2:
        widths = [width * 0.28, width * 0.72]
    elif column_count == 3:
        widths = [width * 0.34, width * 0.33, width * 0.33]
    elif column_count == 4:
        widths = [width * 0.31, width * 0.17, width * 0.17, width * 0.35]
    else:
        widths = [width / column_count] * column_count
    table = LongTable(prepared, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER_ALT]),
        ("BOX", (0, 0), (-1, -1), 0.7, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return KeepTogether([table, Spacer(1, 5)]) if len(rows) <= 5 else table


def callout_flowable(text: str, styles: dict[str, ParagraphStyle], width: float) -> Flowable:
    marker = Paragraph("说明", ParagraphStyle("CalloutMarker", parent=styles["table_header"], alignment=TA_CENTER))
    body = Paragraph(inline_markup(text), styles["callout"])
    table = Table([[marker, body]], colWidths=[17 * mm, width - 17 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BRASS),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F0E8D6")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBB88C")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return KeepTogether([table, Spacer(1, 5)])


def markdown_story(source: str, styles: dict[str, ParagraphStyle], width: float) -> list[Flowable]:
    lines = source.splitlines()
    story: list[Flowable] = []
    index = 0
    skipped_title = False
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("# ") and not skipped_title:
            skipped_title = True
            index += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), styles["h1"]))
            index += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), styles["h2"]))
            index += 1
            continue
        if stripped.startswith(">"):
            quotes = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                value = lines[index].strip()[1:].strip()
                if value:
                    quotes.append(value)
                index += 1
            if quotes:
                story.append(callout_flowable(" · ".join(quotes), styles, width))
            continue
        if stripped.startswith("|"):
            raw_rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                raw_rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            rows = [row for row in raw_rows if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)]
            story.append(table_flowable(rows, styles, width))
            continue
        unordered = re.match(r"^-\s+(.+)$", stripped)
        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if unordered or ordered:
            is_ordered = ordered is not None
            pattern = r"^\d+\.\s+(.+)$" if is_ordered else r"^-\s+(.+)$"
            items = []
            while index < len(lines):
                match = re.match(pattern, lines[index].strip())
                if not match:
                    break
                items.append(match.group(1))
                index += 1
            story.append(list_flowable(items, is_ordered, styles))
            continue
        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if candidate.startswith(("#", ">", "|", "- ")) or re.match(r"^\d+\.\s+", candidate):
                break
            paragraph_lines.append(candidate)
            index += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), styles["body"]))
    return story


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    document = RulebookTemplate(str(OUTPUT))
    story: list[Flowable] = []
    story.extend(cover_story(styles, document.width))
    story.extend(toc_story(styles, document.width))
    story.extend(markdown_story(SOURCE.read_text(encoding="utf-8"), styles, document.width))
    document.multiBuild(story)
    return OUTPUT


if __name__ == "__main__":
    result = build()
    print(f"Built rulebook PDF: {result}")
