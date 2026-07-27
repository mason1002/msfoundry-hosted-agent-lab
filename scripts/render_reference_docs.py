import html
import re
import sys
from pathlib import Path

import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def inline_markdown(value: str) -> str:
    rendered = markdown.markdown(value).strip()
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        rendered = rendered[3:-4]
    rendered = rendered.replace("<strong>", "<b>").replace("</strong>", "</b>")
    rendered = rendered.replace("<em>", "<i>").replace("</em>", "</i>")
    return re.sub(r"<code>(.*?)</code>", r'<font backColor="#F3F6F8">\1</font>', rendered)


def split_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    return line.startswith("|") and all(
        re.fullmatch(r":?\s*-{3,}\s*:?", cell) for cell in split_cells(line)
    )


def render(source: Path, output: Path) -> None:
    font_path = next(
        path
        for path in (
            Path(r"C:\Windows\Fonts\msyh.ttc"),
            Path(r"C:\Windows\Fonts\msyh.ttf"),
            Path(r"C:\Windows\Fonts\simsun.ttc"),
        )
        if path.exists()
    )
    if "TrainingCN" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("TrainingCN", str(font_path)))
        pdfmetrics.registerFontFamily(
            "TrainingCN",
            normal="TrainingCN",
            bold="TrainingCN",
            italic="TrainingCN",
            boldItalic="TrainingCN",
        )

    page_width, _ = A4
    left = right = 16 * mm
    top = bottom = 18 * mm
    available = page_width - left - right
    navy = colors.HexColor("#0B3A63")
    blue = colors.HexColor("#1683C4")
    grid = colors.HexColor("#AEBBC5")
    row_fill = colors.HexColor("#F5F8FA")

    styles = {
        "title": ParagraphStyle("Title", fontName="TrainingCN", fontSize=21, leading=28, textColor=navy, spaceAfter=7 * mm),
        "h2": ParagraphStyle("H2", fontName="TrainingCN", fontSize=14.5, leading=20, textColor=navy, leftIndent=3 * mm),
        "h3": ParagraphStyle("H3", fontName="TrainingCN", fontSize=11.5, leading=16, textColor=colors.HexColor("#155477"), spaceBefore=4 * mm, spaceAfter=2 * mm, keepWithNext=True),
        "body": ParagraphStyle("Body", fontName="TrainingCN", fontSize=9.4, leading=14.7, textColor=colors.HexColor("#202124"), spaceAfter=2.2 * mm, wordWrap="CJK"),
        "meta": ParagraphStyle("Meta", fontName="TrainingCN", fontSize=9.2, leading=14, textColor=colors.HexColor("#52697A"), spaceAfter=1.5 * mm),
        "bullet": ParagraphStyle("Bullet", fontName="TrainingCN", fontSize=9.3, leading=14.5, leftIndent=5 * mm, firstLineIndent=-3.5 * mm, bulletIndent=1 * mm, spaceAfter=1 * mm, wordWrap="CJK"),
        "code": ParagraphStyle("Code", fontName="TrainingCN", fontSize=7.8, leading=11.7, backColor=colors.HexColor("#F3F6F8"), borderColor=colors.HexColor("#C7D2DA"), borderWidth=0.5, borderPadding=3 * mm, leftIndent=2 * mm, rightIndent=2 * mm, spaceAfter=3 * mm, wordWrap="CJK"),
        "cell": ParagraphStyle("Cell", fontName="TrainingCN", fontSize=7.3, leading=10.4, wordWrap="CJK"),
        "head": ParagraphStyle("Head", fontName="TrainingCN", fontSize=7.3, leading=10.4, textColor=colors.white, wordWrap="CJK"),
    }

    lines = source.read_text(encoding="utf-8").splitlines()
    story = []
    index = 0
    pending_anchor = None
    while index < len(lines):
        value = lines[index].strip()
        if not value:
            index += 1
            continue
        anchor_match = re.fullmatch(r'<a\s+(?:id|name)="([A-Za-z0-9_-]+)"></a>', value)
        if anchor_match:
            pending_anchor = anchor_match.group(1)
            index += 1
            continue
        anchor_markup = f'<a name="{pending_anchor}"/>' if pending_anchor else ""
        if value.startswith("```"):
            index += 1
            code = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            story.append(Preformatted("\n".join(code), styles["code"], maxLineLength=115))
            continue
        if value == "---":
            story.append(HRFlowable(width="100%", thickness=0.5, color=grid, spaceAfter=3 * mm))
            index += 1
            continue
        if value.startswith("# "):
            story.append(Paragraph(anchor_markup + inline_markdown(value[2:]), styles["title"]))
            pending_anchor = None
            story.append(HRFlowable(width="100%", thickness=2, color=blue, spaceAfter=4 * mm))
            index += 1
            continue
        if value.startswith("## "):
            heading = Paragraph(anchor_markup + inline_markdown(value[3:]), styles["h2"])
            pending_anchor = None
            accent = Table(
                [["", heading]],
                colWidths=[2 * mm, available - 2 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), blue),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            )
            story.append(KeepTogether([Spacer(1, 3 * mm), accent, Spacer(1, 2 * mm)]))
            index += 1
            continue
        if value.startswith("### "):
            story.append(Paragraph(anchor_markup + inline_markdown(value[4:]), styles["h3"]))
            pending_anchor = None
            index += 1
            continue
        if value.startswith("|") and index + 1 < len(lines) and is_separator(lines[index + 1].strip()):
            rows = [split_cells(value)]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_cells(lines[index]))
                index += 1
            column_count = len(rows[0])
            data = []
            for row_index, row in enumerate(rows):
                style = styles["head"] if row_index == 0 else styles["cell"]
                data.append([Paragraph(inline_markdown(cell), style) for cell in row])
            table = Table(data, colWidths=[available / column_count] * column_count, repeatRows=1)
            commands = [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("GRID", (0, 0), (-1, -1), 0.4, grid),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1.8 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.8 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]
            for row_index in range(2, len(data), 2):
                commands.append(("BACKGROUND", (0, row_index), (-1, row_index), row_fill))
            table.setStyle(TableStyle(commands))
            story.extend([table, Spacer(1, 3 * mm)])
            continue
        match = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", value)
        if match:
            marker = value.split(maxsplit=1)[0]
            story.append(Paragraph(inline_markdown(match.group(1)), styles["bullet"], bulletText="•" if marker in ("-", "*") else marker))
            index += 1
            continue
        paragraph = [value]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if not next_line or next_line.startswith(("#", "```", "|", "---")) or re.match(r"^(?:[-*]|\d+\.)\s+", next_line):
                break
            paragraph.append(next_line)
            index += 1
        text = " ".join(paragraph)
        story.append(Paragraph(inline_markdown(text), styles["meta"] if text.startswith(("版本：", "示例应用：", "建议时长：", "验证日期：")) else styles["body"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("TrainingCN", 7.5)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(left, 9 * mm, f"{source.stem} · v1.0")
        canvas.drawRightString(page_width - right, 9 * mm, str(document.page))
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom,
        title=source.stem,
        subject="xAgent Microsoft Foundry reference material",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: render_reference_docs.py <markdown> [<markdown> ...]")
    for argument in sys.argv[1:]:
        source_path = Path(argument).resolve()
        output_path = source_path.with_suffix(".pdf")
        render(source_path, output_path)
        print(f"Generated {output_path.name}: {output_path.stat().st_size} bytes")