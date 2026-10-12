# -*- coding: utf-8 -*-
"""Большая этикетка МАГНИЙ B6, 120 капсул, 220 × 42 мм."""
from __future__ import annotations

import io
import re
from pathlib import Path

import fitz
from reportlab.graphics.barcode.code128 import Code128
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
LARGE_REFERENCE = Path(__file__).resolve().parent / "input" / '1787202986538-986203317.pdf'
SMALL_MAGNIY = ROOT / "MAGNIY_B6_v2_REVIEW_158x52mm.pdf"

OUT_PDF = ROOT / "MAGNIY_B6_120_CAPS_REVIEW_220x42mm.pdf"
OUT_SVG = ROOT / "MAGNIY_B6_120_CAPS_REVIEW_220x42mm_outlined.svg"
OUT_PNG = ROOT / "MAGNIY_B6_120_CAPS_REVIEW_preview_300dpi.png"

FONT_REGULAR = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")

BLACK = (0.102449, 0.101183, 0.095109)
BLUE = (0.0, 0.401190, 0.587304)
GOLD = (219 / 255, 200 / 255, 145 / 255)

LEFT_X = 61.0
LEFT_WIDTH = 134.0
BODY_SIZE = 4.4
BODY_LEADING = 4.60
BODY_GAP = 0.80

TOP_PARAGRAPHS = [
    (
        "Область применения:",
        "для реализации населению в качестве биологически активной добавки к пище - дополнительного источника магния и витамина B6.",
    ),
    (
        "Состав:",
        "хелатный глицинат магния, витамин B6 (пиридоксин), микрокристаллическая целлюлоза, желатиновая капсула.",
    ),
    (
        "Рекомендации по применению:",
        "взрослым по 1 капсуле в день во время еды.",
    ),
    (
        "",
        "При употреблении БАД в рекомендуемой дозе в организм будет поступать:",
    ),
]

FOOTNOTES = [
    (
        "* адекватный уровень потребления согласно Единым санитарно-эпидемиологическим и гигиеническим требованиям к товарам, подлежащим санитарно-эпидемиологическому надзору (контролю), Глава II, Раздел 1, Приложение 5;"
    ),
    "** уровень суточного потребления не установлен.",
]

BOTTOM_PARAGRAPHS = [
    (
        "Продолжительность приема:",
        "1 месяц. При необходимости прием можно повторить.",
    ),
    (
        "Противопоказания:",
        "индивидуальная непереносимость компонентов, беременность, кормление грудью. Перед применением рекомендуется проконсультироваться с врачом.",
    ),
    (
        "Условия хранения:",
        "хранить в сухом, защищенном от попадания прямых солнечных лучей, недоступном для детей месте, при температуре не выше 25°С.",
    ),
    ("Срок годности:", "2 года."),
    ("Не является лекарственным средством.", ""),
]


def text_width(text: str, font: fitz.Font, size: float) -> float:
    return font.text_length(text, fontsize=size)


def wrap_paragraph(
    label: str,
    body: str,
    size: float,
    regular: fitz.Font,
    bold: fitz.Font,
    max_width: float = LEFT_WIDTH,
) -> list[list[tuple[str, str, fitz.Font]]]:
    tokens: list[tuple[str, str, fitz.Font]] = []
    if label:
        tokens.append((label, "ptnblarge", bold))
    if body:
        tokens.extend((word, "ptnreglarge", regular) for word in body.split())

    lines: list[list[tuple[str, str, fitz.Font]]] = []
    current: list[tuple[str, str, fitz.Font]] = []
    current_width = 0.0
    for token, fontname, font in tokens:
        rendered = token if not current else " " + token
        candidate = text_width(rendered, font, size)
        if current and current_width + candidate > max_width:
            lines.append(current)
            current = [(token, fontname, font)]
            current_width = text_width(token, font, size)
        else:
            current.append((rendered, fontname, font))
            current_width += candidate
    if current:
        lines.append(current)
    return lines


def draw_paragraphs(
    page: fitz.Page,
    paragraphs: list[tuple[str, str]],
    baseline: float,
    size: float,
    leading: float,
    gap: float,
    regular: fitz.Font,
    bold: fitz.Font,
) -> tuple[float, int]:
    line_count = 0
    for index, (label, body) in enumerate(paragraphs):
        lines = wrap_paragraph(label, body, size, regular, bold)
        for line in lines:
            cursor_x = LEFT_X
            for text, fontname, font in line:
                page.insert_text(
                    (cursor_x, baseline),
                    text,
                    fontname=fontname,
                    fontsize=size,
                    color=BLACK,
                )
                cursor_x += text_width(text, font, size)
            baseline += leading
            line_count += 1
        if index < len(paragraphs) - 1:
            baseline += gap
    return baseline, line_count


