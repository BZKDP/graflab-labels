from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import zxingcpp
from PIL import Image, ImageChops, ImageDraw

from build_batch_dates_2026_08_09 import OUT_DIR as DATED_DIR, SPECS
from build_batch_original_product import LARGE, OUT_DIR, PHRASE, STANDARD


QA_DIR = OUT_DIR / "qa"
EXPECTED = [
    ([157.99999, 52.00001], "400000001210", fitz.Rect(304, 0, 447.8, 147.4), STANDARD),
    ([220.00001, 42.0], "4627174095012", fitz.Rect(458, 0, 570, 119.0), LARGE),
    ([157.99999, 52.00001], "4627174095012", fitz.Rect(304, 0, 447.8, 147.4), STANDARD),
    ([157.99999, 52.00001], "4627174095128", fitz.Rect(304, 0, 447.8, 147.4), STANDARD),
]


def render(pdf: Path, dpi: int) -> tuple[Image.Image, fitz.Rect]:
    doc = fitz.open(pdf)
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(image: Image.Image) -> list[dict[str, object]]:
    return [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(image)
    ]


def main() -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for index, (spec, expected) in enumerate(zip(SPECS, EXPECTED), 1):
        page_mm_expected, barcode_expected, code_rect, geometry = expected
        source = DATED_DIR / spec["output"]
        final = OUT_DIR / spec["output"]
        source_image, source_rect = render(source, 600)
        final_image, final_rect = render(final, 600)
        if source_rect != final_rect or source_image.size != final_image.size:
            raise RuntimeError(f"Размер изменился в файле {index}")

        final_image.save(QA_DIR / f"{index:02d}_full_600dpi.png")
        caption_rect = (
            fitz.Rect(150, 88, 300, 108)
            if index != 2
            else fitz.Rect(255, 79, 405, 97)
        )
        caption_image = crop_pt(final_image, final_rect, caption_rect)
        caption_image.save(QA_DIR / f"{index:02d}_caption_600dpi.png")

        diff = ImageChops.difference(source_image, final_image)
        diff_mask = diff.convert("L").point(lambda value: 255 if value > 3 else 0)
        allowed_mask = Image.new("L", final_image.size, 0)
        draw = ImageDraw.Draw(allowed_mask)
        sx = final_image.width / final_rect.width
        sy = final_image.height / final_rect.height
        cover = geometry["cover"]
        permitted = fitz.Rect(cover.x0 - 1.5, cover.y0 - 1.0, cover.x1 + 1.5, cover.y1 + 1.0)
        draw.rectangle(
            (
                round(permitted.x0 * sx),
                round(permitted.y0 * sy),
                round(permitted.x1 * sx),
                round(permitted.y1 * sy),
            ),
            fill=255,
        )
        outside_diff = ImageChops.multiply(diff_mask, ImageChops.invert(allowed_mask))

        doc = fitz.open(final)
        page = doc[0]
        text = page.get_text("text")
        compact_text = re.sub(r"\s+", "", text)
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
        fonts = [font[3] for font in doc.get_page_fonts(0, full=True)]
        doc.close()

        codes = decode(crop_pt(final_image, final_rect, code_rect))
        item = {
            "index": index,
            "label": spec["label"],
            "filename": final.name,
            "sha256": sha256(final),
            "page_mm": page_mm,
            "render_600dpi_px": final_image.size,
            "original_product_present": PHRASE.replace(" ", "") in compact_text,
            "manufactured_present": "09.08.2026" in text,
            "expires_present": "09.08.2028" in text,
            "outside_word_count": len(outside_words),
            "pixel_diff_bbox": diff_mask.getbbox(),
            "pixel_diff_outside_caption_bbox": outside_diff.getbbox(),
            "arial_font_embedded": any("Arial" in font for font in fonts),
            "decoded_codes": codes,
        }
        results.append(item)

        if page_mm != page_mm_expected:
            raise RuntimeError(f"Неверный размер страницы в файле {index}: {page_mm}")
        if not item["original_product_present"]:
            raise RuntimeError(f"Новая надпись не обнаружена в файле {index}")
        if not item["manufactured_present"] or not item["expires_present"]:
            raise RuntimeError(f"Даты повреждены в файле {index}")
        if outside_words:
            raise RuntimeError(f"Есть текст за страницей в файле {index}")
        if outside_diff.getbbox() is not None:
            raise RuntimeError(f"Изменения вышли за декоративную строку в файле {index}")
        if not item["arial_font_embedded"]:
            raise RuntimeError(f"Шрифт новой надписи не встроен в файл {index}")
        if not any(code["text"] == "https://graf-lab.ru/" and code["valid"] for code in codes):
            raise RuntimeError(f"QR не читается в файле {index}")
        if not any(code["text"] == barcode_expected and code["valid"] for code in codes):
            raise RuntimeError(f"Штрихкод не читается в файле {index}")

    report = {"replacement": PHRASE, "files": results}
    (QA_DIR / "qa-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
