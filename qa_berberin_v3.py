from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import zxingcpp
from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "BERBERIN_v2_158x52mm.pdf"
FINAL = ROOT / "BERBERIN_v3_2026-06-09_158x52mm.pdf"
SVG = ROOT / "BERBERIN_v3_2026-06-09_158x52mm_outlined.svg"
PREVIEW = ROOT / "BERBERIN_v3_2026-06-09_preview_300dpi.png"
QA = ROOT / "qa-v3"


def render(pdf: Path, dpi: int) -> Image.Image:
    doc = fitz.open(pdf)
    pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return image


def crop_pt(image: Image.Image, page: fitz.Rect, rect: fitz.Rect) -> Image.Image:
    sx = image.width / page.width
    sy = image.height / page.height
    box = (
        round(rect.x0 * sx),
        round(rect.y0 * sy),
        round(rect.x1 * sx),
        round(rect.y1 * sy),
    )
    return image.crop(box)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    final_doc = fitz.open(FINAL)
    page = final_doc[0]
    page_rect = page.rect

    full = render(FINAL, 600)
    source = render(SOURCE, 600)
    full.save(QA / "full-600dpi.png")

    crops = {
        "left-600dpi.png": fitz.Rect(0, 0, 148, page_rect.height),
        "center-600dpi.png": fitz.Rect(148, 0, 304, page_rect.height),
        "right-600dpi.png": fitz.Rect(304, 0, page_rect.width, page_rect.height),
        "date-party-600dpi.png": fitz.Rect(312, 57, 436, 92),
        "barcode-600dpi.png": fitz.Rect(350, 96, 434, 142),
    }
    for name, rect in crops.items():
        crop_pt(full, page_rect, rect).save(QA / name)

    diff = ImageChops.difference(source, full)
    bbox_px = diff.getbbox()
    mask = diff.convert("L").point(lambda value: 255 if value > 3 else 0)
    diff_visual = Image.new("RGB", full.size, "white")
    diff_visual.paste((220, 0, 0), mask=mask)
    diff_visual.save(QA / "diff-v2-v3-red.png")

    words = page.get_text("words")
    outside = [
        word for word in words
        if word[0] < 0 or word[1] < 0 or word[2] > page_rect.width or word[3] > page_rect.height
    ]
    spans = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text") in {"09.06.2026", "Партия (Серия):", "50609"}:
                    spans.append(
                        {
                            "text": span["text"],
                            "bbox": [round(value, 3) for value in span["bbox"]],
                            "font": span["font"],
                            "size": round(span["size"], 3),
                            "color": f"#{span['color'] & 0xFFFFFF:06X}",
                        }
                    )

    decoded = [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(Image.open(PREVIEW))
    ]
    svg_text = SVG.read_text(encoding="utf-8")
    svg_size = re.search(r'<svg[^>]*width="([^"]+)"[^>]*height="([^"]+)"', svg_text)

    report = {
        "pdf_sha256": sha256(FINAL),
        "page_count": final_doc.page_count,
        "page_mm": [
            round(page_rect.width * 25.4 / 72, 5),
            round(page_rect.height * 25.4 / 72, 5),
        ],
        "preview_px": Image.open(PREVIEW).size,
        "render_600dpi_px": full.size,
        "word_count": len(words),
        "outside_word_count": len(outside),
        "drawings": len(page.get_drawings()),
        "images": len(page.get_images(full=True)),
        "edited_text_spans": spans,
        "decoded_codes": decoded,
        "svg_text_elements": len(re.findall(r"<text\b", svg_text)),
        "svg_size": list(svg_size.groups()) if svg_size else None,
        "pixel_diff_bbox_600dpi": bbox_px,
        "pdf_fonts": [font[3] for font in final_doc.get_page_fonts(0, full=True)],
        "qa_files": [str(QA / name) for name in [
            "full-600dpi.png",
            "left-600dpi.png",
            "center-600dpi.png",
            "right-600dpi.png",
            "date-party-600dpi.png",
            "barcode-600dpi.png",
            "diff-v2-v3-red.png",
        ]],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    final_doc.close()


if __name__ == "__main__":
    main()
