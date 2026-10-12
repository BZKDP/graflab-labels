# -*- coding: utf-8 -*-
"""Точечная замена изготовителя и юридического адреса в заданном PDF."""
from pathlib import Path

import fitz


SOURCE = Path(__file__).resolve().parent / "input" / '1788591893804-157679005.pdf'
OUT_DIR = Path(__file__).resolve().parent / 'output/pdf/MAGNIY_B6_MAX_LAB_LEGAL_ADDRESS'
OUT_PDF = OUT_DIR / "MAGNIY_B6_60_MAX_LAB_158x52mm.pdf"
OUT_PREVIEW = OUT_DIR / "MAGNIY_B6_60_MAX_LAB_preview_300dpi.png"
OUT_QA = OUT_DIR / "MAGNIY_B6_60_MAX_LAB_QA_600dpi.png"

FONT_REGULAR = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf")
INK = (20 / 255, 20 / 255, 19 / 255)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(SOURCE)
    if doc.page_count != 1:
        raise RuntimeError(f"Ожидалась одна страница, получено: {doc.page_count}")
    page = doc[0]
    width_mm = page.rect.width * 25.4 / 72
    height_mm = page.rect.height * 25.4 / 72
    if abs(width_mm - 158.0) > 0.01 or abs(height_mm - 52.0) > 0.01:
        raise RuntimeError(f"Неожиданный размер страницы: {width_mm:.4f} x {height_mm:.4f} мм")

    # Удаляются только старое название организации и следующая строка
    # юридического адреса. Заголовок и адрес места производства не меняются.
    for rect in (
        fitz.Rect(337.75, 14.90, 432.75, 20.02),
        fitz.Rect(316.55, 19.95, 432.75, 24.82),
    ):
        page.add_redact_annot(rect, fill=(1.0, 1.0, 1.0))
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_NONE,
    )

    page.insert_font(fontname="ptn_maxlab_legal", fontfile=str(FONT_REGULAR))
    page.insert_text(
        (338.10, 19.55),
        "ООО «МАКС ЛАБ»,",
        fontname="ptn_maxlab_legal",
        fontsize=4.2,
        color=INK,
    )
    page.insert_text(
        (316.83, 24.38),
        "г. Одинцово, ул. Кутузовская, 12.",
        fontname="ptn_maxlab_legal",
        fontsize=4.2,
        color=INK,
    )

    doc.subset_fonts()
    doc.save(OUT_PDF, garbage=4, deflate=True)

    preview = page.get_pixmap(dpi=300, alpha=False)
    preview.save(OUT_PREVIEW)
    qa = page.get_pixmap(dpi=600, alpha=False)
    qa.save(OUT_QA)

    doc.close()
    print(f"PDF: {OUT_PDF}")
    print(f"Preview: {OUT_PREVIEW} ({preview.width}x{preview.height})")
    print(f"QA: {OUT_QA} ({qa.width}x{qa.height})")


if __name__ == "__main__":
    main()
