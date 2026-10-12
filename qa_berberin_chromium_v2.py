from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import zxingcpp
from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE = Path(__file__).resolve().parent / "input" / '1787907920909-476952334.pdf'
FINAL = ROOT / "BERBERIN_CHROMIUM_v2_REVIEW_158x52mm.pdf"
SVG = ROOT / "BERBERIN_CHROMIUM_v2_REVIEW_158x52mm_outlined.svg"
PREVIEW = ROOT / "BERBERIN_CHROMIUM_v2_REVIEW_preview_300dpi.png"
QA = ROOT / "qa-berberin-chromium-v2"


def render(pdf: Path, dpi: int) -> Image.Image:
    doc = fitz.open(pdf)
    pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return image


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


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(FINAL)
    page = doc[0]
    page_rect = page.rect

    source = render(SOURCE, 600)
    final = render(FINAL, 600)
    final.save(QA / "full-600dpi.png")

    crops = {
        "left-copy-600dpi.png": fitz.Rect(14, 6, 140, 82),
        "left-copy-and-table-600dpi.png": fitz.Rect(14, 6, 140, 136),
        "center-600dpi.png": fitz.Rect(148, 0, 304, page_rect.height),
        "right-600dpi.png": fitz.Rect(304, 0, page_rect.width, page_rect.height),
        "codes-600dpi.png": fitz.Rect(316, 91, 434, 139),
    }
    for name, rect in crops.items():
        crop_pt(final, page_rect, rect).save(QA / name)

    diff = ImageChops.difference(source, final)
    diff_mask = diff.convert("L").point(lambda value: 255 if value > 3 else 0)
    diff_bbox = diff_mask.getbbox()

    allowed = Image.new("L", final.size, 0)
    draw = ImageDraw.Draw(allowed)
    sx = final.width / page_rect.width
    sy = final.height / page_rect.height
    permitted = fitz.Rect(13.0, 7.0, 140.0, 81.5)
    draw.rectangle(
        (
            round(permitted.x0 * sx),
            round(permitted.y0 * sy),
            round(permitted.x1 * sx),
            round(permitted.y1 * sy),
        ),
        fill=255,
    )
    outside_change_mask = ImageChops.multiply(diff_mask, ImageChops.invert(allowed))
    outside_change_bbox = outside_change_mask.getbbox()

    diff_visual = Image.new("RGB", final.size, "white")
    diff_visual.paste((220, 0, 0), mask=diff_mask)
    diff_visual.save(QA / "diff-source-final-red.png")

    extracted = page.get_text("text")
    words = page.get_text("words")
    outside_words = [
        word for word in words
        if word[0] < 0 or word[1] < 0
        or word[2] > page_rect.width or word[3] > page_rect.height
    ]
    flat_text = re.sub(r"\s+", " ", extracted).strip()
    required = [
        "Берберин с пиколинатом хрома - это добавка",
        "приёма пищи или по назначению врача.",
        "Состав:",
        "Срок годности:",
        "Условия хранения:",
        "в сухом месте, беречь от попадания солнечных лучей.",
        "Не является лекарственным средством",
    ]
    forbidden = [
        "пищиили",
        "пищи  или",
        "БАД",
        "биологически активной добавки",
        "�",
    ]
    missing_required = [value for value in required if value not in flat_text]
    present_forbidden = [value for value in forbidden if value in flat_text]

    codes = [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(Image.open(PREVIEW))
    ]

    svg_text = SVG.read_text(encoding="utf-8")
    svg_size = re.search(
        r'<svg[^>]*width="([^"]+)"[^>]*height="([^"]+)"', svg_text
    )

    report = {
        "pdf_sha256": sha256(FINAL),
        "svg_sha256": sha256(SVG),
        "preview_sha256": sha256(PREVIEW),
        "page_count": doc.page_count,
        "page_mm": [
            round(page_rect.width * 25.4 / 72, 5),
            round(page_rect.height * 25.4 / 72, 5),
        ],
        "preview_px": Image.open(PREVIEW).size,
        "render_600dpi_px": final.size,
        "outside_word_count": len(outside_words),
        "missing_required_text": missing_required,
        "present_forbidden_text": present_forbidden,
        "pixel_diff_bbox_600dpi": diff_bbox,
        "pixel_diff_outside_permitted_bbox": outside_change_bbox,
        "decoded_codes": codes,
        "svg_text_elements": len(re.findall(r"<text\b", svg_text)),
        "svg_size": list(svg_size.groups()) if svg_size else None,
        "pdf_fonts": sorted({font[3] for font in doc.get_page_fonts(0, full=True)}),
        "qa_files": [str(QA / name) for name in [
            "full-600dpi.png",
            *crops,
            "diff-source-final-red.png",
        ]],
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))

    if doc.page_count != 1 or report["page_mm"] != [157.99999, 52.00001]:
        raise RuntimeError("Неверный формат страницы")
    if outside_words or missing_required or present_forbidden:
        raise RuntimeError("Текстовая проверка не пройдена")
    if outside_change_bbox is not None:
        raise RuntimeError(f"Обнаружены изменения за пределами левого блока: {outside_change_bbox}")
    if not any(code["text"] == "https://graf-lab.ru/" and code["valid"] for code in codes):
        raise RuntimeError("QR не читается")
    if not any(code["text"] == "400000001210" and code["valid"] for code in codes):
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
