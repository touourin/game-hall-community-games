#!/usr/bin/env python3
"""Build the Simplified Chinese rulebook PDF from docs/RULEBOOK.md."""

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
OUTPUT = ROOT / "output" / "pdf" / "ticket-to-ride-europe-rulebook-zh-CN.pdf"

INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#586674")
PAPER = colors.HexColor("#F8F4EA")
PAPER_DARK = colors.HexColor("#EEE5D4")
NAVY = colors.HexColor("#142533")
BLUE = colors.HexColor("#2E7085")
GOLD = colors.HexColor("#BD8E42")
RED = colors.HexColor("#A85248")
GREEN = colors.HexColor("#477665")
WHITE = colors.HexColor("#FAF7F0")
GRID = colors.HexColor("#CBC1AF")


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc")),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf")),
        (Path("C:/Windows/Fonts/simsun.ttc"), Path("C:/Windows/Fonts/simsun.ttc")),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")),
    ]
    for regular_path, bold_path in candidates:
        if not regular_path.is_file() or not bold_path.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont("RulebookCJK", str(regular_path), subfontIndex=0))
            pdfmetrics.registerFont(TTFont("RulebookCJKBold", str(bold_path), subfontIndex=0))
            pdfmetrics.registerFontFamily(
                "RulebookCJK",
                normal="RulebookCJK",
                bold="RulebookCJKBold",
                italic="RulebookCJK",
                boldItalic="RulebookCJKBold",
            )
            return "RulebookCJK", "RulebookCJKBold"
        except Exception:
            continue
    raise RuntimeError("No usable Chinese TrueType/OpenType font was found.")


FONT, FONT_BOLD = register_fonts()


def inline_markup(text: str) -> str:
    escaped = html.escape(text.strip(), quote=False)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda match: f'<a href="{match.group(2)}" color="#2E7085"><u>{match.group(1)}</u></a>',
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", r'<font name="RulebookCJKBold" color="#8C4C43">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


