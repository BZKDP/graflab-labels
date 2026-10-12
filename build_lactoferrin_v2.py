# -*- coding: utf-8 -*-
"""Собирает доработанную этикетку лактоферрина 60 капсул, 158 x 52 мм."""
from __future__ import annotations

import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
SOURCE = Path(__file__).resolve().parent / "input" / '38cdd862142cbe9772a6 (1).pdf'
REFERENCE = ROOT / 'output/pdf/PRINT_BATCH_5_LABELS_2026-08-09_ORIGINAL_PRODUCT_v2/03_МАГНИЙ_B6_60_158x52.pdf'

OUT_DIR = ROOT / "output" / "pdf" / "LACTOFERRIN_FINAL_2026-08-09"
OUT_PDF = OUT_DIR / "LACTOFERRIN_60_FINAL_158x52mm.pdf"
OUT_SVG = OUT_DIR / "LACTOFERRIN_60_FINAL_158x52mm_outlined.svg"
OUT_PNG_300 = OUT_DIR / "LACTOFERRIN_60_FINAL_preview_300dpi.png"
OUT_PNG_600 = OUT_DIR / "LACTOFERRIN_60_FINAL_QA_600dpi.png"

FONT_REGULAR = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")
# Ближайшая кириллическая геометрическая полужирная гарнитура к Averta,
# использованной на серебряных плашках остальных этикеток.
FONT_SUBTITLE = Path(r"C:\Windows\Fonts\Montserrat-SemiBold.ttf")

BLACK = (0.102449, 0.101183, 0.095109)
LEFT_X = 18.8
LEFT_WIDTH = 118.0
BODY_SIZE = 4.2
BODY_LEADING = 4.72
BODY_GAP = 1.05