def centered_x(text: str, font: fitz.Font, size: float, x0: float, x1: float) -> float:
    return (x0 + x1 - text_width(text, font, size)) / 2


def draw_table(page: fitz.Page, regular: fitz.Font) -> None:
    x0, x1 = LEFT_X, LEFT_X + LEFT_WIDTH
    c1, c2 = 111.5, 175.0
    y0, yh, y1, y2 = 41.50, 47.80, 51.55, 55.30

    page.draw_rect(fitz.Rect(x0, y0, x1, y2), color=BLACK, width=0.32, overlay=True)
    for x in (c1, c2):
        page.draw_line((x, y0), (x, y2), color=BLACK, width=0.24, overlay=True)
    for y in (yh, y1):
        page.draw_line((x0, y), (x1, y), color=BLACK, width=0.24, overlay=True)

    header_size = 3.25
    page.insert_text(
        (x0 + 0.9, 46.15),
        "Биологически активные вещества",
        fontname="ptnreglarge",
        fontsize=header_size,
        color=BLACK,
    )
    header_2 = "Содержание в 1 капсуле (суточной порции)"
    page.insert_text(
        (centered_x(header_2, regular, header_size, c1, c2), 46.15),
        header_2,
        fontname="ptnreglarge",
        fontsize=header_size,
        color=BLACK,
    )
    header_3 = "% от АУП*"
    page.insert_text(
        (centered_x(header_3, regular, header_size, c2, x1), 46.15),
        header_3,
        fontname="ptnreglarge",
        fontsize=header_size,
        color=BLACK,
    )

    row_size = 3.50
    rows = [
        ("Хелатный глицинат магния", "450 мг", "-**", 50.90),
        ("Витамин B6", "10 мг", "500", 54.65),
    ]
    for substance, amount, percent, baseline in rows:
        page.insert_text(
            (x0 + 0.9, baseline),
            substance,
            fontname="ptnreglarge",
            fontsize=row_size,
            color=BLACK,
        )
        page.insert_text(
            (centered_x(amount, regular, row_size, c1, c2), baseline),
            amount,
            fontname="ptnreglarge",
            fontsize=row_size,
            color=BLACK,
        )
        page.insert_text(
            (centered_x(percent, regular, row_size, c2, x1), baseline),
            percent,
            fontname="ptnreglarge",
            fontsize=row_size,
            color=BLACK,
        )


def make_barcode_pdf(value: str) -> fitz.Document:
    page_width, page_height = 64.0, 32.0
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    barcode = Code128(
        value,
        barHeight=20.0,
        barWidth=0.45,
        humanReadable=False,
        quiet=False,
    )
    barcode.drawOn(pdf_canvas, (page_width - barcode.width) / 2, 9.0)
    pdf_canvas.setFillColorRGB(*BLACK)
    pdf_canvas.setFont("Helvetica", 6.0)
    pdf_canvas.drawCentredString(page_width / 2, 1.4, value)
    pdf_canvas.showPage()
    pdf_canvas.save()
    return fitz.open(stream=buffer.getvalue(), filetype="pdf")