class RouteMark(Flowable):
    """Original abstract railway motif for the cover."""

    def __init__(self, width: float, height: float = 80 * mm) -> None:
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        w, h = self.width, self.height
        canvas.saveState()
        canvas.setLineCap(1)
        routes = [
            ((0.03, 0.18), (0.25, 0.56), (0.47, 0.42), GOLD),
            ((0.18, 0.84), (0.43, 0.62), (0.68, 0.76), BLUE),
            ((0.47, 0.42), (0.70, 0.30), (0.95, 0.56), RED),
            ((0.25, 0.56), (0.55, 0.88), (0.86, 0.84), GREEN),
        ]
        points: set[tuple[float, float]] = set()
        for start, middle, end, color in routes:
            points.update((start, middle, end))
            canvas.setStrokeColor(colors.HexColor("#0B1720"))
            canvas.setLineWidth(13)
            canvas.line(start[0] * w, start[1] * h, middle[0] * w, middle[1] * h)
            canvas.line(middle[0] * w, middle[1] * h, end[0] * w, end[1] * h)
            canvas.setStrokeColor(color)
            canvas.setLineWidth(6)
            canvas.line(start[0] * w, start[1] * h, middle[0] * w, middle[1] * h)
            canvas.line(middle[0] * w, middle[1] * h, end[0] * w, end[1] * h)
        for x, y in points:
            canvas.setFillColor(PAPER)
            canvas.setStrokeColor(NAVY)
            canvas.setLineWidth(2.2)
            canvas.circle(x * w, y * h, 5.2, fill=1, stroke=1)

        # A compact, geometric locomotive silhouette; deliberately not tied to official art.
        tx, ty = w * 0.58, h * 0.49
        canvas.setFillColor(colors.HexColor("#0C1821"))
        canvas.roundRect(tx, ty, 62, 27, 5, fill=1, stroke=0)
        canvas.rect(tx + 39, ty + 18, 18, 20, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(tx + 43, ty + 23, 10, 9, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#0C1821"))
        canvas.circle(tx + 15, ty - 1, 8, fill=1, stroke=0)
        canvas.circle(tx + 49, ty - 1, 8, fill=1, stroke=0)
        canvas.restoreState()


class RulebookDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=17 * mm,
            title="《欧洲车票之旅》规则说明书",
            author="game-hall 非官方数字化设计包",
            subject="Ticket to Ride: Europe 基础规则原创摘要与数字化边界",
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
        self._heading_index = 0

    def beforeDocument(self) -> None:
        # multiBuild runs more than one pass; bookmark identifiers must stay stable.
        self._heading_index = 0

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        if flowable.style.name not in {"RBHeading1", "RBHeading2"}:
            return
        level = 0 if flowable.style.name == "RBHeading1" else 1
        text = flowable.getPlainText()
        key = f"heading-{self._heading_index}"
        self._heading_index += 1
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


def draw_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setTitle("《欧洲车票之旅》规则说明书")
    canvas.setAuthor("game-hall 非官方数字化设计包")
    if doc.page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(BLUE)
        canvas.circle(width + 12 * mm, height - 26 * mm, 58 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#1C3545"))
        canvas.circle(-17 * mm, 18 * mm, 55 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(2)
        canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(colors.HexColor("#C7D0D4"))
        canvas.drawString(18 * mm, 9.5 * mm, "NON-OFFICIAL · ORIGINAL RULE SUMMARY · v1.0")
    else:
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
        canvas.setFont(FONT_BOLD, 7.4)
        canvas.setFillColor(WHITE)
        canvas.drawString(18 * mm, height - 5.8 * mm, "欧洲车票之旅 · 基础版规则说明")
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.8)
        canvas.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 7.5 * mm, "非官方数字化整理稿 · 不含扩展与官方美术")
        canvas.drawRightString(width - 18 * mm, 7.5 * mm, f"第 {doc.page - 1} 页")
    canvas.restoreState()


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "CoverKicker",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#BFD3DB"),
            spaceAfter=8,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=34,
            leading=43,
            alignment=TA_LEFT,
            textColor=WHITE,
            spaceAfter=6,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=12.5,
            leading=19,
            textColor=colors.HexColor("#D6E0E3"),
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#DFE5E6"),
            alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "RBTitle",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=28,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "RBHeading1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=16,
            leading=21,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "RBHeading2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=11.5,
            leading=16,
            textColor=BLUE,
            spaceBefore=7,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "RBBody",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.1,
            leading=14.7,
            textColor=INK,
            spaceAfter=5,
            wordWrap="CJK",
            allowWidows=0,
            allowOrphans=0,
        ),
        "list": ParagraphStyle(
            "RBList",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.9,
            leading=14.2,
            textColor=INK,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=1.8,
            wordWrap="CJK",
        ),
        "table": ParagraphStyle(
            "RBTable",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=7.9,
            leading=11.8,
            textColor=INK,
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "RBTableHeader",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=8,
            leading=11.5,
            textColor=WHITE,
            wordWrap="CJK",
        ),
        "callout": ParagraphStyle(
            "RBCallout",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.6,
            leading=13.5,
            textColor=INK,
            wordWrap="CJK",
        ),
        "toc_heading": ParagraphStyle(
            "TOCHeading",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=28,
            textColor=NAVY,
            spaceAfter=12,
        ),
        "toc0": ParagraphStyle(
            "TOC0",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=9.4,
            leading=16,
            leftIndent=0,
            firstLineIndent=0,
            textColor=INK,
        ),
        "toc1": ParagraphStyle(
            "TOC1",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=8.3,
            leading=13,
            leftIndent=12,
            firstLineIndent=0,
            textColor=MUTED,
        ),
    }


def cover_story(styles: dict[str, ParagraphStyle], content_width: float) -> list[Flowable]:
    stats = Table(
        [
            [
                Paragraph("<b>2–5</b><br/><font size=7>玩家</font>", styles["cover_meta"]),
                Paragraph("<b>30–60</b><br/><font size=7>分钟</font>", styles["cover_meta"]),
                Paragraph("<b>47</b><br/><font size=7>城市</font>", styles["cover_meta"]),
                Paragraph("<b>101</b><br/><font size=7>轨道</font>", styles["cover_meta"]),
            ]
        ],
        colWidths=[content_width / 4] * 4,
        rowHeights=[18 * mm],
    )
    stats.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1D3544")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#426171")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#426171")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return [
        Spacer(1, 22 * mm),
        Paragraph("GAME-HALL · DIGITAL DESIGN DOSSIER", styles["cover_kicker"]),
        Paragraph("《欧洲车票之旅》<br/>规则说明书", styles["cover_title"]),
        Paragraph("Ticket to Ride: Europe 基础版<br/>简体中文数字化整理稿 · v1.0", styles["cover_subtitle"]),
        Spacer(1, 9 * mm),
        RouteMark(content_width, 69 * mm),
        Spacer(1, 5 * mm),
        stats,
        Spacer(1, 8 * mm),
        Paragraph(
            "规则讲解 · 特殊线路 · 终局计分 · 数字版公开信息边界<br/>"
            "依据官方规则整理；本文件为非官方原创摘要，不包含官方美术或可印刷仿制组件。",
            styles["cover_meta"],
        ),
        PageBreak(),
    ]


