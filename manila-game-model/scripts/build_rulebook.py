#!/usr/bin/env python3
"""Build the Chinese Manila rulebook PDF from docs/RULEBOOK.md."""

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
OUTPUT = ROOT / "output" / "pdf" / "manila-rulebook-zh-CN.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 17 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

INK = colors.HexColor("#1F2B31")
MUTED = colors.HexColor("#66747A")
PAPER = colors.HexColor("#F7F1E5")
PANEL = colors.HexColor("#EAE0CC")
LINE = colors.HexColor("#C8B99B")
NAVY = colors.HexColor("#173C4A")
TEAL = colors.HexColor("#1F6D70")
GOLD = colors.HexColor("#C48A2C")
CORAL = colors.HexColor("#B94D3F")
GREEN = colors.HexColor("#547D5B")
JADE = colors.HexColor("#3C8870")
SILK = colors.HexColor("#A94E6E")
NUTMEG = colors.HexColor("#B56A35")
GINSENG = colors.HexColor("#729C49")


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc"), 0),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf"), 0),
        (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            0,
        ),
    ]
    for regular, bold, index in candidates:
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(
                TTFont("ManilaSans", str(regular), subfontIndex=index)
            )
            pdfmetrics.registerFont(
                TTFont("ManilaSans-Bold", str(bold), subfontIndex=index)
            )
            pdfmetrics.registerFontFamily(
                "ManilaSans",
                normal="ManilaSans",
                bold="ManilaSans-Bold",
                italic="ManilaSans",
                boldItalic="ManilaSans-Bold",
            )
            return "ManilaSans", "ManilaSans-Bold"
    raise RuntimeError("No Chinese font found; install Microsoft YaHei or Noto Sans CJK.")


FONT, FONT_BOLD = register_fonts()