def main() -> None:
    doc = fitz.open(LARGE_REFERENCE)
    page = doc[0]
    small = fitz.open(SMALL_MAGNIY)
    small_page = small[0]

    # В малом исходнике меняется только цифра в среднем золотом знаке: 60 -> 120.
    small_page.add_redact_annot(fitz.Rect(217.7, 113.7, 231.0, 123.2), fill=None)
    small_page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )
    # Цифры 60 входят в состав составного векторного объекта, поэтому сердцевина
    # дополнительно перекрывается белым, не касаясь золотой внутренней окружности.
    small_page.draw_rect(
        fitz.Rect(216.9, 113.4, 231.8, 123.5),
        color=None,
        fill=(1.0, 1.0, 1.0),
        overlay=True,
    )
    small_page.insert_font(fontname="ptn120", fontfile=str(FONT_REGULAR))
    small_regular = fitz.Font(fontfile=str(FONT_REGULAR))
    count_text = "120"
    count_size = 7.0
    count_center = 224.35
    small_page.insert_text(
        (count_center - text_width(count_text, small_regular, count_size) / 2, 121.75),
        count_text,
        fontname="ptn120",
        fontsize=count_size,
        color=GOLD,
    )

    # Очищаются только заменяемые зоны большой желатиновой геометрии.
    for rect in (
        fitz.Rect(58.0, 6.0, 198.0, 116.0),
        fitz.Rect(240.0, 38.0, 418.0, 63.8),
        fitz.Rect(258.0, 65.0, 400.5, 80.2),
        fitz.Rect(316.2, 89.2, 341.8, 113.0),
        fitz.Rect(464.5, 61.0, 502.0, 69.2),
        fitz.Rect(524.5, 61.0, 561.2, 69.2),
        fitz.Rect(497.5, 80.0, 561.5, 112.5),
    ):
        page.add_redact_annot(rect, fill=None)
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    # Центральные элементы переносятся без изменения пропорций.
    page.show_pdf_page(
        fitz.Rect(274.45, 39.71, 383.45, 63.71),
        small,
        0,
        clip=fitz.Rect(169.0, 45.0, 278.0, 69.0),
        keep_proportion=True,
    )
    page.show_pdf_page(
        fitz.Rect(259.50, 66.18, 399.25, 79.88),
        small,
        0,
        clip=fitz.Rect(154.0, 73.20, 293.75, 86.90),
        keep_proportion=True,
    )
    page.show_pdf_page(
        fitz.Rect(317.15, 90.20, 340.85, 112.20),
        small,
        0,
        clip=fitz.Rect(208.8, 104.5, 240.0, 133.5),
        keep_proportion=True,
    )

    page.insert_font(fontname="ptnreglarge", fontfile=str(FONT_REGULAR))
    page.insert_font(fontname="ptnblarge", fontfile=str(FONT_BOLD))
    regular = fitz.Font(fontfile=str(FONT_REGULAR))
    bold = fitz.Font(fontfile=str(FONT_BOLD))

    _, top_lines = draw_paragraphs(
        page,
        TOP_PARAGRAPHS,
        baseline=13.00,
        size=BODY_SIZE,
        leading=BODY_LEADING,
        gap=BODY_GAP,
        regular=regular,
        bold=bold,
    )
    if top_lines != 6:
        raise RuntimeError(f"Верхний блок должен занимать 6 строк, получено {top_lines}")

    draw_table(page, regular)

    footnote_paragraphs = [("", value) for value in FOOTNOTES]
    _, footnote_lines = draw_paragraphs(
        page,
        footnote_paragraphs,
        baseline=59.00,
        size=3.6,
        leading=3.90,
        gap=0.60,
        regular=regular,
        bold=bold,
    )
    if footnote_lines != 4:
        raise RuntimeError(f"Сноски должны занимать 4 строки, получено {footnote_lines}")

    bottom_cursor, bottom_lines = draw_paragraphs(
        page,
        BOTTOM_PARAGRAPHS,
        baseline=77.20,
        size=BODY_SIZE,
        leading=BODY_LEADING,
        gap=0.95,
        regular=regular,
        bold=bold,
    )
    if bottom_lines != 8 or bottom_cursor > 120.0:
        raise RuntimeError(
            f"Нижний блок не помещается: lines={bottom_lines}, cursor={bottom_cursor:.3f}"
        )

    # Даты и исходный штрихкод магния.
    page.insert_text(
        (465.75, 68.00),
        "04.08.2025",
        fontname="ptnblarge",
        fontsize=8.0,
        color=BLUE,
    )
    page.insert_text(
        (525.75, 68.00),
        "04.08.2027",
        fontname="ptnblarge",
        fontsize=8.0,
        color=BLUE,
    )

    barcode_doc = make_barcode_pdf("4627174095012")
    page.show_pdf_page(
        fitz.Rect(497.5, 80.5, 561.5, 112.5),
        barcode_doc,
        0,
        keep_proportion=True,
    )

    doc.subset_fonts()
    doc.save(OUT_PDF, garbage=4, deflate=True)

    pix = doc[0].get_pixmap(dpi=300, alpha=False)
    pix.save(OUT_PNG)

    svg = doc[0].get_svg_image(text_as_path=True)
    svg = re.sub(r'width="[^"]+"', 'width="220mm"', svg, count=1)
    svg = re.sub(r'height="[^"]+"', 'height="42mm"', svg, count=1)
    OUT_SVG.write_text(svg, encoding="utf-8")

    barcode_doc.close()
    small.close()
    doc.close()

    print(f"PDF: {OUT_PDF}")
    print(f"SVG: {OUT_SVG}")
    print(f"PNG: {OUT_PNG} ({pix.width}x{pix.height})")
    print(f"Lines: top={top_lines}, footnotes={footnote_lines}, bottom={bottom_lines}")


if __name__ == "__main__":
    main()
