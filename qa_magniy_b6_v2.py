from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import zxingcpp
from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parent
SOURCE = Path(__file__).resolve().parent / "input" / '1787905591846-111930516.pdf'
FINAL = ROOT / "MAGNIY_B6_v2_REVIEW_158x52mm.pdf"
SVG = ROOT / "MAGNIY_B6_v2_REVIEW_158x52mm_outlined.svg"
PREVIEW = ROOT / "MAGNIY_B6_v2_REVIEW_preview_300dpi.png"
QA = ROOT / "qa-magniy-b6-v2"


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

    full = render(FINAL, 600)
    source = render(SOURCE, 600)
    full.save(QA / "full-600dpi.png")

    crops = {
        "left-copy-600dpi.png": fitz.Rect(14, 5, 141, 139),
        "left-table-600dpi.png": fitz.Rect(16, 40, 140, 81),
        "center-600dpi.png": fitz.Rect(140, 0, 304, page_rect.height),
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
    diff_visual.save(QA / "diff-source-v2-red.png")

    center_source = crop_pt(source, page_rect, fitz.Rect(140, 0, 304, page_rect.height))
    center_final = crop_pt(full, page_rect, fitz.Rect(140, 0, 304, page_rect.height))
    center_diff_bbox = ImageChops.difference(center_source, center_final).getbbox()

    extracted = page.get_text("text")
    words = page.get_text("words")
    outside = [
        word for word in words
        if word[0] < 0 or word[1] < 0 or word[2] > page_rect.width or word[3] > page_rect.height
    ]

    required = [
        "Область применения:",
        "желатиновая капсула.",
        "Продолжительность приема:",
        "Противопоказания:",
        "Условия хранения:",
        "Не является лекарственным средством.",
        "04.08.2025",
        "04.08.2027",
        "450 мг",
        "10 мг",
    ]
    forbidden = [
        "Форма выпуска:",
        "Пищевая ценность",
        "Энергетическая ценность",
        "Масса нетто",
        "Партия (Серия):",
        "60804",
        "***не превышает",
        "10.06.2026",
        "10.06.2028",
        "�",
    ]
    missing_required = [value for value in required if value not in extracted]
    present_forbidden = [value for value in forbidden if value in extracted]

    codes = [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(Image.open(PREVIEW))
    ]

    svg_text = SVG.read_text(encoding="utf-8")
    svg_size = re.search(r'<svg[^>]*width="([^"]+)"[^>]*height="([^"]+)"', svg_text)

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
        "center_pixel_diff_bbox_600dpi": center_diff_bbox,
        "decoded_codes": codes,
        "svg_text_elements": len(re.findall(r"<text\b", svg_text)),
        "svg_size": list(svg_size.groups()) if svg_size else None,
        "pdf_fonts": [font[3] for font in doc.get_page_fonts(0, full=True)],
        "qa_files": [str(QA / name) for name in [
            "full-600dpi.png",
            "left-copy-600dpi.png",
            "left-table-600dpi.png",
            "center-600dpi.png",
            "right-600dpi.png",
            "date-expiry-600dpi.png",
            "barcode-600dpi.png",
            "diff-source-v2-red.png",
        ]],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if doc.page_count != 1 or report["page_mm"] != [157.99999, 52.00001]:
        raise RuntimeError("Неверный формат страницы")
    if outside or missing_required or present_forbidden:
        raise RuntimeError("Текстовая проверка не пройдена")
    if center_diff_bbox is not None:
        raise RuntimeError(f"Центральный блок изменился: {center_diff_bbox}")
    if not any(code["text"] == "https://graf-lab.ru/" and code["valid"] for code in codes):
        raise RuntimeError("QR не читается")
    if not any(code["text"] == "4627174095012" and code["valid"] for code in codes):
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