class HarborDiagram(Flowable):
    """Original schematic harbor scene used on the cover."""

    def __init__(self, width: float, height: float = 220):
        super().__init__()
        self.width = width
        self.height = height

    def _boat(self, canvas: Canvas, x: float, y: float, color: colors.Color, label: str) -> None:
        canvas.saveState()
        canvas.setFillColor(color)
        canvas.setStrokeColor(colors.white)
        canvas.setLineWidth(1)
        canvas.roundRect(x - 22, y - 9, 44, 18, 5, fill=1, stroke=1)
        canvas.setFillColor(colors.HexColor("#FBF5E8"))
        canvas.setFont(FONT_BOLD, 7)
        canvas.drawCentredString(x, y - 2.4, label)
        canvas.restoreState()

    def _die(self, canvas: Canvas, x: float, y: float, value: int, color: colors.Color) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#FFF8E9"))
        canvas.setStrokeColor(color)
        canvas.setLineWidth(1.5)
        canvas.roundRect(x - 9, y - 9, 18, 18, 3, fill=1, stroke=1)
        canvas.setFillColor(color)
        canvas.setFont(FONT_BOLD, 9)
        canvas.drawCentredString(x, y - 3.2, str(value))
        canvas.restoreState()

    def draw(self) -> None:
        canvas = self.canv
        width = self.width
        height = self.height
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.roundRect(0, 0, width, height, 12, fill=1, stroke=0)

        # Water and shore.
        canvas.setFillColor(colors.HexColor("#245768"))
        canvas.roundRect(16, 18, width - 32, height - 36, 9, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#63909B"))
        canvas.setLineWidth(0.7)
        for y in range(36, int(height - 24), 18):
            canvas.line(24, y, width - 24, y)

        route_left = 44
        route_right = width - 107
        for row, color in enumerate((GINSENG, NUTMEG, SILK)):
            y = height - 55 - row * 48
            canvas.setStrokeColor(colors.HexColor("#CFE2E3"))
            canvas.setLineWidth(2.2)
            canvas.line(route_left, y, route_right, y)
            for step in (0, 5, 9, 13):
                x = route_left + (route_right - route_left) * step / 13
                canvas.setFillColor(colors.HexColor("#E8F0EB"))
                canvas.circle(x, y, 3, fill=1, stroke=0)
                canvas.setFillColor(colors.HexColor("#B9D0D3"))
                canvas.setFont(FONT, 6)
                canvas.drawCentredString(x, y - 12, str(step))
            boat_x = route_left + (route_right - route_left) * (3 + row * 2) / 13
            labels = ("人参", "肉豆蔻", "丝绸")
            self._boat(canvas, boat_x, y + 8, color, labels[row])
            self._die(canvas, route_left - 20, y, (4, 2, 6)[row], color)

        # Destination stack and pirate marker.
        dock_x = width - 91
        canvas.setFillColor(colors.HexColor("#E7D1A6"))
        canvas.roundRect(dock_x, 30, 70, height - 60, 7, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawCentredString(dock_x + 35, height - 45, "港口 / 船坞")
        for index, (label, reward) in enumerate((("A", "6"), ("B", "8"), ("C", "15"))):
            y = height - 75 - index * 34
            canvas.setFillColor(colors.HexColor("#FBF3E2"))
            canvas.setStrokeColor(GOLD)
            canvas.roundRect(dock_x + 9, y - 12, 52, 24, 4, fill=1, stroke=1)
            canvas.setFillColor(INK)
            canvas.setFont(FONT_BOLD, 7)
            canvas.drawString(dock_x + 16, y - 2, label)
            canvas.drawRightString(dock_x + 54, y - 2, reward)

        canvas.setFillColor(CORAL)
        canvas.circle(width - 56, 27, 18, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(FONT_BOLD, 7)
        canvas.drawCentredString(width - 56, 24.5, "海盗 13")

        canvas.setFillColor(colors.HexColor("#E5D6B5"))
        canvas.setFont(FONT, 7)
        canvas.drawString(25, 9, "竞价决定港务长 · 部署下注 · 三轮航行 · 到港货物升值")
        canvas.restoreState()


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_eyebrow": ParagraphStyle(
            "cover_eyebrow",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.5,
            leading=12,
            textColor=TEAL,
            spaceAfter=5,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=29,
            leading=36,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=11,
            leading=18,
            textColor=MUTED,
            spaceAfter=13,
            wordWrap="CJK",
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=16.5,
            leading=22,
            textColor=NAVY,
            spaceBefore=7,
            spaceAfter=7,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=11.7,
            leading=16,
            textColor=TEAL,
            spaceBefore=5,
            spaceAfter=4,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName=FONT_BOLD,
            fontSize=10.2,
            leading=14,
            textColor=CORAL,
            spaceBefore=4,
            spaceAfter=3,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.85,
            leading=13.7,
            textColor=INK,
            spaceAfter=5,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.75,
            leading=13.2,
            textColor=INK,
            leftIndent=12,
            firstLineIndent=-8,
            bulletIndent=0,
            spaceAfter=2.6,
            wordWrap="CJK",
        ),
        "number": ParagraphStyle(
            "number",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.75,
            leading=13.2,
            textColor=INK,
            leftIndent=16,
            firstLineIndent=-16,
            spaceAfter=2.6,
            wordWrap="CJK",
        ),
        "quote": ParagraphStyle(
            "quote",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.8,
            leading=13.5,
            textColor=colors.HexColor("#4C463E"),
            backColor=PANEL,
            borderColor=GOLD,
            borderWidth=0,
            borderPadding=(7, 9, 7, 9),
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "code",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=8.6,
            leading=13,
            textColor=colors.HexColor("#FFF6E3"),
            backColor=NAVY,
            borderPadding=(7, 9, 7, 9),
            alignment=TA_CENTER,
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=7.9,
            leading=11,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=7.7,
            leading=11,
            textColor=INK,
            wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=7.2,
            leading=10.5,
            textColor=MUTED,
            wordWrap="CJK",
        ),
    }


STYLES = build_styles()


def inline_markup(text: str) -> str:
    text = text.replace("\\`", "`")
    escaped = html.escape(text.strip(), quote=False)
    link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
    escaped = link_pattern.sub(
        lambda match: (
            f'<link href="{html.escape(match.group(2), quote=True)}" '
            f'color="#7B5420"><u>{match.group(1)}</u></link>'
        ),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", r'<font color="#9A493B"><b>\1</b></font>', escaped)
    return escaped


def text_weight(value: str) -> float:
    return max(sum(1.0 if ord(char) > 127 else 0.55 for char in value), 2.0)


def make_table(rows: list[list[str]]) -> Table:
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    weights = [max(text_weight(row[col]) for row in normalized) for col in range(column_count)]
    minimum = 18 * mm if column_count <= 4 else 14 * mm
    widths = [max(minimum, CONTENT_WIDTH * weight / sum(weights)) for weight in weights]
    scale = CONTENT_WIDTH / sum(widths)
    widths = [width * scale for width in widths]
    data: list[list[Paragraph]] = []
    for row_index, row in enumerate(normalized):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table_cell"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7F2E8"), colors.HexColor("#ECE3D2")]),
                ("GRID", (0, 0), (-1, -1), 0.45, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )
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
        normalized = stripped.replace("\\`", "`")
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
            story.append(HRFlowable(width="100%", thickness=0.7, color=LINE, spaceAfter=6))
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
                quote_lines.append(lines[index].strip()[1:].strip())
                index += 1
            story.append(Paragraph(inline_markup(" · ".join(quote_lines)), STYLES["quote"]))
            continue
        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            story.append(make_table(rows))
            story.append(Spacer(1, 6))
            continue
        if stripped.startswith("- "):
            while index < len(lines) and lines[index].strip().startswith("- "):
                item = lines[index].strip()[2:]
                story.append(Paragraph(inline_markup(item), STYLES["bullet"], bulletText="•"))
                index += 1
            story.append(Spacer(1, 1.5))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            while index < len(lines):
                current = re.match(r"^(\d+)\.\s+(.*)$", lines[index].strip())
                if not current:
                    break
                story.append(
                    Paragraph(
                        f"<b>{current.group(1)}.</b> {inline_markup(current.group(2))}",
                        STYLES["number"],
                    )
                )
                index += 1
            story.append(Spacer(1, 1.5))
            continue
        if normalized.startswith("`") and normalized.endswith("`") and normalized.count("`") == 2:
            story.append(Paragraph(html.escape(normalized[1:-1]), STYLES["code"]))
            index += 1
            continue
        if stripped in {"---", "***"}:
            story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=4, spaceAfter=7))
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if (
                candidate.startswith(("#", ">", "|", "- ", "<!--"))
                or re.match(r"^\d+\.\s+", candidate)
                or candidate in {"---", "***"}
            ):
                break
            paragraph_lines.append(candidate)
            index += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), STYLES["body"]))
    return story


