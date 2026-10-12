from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz
import zxingcpp
from PIL import Image, ImageChops, ImageDraw

from build_batch_dates_2026_08_09 import (
    EXPIRES,
    LARGE_RECTS,
    MADE,
    OUT_DIR,
    SPECS,
    STANDARD_RECTS,
)


QA_DIR = OUT_DIR / "qa"

EXPECTED = [
    {
        "page_mm": [157.99999, 52.00001],
        "barcode": "400000001210",
        "old_dates": ["04.03.2026", "04.03.2028"],
        "code_crop": fitz.Rect(304, 0, 447.8, 147.4),
        "allowed": [fitz.Rect(315.7, 72.4, 359.5, 86.0), fitz.Rect(384.7, 72.4, 433.5, 86.0)],
    },
    {
        "page_mm": [220.00001, 42.0],
        "barcode": "4627174095012",
        "old_dates": ["04.08.2025", "04.08.2027"],
        "code_crop": fitz.Rect(458, 0, 570, 119.0),
        "allowed": [fitz.Rect(463.3, 58.7, 503.5, 71.0), fitz.Rect(523.3, 58.7, 562.7, 71.0)],
    },
    {
        "page_mm": [157.99999, 52.00001],
        "barcode": "4627174095012",
        "old_dates": ["04.08.2025", "04.08.2027"],
        "code_crop": fitz.Rect(304, 0, 447.8, 147.4),
        "allowed": [fitz.Rect(315.7, 72.4, 359.5, 86.0), fitz.Rect(384.7, 72.4, 433.5, 86.0)],
    },
    {
        "page_mm": [157.99999, 52.00001],
        "barcode": "4627174095128",
        "old_dates": ["09.06.2026", "09.06.2028"],
        "code_crop": fitz.Rect(304, 0, 447.8, 147.4),
        "allowed": [fitz.Rect(315.7, 72.4, 359.5, 86.0), fitz.Rect(384.7, 72.4, 433.5, 86.0)],
    },
]


def render(pdf: Path, dpi: int) -> tuple[Image.Image, fitz.Rect]:
    doc = fitz.open(pdf)
    page_rect = doc[0].rect
    pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return image, page_rect


def crop_pt(image: Image.Image, page: fitz.Rect, rect: fitz.Rect) -> Image.Image:
    sx = image.width / page.width
    sy = image.height / page.height
    return image.crop((
        round(rect.x0 * sx),
        round(rect.y0 * sy),
        round(rect.x1 * sx),
        round(rect.y1 * sy),
    ))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decoded(image: Image.Image) -> list[dict[str, object]]:
    return [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(image)
    ]


def main() -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for index, (spec, expected) in enumerate(zip(SPECS, EXPECTED), 1):
        source = spec["source"]
        final = OUT_DIR / spec["output"]
        source_image, source_rect = render(source, 600)
        final_image, final_rect = render(final, 600)
        if source_rect != final_rect or source_image.size != final_image.size:
            raise RuntimeError(f"Размер изменился в файле {index}")

        final_image.save(QA_DIR / f"{index:02d}_full_600dpi.png")
        date_crop_rect = (
            fitz.Rect(308, 68, 439, 91)
            if index != 2
            else fitz.Rect(458, 55, 567, 75)
        )
        crop_pt(final_image, final_rect, date_crop_rect).save(
            QA_DIR / f"{index:02d}_dates_600dpi.png"
        )

        diff = ImageChops.difference(source_image, final_image)
        diff_mask = diff.convert("L").point(lambda value: 255 if value > 3 else 0)
        allowed_mask = Image.new("L", final_image.size, 0)
        draw = ImageDraw.Draw(allowed_mask)
        sx = final_image.width / final_rect.width
        sy = final_image.height / final_rect.height
        for rect in expected["allowed"]:
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

        code_crop = crop_pt(final_image, final_rect, expected["code_crop"])
        codes = decoded(code_crop)
        unique_codes = []
        seen = set()
        for code in codes:
            key = (code["format"], code["text"])
            if key not in seen:
                unique_codes.append(code)
                seen.add(key)

        item = {
            "index": index,
            "label": spec["label"],
            "filename": final.name,
            "sha256": sha256(final),
            "page_mm": page_mm,
            "render_600dpi_px": final_image.size,
            "date_made_present": MADE in text,
            "date_expiry_present": EXPIRES in text,
            "old_dates_present": [date for date in expected["old_dates"] if date in text],
            "outside_word_count": len(outside_words),
            "pixel_diff_bbox": diff_mask.getbbox(),
            "pixel_diff_outside_dates_bbox": outside_diff.getbbox(),
            "decoded_codes": unique_codes,
        }
        results.append(item)

        if page_mm != expected["page_mm"]:
            raise RuntimeError(f"Неверный размер страницы в файле {index}: {page_mm}")
        if MADE not in text or EXPIRES not in text or item["old_dates_present"]:
            raise RuntimeError(f"Проверка дат не пройдена в файле {index}")
        if outside_words:
            raise RuntimeError(f"Есть текст за страницей в файле {index}")
        if outside_diff.getbbox() is not None:
            raise RuntimeError(f"Изменения вышли за поля дат в файле {index}")
        if not any(code["text"] == "https://graf-lab.ru/" and code["valid"] for code in codes):
            raise RuntimeError(f"QR не читается в файле {index}")
        if not any(code["text"] == expected["barcode"] and code["valid"] for code in codes):
            raise RuntimeError(f"Штрихкод не читается в файле {index}")

    report = {
        "manufactured": MADE,
        "expires": EXPIRES,
        "files": results,
    }
    (QA_DIR / "qa-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