TOP_PARAGRAPHS = [
    (
        "Область применения:",
        "для реализации населению в качестве биологически активной добавки к пище - источника лактоферрина.",
    ),
    (
        "Состав:",
        "лактоферрин, оболочка капсулы (желатин).",
    ),
    (
        "Рекомендации по применению:",
        "взрослым по 1 капсуле в день во время еды, запивая небольшим количеством воды.",
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
        tokens.append((label, "ptnb_lf", bold))
    if body:
        tokens.extend((word, "ptnreg_lf", regular) for word in body.split())

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
            for value, fontname, font in line:
                page.insert_text(
                    (cursor_x, baseline),
                    value,
                    fontname=fontname,
                    fontsize=size,
                    color=BLACK,
                )
                cursor_x += text_width(value, font, size)
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
    y0, yh, y1 = 43.30, 50.10, 54.65

    page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=BLACK, width=0.35, overlay=True)
    for x in (c1, c2):
        page.draw_line((x, y0), (x, y1), color=BLACK, width=0.25, overlay=True)
    page.draw_line((x0, yh), (x1, yh), color=BLACK, width=0.25, overlay=True)

    header_size = 3.4
    page.insert_text(
        (x0 + 1.0, 47.50),
        "Биологически активные вещества",
        fontname="ptnreg_lf",
        fontsize=header_size,
        color=BLACK,
    )
    header_2 = "Содержание в 1 капсуле (суточной порции)"
    page.insert_text(
        (centered_x(header_2, regular, header_size, c1, c2), 47.50),
        header_2,
        fontname="ptnreg_lf",
        fontsize=header_size,
        color=BLACK,
    )
    header_3 = "% от АУП*"
    page.insert_text(
        (centered_x(header_3, regular, header_size, c2, x1), 47.50),
        header_3,
        fontname="ptnreg_lf",
        fontsize=header_size,
        color=BLACK,
    )

    row_size = 3.65
    baseline = 53.55
    page.insert_text(
        (x0 + 1.0, baseline),
        "Лактоферрин",
        fontname="ptnreg_lf",
        fontsize=row_size,
        color=BLACK,
    )
    page.insert_text(
        (centered_x("500 мг", regular, row_size, c1, c2), baseline),
        "500 мг",
        fontname="ptnreg_lf",
        fontsize=row_size,
        color=BLACK,
    )
    page.insert_text(
        (centered_x("-**", regular, row_size, c2, x1), baseline),
        "-**",
        fontname="ptnreg_lf",
        fontsize=row_size,
        color=BLACK,
    )


def draw_tracked_centered_text(
    page: fitz.Page,
    text: str,
    font: fitz.Font,
    fontname: str,
    size: float,
    tracking: float,
    x0: float,
    x1: float,
    baseline: float,
) -> None:
    glyph_width = sum(text_width(char, font, size) for char in text)
    total_width = glyph_width + tracking * max(0, len(text) - 1)
    cursor_x = (x0 + x1 - total_width) / 2
    for char in text:
        page.insert_text(
            (cursor_x, baseline),
            char,
            fontname=fontname,
            fontsize=size,
            color=BLACK,
        )
        cursor_x += text_width(char, font, size) + tracking


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(SOURCE)
    page = doc[0]
    reference = fitz.open(REFERENCE)
    ref_page = reference[0]

    if abs(page.rect.width - 447.874) > 0.1 or abs(page.rect.height - 147.402) > 0.1:
        raise RuntimeError(f"Неожиданный размер исходника: {page.rect}")

    # В эталоне удаляем только буквы подзаголовка, сохраняя серебряный градиент.
    ref_page.add_redact_annot(fitz.Rect(159.0, 74.0, 290.0, 85.2), fill=None)
    ref_page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_NONE,
    )

    # Пересобираем левый текст, нижний декоративный блок и правую служебную часть.
    for rect in (
        fitz.Rect(17.5, 8.0, 137.5, 137.2),
        fitz.Rect(194.0, 7.5, 294.0, 44.5),
        fitz.Rect(153.8, 73.0, 294.0, 87.0),
        fitz.Rect(151.0, 89.0, 296.5, 140.0),
        fitz.Rect(304.0, 0.0, page.rect.width, 91.2),
    ):
        page.add_redact_annot(rect, fill=(1.0, 1.0, 1.0))
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    header_clip = fitz.Rect(194.0, 7.5, 294.0, 44.5)
    subtitle_clip = fitz.Rect(153.8, 73.0, 294.0, 87.0)
    lower_clip = fitz.Rect(151.0, 89.0, 296.5, 140.0)
    right_clip = fitz.Rect(304.0, 0.0, page.rect.width, 91.2)
    page.show_pdf_page(header_clip, reference, 0, clip=header_clip, keep_proportion=True)
    page.show_pdf_page(subtitle_clip, reference, 0, clip=subtitle_clip, keep_proportion=True)
    page.show_pdf_page(lower_clip, reference, 0, clip=lower_clip, keep_proportion=True)
    page.show_pdf_page(right_clip, reference, 0, clip=right_clip, keep_proportion=True)

    page.insert_font(fontname="ptnreg_lf", fontfile=str(FONT_REGULAR))
    page.insert_font(fontname="ptnb_lf", fontfile=str(FONT_BOLD))
    page.insert_font(fontname="futura_sub_lf", fontfile=str(FONT_SUBTITLE))
    regular = fitz.Font(fontfile=str(FONT_REGULAR))
    bold = fitz.Font(fontfile=str(FONT_BOLD))
    subtitle_font = fitz.Font(fontfile=str(FONT_SUBTITLE))

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
        baseline=59.15,
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
        baseline=78.00,
        size=BODY_SIZE,
        leading=BODY_LEADING,
        gap=1.10,
        regular=regular,
        bold=bold,
    )
    if bottom_cursor > 136.0:
        raise RuntimeError(
            f"Нижний левый блок не помещается: lines={bottom_lines}, cursor={bottom_cursor:.3f}"
        )

    draw_tracked_centered_text(
        page,
        "500 МГ В КАПСУЛЕ",
        subtitle_font,
        "futura_sub_lf",
        size=8.0,
        tracking=1.85,
        x0=158.0,
        x1=289.5,
        baseline=83.65,
    )

    doc.subset_fonts()
    doc.save(OUT_PDF, garbage=4, deflate=True)

    pix_300 = page.get_pixmap(dpi=300, alpha=False)
    pix_300.save(OUT_PNG_300)
    pix_600 = page.get_pixmap(dpi=600, alpha=False)
    pix_600.save(OUT_PNG_600)

    svg = page.get_svg_image(text_as_path=True)
    svg = re.sub(r'width="[^"]+"', 'width="158mm"', svg, count=1)
    svg = re.sub(r'height="[^"]+"', 'height="52mm"', svg, count=1)
    OUT_SVG.write_text(svg, encoding="utf-8")

    reference.close()
    doc.close()

    print(f"PDF: {OUT_PDF}")
    print(f"SVG: {OUT_SVG}")
    print(f"PNG 300: {OUT_PNG_300} ({pix_300.width}x{pix_300.height})")
    print(f"PNG 600: {OUT_PNG_600} ({pix_600.width}x{pix_600.height})")
    print(f"Lines: top={top_lines}, footnotes={footnote_lines}, bottom={bottom_lines}")


if __name__ == "__main__":
    main()
