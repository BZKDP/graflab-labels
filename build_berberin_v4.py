# -*- coding: utf-8 -*-
"""BERBERIN v4: правки по двум сообщениям сотрудника и присланному эталону.

Источник дизайна: BERBERIN_v2_158x52mm.pdf.
Эталон обязательных надписей и ритма левого блока:
1787900292255-549080441.pdf (COLLAGEN UP, CorelDRAW 2026).
Эталон пропорций центрального названия: старая этикетка берберин.pdf.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "BERBERIN_v2_158x52mm.pdf"
OLD_LABEL = Path(__file__).resolve().parent / "input" / 'Telegram Desktop/берберин.pdf'

OUT_PDF = ROOT / "BERBERIN_v4_REVIEW_2026-06-09_158x52mm.pdf"
OUT_SVG = ROOT / "BERBERIN_v4_REVIEW_2026-06-09_158x52mm_outlined.svg"
OUT_PNG = ROOT / "BERBERIN_v4_REVIEW_2026-06-09_preview_300dpi.png"

PT_SANS_NARROW_REGULAR = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf")
PT_SANS_NARROW_BOLD = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")

BLACK = (0.102449, 0.101183, 0.095109)
BLUE = (0.0, 0.401190, 0.587304)

BODY_SIZE = 5.7
BODY_X = 19.0
BODY_MAX_WIDTH = 116.0
FIRST_BASELINE = 18.642
LINE_LEADING = 5.664
PARAGRAPH_GAP = 1.524

PARAGRAPHS = [
    (
        "Область применения:",
        "для реализации населению в качестве биологически активной добавки к пище - источника берберина.",
    ),
    (
        "Рекомендации по применению:",
        "взрослым по 1 капсуле в день во время еды.",
    ),
    (
        "Состав:",
        "берберин, микрокристаллическая целлюлоза, агент антислеживающий - диоксид кремния аморфный, оболочка капсулы (желатин).",
    ),
    ("Срок годности:", "2 года от даты изготовления."),
    (
        "Условия хранения:",
        "в сухом месте, беречь от попадания солнечных лучей.",
    ),
    ("Не является лекарственным средством", ""),
]


def width(text: str, font: fitz.Font) -> float:
    return font.text_length(text, fontsize=BODY_SIZE)


def wrap_paragraph(
    label: str,
    body: str,
    regular: fitz.Font,
    bold: fitz.Font,
) -> list[list[tuple[str, str, fitz.Font]]]:
    tokens: list[tuple[str, str, fitz.Font]] = [(label, "ptnbv4", bold)]
    if body:
        tokens.extend((word, "ptnregv4", regular) for word in body.split())

    lines: list[list[tuple[str, str, fitz.Font]]] = []
    current: list[tuple[str, str, fitz.Font]] = []
    current_width = 0.0
    for token, fontname, font in tokens:
        rendered = token if not current else " " + token
        rendered_width = width(rendered, font)
        if current and current_width + rendered_width > BODY_MAX_WIDTH:
            lines.append(current)
            current = [(token, fontname, font)]
            current_width = width(token, font)
        else:
            current.append((rendered, fontname, font))
            current_width += rendered_width
    if current:
        lines.append(current)
    return lines


def main() -> None:
    doc = fitz.open(SOURCE)
    page = doc[0]
    old_label = fitz.open(OLD_LABEL)

    regular = fitz.Font(fontfile=str(PT_SANS_NARROW_REGULAR))
    bold = fitz.Font(fontfile=str(PT_SANS_NARROW_BOLD))

    # Удаляем только старый левый текст, увеличенное название и старые значения дат.
    redactions = [
        fitz.Rect(18.0, 12.0, 136.5, 93.0),
        fitz.Rect(175.0, 40.0, 279.0, 70.9),
        fitz.Rect(316.70, 74.80, 358.00, 83.50),
        fitz.Rect(385.90, 74.80, 432.10, 83.50),
    ]
    for rect in redactions:
        page.add_redact_annot(rect, fill=None)
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    # Точные пропорции и позиция слова «БЕРБЕРИН» со старой этикетки.
    title_clip = fitz.Rect(175.20, 48.00, 271.05, 67.95)
    page.show_pdf_page(title_clip, old_label, 0, clip=title_clip, keep_proportion=True)

    page.insert_font(fontname="ptnregv4", fontfile=str(PT_SANS_NARROW_REGULAR))
    page.insert_font(fontname="ptnbv4", fontfile=str(PT_SANS_NARROW_BOLD))

    # Левый блок повторяет кегль и вертикальный ритм присланного корректного примера.
    baseline = FIRST_BASELINE
    rendered_lines = 0
    for paragraph_index, (label, body) in enumerate(PARAGRAPHS):
        lines = wrap_paragraph(label, body, regular, bold)
        for line in lines:
            cursor_x = BODY_X
            for text, fontname, font in line:
                page.insert_text(
                    (cursor_x, baseline),
                    text,
                    fontname=fontname,
                    fontsize=BODY_SIZE,
                    color=BLACK,
                )
                cursor_x += width(text, font)
            baseline += LINE_LEADING
            rendered_lines += 1
        if paragraph_index < len(PARAGRAPHS) - 1:
            baseline += PARAGRAPH_GAP

    if rendered_lines != 12:
        raise RuntimeError(f"Неожиданное число строк слева: {rendered_lines}, ожидалось 12")
    if baseline > 95.0:
        raise RuntimeError(f"Левый текст не помещается до таблицы: baseline={baseline}")

    # Заголовки полей остаются исходными векторными; меняются только значения.
    page.insert_text(
        (317.78, 82.40),
        "09.06.2026",
        fontname="ptnbv4",
        fontsize=9.0,
        color=BLUE,
    )
    page.insert_text(
        (391.80, 82.40),
        "09.06.2028",
        fontname="ptnbv4",
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

    old_label.close()
    doc.close()

    print(f"PDF: {OUT_PDF}")
    print(f"SVG: {OUT_SVG}")
    print(f"PNG: {OUT_PNG} ({pix.width}x{pix.height})")
    print(f"Left body lines: {rendered_lines}; final baseline cursor: {baseline:.3f}")


if __name__ == "__main__":
    main()
