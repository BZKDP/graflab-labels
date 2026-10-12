from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import numpy as np
import zxingcpp
from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "BERBERIN_v2_158x52mm.pdf"
FINAL = ROOT / "BERBERIN_v4_REVIEW_2026-06-09_158x52mm.pdf"
SVG = ROOT / "BERBERIN_v4_REVIEW_2026-06-09_158x52mm_outlined.svg"
PREVIEW = ROOT / "BERBERIN_v4_REVIEW_2026-06-09_preview_300dpi.png"
QA = ROOT / "qa-v4"


def render(pdf: Path, dpi: int) -> Image.Image:
    doc = fitz.open(pdf)
    pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return image


def crop_pt(image: Image.Image, page: fitz.Rect, rect: fitz.Rect) -> Image.Image:
    sx = image.width / page.width
    sy = image.height / page.height
    return image.crop(
        (
            round(rect.x0 * sx),
            round(rect.y0 * sy),
            round(rect.x1 * sx),
            round(rect.y1 * sy),
        )
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def central_black_y_runs(image: Image.Image, page: fitz.Rect) -> list[list[float]]:
    rgb = np.asarray(image.convert("RGB"))
    sx = image.width / page.width
    sy = image.height / page.height
    x0, x1 = round(155 * sx), round(295 * sx)
    black = (rgb[:, :, 0] < 80) & (rgb[:, :, 1] < 80) & (rgb[:, :, 2] < 80)
    projection = black[:, x0:x1].sum(axis=1)
    active = np.where(projection > 10)[0]
    runs: list[tuple[int, int]] = []
    if len(active):
        start = previous = int(active[0])
        for value in active[1:]:
            value = int(value)
            if value > previous + 1:
                runs.append((start, previous + 1))
                start = value
            previous = value
        runs.append((start, previous + 1))
    return [
        [round(start / sy, 3), round(end / sy, 3)]
        for start, end in runs
        if 25 < start / sy < 90
    ]


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(FINAL)
    page = doc[0]
    page_rect = page.rect

    full = render(FINAL, 600)
    source = render(SOURCE, 600)
    full.save(QA / "full-600dpi.png")

    crops = {
        "left-copy-600dpi.png": fitz.Rect(14, 8, 140, 96),
        "center-title-600dpi.png": fitz.Rect(150, 28, 300, 90),
        "right-600dpi.png": fitz.Rect(304, 0, page_rect.width, page_rect.height),
        "date-expiry-600dpi.png": fitz.Rect(312, 57, 436, 92),
        "barcode-600dpi.png": fitz.Rect(350, 96, 434, 142),
    }
    for name, rect in crops.items():
        crop_pt(full, page_rect, rect).save(QA / name)

    diff = ImageChops.difference(source, full)
    mask = diff.convert("L").point(lambda value: 255 if value > 3 else 0)
    diff_visual = Image.new("RGB", full.size, "white")
    diff_visual.paste((220, 0, 0), mask=mask)
    diff_visual.save(QA / "diff-v2-v4-red.png")

    words = page.get_text("words")
    outside = [
        word
        for word in words
        if word[0] < 0
        or word[1] < 0
        or word[2] > page_rect.width
        or word[3] > page_rect.height
    ]
    extracted = page.get_text("text")
    required = [
        "Условия хранения:",
        "Не является лекарственным средством",
        "09.06.2026",
        "09.06.2028",
    ]
    forbidden = ["Партия", "50609", "04.03.2026", "04.03.2028", "�"]
    missing_required = [value for value in required if value not in extracted]
    present_forbidden = [value for value in forbidden if value in extracted]

    body_spans = []
    all_spans = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                rect = fitz.Rect(span["bbox"])
                entry = {
                    "text": span.get("text", ""),
                    "bbox": [round(v, 3) for v in rect],
                    "font": span.get("font"),
                    "size": round(span.get("size", 0), 3),
                }
                all_spans.append(entry)
                if rect.x0 < 140 and rect.y0 < 94:
                    body_spans.append(entry)

    body_bottom = max((item["bbox"][3] for item in body_spans), default=0)
    codes = [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(Image.open(PREVIEW))
    ]

    svg_text = SVG.read_text(encoding="utf-8")
    svg_size = re.search(r'<svg[^>]*width="([^"]+)"[^>]*height="([^"]+)"', svg_text)
    title_runs = central_black_y_runs(full, page_rect)

    report = {
        "pdf_sha256": sha256(FINAL),
        "page_count": doc.page_count,
        "page_mm": [
            round(page_rect.width * 25.4 / 72, 5),
            round(page_rect.height * 25.4 / 72, 5),
        ],
        "preview_px": Image.open(PREVIEW).size,
        "render_600dpi_px": full.size,
        "outside_word_count": len(outside),
        "missing_required_text": missing_required,
        "present_forbidden_text": present_forbidden,
        "left_body_bottom_pt": body_bottom,
        "left_table_clearance_pt": round(94.0 - body_bottom, 3),
        "central_black_y_runs_pt": title_runs,
        "decoded_codes": codes,
        "svg_text_elements": len(re.findall(r"<text\b", svg_text)),
        "svg_size": list(svg_size.groups()) if svg_size else None,
        "pdf_fonts": [font[3] for font in doc.get_page_fonts(0, full=True)],
        "body_spans": body_spans,
        "qa_files": [str(QA / name) for name in [
            "full-600dpi.png",
            "left-copy-600dpi.png",
            "center-title-600dpi.png",
            "right-600dpi.png",
            "date-expiry-600dpi.png",
            "barcode-600dpi.png",
            "diff-v2-v4-red.png",
        ]],
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if doc.page_count != 1 or report["page_mm"] != [157.99999, 52.00001]:
        raise RuntimeError("Неверный формат страницы")
    if outside or missing_required or present_forbidden:
        raise RuntimeError("Текстовая проверка не пройдена")
    if body_bottom >= 94.0:
        raise RuntimeError("Левый текст заходит на таблицу")
    if not any(code["text"] == "https://graf-lab.ru/" and code["valid"] for code in codes):
        raise RuntimeError("QR не читается")
    if not any(code["text"] == "4627174095128" and code["valid"] for code in codes):
        raise RuntimeError("Штрихкод не читается")
    if report["svg_text_elements"] != 0 or report["svg_size"] != ["158mm", "52mm"]:
        raise RuntimeError("SVG не прошел проверку")

    (QA / "qa-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    doc.close()


if __name__ == "__main__":
    main()
