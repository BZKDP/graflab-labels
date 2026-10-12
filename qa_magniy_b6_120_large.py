from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import zxingcpp
from PIL import Image


ROOT = Path(__file__).resolve().parent
FINAL = ROOT / "MAGNIY_B6_120_CAPS_REVIEW_220x42mm.pdf"
SVG = ROOT / "MAGNIY_B6_120_CAPS_REVIEW_220x42mm_outlined.svg"
PREVIEW = ROOT / "MAGNIY_B6_120_CAPS_REVIEW_preview_300dpi.png"
QA = ROOT / "qa-magniy-b6-120-large"


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
    full.save(QA / "full-600dpi.png")

    crops = {
        "left-copy-600dpi.png": fitz.Rect(57, 5, 199, 116),
        "left-table-600dpi.png": fitz.Rect(59, 39, 197, 59),
        "center-600dpi.png": fitz.Rect(228, 0, 430, page_rect.height),
        "badge-120-600dpi.png": fitz.Rect(309, 83, 349, 117),
        "right-600dpi.png": fitz.Rect(457, 0, 570, page_rect.height),
        "date-expiry-600dpi.png": fitz.Rect(461, 52, 564, 73),
        "barcode-600dpi.png": fitz.Rect(493, 77, 566, 116),
    }
    for name, rect in crops.items():
        crop_pt(full, page_rect, rect).save(QA / name)

    extracted = page.get_text("text")
    words = page.get_text("words")
    outside = [
        word for word in words
        if word[0] < 0 or word[1] < 0
        or word[2] > page_rect.width or word[3] > page_rect.height
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
        "120",
        "4627174095012",
    ]
    forbidden = [
        "Форма выпуска",
        "Пищевая ценность",
        "Энергетическая ценность",
        "Масса нетто",
        "Партия",
        "60804",
        "***не превышает",
        "ЖЕЛАТИН ПИЩЕВОЙ",
        "BIOLOGICAL SHOCK ABSORBER",
        "10.06.2026",
        "10.06.2028",
        "652861588677",
        "�",
    ]
    missing_required = [value for value in required if value not in extracted]
    present_forbidden = [value for value in forbidden if value in extracted]

    qr_codes = [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(Image.open(PREVIEW))
    ]
    barcode_image = Image.open(QA / "barcode-600dpi.png")
    barcode_codes = [
        {"format": result.format.name, "text": result.text, "valid": result.valid}
        for result in zxingcpp.read_barcodes(
            barcode_image,
            formats=zxingcpp.BarcodeFormat.Code128,
        )
    ]
    codes = qr_codes + barcode_codes

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
        "render_600dpi_px": full.size,
        "outside_word_count": len(outside),
        "missing_required_text": missing_required,
        "present_forbidden_text": present_forbidden,
        "decoded_codes": codes,
        "svg_text_elements": len(re.findall(r"<text\b", svg_text)),
        "svg_size": list(svg_size.groups()) if svg_size else None,
        "pdf_fonts": sorted({font[3] for font in doc.get_page_fonts(0, full=True)}),
        "qa_files": [str(QA / name) for name in ["full-600dpi.png", *crops]],
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))

    if doc.page_count != 1 or report["page_mm"] != [220.00001, 42.0]:
        raise RuntimeError("Неверный формат страницы")
    if outside or missing_required or present_forbidden:
        raise RuntimeError("Текстовая проверка не пройдена")
    if not any(code["text"] == "https://graf-lab.ru/" and code["valid"] for code in codes):
        raise RuntimeError("QR не читается")
    if not any(code["text"] == "4627174095012" and code["valid"] for code in codes):
        raise RuntimeError("Штрихкод не читается")
    if report["svg_text_elements"] != 0 or report["svg_size"] != ["220mm", "42mm"]:
        raise RuntimeError("SVG не прошел проверку")

    (QA / "qa-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    doc.close()


if __name__ == "__main__":
    main()
