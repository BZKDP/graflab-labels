# -*- coding: utf-8 -*-
"""Хирургическая замена дат в четырёх готовых этикетках."""
from __future__ import annotations

from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "output" / "pdf" / "PRINT_BATCH_2026-08-09"
PREVIEW_DIR = OUT_DIR / "previews"

FONT_BOLD = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")
BLUE = (0.0, 0.401190, 0.587304)
MADE = "09.08.2026"
EXPIRES = "09.08.2028"

STANDARD_RECTS = (
    fitz.Rect(316.70, 74.65, 358.50, 83.75),
    fitz.Rect(385.70, 74.65, 432.50, 83.75),
)
STANDARD_POSITIONS = ((317.78, 82.40), (391.80, 82.40))

LARGE_RECTS = (
    fitz.Rect(464.30, 60.75, 502.50, 69.45),
    fitz.Rect(524.30, 60.75, 561.70, 69.45),
)
LARGE_POSITIONS = ((465.75, 68.00), (525.75, 68.00))

SPECS = [
    {
        "source": Path(__file__).resolve().parent / "input" / '1788157165377-664393331.pdf',
        "output": "01_БЕРБЕРИН_С_ПИКОЛИНАТОМ_ХРОМА_60_158x52.pdf",
        "label": "Берберин с пиколинатом хрома, 60 капсул",
        "rects": STANDARD_RECTS,
        "positions": STANDARD_POSITIONS,
        "font_size": 9.0,
    },
    {
        "source": Path(__file__).resolve().parent / "input" / '1788157172107-568268121.pdf',
        "output": "02_МАГНИЙ_B6_120_220x42.pdf",
        "label": "Магний B6, 120 капсул",
        "rects": LARGE_RECTS,
        "positions": LARGE_POSITIONS,
        "font_size": 8.0,
    },
    {
        "source": Path(__file__).resolve().parent / "input" / '1788157176578-330167730.pdf',
        "output": "03_МАГНИЙ_B6_60_158x52.pdf",
        "label": "Магний B6, 60 капсул",
        "rects": STANDARD_RECTS,
        "positions": STANDARD_POSITIONS,
        "font_size": 9.0,
    },
    {
        "source": Path(__file__).resolve().parent / "input" / '1788157182149-772584038.pdf',
        "output": "04_БЕРБЕРИН_60_158x52.pdf",
        "label": "Берберин, 60 капсул",
        "rects": STANDARD_RECTS,
        "positions": STANDARD_POSITIONS,
        "font_size": 9.0,
    },
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    for index, spec in enumerate(SPECS, 1):
        source = spec["source"]
        output = OUT_DIR / spec["output"]
        doc = fitz.open(source)
        if doc.page_count != 1:
            raise RuntimeError(f"Ожидалась одна страница: {source}")
        page = doc[0]

        for rect in spec["rects"]:
            page.add_redact_annot(rect, fill=(1.0, 1.0, 1.0))
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,
            graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
        )

        fontname = f"ptnbdate{index}"
        page.insert_font(fontname=fontname, fontfile=str(FONT_BOLD))
        for position, value in zip(spec["positions"], (MADE, EXPIRES)):
            page.insert_text(
                position,
                value,
                fontname=fontname,
                fontsize=spec["font_size"],
                color=BLUE,
            )

        doc.subset_fonts()
        doc.save(output, garbage=4, deflate=True)
        pix = doc[0].get_pixmap(dpi=300, alpha=False)
        preview = PREVIEW_DIR / f"{index:02d}_preview_300dpi.png"
        pix.save(preview)

        page_mm = (
            page.rect.width * 25.4 / 72,
            page.rect.height * 25.4 / 72,
        )
        print(
            f"{index}. {spec['label']}: {output.name}; "
            f"{page_mm[0]:.5f}x{page_mm[1]:.5f} mm; {pix.width}x{pix.height}px"
        )
        doc.close()


if __name__ == "__main__":
    main()
