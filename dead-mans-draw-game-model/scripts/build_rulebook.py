#!/usr/bin/env python3
"""Build the Chinese Dead Man's Draw rulebook PDF from docs/RULEBOOK.md."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "RULEBOOK.md"
OUTPUT = ROOT / "output" / "pdf" / "dead-mans-draw-rulebook-zh-CN.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 17 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

INK = colors.HexColor("#1E2928")
MUTED = colors.HexColor("#66716D")
PAPER = colors.HexColor("#F7F1E5")
PANEL = colors.HexColor("#EDE2CE")
LINE = colors.HexColor("#C7B58E")
SEA = colors.HexColor("#173B3A")
SEA_LIGHT = colors.HexColor("#4F7F78")
BRASS = colors.HexColor("#B28A4A")
DANGER = colors.HexColor("#A3473D")
WHITE = colors.HexColor("#FFF9EA")


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc"), 0),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf"), 0),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"), 0),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"), Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf"), 0),
    ]
    for normal_path, bold_path, index in candidates:
        if normal_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont("DmdSans", str(normal_path), subfontIndex=index))
            pdfmetrics.registerFont(TTFont("DmdSans-Bold", str(bold_path), subfontIndex=index))
            pdfmetrics.registerFontFamily(
                "DmdSans",
                normal="DmdSans",
                bold="DmdSans-Bold",
                italic="DmdSans",
                boldItalic="DmdSans-Bold",
            )
            return "DmdSans", "DmdSans-Bold"
    raise RuntimeError("No Chinese font found. Install Microsoft YaHei, SimHei, or Noto Sans CJK.")


FONT, FONT_BOLD = register_fonts()


def normalize_pdf_text(text: str) -> str:
    return (
        text.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )


class TableDiagram(Flowable):
    """Original compact table scene for the cover."""

    def __init__(self, width: float, height: float = 215):
        super().__init__()
        self.width = width
        self.height = height

    def draw_card(self, canvas: Canvas, x: float, y: float, label: str, value: int, color: colors.Color, protected: bool = False) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#F6E9CF"))
        canvas.setStrokeColor(BRASS if protected else colors.HexColor("#C9B489"))
        canvas.setLineWidth(2 if protected else 1)
        canvas.roundRect(x, y, 42, 60, 6, fill=1, stroke=1)
        canvas.setFillColor(color)
        canvas.roundRect(x + 4, y + 36, 34, 20, 4, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 10)
        canvas.drawString(x + 8, y + 42, str(value))
        canvas.setFillColor(INK)
        canvas.setFont(FONT_BOLD, 7.2)
        canvas.drawCentredString(x + 21, y + 13, label)
        if protected:
            canvas.setFillColor(SEA_LIGHT)
            canvas.circle(x + 35, y + 52, 6, fill=1, stroke=0)
            canvas.setFillColor(WHITE)
            canvas.setFont(FONT_BOLD, 6)
            canvas.drawCentredString(x + 35, y + 50, "保")
        canvas.restoreState()

    def draw_player(self, canvas: Canvas, x: float, y: float, label: str, score: int) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#153332"))
        canvas.setStrokeColor(colors.HexColor("#52736E"))
        canvas.roundRect(x, y, 96, 32, 8, fill=1, stroke=1)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawString(x + 9, y + 12, label)
        canvas.setFillColor(colors.HexColor("#F2C96D"))
        canvas.setFont(FONT_BOLD, 11)
        canvas.drawRightString(x + 87, y + 11, str(score))
        canvas.restoreState()

    def draw(self) -> None:
        canvas = self.canv
        width, height = self.width, self.height
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#102829"))
        canvas.roundRect(0, 0, width, height, 14, fill=1, stroke=0)
        canvas.setFillColor(SEA)
        canvas.setStrokeColor(colors.HexColor("#42635F"))
        canvas.setLineWidth(2)
        canvas.roundRect(12, 12, width - 24, height - 24, 28, fill=1, stroke=1)

        self.draw_player(canvas, width / 2 - 48, height - 47, "白露", 13)
        self.draw_player(canvas, 27, height / 2 - 16, "青禾", 18)
        self.draw_player(canvas, width - 123, height / 2 - 16, "赤岩", 14)
        self.draw_player(canvas, width / 2 - 48, 22, "你 · 阿岚", 13)

        labels = [
            ("炮", 6, colors.HexColor("#9D4B3D"), True),
            ("锚", 5, colors.HexColor("#2E7480"), False),
            ("图", 4, colors.HexColor("#53744E"), False),
            ("怪", 3, colors.HexColor("#345B58"), False),
            ("鱼", 8, colors.HexColor("#985173"), False),
        ]
        start_x = width / 2 - (len(labels) * 48 - 6) / 2
        for index, (label, value, color, protected) in enumerate(labels):
            self.draw_card(canvas, start_x + index * 48, height / 2 - 28, label, value, color, protected)

        canvas.setFillColor(colors.HexColor("#203F3E"))
        canvas.roundRect(width / 2 - 112, 61, 224, 26, 9, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT, 7.5)
        canvas.drawCentredString(width / 2, 71, "爆牌花色：炮 · 锚 · 图 · 怪 · 鱼")
        canvas.setFillColor(DANGER)
        canvas.roundRect(width / 2 + 66, 64, 37, 20, 8, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 6.6)
        canvas.drawCentredString(width / 2 + 84.5, 71, "海怪 1")
        canvas.restoreState()


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_eyebrow": ParagraphStyle("cover_eyebrow", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=12, textColor=SEA_LIGHT, spaceAfter=5),
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontName=FONT_BOLD, fontSize=28, leading=35, textColor=SEA, alignment=TA_LEFT, spaceAfter=7, wordWrap="CJK"),
        "cover_subtitle": ParagraphStyle("cover_subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=17, textColor=MUTED, spaceAfter=13, wordWrap="CJK"),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=16, leading=22, textColor=SEA, spaceBefore=8, spaceAfter=7, keepWithNext=True, wordWrap="CJK"),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=11.7, leading=16, textColor=colors.HexColor("#32645F"), spaceBefore=6, spaceAfter=4, keepWithNext=True, wordWrap="CJK"),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName=FONT_BOLD, fontSize=10.2, leading=14.5, textColor=DANGER, spaceBefore=5, spaceAfter=3, keepWithNext=True, wordWrap="CJK"),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=8.9, leading=13.8, textColor=INK, spaceAfter=5, wordWrap="CJK"),
        "bullet": ParagraphStyle("bullet", parent=base["BodyText"], fontName=FONT, fontSize=8.8, leading=13.3, textColor=INK, leftIndent=12, firstLineIndent=-9, bulletIndent=0, spaceAfter=2.5, wordWrap="CJK"),
        "number": ParagraphStyle("number", parent=base["BodyText"], fontName=FONT, fontSize=8.8, leading=13.3, textColor=INK, leftIndent=17, firstLineIndent=-17, spaceAfter=2.5, wordWrap="CJK"),
        "quote": ParagraphStyle("quote", parent=base["BodyText"], fontName=FONT, fontSize=8.7, leading=13.7, textColor=colors.HexColor("#3A4A46"), backColor=PANEL, borderColor=BRASS, borderWidth=0, borderPadding=(7, 9, 7, 9), spaceAfter=7, wordWrap="CJK"),
        "code": ParagraphStyle("code", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=8.2, leading=12.5, textColor=WHITE, backColor=SEA, borderPadding=(7, 9, 7, 9), alignment=TA_CENTER, spaceAfter=7, wordWrap="CJK"),
        "table_header": ParagraphStyle("table_header", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.5, leading=10.6, textColor=WHITE, wordWrap="CJK"),
        "table_cell": ParagraphStyle("table_cell", parent=base["Normal"], fontName=FONT, fontSize=7.4, leading=10.7, textColor=INK, wordWrap="CJK"),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName=FONT, fontSize=7.2, leading=10.5, textColor=MUTED, wordWrap="CJK"),
    }


STYLES = build_styles()


def inline_markup(text: str) -> str:
    normalized = normalize_pdf_text(text.strip())
    escaped = html.escape(normalized, quote=False)
    http_link = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
    escaped = http_link.sub(lambda match: f'<link href="{html.escape(match.group(2), quote=True)}" color="#32645F"><u>{match.group(1)}</u></link>', escaped)
    local_link = re.compile(r"\[([^\]]+)\]\((?!https?://)[^)]+\)")
    escaped = local_link.sub(lambda match: f"<u>{match.group(1)}</u>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", r'<font color="#9A493E"><b>\1</b></font>', escaped)
    return escaped


def text_weight(value: str) -> float:
    return max(2.0, sum(1.0 if ord(char) > 127 else 0.55 for char in value))


def make_table(rows: list[list[str]]) -> Table:
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    weights = [max(text_weight(row[column]) for row in normalized) for column in range(column_count)]
    minimum = 17 * mm
    widths = [max(minimum, CONTENT_WIDTH * weight / sum(weights)) for weight in weights]
    scale = CONTENT_WIDTH / sum(widths)
    widths = [value * scale for value in widths]
    data = []
    for row_index, row in enumerate(normalized):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table_cell"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SEA),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F4ECDE"), colors.HexColor("#EBE0CC")]),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
        index += 1
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
        rows.pop(1)
    return rows, index


def markdown_story(markdown: str) -> list[Flowable]:
    lines = markdown.splitlines()
    story: list[Flowable] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped == "<!-- PAGE BREAK -->":
            story.append(PageBreak())
            index += 1
            continue
        if stripped.startswith("# "):
            index += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), STYLES["h1"]))
            story.append(HRFlowable(width="100%", thickness=0.55, color=LINE, spaceAfter=5))
            index += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), STYLES["h2"]))
            index += 1
            continue
        if stripped.startswith("#### "):
            story.append(Paragraph(inline_markup(stripped[5:]), STYLES["h3"]))
            index += 1
            continue
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                content = lines[index].strip()[1:].strip()
                if content:
                    quote_lines.append(content)
                index += 1
            if quote_lines:
                story.append(Paragraph(inline_markup(" · ".join(quote_lines)), STYLES["quote"]))
            continue
        if stripped.startswith("|"):
            table_rows, index = parse_table(lines, index)
            story.append(make_table(table_rows))
            story.append(Spacer(1, 6))
            continue
        if stripped.startswith("- "):
            while index < len(lines) and lines[index].strip().startswith("- "):
                item = lines[index].strip()[2:].strip()
                story.append(Paragraph(inline_markup(item), STYLES["bullet"], bulletText="•"))
                index += 1
            story.append(Spacer(1, 2))
            continue
        number_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if number_match:
            while index < len(lines):
                current = re.match(r"^(\d+)\.\s+(.*)$", lines[index].strip())
                if not current:
                    break
                story.append(Paragraph(f"<b>{current.group(1)}.</b> {inline_markup(current.group(2))}", STYLES["number"]))
                index += 1
            story.append(Spacer(1, 2))
            continue
        if stripped.startswith("`") and stripped.endswith("`") and stripped.count("`") == 2:
            story.append(Paragraph(inline_markup(stripped[1:-1]), STYLES["code"]))
            index += 1
            continue
        if stripped in {"---", "***"}:
            story.append(HRFlowable(width="100%", thickness=0.55, color=LINE, spaceBefore=3, spaceAfter=6))
            index += 1
            continue

        paragraph = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if candidate.startswith(("#", ">", "|", "- ", "<!--")) or re.match(r"^\d+\.\s+", candidate) or candidate in {"---", "***"}:
                break
            paragraph.append(candidate)
            index += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph)), STYLES["body"]))
    return story


def cover_story() -> list[Flowable]:
    summary_data = [
        [Paragraph("玩家", STYLES["table_header"]), Paragraph("目标", STYLES["table_header"]), Paragraph("核心循环", STYLES["table_header"])],
        [Paragraph("2-4 人", STYLES["table_cell"]), Paragraph("抽牌堆耗尽后取得最高银行分", STYLES["table_cell"]), Paragraph("翻牌 · 能力 · 试胆 · 收牌／爆牌", STYLES["table_cell"])],
    ]
    summary = Table(summary_data, colWidths=[30 * mm, 70 * mm, CONTENT_WIDTH - 100 * mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SEA),
        ("BACKGROUND", (0, 1), (-1, 1), PANEL),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [
        Spacer(1, 7 * mm),
        Paragraph("GAME HALL · COMMUNITY GAME MODEL", STYLES["cover_eyebrow"]),
        Paragraph("《亡命神抽》规则说明书", STYLES["cover_title"]),
        Paragraph("Dead Man's Draw 简体中文数字化建模版 v1.0<br/>面向规则评审、实体试玩与服务端实现的原创整理稿", STYLES["cover_subtitle"]),
        summary,
        Spacer(1, 8 * mm),
        TableDiagram(CONTENT_WIDTH, 215),
        Spacer(1, 7 * mm),
        Paragraph("逐张翻开战利品并执行能力；适时收牌，或冒险追求更长连锁。航道出现重复花色就会爆牌，船锚与特性则能改变损失。", STYLES["quote"]),
        Paragraph("非官方资料 · 原创功能图 · 规则来源与数字化裁决见第 16 节 · 2026-09-02", STYLES["small"]),
        PageBreak(),
    ]


def page_background(canvas: Canvas) -> None:
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.restoreState()


def first_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    page_background(canvas)
    canvas.saveState()
    canvas.setFillColor(SEA)
    canvas.rect(0, PAGE_HEIGHT - 7 * mm, PAGE_WIDTH, 7 * mm, fill=1, stroke=0)
    canvas.setFillColor(BRASS)
    canvas.rect(0, 0, PAGE_WIDTH, 3 * mm, fill=1, stroke=0)
    canvas.restoreState()


def later_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    page_background(canvas)
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_X, PAGE_HEIGHT - 12 * mm, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7.2)
    canvas.drawString(MARGIN_X, PAGE_HEIGHT - 9.5 * mm, "亡命神抽 · 规则说明书")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 9.5 * mm, "数字化建模版 v1.0")
    canvas.line(MARGIN_X, 11 * mm, PAGE_WIDTH - MARGIN_X, 11 * mm)
    canvas.drawString(MARGIN_X, 7.2 * mm, "原创中文整理 · 非官方规则书")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 7.2 * mm, str(doc.page))
    canvas.restoreState()


def build() -> Path:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    markdown = SOURCE.read_text(encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=MARGIN_X,
        leftMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="《亡命神抽》规则说明书",
        author="Game Hall Contributors",
        subject="Dead Man's Draw Chinese rulebook and digital implementation model",
        creator="game-hall dead-mans-draw-game-model",
        displayDocTitle=True,
    )
    story: list[Flowable] = [*cover_story(), *markdown_story(markdown)]
    doc.build(story, onFirstPage=first_page, onLaterPages=later_page)
    return OUTPUT


def main() -> int:
    try:
        output = build()
    except Exception as exc:  # noqa: BLE001 - CLI should surface all build failures
        print(f"Failed to build rulebook: {exc}", file=sys.stderr)
        return 1
    print(f"Built {output.relative_to(ROOT)} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