def toc_story(styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    toc = TableOfContents()
    toc.levelStyles = [styles["toc0"], styles["toc1"]]
    quick = Table(
        [
            [Paragraph("回合只能选一项", styles["table_header"]), Paragraph("终局触发", styles["table_header"]), Paragraph("核心奖励", styles["table_header"])],
            [Paragraph("抽车票 / 占轨 / 抽任务 / 建站", styles["table"]), Paragraph("回合末剩余车厢 ≤ 2", styles["table"]), Paragraph("最长路线 +10；未建站每座 +4", styles["table"])],
        ],
        colWidths=[55 * mm, 55 * mm, 55 * mm],
    )
    quick.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, GRID),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [
        Paragraph("目录与速查", styles["toc_heading"]),
        Paragraph("这份说明书先讲完整流程，再分别解释双线、渡轮、隧道与火车站，最后给出计分、同分和隐藏信息规则。", styles["body"]),
        Spacer(1, 3 * mm),
        quick,
        Spacer(1, 7 * mm),
        toc,
        PageBreak(),
    ]


def list_flowable(items: list[str], ordered: bool, styles: dict[str, ParagraphStyle]) -> Flowable:
    bullet_type = "1" if ordered else "bullet"
    children = [ListItem(Paragraph(inline_markup(item), styles["list"]), leftIndent=7) for item in items]
    options = {
        "bulletType": bullet_type,
        "leftIndent": 16,
        "bulletFontName": FONT_BOLD,
        "bulletFontSize": 8.5,
        "bulletColor": RED if ordered else BLUE,
        "spaceAfter": 5,
    }
    if ordered:
        options["start"] = 1
    else:
        options["bulletChar"] = "•"
    return ListFlowable(
        children,
        **options,
    )


def table_flowable(rows: list[list[str]], styles: dict[str, ParagraphStyle], content_width: float) -> Flowable:
    if not rows:
        return Spacer(1, 0)
    column_count = len(rows[0])
    prepared: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        cell_style = styles["table_header"] if row_index == 0 else styles["table"]
        prepared.append([Paragraph(inline_markup(cell), cell_style) for cell in row])
    if column_count == 2:
        first_ratio = 0.32
        col_widths = [content_width * first_ratio, content_width * (1 - first_ratio)]
    else:
        col_widths = [content_width / column_count] * column_count
    table = LongTable(prepared, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER_DARK]),
                ("BOX", (0, 0), (-1, -1), 0.7, GRID),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
            ]
        )
    )
    return KeepTogether([table, Spacer(1, 5)]) if len(rows) <= 5 else table


def callout_flowable(text: str, styles: dict[str, ParagraphStyle], content_width: float) -> Flowable:
    marker = Paragraph("提示", ParagraphStyle("CalloutMarker", parent=styles["table_header"], alignment=TA_CENTER))
    body = Paragraph(inline_markup(text), styles["callout"])
    table = Table([[marker, body]], colWidths=[16 * mm, content_width - 16 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), BLUE),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#E7EFF1")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#A8BEC5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return KeepTogether([table, Spacer(1, 5)])


def markdown_story(text: str, styles: dict[str, ParagraphStyle], content_width: float) -> list[Flowable]:
    lines = text.splitlines()
    story: list[Flowable] = []
    index = 0
    # The title and two subtitle quote lines are represented on the cover.
    while index < len(lines) and (not lines[index].strip() or lines[index].startswith("# ") or lines[index].startswith("> ")):
        index += 1

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
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
        if stripped.startswith("> "):
            quotes: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("> "):
                quotes.append(lines[index].strip()[2:].rstrip("  "))
                index += 1
            story.append(callout_flowable(" ".join(quotes), styles, content_width))
            continue
        if stripped.startswith("| "):
            raw_rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                raw_rows.append(cells)
                index += 1
            rows = [row for row in raw_rows if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)]
            story.append(table_flowable(rows, styles, content_width))
            continue
        unordered = re.match(r"^-\s+(.+)$", stripped)
        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if unordered or ordered:
            items: list[str] = []
            list_is_ordered = ordered is not None
            pattern = r"^\d+\.\s+(.+)$" if list_is_ordered else r"^-\s+(.+)$"
            while index < len(lines):
                match = re.match(pattern, lines[index].strip())
                if not match:
                    break
                items.append(match.group(1))
                index += 1
            story.append(list_flowable(items, list_is_ordered, styles))
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
    doc = RulebookDocTemplate(str(OUTPUT))
    story: list[Flowable] = []
    story.extend(cover_story(styles, doc.width))
    story.extend(toc_story(styles))
    story.extend(markdown_story(SOURCE.read_text(encoding="utf-8"), styles, doc.width))
    doc.multiBuild(story)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Built rulebook PDF: {path}")
