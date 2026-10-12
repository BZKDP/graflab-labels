from __future__ import annotations
from pathlib import Path

import fitz

from build_batch_dates_2026_08_09 import SPECS
from build_batch_original_product import OUT_DIR


COMBINED = OUT_DIR / "00_ВСЕ_4_ЭТИКЕТКИ_ORIGINAL_PRODUCT.pdf"


def main() -> None:
    combined = fitz.open()
    expected_sizes = []
    for spec in SPECS:
        source = OUT_DIR / spec["output"]
        doc = fitz.open(source)
        expected_sizes.append((doc[0].rect.width, doc[0].rect.height))
        combined.insert_pdf(doc)
        doc.close()
    combined.save(COMBINED, garbage=4, deflate=True)
    combined.close()

    check = fitz.open(COMBINED)
    actual_sizes = [(page.rect.width, page.rect.height) for page in check]
    if check.page_count != 4 or actual_sizes != expected_sizes:
        raise RuntimeError("Общий PDF не сохранил размеры отдельных этикеток")
    print(f"Combined PDF: {COMBINED}")
    for index, page in enumerate(check, 1):
        print(
            f"  page {index}: "
            f"{page.rect.width * 25.4 / 72:.5f}x{page.rect.height * 25.4 / 72:.5f} mm"
        )
    check.close()


if __name__ == "__main__":
    main()
