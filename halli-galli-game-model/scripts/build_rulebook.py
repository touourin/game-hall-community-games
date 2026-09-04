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
OUTPUT = ROOT / "output" / "pdf" / "halli-galli-rulebook-zh-CN.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 17 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

INK = colors.HexColor("#18211F")
MUTED = colors.HexColor("#66736F")
PAPER = colors.HexColor("#F8F4EA")
PANEL = colors.HexColor("#EBE3D5")
LINE = colors.HexColor("#C8B99D")
TABLE = colors.HexColor("#173C36")
TABLE_LIGHT = colors.HexColor("#2C5B52")
BRASS = colors.HexColor("#B58A4A")
BRASS_LIGHT = colors.HexColor("#E6CC8E")
DANGER = colors.HexColor("#B23A48")
WHITE = colors.HexColor("#FFFDF7")
BANANA = colors.HexColor("#F3C94A")
STRAWBERRY = colors.HexColor("#E9545B")
LIME = colors.HexColor("#79B94B")
PLUM = colors.HexColor("#7D5AA6")


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc"), 0),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf"), 0),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"), 0),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"), Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf"), 0),
    ]
    for normal_path, bold_path, index in candidates:
        if normal_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont("HgSans", str(normal_path), subfontIndex=index))
            pdfmetrics.registerFont(TTFont("HgSans-Bold", str(bold_path), subfontIndex=index))
            pdfmetrics.registerFontFamily(
                "HgSans",
                normal="HgSans",
                bold="HgSans-Bold",
                italic="HgSans",
                boldItalic="HgSans-Bold",
            )
            return "HgSans", "HgSans-Bold"
    raise RuntimeError("No Chinese font found. Install Microsoft YaHei, SimHei, or Noto Sans CJK.")


FONT, FONT_BOLD = register_fonts()


def normalize_pdf_text(value: str) -> str:
    return (
        value.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("  ", " ")
    )


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_eyebrow": ParagraphStyle("cover_eyebrow", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=12, textColor=TABLE_LIGHT, spaceAfter=5),
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontName=FONT_BOLD, fontSize=28, leading=35, textColor=TABLE, alignment=TA_LEFT, spaceAfter=6, wordWrap="CJK"),
        "cover_subtitle": ParagraphStyle("cover_subtitle", parent=base["Normal"], fontName=FONT, fontSize=10.8, leading=16.5, textColor=MUTED, spaceAfter=12, wordWrap="CJK"),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=16, leading=22, textColor=TABLE, spaceBefore=8, spaceAfter=6, keepWithNext=True, wordWrap="CJK"),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=11.5, leading=16, textColor=TABLE_LIGHT, spaceBefore=6, spaceAfter=4, keepWithNext=True, wordWrap="CJK"),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName=FONT_BOLD, fontSize=10.1, leading=14.5, textColor=DANGER, spaceBefore=5, spaceAfter=3, keepWithNext=True, wordWrap="CJK"),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=8.8, leading=13.7, textColor=INK, spaceAfter=5, wordWrap="CJK"),
        "bullet": ParagraphStyle("bullet", parent=base["BodyText"], fontName=FONT, fontSize=8.7, leading=13.2, textColor=INK, leftIndent=12, firstLineIndent=-9, bulletIndent=0, spaceAfter=2.5, wordWrap="CJK"),
        "number": ParagraphStyle("number", parent=base["BodyText"], fontName=FONT, fontSize=8.7, leading=13.2, textColor=INK, leftIndent=17, firstLineIndent=-17, spaceAfter=2.5, wordWrap="CJK"),
        "quote": ParagraphStyle("quote", parent=base["BodyText"], fontName=FONT, fontSize=8.6, leading=13.5, textColor=colors.HexColor("#344641"), backColor=PANEL, borderColor=BRASS, borderWidth=0, borderPadding=(7, 9, 7, 9), spaceAfter=7, wordWrap="CJK"),
        "code": ParagraphStyle("code", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=8.2, leading=12.5, textColor=WHITE, backColor=TABLE, borderPadding=(7, 9, 7, 9), alignment=TA_CENTER, spaceAfter=7, wordWrap="CJK"),
        "table_header": ParagraphStyle("table_header", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.4, leading=10.5, textColor=WHITE, wordWrap="CJK"),
        "table_cell": ParagraphStyle("table_cell", parent=base["Normal"], fontName=FONT, fontSize=7.3, leading=10.6, textColor=INK, wordWrap="CJK"),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName=FONT, fontSize=7.1, leading=10.3, textColor=MUTED, wordWrap="CJK"),
    }


