# -*- coding: utf-8 -*-
"""Замена декоративной надписи DIETARY SUPPLEMENT на ORIGINAL PRODUCT."""
from __future__ import annotations

from pathlib import Path

import fitz

from build_batch_dates_2026_08_09 import OUT_DIR as DATED_DIR, SPECS


OUT_DIR = Path(__file__).resolve().parent / 'output/pdf/PRINT_BATCH_2026-08-09_ORIGINAL_PRODUCT'
PREVIEW_DIR = OUT_DIR / "previews"
# Исходная декоративная строка выполнена геометрической Futura Book,
# а не Arial. Сравнение букв D/E/T/A/R/Y/S/U/P/L/M/N при 600 dpi
# подтверждает совпадение формы и толщины штрихов.
FONT_REGULAR = Path(r"C:\Windows\Fonts\Futura Bk BT Book.ttf")
BLACK = (0.102449, 0.101183, 0.095109)
PHRASE = "ORIGINAL PRODUCT"

STANDARD = {
    # Геометрия снята с исходной строки DIETARY SUPPLEMENT при 1200 dpi:
    # bbox 160.62..287.28 x 98.10..101.58 pt.
    "cover": fitz.Rect(158.8, 96.7, 289.0, 102.9),
    "center_x": 223.94,
    "baseline": 101.52,
    "font_size": 4.68,
    "target_width": 126.66,
}

LARGE = {
    # Геометрия исходной строки на макете 220 x 42 мм:
    # bbox 284.68..372.46 x 86.70..89.10 pt.
    "cover": fitz.Rect(282.0, 85.8, 375.2, 90.1),
    "center_x": 328.57,
    "baseline": 89.05,
    "font_size": 3.23,
    "target_width": 87.78,
}


def draw_tracked_text(
    page: fitz.Page,
    fontname: str,
    font: fitz.Font,
    text: str,
    center_x: float,
    baseline: float,
    font_size: float,
    target_width: float,
) -> None:
    widths = [font.text_length(char, fontsize=font_size) for char in text]
    tracking = (target_width - sum(widths)) / (len(text) - 1)
    if tracking <= 0:
        raise RuntimeError("Недостаточная ширина для межбуквенного интервала")

    cursor_x = center_x - target_width / 2
    for index, (char, width) in enumerate(zip(text, widths)):
        if char != " ":
            page.insert_text(
                (cursor_x, baseline),
                char,
                fontname=fontname,
                fontsize=font_size,
                color=BLACK,
            )
        cursor_x += width
        if index < len(text) - 1:
            cursor_x += tracking

    if abs(cursor_x - (center_x + target_width / 2)) > 0.01:
        raise RuntimeError("Ошибка центрирования декоративной надписи")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    font = fitz.Font(fontfile=str(FONT_REGULAR))

    for index, spec in enumerate(SPECS, 1):
        source = DATED_DIR / spec["output"]
        output = OUT_DIR / spec["output"]
        doc = fitz.open(source)
        page = doc[0]
        geometry = LARGE if index == 2 else STANDARD

        # Прежняя строка удаляется из PDF, а не маскируется белой заплаткой.
        # Рамка и золотые знаки расположены вне зоны удаления.
        page.add_redact_annot(geometry["cover"], fill=(1.0, 1.0, 1.0))
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,
            graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
        )

        fontname = f"arialproduct{index}"
        page.insert_font(fontname=fontname, fontfile=str(FONT_REGULAR))
        draw_tracked_text(
            page,
            fontname,
            font,
            PHRASE,
            geometry["center_x"],
            geometry["baseline"],
            geometry["font_size"],
            geometry["target_width"],
        )

        doc.subset_fonts()
        doc.save(output, garbage=4, deflate=True)
        pix = doc[0].get_pixmap(dpi=300, alpha=False)
        pix.save(PREVIEW_DIR / f"{index:02d}_preview_300dpi.png")
        print(f"{index}. {spec['label']}: {output.name}; {pix.width}x{pix.height}px")
        doc.close()


if __name__ == "__main__":
    main()
