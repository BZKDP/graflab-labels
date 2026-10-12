# -*- coding: utf-8 -*-
"""MAGNIY B6 v2: доработка по замечаниям сотрудника от 28.08.2026."""
from __future__ import annotations

import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
SOURCE = Path(__file__).resolve().parent / "input" / '1787905591846-111930516.pdf'
RIGHT_REFERENCE = Path(__file__).resolve().parent / "input" / '1787900292255-549080441.pdf'

OUT_PDF = ROOT / "MAGNIY_B6_v2_REVIEW_158x52mm.pdf"
OUT_SVG = ROOT / "MAGNIY_B6_v2_REVIEW_158x52mm_outlined.svg"
OUT_PNG = ROOT / "MAGNIY_B6_v2_REVIEW_preview_300dpi.png"

FONT_REGULAR = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")

BLACK = (0.102449, 0.101183, 0.095109)
BLUE = (0.0, 0.401190, 0.587304)

LEFT_X = 18.8
LEFT_WIDTH = 118.0
BODY_SIZE = 4.2
BODY_LEADING = 4.72
BODY_GAP = 1.05

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
        tokens.append((label, "ptnbmag", bold))
    if body:
        tokens.extend((word, "ptnregmag", regular) for word in body.split())

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
    c1, c2 = 65.0, 119.5
    y0, yh, y1, y2 = 43.30, 50.10, 54.45, 58.80

    page.draw_rect(fitz.Rect(x0, y0, x1, y2), color=BLACK, width=0.35, overlay=True)
    for x in (c1, c2):
        page.draw_line((x, y0), (x, y2), color=BLACK, width=0.25, overlay=True)
    for y in (yh, y1):
        page.draw_line((x0, y), (x1, y), color=BLACK, width=0.25, overlay=True)

    header_size = 3.4
    page.insert_text(
        (x0 + 1.0, 47.50),
        "Биологически активные вещества",
        fontname="ptnregmag",
        fontsize=header_size,
        color=BLACK,
    )
    header_2 = "Содержание в 1 капсуле (суточной порции)"
    page.insert_text(
        (centered_x(header_2, regular, header_size, c1, c2), 47.50),
        header_2,
        fontname="ptnregmag",
        fontsize=header_size,
        color=BLACK,
    )
    header_3 = "% от АУП*"
    page.insert_text(
        (centered_x(header_3, regular, header_size, c2, x1), 47.50),
        header_3,
        fontname="ptnregmag",
        fontsize=header_size,
        color=BLACK,
    )

    row_size = 3.65
    rows = [
        ("Хелатный глицинат магния", "450 мг", "-**", 53.35),
        ("Витамин B6", "10 мг", "500", 57.70),
    ]
    for substance, amount, percent, baseline in rows:
        page.insert_text(
            (x0 + 1.0, baseline),
            substance,
            fontname="ptnregmag",
            fontsize=row_size,
            color=BLACK,
        )
        page.insert_text(
            (centered_x(amount, regular, row_size, c1, c2), baseline),
            amount,
            fontname="ptnregmag",
            fontsize=row_size,
            color=BLACK,
        )
        page.insert_text(
            (centered_x(percent, regular, row_size, c2, x1), baseline),
            percent,
            fontname="ptnregmag",
            fontsize=row_size,
            color=BLACK,
        )


def main() -> None:
    doc = fitz.open(SOURCE)
    page = doc[0]
    reference = fitz.open(RIGHT_REFERENCE)
    ref_page = reference[0]

    # У стандартного правого блока удаляем только старые значения дат.
    for rect in (
        fitz.Rect(316.70, 74.80, 358.00, 83.50),
        fitz.Rect(385.90, 74.80, 432.10, 83.50),
    ):
        ref_page.add_redact_annot(rect, fill=None)
    ref_page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    # Полностью очищаем только левый информационный и верхний правый блоки.
    for rect in (
        fitz.Rect(17.5, 8.0, 137.5, 137.2),
        fitz.Rect(304.0, 0.0, page.rect.width, 91.2),
    ):
        page.add_redact_annot(rect, fill=None)
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    # Правый блок приводится к принятой системе: QR, короткий изготовитель, даты.
    right_clip = fitz.Rect(304.0, 0.0, page.rect.width, 91.2)
    page.show_pdf_page(right_clip, reference, 0, clip=right_clip, keep_proportion=True)

    page.insert_font(fontname="ptnregmag", fontfile=str(FONT_REGULAR))
    page.insert_font(fontname="ptnbmag", fontfile=str(FONT_BOLD))
    regular = fitz.Font(fontfile=str(FONT_REGULAR))
    bold = fitz.Font(fontfile=str(FONT_BOLD))

    _, top_lines = draw_paragraphs(
        page,
        TOP_PARAGRAPHS,
        baseline=12.60,
        size=BODY_SIZE,
        leading=BODY_LEADING,
        gap=BODY_GAP,
        regular=regular,
        bold=bold,
    )
    if top_lines != 6:
        raise RuntimeError(f"Верхний левый блок должен занимать 6 строк, получено {top_lines}")

    draw_table(page, regular)

    footnote_paragraphs = [("", value) for value in FOOTNOTES]
    _, footnote_lines = draw_paragraphs(
        page,
        footnote_paragraphs,
        baseline=63.20,
        size=3.7,
        leading=4.10,
        gap=0.80,
        regular=regular,
        bold=bold,
    )
    if footnote_lines != 4:
        raise RuntimeError(f"Сноски должны занимать 4 строки, получено {footnote_lines}")

    bottom_cursor, bottom_lines = draw_paragraphs(
        page,
        BOTTOM_PARAGRAPHS,
        baseline=82.00,
        size=BODY_SIZE,
        leading=BODY_LEADING,
        gap=1.10,
        regular=regular,
        bold=bold,
    )
    if bottom_lines != 10 or bottom_cursor > 136.0:
        raise RuntimeError(
            f"Нижний левый блок не помещается: lines={bottom_lines}, cursor={bottom_cursor:.3f}"
        )

    # Даты сохраняют исходную дату изготовления; срок годности рассчитан по 2 годам.
    page.insert_text(
        (317.78, 82.40),
        "04.08.2025",
        fontname="ptnbmag",
        fontsize=9.0,
        color=BLUE,
    )
    page.insert_text(
        (391.80, 82.40),
        "04.08.2027",
        fontname="ptnbmag",
        fontsize=9.0,
        color=BLUE,
    )

    doc.subset_fonts()
    doc.save(OUT_PDF, garbage=4, deflate=True)

    pix = doc[0].get_pixmap(dpi=300, alpha=False)
    pix.save(OUT_PNG)

    svg = doc[0].get_svg_image(text_as_path=True)
    svg = re.sub(r'width="[^"]+"', 'width="158mm"', svg, count=1)
    svg = re.sub(r'height="[^"]+"', 'height="52mm"', svg, count=1)
    OUT_SVG.write_text(svg, encoding="utf-8")

    reference.close()
    doc.close()

    print(f"PDF: {OUT_PDF}")
    print(f"SVG: {OUT_SVG}")
    print(f"PNG: {OUT_PNG} ({pix.width}x{pix.height})")
    print(f"Lines: top={top_lines}, footnotes={footnote_lines}, bottom={bottom_lines}")


if __name__ == "__main__":
    main()
