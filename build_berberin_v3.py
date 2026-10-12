# -*- coding: utf-8 -*-
"""
Финальная локальная правка BERBERIN_v2 по найденному чату Claude и handoff.

Меняется только блок дат справа:
- Дата изготовления: 09.06.2026
- второй столбец: Партия (Серия): 50609

Остальная геометрия BERBERIN_v2 остаётся неизменной.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "BERBERIN_v2_158x52mm.pdf"
OUT_PDF = ROOT / "BERBERIN_v3_2026-06-09_158x52mm.pdf"
OUT_SVG = ROOT / "BERBERIN_v3_2026-06-09_158x52mm_outlined.svg"
OUT_PNG = ROOT / "BERBERIN_v3_2026-06-09_preview_300dpi.png"

F_PTNB = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")

BLACK = (0.102449, 0.101183, 0.095109)
BLUE = (0.0, 0.401190, 0.587304)


def text_width(text: str, font: fitz.Font, size: float) -> float:
    return sum(font.glyph_advance(ord(char)) for char in text) * size


def main() -> None:
    doc = fitz.open(SOURCE)
    page = doc[0]

    # Точные зоны старого синего значения даты и второго поля. Разделительные
    # линии y=60.57 и y=88.51 pt остаются вне масок.
    date_value_zone = fitz.Rect(316.70, 74.80, 358.00, 83.50)
    second_field_zone = fitz.Rect(385.90, 64.20, 432.10, 83.50)
    for rect in (date_value_zone, second_field_zone):
        page.add_redact_annot(rect, fill=None)
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    page.insert_font(fontname="ptnbv3", fontfile=str(F_PTNB))
    ptnb = fitz.Font(fontfile=str(F_PTNB))

    # Дата остаётся по той же левой оси, что и в эталоне.
    page.insert_text(
        (317.78, 82.40),
        "09.06.2026",
        fontname="ptnbv3",
        fontsize=9.0,
        color=BLUE,
    )

    # Заголовок и номер партии центрируются по единой оси второго поля.
    field_center_x = 406.65
    party_header = "Партия (Серия):"
    header_size = 8.0
    header_x = field_center_x - text_width(party_header, ptnb, header_size) / 2
    page.insert_text(
        (header_x, 72.20),
        party_header,
        fontname="ptnbv3",
        fontsize=header_size,
        color=BLACK,
    )

    party_value = "50609"
    value_size = 9.0
    value_x = field_center_x - text_width(party_value, ptnb, value_size) / 2
    page.insert_text(
        (value_x, 82.40),
        party_value,
        fontname="ptnbv3",
        fontsize=value_size,
        color=BLUE,
    )

    doc.subset_fonts()
    doc.save(OUT_PDF, garbage=4, deflate=True)

    # Контрольное превью 300 dpi.
    pix = doc[0].get_pixmap(dpi=300, alpha=False)
    pix.save(OUT_PNG)

    # Отдельный SVG без <text>: вся типографика превращена в пути.
    svg = doc[0].get_svg_image(text_as_path=True)
    svg = re.sub(r'width="[^"]+"', 'width="158mm"', svg, count=1)
    svg = re.sub(r'height="[^"]+"', 'height="52mm"', svg, count=1)
    OUT_SVG.write_text(svg, encoding="utf-8")
    doc.close()

    print(f"PDF: {OUT_PDF}")
    print(f"SVG: {OUT_SVG}")
    print(f"PNG: {OUT_PNG} ({pix.width}x{pix.height})")


if __name__ == "__main__":
    main()
