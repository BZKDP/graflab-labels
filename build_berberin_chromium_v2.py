# -*- coding: utf-8 -*-
"""Берберин с пиколинатом хрома: правки сотрудника, версия на проверку."""
from __future__ import annotations

import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
SOURCE = Path(__file__).resolve().parent / "input" / '1787907920909-476952334.pdf'

OUT_PDF = ROOT / "BERBERIN_CHROMIUM_v2_REVIEW_158x52mm.pdf"
OUT_SVG = ROOT / "BERBERIN_CHROMIUM_v2_REVIEW_158x52mm_outlined.svg"
OUT_PNG = ROOT / "BERBERIN_CHROMIUM_v2_REVIEW_preview_300dpi.png"

FONT_REGULAR = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")

BLACK = (0.102449, 0.101183, 0.095109)
BODY_SIZE = 5.2
BODY_X = 17.0
BODY_MAX_WIDTH = 116.0
FIRST_BASELINE = 13.8
LINE_LEADING = 5.3
PARAGRAPH_GAP = 0.4

PARAGRAPHS = [
    (
        "",
        "Берберин с пиколинатом хрома - это добавка, содержащая природные компоненты, поддерживающие обмен веществ и нормальное функционирование организма.",
    ),
    (
        "Инструкция по применению:",
        "принимать по одной капсуле в день, запивая водой во время приёма пищи или по назначению врача.",
    ),
    (
        "Состав:",
        "берберин, пиколинат хрома, желатиновая капсула.",
    ),
    ("Срок годности:", "2 года от даты изготовления."),
    (
        "Условия хранения:",
        "в сухом месте, беречь от попадания солнечных лучей.",
    ),
    ("Не является лекарственным средством", ""),
]


def text_width(text: str, font: fitz.Font) -> float:
    return font.text_length(text, fontsize=BODY_SIZE)


def wrap_paragraph(
    label: str,
    body: str,
    regular: fitz.Font,
    bold: fitz.Font,
) -> list[list[tuple[str, str, fitz.Font]]]:
    tokens: list[tuple[str, str, fitz.Font]] = []
    if label:
        tokens.append((label, "ptnbchrom", bold))
    if body:
        tokens.extend((word, "ptnrchrom", regular) for word in body.split())

    lines: list[list[tuple[str, str, fitz.Font]]] = []
    current: list[tuple[str, str, fitz.Font]] = []
    current_width = 0.0
    for token, fontname, font in tokens:
        rendered = token if not current else " " + token
        candidate_width = text_width(rendered, font)
        if current and current_width + candidate_width > BODY_MAX_WIDTH:
            lines.append(current)
            current = [(token, fontname, font)]
            current_width = text_width(token, font)
        else:
            current.append((rendered, fontname, font))
            current_width += candidate_width
    if current:
        lines.append(current)
    return lines


def main() -> None:
    doc = fitz.open(SOURCE)
    page = doc[0]
    regular = fitz.Font(fontfile=str(FONT_REGULAR))
    bold = fitz.Font(fontfile=str(FONT_BOLD))

    # Исходный текст переведён в кривые. Заменяется только левый верхний блок;
    # таблица, центр, QR, даты, служебные знаки и штрихкод остаются исходными.
    page.add_redact_annot(fitz.Rect(14.0, 8.0, 139.0, 80.5), fill=(1.0, 1.0, 1.0))
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    page.insert_font(fontname="ptnrchrom", fontfile=str(FONT_REGULAR))
    page.insert_font(fontname="ptnbchrom", fontfile=str(FONT_BOLD))

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
                cursor_x += text_width(text, font)
            baseline += LINE_LEADING
            rendered_lines += 1
        if paragraph_index < len(PARAGRAPHS) - 1:
            baseline += PARAGRAPH_GAP

    if rendered_lines != 11:
        raise RuntimeError(
            f"Неожиданное число строк слева: {rendered_lines}, ожидалось 11"
        )
    if baseline > 75.0:
        raise RuntimeError(f"Текст слишком близко к таблице: baseline={baseline:.3f}")

    doc.subset_fonts()
    doc.save(OUT_PDF, garbage=4, deflate=True)

    pix = doc[0].get_pixmap(dpi=300, alpha=False)
    pix.save(OUT_PNG)

    svg = doc[0].get_svg_image(text_as_path=True)
    svg = re.sub(r'width="[^"]+"', 'width="158mm"', svg, count=1)
    svg = re.sub(r'height="[^"]+"', 'height="52mm"', svg, count=1)
    OUT_SVG.write_text(svg, encoding="utf-8")
    doc.close()

    print(f"PDF: {OUT_PDF}")
    print(f"SVG: {OUT_SVG}")
    print(f"PNG: {OUT_PNG} ({pix.width}x{pix.height})")
    print(f"Left lines: {rendered_lines}; final baseline cursor: {baseline:.3f}")


if __name__ == "__main__":
    main()
