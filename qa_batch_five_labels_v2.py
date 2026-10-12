from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import zxingcpp
from PIL import Image, ImageChops, ImageDraw

from build_batch_dates_2026_08_09 import SPECS
from build_batch_five_labels_v2 import GELATIN_NAME, GELATIN_SOURCE, OUT_DIR
from build_batch_original_product import OUT_DIR as FOUR_LABEL_DIR


QA_DIR = OUT_DIR / "qa"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(path: Path, dpi: int) -> tuple[Image.Image, fitz.Rect]:
    doc = fitz.open(path)
    rect = doc[0].rect
    pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return image, rect


def crop_pt(image: Image.Image, page: fitz.Rect, rect: fitz.Rect) -> Image.Image:
    sx = image.width / page.width
    sy = image.height / page.height
    return image.crop((
        round(rect.x0 * sx),
        round(rect.y0 * sy),
        round(rect.x1 * sx),
        round(rect.y1 * sy),
    ))


def decode(image: Image.Image) -> list[dict[str, object]]:
    return [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(image)
    ]


def main() -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)

    finals = [OUT_DIR / spec["output"] for spec in SPECS] + [OUT_DIR / GELATIN_NAME]
    sources = [
        FOUR_LABEL_DIR / SPECS[0]["output"],
        FOUR_LABEL_DIR / SPECS[1]["output"],
        FOUR_LABEL_DIR / SPECS[2]["output"],
        FOUR_LABEL_DIR / SPECS[3]["output"],
        GELATIN_SOURCE,
    ]
    expected = [
        ([157.99999, 52.00001], "400000001210", fitz.Rect(304, 0, 447.8, 147.4)),
        ([220.00001, 42.0], "4627174095012", fitz.Rect(458, 0, 570, 119.0)),
        ([157.99999, 52.00001], "4627174095012", fitz.Rect(304, 0, 447.8, 147.4)),
        ([157.99999, 52.00001], "4627174095128", fitz.Rect(304, 0, 447.8, 147.4)),
        ([220.00001, 42.0], "652861588677", fitz.Rect(458, 0, 570, 119.0)),
    ]
    permitted = [
        [],
        [fitz.Rect(315.8, 88.8, 342.2, 113.6)],
        [fitz.Rect(357.0, 18.8, 434.0, 26.2)],
        [fitz.Rect(355.0, 96.0, 436.0, 141.5)],
        [
            fitz.Rect(462.8, 58.5, 503.5, 71.0),
            fitz.Rect(522.8, 58.5, 562.8, 71.0),
            fitz.Rect(277.5, 83.0, 379.5, 91.0),
            fitz.Rect(496.3, 78.8, 562.7, 113.8),
        ],
    ]

    results = []
    for index, (source, final, exp, allowed_rects) in enumerate(
        zip(sources, finals, expected, permitted), 1
    ):
        page_mm_expected, barcode_expected, code_rect = exp
        source_image, source_rect = render(source, 600)
        final_image, final_rect = render(final, 600)
        if source_rect != final_rect or source_image.size != final_image.size:
            raise RuntimeError(f"Изменился размер файла {index}")

        final_image.save(QA_DIR / f"{index:02d}_full_600dpi.png")
        if index == 2:
            crop_pt(final_image, final_rect, fitz.Rect(309, 82, 349, 117)).save(
                QA_DIR / "02_badge_120_600dpi.png"
            )
        if index == 5:
            crop_pt(final_image, final_rect, fitz.Rect(458, 55, 567, 117)).save(
                QA_DIR / "05_dates_and_barcode_600dpi.png"
            )

        diff = ImageChops.difference(source_image, final_image)
        diff_mask = diff.convert("L").point(lambda value: 255 if value > 3 else 0)
        allowed_mask = Image.new("L", final_image.size, 0)
        draw = ImageDraw.Draw(allowed_mask)
        sx = final_image.width / final_rect.width
        sy = final_image.height / final_rect.height
        for rect in allowed_rects:
            draw.rectangle(
                (
                    round(rect.x0 * sx),
                    round(rect.y0 * sy),
                    round(rect.x1 * sx),
                    round(rect.y1 * sy),
                ),
                fill=255,
            )
        outside_diff = ImageChops.multiply(diff_mask, ImageChops.invert(allowed_mask))

        doc = fitz.open(final)
        page = doc[0]
        text = page.get_text("text")
        compact = re.sub(r"\s+", "", text)
        words = page.get_text("words")
        outside_words = [
            word for word in words
            if word[0] < 0 or word[1] < 0
            or word[2] > page.rect.width or word[3] > page.rect.height
        ]
        page_mm = [
            round(page.rect.width * 25.4 / 72, 5),
            round(page.rect.height * 25.4 / 72, 5),
        ]
        doc.close()

        codes = decode(crop_pt(final_image, final_rect, code_rect))
        item = {
            "index": index,
            "filename": final.name,
            "sha256": sha256(final),
            "page_mm": page_mm,
            "render_600dpi_px": final_image.size,
            "original_product_present": "ORIGINALPRODUCT" in compact,
            "manufactured_present": "09.08.2026" in compact,
            "expires_present": "09.08.2028" in compact,
            "badge_120_present": index != 2 or "120" in compact,
            "outside_word_count": len(outside_words),
            "pixel_diff_bbox": diff_mask.getbbox(),
            "pixel_diff_outside_permitted_bbox": outside_diff.getbbox(),
            "decoded_codes": codes,
        }
        results.append(item)

        if page_mm != page_mm_expected:
            raise RuntimeError(f"Неверный размер страницы в файле {index}: {page_mm}")
        if not item["original_product_present"]:
            raise RuntimeError(f"Нет ORIGINAL PRODUCT в файле {index}")
        if not item["manufactured_present"] or not item["expires_present"]:
            raise RuntimeError(f"Даты не прошли проверку в файле {index}")
        if not item["badge_120_present"]:
            raise RuntimeError("Нет значения 120 в большой этикетке магния")
        if outside_words:
            raise RuntimeError(f"Есть текст за страницей в файле {index}")
        if outside_diff.getbbox() is not None:
            raise RuntimeError(f"Изменения вышли за разрешённые зоны в файле {index}")
        if not any(code["text"] == "https://graf-lab.ru/" and code["valid"] for code in codes):
            raise RuntimeError(f"QR не читается в файле {index}")
        if not any(code["text"] == barcode_expected and code["valid"] for code in codes):
            raise RuntimeError(f"Штрихкод не читается в файле {index}")

    report = {"files": results}
    (QA_DIR / "qa-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