def cover_story() -> list[Flowable]:
    summary_data = [
        [
            Paragraph("玩家", STYLES["table_header"]),
            Paragraph("终局目标", STYLES["table_header"]),
            Paragraph("核心循环", STYLES["table_header"]),
        ],
        [
            Paragraph("3-5 人", STYLES["table_cell"]),
            Paragraph("货物价值到达 30 后，总财富最高", STYLES["table_cell"]),
            Paragraph("拍卖 · 装船 · 部署 · 航行 · 结算", STYLES["table_cell"]),
        ],
    ]
    summary = Table(summary_data, colWidths=[31 * mm, 69 * mm, CONTENT_WIDTH - 100 * mm])
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (-1, 1), PANEL),
                ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [
        Spacer(1, 7 * mm),
        Paragraph("GAME HALL · INDEPENDENT GAME MODEL", STYLES["cover_eyebrow"]),
        Paragraph("《马尼拉》规则说明书", STYLES["cover_title"]),
        Paragraph(
            "Manila 简体中文数字化建模版 v1.0<br/>"
            "面向规则评审、程序实现与原创场景制作的独立整理稿",
            STYLES["cover_subtitle"],
        ),
        summary,
        Spacer(1, 8 * mm),
        HarborDiagram(CONTENT_WIDTH, 220),
        Spacer(1, 6 * mm),
        Paragraph(
            "在三艘船和四种货物之间下注：港务长控制装载与起航位置，"
            "骰点决定航程，海盗、引航员和保险把每次部署变成一笔风险投资。",
            STYLES["quote"],
        ),
        Paragraph(
            "非官方资料 · 不含官方美术 · 规则来源与数字版裁定见文末 · 资料核对：2026-09-02",
            STYLES["small"],
        ),
        PageBreak(),
    ]


def draw_page_background(canvas: Canvas) -> None:
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.restoreState()


def first_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    del doc
    draw_page_background(canvas)
    canvas.saveState()
    canvas.setFillColor(TEAL)
    canvas.rect(0, PAGE_HEIGHT - 7 * mm, PAGE_WIDTH, 7 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 0, PAGE_WIDTH, 3 * mm, fill=1, stroke=0)
    canvas.restoreState()


def later_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    draw_page_background(canvas)
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_X, PAGE_HEIGHT - 12 * mm, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7.2)
    canvas.drawString(MARGIN_X, PAGE_HEIGHT - 9.5 * mm, "马尼拉 · 规则说明书")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 9.5 * mm, "数字化建模版 v1.0")
    canvas.line(MARGIN_X, 11 * mm, PAGE_WIDTH - MARGIN_X, 11 * mm)
    canvas.drawString(MARGIN_X, 7.3 * mm, "独立中文整理 · 来源见第 15 节")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 7.3 * mm, str(doc.page))
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
        title="Manila Rulebook - Simplified Chinese",
        author="Game Hall Contributors",
        subject="Manila board game Chinese rules and digital modeling guide",
        creator="game-hall manila-game-model",
        displayDocTitle=True,
    )
    story: list[Flowable] = [*cover_story(), *markdown_story(markdown)]
    doc.build(story, onFirstPage=first_page, onLaterPages=later_page)
    return OUTPUT


def main() -> int:
    try:
        output = build()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to build rulebook: {exc}", file=sys.stderr)
        return 1
    print(f"Built {output.relative_to(ROOT)} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