STYLES = build_styles()


class FruitBellDiagram(Flowable):
    def __init__(self, width: float, height: float = 214):
        super().__init__()
        self.width = width
        self.height = height

    def draw_banana(self, canvas: Canvas, x: float, y: float, scale: float = 1) -> None:
        canvas.saveState()
        canvas.setLineCap(1)
        canvas.setStrokeColor(colors.HexColor("#8A6512"))
        canvas.setLineWidth(7 * scale)
        canvas.setFillColor(BANANA)
        path = canvas.beginPath()
        path.moveTo(x - 19 * scale, y + 13 * scale)
        path.curveTo(x - 11 * scale, y - 21 * scale, x + 18 * scale, y - 25 * scale, x + 27 * scale, y + 5 * scale)
        path.curveTo(x + 8 * scale, y - 8 * scale, x - 4 * scale, y + 2 * scale, x - 6 * scale, y + 20 * scale)
        path.close()
        canvas.drawPath(path, fill=1, stroke=1)
        canvas.restoreState()

    def draw_card(self, canvas: Canvas, x: float, y: float, fruit: str, count: int, color: colors.Color) -> None:
        canvas.saveState()
        canvas.setFillColor(WHITE)
        canvas.setStrokeColor(colors.HexColor("#C3B69D"))
        canvas.setLineWidth(1.2)
        canvas.roundRect(x, y, 66, 102, 7, fill=1, stroke=1)
        canvas.setFillColor(color)
        canvas.setFont(FONT_BOLD, 13)
        canvas.drawString(x + 7, y + 84, str(count))
        positions = {
            1: [(33, 49)],
            2: [(22, 62), (44, 38)],
            3: [(20, 65), (46, 65), (33, 36)],
            4: [(20, 65), (46, 65), (20, 37), (46, 37)],
        }[count]
        for px, py in positions:
            if fruit == "banana":
                self.draw_banana(canvas, x + px, y + py, 0.42)
            else:
                canvas.setFillColor(color)
                canvas.setStrokeColor(colors.HexColor("#852637") if fruit == "strawberry" else colors.HexColor("#432965"))
                canvas.circle(x + px, y + py, 8, fill=1, stroke=1)
        canvas.setFillColor(colors.HexColor("#5F574A"))
        canvas.setFont(FONT_BOLD, 6.8)
        canvas.drawCentredString(x + 33, y + 9, fruit)
        canvas.restoreState()

    def draw_bell(self, canvas: Canvas, cx: float, cy: float) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#102823"))
        canvas.setStrokeColor(BRASS_LIGHT)
        canvas.setLineWidth(2)
        canvas.circle(cx, cy, 48, fill=1, stroke=1)
        canvas.setFillColor(colors.HexColor("#D6B56B"))
        canvas.setStrokeColor(colors.HexColor("#7B5725"))
        canvas.setLineWidth(3)
        path = canvas.beginPath()
        path.moveTo(cx - 31, cy - 13)
        path.curveTo(cx - 29, cy + 22, cx - 16, cy + 34, cx, cy + 34)
        path.curveTo(cx + 16, cy + 34, cx + 29, cy + 22, cx + 31, cy - 13)
        path.close()
        canvas.drawPath(path, fill=1, stroke=1)
        canvas.roundRect(cx - 39, cy - 20, 78, 10, 5, fill=1, stroke=1)
        canvas.circle(cx, cy + 39, 8, fill=1, stroke=1)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 7.2)
        canvas.drawCentredString(cx, cy - 40, "SPACE · 抢铃")
        canvas.restoreState()

    def draw(self) -> None:
        canvas = self.canv
        width, height = self.width, self.height
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#102823"))
        canvas.roundRect(0, 0, width, height, 14, fill=1, stroke=0)
        canvas.setFillColor(TABLE)
        canvas.setStrokeColor(colors.HexColor("#4C746A"))
        canvas.setLineWidth(2)
        canvas.roundRect(10, 10, width - 20, height - 20, 26, fill=1, stroke=1)

        self.draw_card(canvas, width / 2 - 33, height - 116, "香蕉", 3, BANANA)
        self.draw_card(canvas, 28, height / 2 - 51, "草莓", 4, STRAWBERRY)
        self.draw_card(canvas, width - 94, height / 2 - 51, "李子", 1, PLUM)
        self.draw_card(canvas, width / 2 - 33, 15, "香蕉", 2, BANANA)
        self.draw_bell(canvas, width / 2, height / 2)

        canvas.setFillColor(PANEL)
        canvas.roundRect(width / 2 - 102, height / 2 - 71, 204, 20, 10, fill=1, stroke=0)
        canvas.setFillColor(INK)
        canvas.setFont(FONT_BOLD, 7.4)
        canvas.drawCentredString(width / 2, height / 2 - 64, "教学示例：2 + 3 个香蕉 = 恰好 5 个")
        canvas.restoreState()


