#!/usr/bin/env python3
"""Build the Chinese Skull rulebook PDF from docs/RULEBOOK.md."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from typing import Iterable

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
OUTPUT = ROOT / "docs" / "skull-rulebook-zh-CN.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

INK = colors.HexColor("#25282C")
MUTED = colors.HexColor("#697078")
PAPER = colors.HexColor("#F7F4EE")
PANEL = colors.HexColor("#ECE7DE")
LINE = colors.HexColor("#C9C1B5")
ACCENT = colors.HexColor("#A55343")
GOLD = colors.HexColor("#B08A4E")
SAFE = colors.HexColor("#587D63")
DANGER = colors.HexColor("#984E4E")
DARK = colors.HexColor("#24272B")


def register_fonts() -> tuple[str, str]:
    candidates = [
        (
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/msyhbd.ttc"),
            0,
        ),
        (
            Path("C:/Windows/Fonts/simhei.ttf"),
            Path("C:/Windows/Fonts/simhei.ttf"),
            0,
        ),
        (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            0,
        ),
    ]
    for normal_path, bold_path, index in candidates:
        if normal_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont("SkullSans", str(normal_path), subfontIndex=index))
            pdfmetrics.registerFont(TTFont("SkullSans-Bold", str(bold_path), subfontIndex=index))
            pdfmetrics.registerFontFamily(
                "SkullSans",
                normal="SkullSans",
                bold="SkullSans-Bold",
                italic="SkullSans",
                boldItalic="SkullSans-Bold",
            )
            return "SkullSans", "SkullSans-Bold"
    raise RuntimeError("No Chinese font found. Install Microsoft YaHei, SimHei, or Noto Sans CJK.")


FONT, FONT_BOLD = register_fonts()


class BoardDiagram(Flowable):
    """Small original table diagram used on the cover."""

    def __init__(self, width: float, height: float = 205):
        super().__init__()
        self.width = width
        self.height = height

    def draw_disc(self, canvas: Canvas, x: float, y: float, kind: str, radius: float = 16) -> None:
        canvas.saveState()
        canvas.setLineWidth(2)
        canvas.setFillColor(colors.HexColor("#333333"))
        if kind == "flower":
            canvas.setStrokeColor(SAFE)
        elif kind == "skull":
            canvas.setStrokeColor(DANGER)
        else:
            canvas.setStrokeColor(colors.HexColor("#8B8F94"))
        canvas.circle(x, y, radius, fill=1, stroke=1)
        canvas.setFillColor(colors.HexColor("#E6DED2"))
        canvas.setFont(FONT_BOLD, 10)
        symbol = "花" if kind == "flower" else "骷" if kind == "skull" else "?"
        canvas.drawCentredString(x, y - 3.5, symbol)
        canvas.restoreState()

    def draw(self) -> None:
        canvas = self.canv
        width = self.width
        height = self.height
        canvas.saveState()

        canvas.setFillColor(colors.HexColor("#1F2226"))
        canvas.roundRect(0, 0, width, height, 14, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#34332F"))
        canvas.setStrokeColor(colors.HexColor("#625C54"))
        canvas.setLineWidth(3)
        canvas.ellipse(40, 20, width - 40, height - 16, fill=1, stroke=1)
        canvas.setStrokeColor(colors.HexColor("#797168"))
        canvas.setDash(3, 5)
        canvas.ellipse(58, 35, width - 58, height - 30, fill=0, stroke=1)
        canvas.setDash()

        seats = [
            (width / 2, 42, "你", ACCENT),
            (width * 0.25, height - 48, "白露", colors.HexColor("#5F91AA")),
            (width * 0.75, height - 48, "赤岩", GOLD),
        ]
        for x, y, label, color in seats:
            canvas.setFillColor(colors.HexColor("#292C30"))
            canvas.setStrokeColor(color)
            canvas.setLineWidth(2)
            canvas.roundRect(x - 49, y - 17, 98, 34, 9, fill=1, stroke=1)
            canvas.setFillColor(colors.HexColor("#F1EDE6"))
            canvas.setFont(FONT_BOLD, 9)
            canvas.drawCentredString(x, y - 3, label)

        self.draw_disc(canvas, width / 2 - 9, 83, "flower", 15)
        self.draw_disc(canvas, width / 2 + 9, 77, "skull", 15)
        self.draw_disc(canvas, width * 0.25 - 7, height - 86, "unknown", 15)
        self.draw_disc(canvas, width * 0.25 + 7, height - 92, "unknown", 15)
        self.draw_disc(canvas, width * 0.75, height - 89, "unknown", 15)

        canvas.setFillColor(colors.HexColor("#24272B"))
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(2.5)
        canvas.circle(width / 2, height / 2 + 7, 42, fill=1, stroke=1)
        canvas.setFillColor(colors.HexColor("#D9C89E"))
        canvas.setFont(FONT, 8)
        canvas.drawCentredString(width / 2, height / 2 + 25, "当前叫价")
        canvas.setFont(FONT_BOLD, 25)
        canvas.drawCentredString(width / 2, height / 2 - 2, "3 / 5")
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(colors.HexColor("#AEB3B8"))
        canvas.drawCentredString(width / 2, height / 2 - 20, "先翻自己的牌")

        canvas.restoreState()


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_eyebrow": ParagraphStyle(
            "cover_eyebrow",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=ACCENT,
            spaceAfter=5,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=31,
            leading=38,
            textColor=DARK,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=12,
            leading=19,
            textColor=MUTED,
            spaceAfter=14,
            wordWrap="CJK",
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=17,
            leading=23,
            textColor=DARK,
            spaceBefore=7,
            spaceAfter=8,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=12.2,
            leading=17,
            textColor=ACCENT,
            spaceBefore=6,
            spaceAfter=5,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=15,
            textColor=DANGER,
            spaceBefore=5,
            spaceAfter=4,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=14.3,
            textColor=INK,
            spaceAfter=5.5,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.1,
            leading=13.8,
            textColor=INK,
            leftIndent=12,
            firstLineIndent=-9,
            bulletIndent=0,
            spaceAfter=3,
            wordWrap="CJK",
        ),
        "number": ParagraphStyle(
            "number",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.1,
            leading=13.8,
            textColor=INK,
            leftIndent=16,
            firstLineIndent=-16,
            spaceAfter=3,
            wordWrap="CJK",
        ),
        "quote": ParagraphStyle(
            "quote",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#554F48"),
            backColor=PANEL,
            borderColor=GOLD,
            borderWidth=0,
            borderPadding=(7, 10, 7, 10),
            leftIndent=0,
            rightIndent=0,
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "code",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.7,
            leading=13,
            textColor=colors.HexColor("#EEE8DE"),
            backColor=DARK,
            borderPadding=(7, 9, 7, 9),
            alignment=TA_CENTER,
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.3,
            leading=11.5,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=8,
            leading=11.5,
            textColor=INK,
            wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=7.5,
            leading=11,
            textColor=MUTED,
            wordWrap="CJK",
        ),
    }


STYLES = build_styles()


def inline_markup(text: str) -> str:
    escaped = html.escape(text.strip(), quote=False)

    link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
    escaped = link_pattern.sub(
        lambda match: (
            f'<link href="{html.escape(match.group(2), quote=True)}" '
            f'color="#795C3C"><u>{match.group(1)}</u></link>'
        ),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", r'<font color="#8B3F34"><b>\1</b></font>', escaped)
    return escaped


def text_weight(value: str) -> float:
    weight = 0.0
    for char in value:
        weight += 1.0 if ord(char) > 127 else 0.55
    return max(weight, 2.0)


def make_table(rows: list[list[str]]) -> Table:
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    weights = []
    for col in range(column_count):
        weights.append(max(text_weight(row[col]) for row in normalized))
    total_weight = sum(weights)
    min_width = 20 * mm
    widths = [max(min_width, CONTENT_WIDTH * weight / total_weight) for weight in weights]
    scale = CONTENT_WIDTH / sum(widths)
    widths = [width * scale for width in widths]

    data: list[list[Paragraph]] = []
    for row_index, row in enumerate(normalized):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table_cell"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])

    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F3EFE8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F5F2EC"), colors.HexColor("#ECE7DE")]),
                ("GRID", (0, 0), (-1, -1), 0.45, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    raw_rows: list[list[str]] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        raw_rows.append(cells)
        index += 1
    if len(raw_rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in raw_rows[1]):
        raw_rows.pop(1)
    return raw_rows, index


def markdown_story(markdown: str) -> list[Flowable]:
    lines = markdown.splitlines()
    story: list[Flowable] = []
    index = 0

    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()

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
            story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=6))
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
            story.append(Spacer(1, 7))
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
                story.append(
                    Paragraph(
                        f"<b>{current.group(1)}.</b> {inline_markup(current.group(2))}",
                        STYLES["number"],
                    )
                )
                index += 1
            story.append(Spacer(1, 2))
            continue
        if stripped.startswith("`") and stripped.endswith("`") and stripped.count("`") == 2:
            story.append(Paragraph(inline_markup(stripped[1:-1]), STYLES["code"]))
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
        [Paragraph("玩家", STYLES["table_header"]), Paragraph("目标", STYLES["table_header"]), Paragraph("核心循环", STYLES["table_header"])],
        [
            Paragraph("3-6 人", STYLES["table_cell"]),
            Paragraph("两次挑战成功，或成为最后存活者", STYLES["table_cell"]),
            Paragraph("暗置 · 竞标 · 翻牌 · 处罚", STYLES["table_cell"]),
        ],
    ]
    summary = Table(summary_data, colWidths=[35 * mm, 69 * mm, CONTENT_WIDTH - 104 * mm])
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
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
        Spacer(1, 8 * mm),
        Paragraph("GAME HALL · THIRD-PARTY GAME MODEL", STYLES["cover_eyebrow"]),
        Paragraph("《骷髅牌》规则说明书", STYLES["cover_title"]),
        Paragraph(
            "Skull 简体中文数字化建模版 v1.0<br/>"
            "面向实体试玩、规则评审与后续服务端实现的原创整理稿",
            STYLES["cover_subtitle"],
        ),
        summary,
        Spacer(1, 9 * mm),
        BoardDiagram(CONTENT_WIDTH, 205),
        Spacer(1, 7 * mm),
        Paragraph(
            "规则主线：每位玩家拥有 3 枚花牌与 1 枚骷髅牌。最高叫价者先翻自己的牌，"
            "再挑战其他牌堆；翻满目标得分，碰到骷髅则秘密失去一枚个人牌。",
            STYLES["quote"],
        ),
        Paragraph(
            "非官方资料 · 不含官方美术 · 规则来源与版本差异见文末 · 2026-08-31",
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
    draw_page_background(canvas)
    canvas.saveState()
    canvas.setFillColor(ACCENT)
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
    canvas.setFont(FONT, 7.5)
    canvas.drawString(MARGIN_X, PAGE_HEIGHT - 9.5 * mm, "骷髅牌 · 规则说明书")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 9.5 * mm, "数字化建模版 v1.0")
    canvas.line(MARGIN_X, 11 * mm, PAGE_WIDTH - MARGIN_X, 11 * mm)
    canvas.drawString(MARGIN_X, 7.3 * mm, "原创中文整理 · 规则来源见第 12 节")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 7.3 * mm, f"{doc.page}")
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
        title="《骷髅牌》规则说明书",
        author="Game Hall Contributors",
        subject="Skull card game Chinese rulebook and digital modeling notes",
        creator="game-hall skull-game-model",
        displayDocTitle=True,
    )
    story: list[Flowable] = [*cover_story(), *markdown_story(markdown)]
    doc.build(story, onFirstPage=first_page, onLaterPages=later_page)
    return OUTPUT


def main() -> int:
    try:
        output = build()
    except Exception as exc:  # noqa: BLE001 - command-line builder should report all failures.
        print(f"Failed to build rulebook: {exc}", file=sys.stderr)
        return 1
    print(f"Built {output.relative_to(ROOT)} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