def inline_markup(text: str) -> str:
    normalized = normalize_pdf_text(text.strip())
    escaped = html.escape(normalized, quote=False)
    http_link = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
    escaped = http_link.sub(lambda match: f'<link href="{html.escape(match.group(2), quote=True)}" color="#2C5B52"><u>{match.group(1)}</u></link>', escaped)
    local_link = re.compile(r"\[([^\]]+)\]\((?!https?://)[^)]+\)")
    escaped = local_link.sub(lambda match: f"<u>{match.group(1)}</u>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", r'<font color="#9A3340"><b>\1</b></font>', escaped)
    return escaped


def text_weight(value: str) -> float:
    clean = re.sub(r"[*`#]", "", value)
    return max(2.0, min(34.0, sum(1.0 if ord(char) > 127 else 0.55 for char in clean)))


def make_table(rows: list[list[str]]) -> Table:
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    weights = [max(text_weight(row[column]) for row in normalized) for column in range(column_count)]
    minimum = 16 * mm
    widths = [max(minimum, CONTENT_WIDTH * weight / sum(weights)) for weight in weights]
    scale = CONTENT_WIDTH / sum(widths)
    widths = [value * scale for value in widths]
    data = []
    for row_index, row in enumerate(normalized):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table_cell"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F5EFE4"), colors.HexColor("#ECE3D4")]),
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
        [Paragraph("人数／时间", STYLES["table_header"]), Paragraph("按铃条件", STYLES["table_header"]), Paragraph("胜利", STYLES["table_header"])],
        [Paragraph("2-6 人 · 约 15 分钟", STYLES["table_cell"]), Paragraph("任一水果在全部顶牌上恰好 5 个", STYLES["table_cell"]), Paragraph("最后一次铃后持牌最多；平手共同获胜", STYLES["table_cell"])],
    ]
    summary = Table(summary_data, colWidths=[47 * mm, 62 * mm, CONTENT_WIDTH - 109 * mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE),
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
        Paragraph("《德国心脏病》规则说明书", STYLES["cover_title"]),
        Paragraph("Halli Galli 简体中文数字化建模版 v1.0<br/>依据 AMIGO 德文说明书 v3.1 整理，面向规则评审与软件实现", STYLES["cover_subtitle"]),
        summary,
        Spacer(1, 7 * mm),
        FruitBellDiagram(CONTENT_WIDTH, 214),
        Spacer(1, 6 * mm),
        Paragraph("轮流翻牌，只看每堆顶牌；某一种水果恰好五个时，第一时间抢铃。正确者收走全部明牌，误按者付出代价。", STYLES["quote"]),
        Paragraph("非官方中文整理 · 原创几何功能图 · 来源与数字化裁决见第 14 节及 SOURCES.md · 2026-09-03", STYLES["small"]),
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
    canvas.setFillColor(TABLE)
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
    canvas.drawString(MARGIN_X, PAGE_HEIGHT - 9.5 * mm, "德国心脏病 · 规则说明书")
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
        title="《德国心脏病》规则说明书",
        author="Game Hall Contributors",
        subject="Halli Galli Chinese rulebook and digital implementation model",
        creator="game-hall halli-galli-game-model",
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
