# -*- coding: utf-8 -*-
"""Пять этикеток: добавление желатина и исправление медальона Mg B6 120."""
from __future__ import annotations

import io
import shutil
from pathlib import Path

import fitz
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.barcode.code128 import Code128
from reportlab.pdfgen import canvas

from build_batch_dates_2026_08_09 import SPECS
from build_batch_original_product import (
    BLACK,
    FONT_REGULAR,
    LARGE,
    OUT_DIR as FOUR_LABEL_DIR,
    PHRASE,
    draw_tracked_text,
)


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "output" / "pdf" / "PRINT_BATCH_5_LABELS_2026-08-09_ORIGINAL_PRODUCT_v2"
PREVIEW_DIR = OUT_DIR / "previews"

GELATIN_SOURCE = Path(__file__).resolve().parent / "input" / '1787202986759-544787856.pdf'
GELATIN_NAME = "05_ЖЕЛАТИН_ПИЩЕВОЙ_160Г_220x42.pdf"

FONT_BOLD = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf")
FONT_NARROW = Path(r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf")
BLUE = (0.0, 0.401190, 0.587304)
GOLD = (219 / 255, 200 / 255, 145 / 255)

MADE = "09.08.2026"
EXPIRES = "09.08.2028"

DATE_RECTS = (
    fitz.Rect(464.30, 60.75, 502.50, 69.45),
    fitz.Rect(524.30, 60.75, 561.70, 69.45),
)
DATE_POSITIONS = ((465.75, 68.00), (525.75, 68.00))


def make_barcode_pdf(value: str) -> fitz.Document:
    width, height = 64.0, 32.0
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    barcode = Code128(
        value,
        barHeight=20.0,
        barWidth=0.45,
        humanReadable=False,
        quiet=False,
    )
    barcode.drawOn(pdf, (width - barcode.width) / 2, 9.0)
    pdf.setFillColorRGB(*BLACK)
    pdf.setFont("Helvetica", 6.0)
    pdf.drawCentredString(width / 2, 1.4, value)
    pdf.showPage()
    pdf.save()
    return fitz.open(stream=buffer.getvalue(), filetype="pdf")


def make_ean13_pdf(value: str) -> fitz.Document:
    """Возвращает стандартный векторный EAN-13 с корректными цифрами и guards."""
    if len(value) != 13 or not value.isdigit():
        raise ValueError(f"Ожидался 13-значный EAN: {value}")
    drawing = createBarcodeDrawing(
        "EAN13",
        value=value[:12],
        barHeight=30.0,
        barWidth=0.68,
        humanReadable=True,
    )
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(drawing.width, drawing.height))
    renderPDF.draw(drawing, pdf, 0, 0)
    pdf.showPage()
    pdf.save()
    return fitz.open(stream=buffer.getvalue(), filetype="pdf")


def add_large_dates_and_caption(page: fitz.Page, suffix: str) -> None:
    # Старые значения дат и старая классифицирующая надпись закрываются белым.
    for rect in DATE_RECTS:
        page.draw_rect(rect, color=None, fill=(1.0, 1.0, 1.0), overlay=True)
    page.draw_rect(LARGE["cover"], color=None, fill=(1.0, 1.0, 1.0), overlay=True)

    date_font = f"ptnbdate{suffix}"
    page.insert_font(fontname=date_font, fontfile=str(FONT_BOLD))
    for position, value in zip(DATE_POSITIONS, (MADE, EXPIRES)):
        page.insert_text(
            position,
            value,
            fontname=date_font,
            fontsize=8.0,
            color=BLUE,
        )

    arial_font = fitz.Font(fontfile=str(FONT_REGULAR))
    arial_name = f"arialproduct{suffix}"
    page.insert_font(fontname=arial_name, fontfile=str(FONT_REGULAR))
    draw_tracked_text(
        page,
        arial_name,
        arial_font,
        PHRASE,
        LARGE["center_x"],
        LARGE["baseline"],
        LARGE["font_size"],
        LARGE["target_width"],
    )


def build_magnesium_120() -> Path:
    source = FOUR_LABEL_DIR / SPECS[1]["output"]
    good_badge_source = FOUR_LABEL_DIR / SPECS[2]["output"]
    output = OUT_DIR / SPECS[1]["output"]

    doc = fitz.open(source)
    page = doc[0]
    badge_doc = fitz.open(good_badge_source)

    # Полностью восстанавливаем медальон из чистой версии на 60 капсул.
    # Затем центр закрывается овальной заливкой внутри золотого кольца,
    # а не прямоугольной заплаткой, и кольцо рисуется заново цельной линией.
    page.draw_rect(
        fitz.Rect(316.8, 89.8, 341.2, 112.6),
        color=None,
        fill=(1.0, 1.0, 1.0),
        overlay=True,
    )
    page.show_pdf_page(
        fitz.Rect(317.15, 90.20, 340.85, 112.20),
        badge_doc,
        0,
        clip=fitz.Rect(208.8, 104.5, 240.0, 133.5),
        keep_proportion=True,
        overlay=True,
    )

    inner_circle = fitz.Rect(323.25, 95.45, 334.75, 106.95)
    page.draw_oval(
        inner_circle,
        color=GOLD,
        fill=(1.0, 1.0, 1.0),
        width=0.48,
        overlay=True,
    )

    page.insert_font(fontname="ptn120clean", fontfile=str(FONT_NARROW))
    number_font = fitz.Font(fontfile=str(FONT_NARROW))
    number = "120"
    number_size = 5.2
    number_x = 329.0 - number_font.text_length(number, fontsize=number_size) / 2
    page.insert_text(
        (number_x, 103.05),
        number,
        fontname="ptn120clean",
        fontsize=number_size,
        color=GOLD,
    )

    doc.subset_fonts()
    doc.save(output, garbage=4, deflate=True)
    badge_doc.close()
    doc.close()
    return output


def build_magnesium_60() -> Path:
    """Заменяет только строку с наименованием изготовителя Mg B6 60."""
    source = FOUR_LABEL_DIR / SPECS[2]["output"]
    output = OUT_DIR / SPECS[2]["output"]
    doc = fitz.open(source)
    page = doc[0]

    # Удаляется полная старая строка с названием и индексом. Заголовок,
    # QR-код и следующая строка адреса остаются на исходных местах.
    name_rect = fitz.Rect(357.5, 19.35, 433.5, 25.75)
    page.add_redact_annot(name_rect, fill=(1.0, 1.0, 1.0))
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    page.insert_font(fontname="ptn_mg60_maker", fontfile=str(FONT_NARROW))
    page.insert_text(
        (359.55, 24.40),
        "ООО Макс Лаб, 121596,",
        fontname="ptn_mg60_maker",
        fontsize=4.2,
        color=BLACK,
    )

    doc.subset_fonts()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output


def build_gelatin() -> Path:
    output = OUT_DIR / GELATIN_NAME
    doc = fitz.open(GELATIN_SOURCE)
    page = doc[0]

    add_large_dates_and_caption(page, "gelatin")

    # В исходнике штрихкод растровый и размытый; значение не меняется,
    # но для печати он заменяется на резкий векторный Code 128.
    page.draw_rect(
        fitz.Rect(497.3, 79.8, 561.7, 112.8),
        color=None,
        fill=(1.0, 1.0, 1.0),
        overlay=True,
    )
    barcode_doc = make_barcode_pdf("652861588677")
    page.show_pdf_page(
        fitz.Rect(497.5, 80.5, 561.5, 112.5),
        barcode_doc,
        0,
        keep_proportion=True,
        overlay=True,
    )

    doc.subset_fonts()
    doc.save(output, garbage=4, deflate=True)
    barcode_doc.close()
    doc.close()
    return output


def build_berberin_60() -> Path:
    """Пересобирает штрихкод берберина в едином для серии формате Code 128."""
    source = FOUR_LABEL_DIR / SPECS[3]["output"]
    output = OUT_DIR / SPECS[3]["output"]
    doc = fitz.open(source)
    page = doc[0]

    # Полностью удаляем прежние полосы и сплошную строку цифр.
    barcode_rect = fitz.Rect(356.0, 97.0, 435.2, 140.5)
    page.add_redact_annot(barcode_rect, fill=(1.0, 1.0, 1.0))
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    )

    # Code 128 выбран осознанно: у него нет удлинённых guard-полос EAN-13,
    # поэтому все штрихи образуют единую ровную линию, как на Mg B6 и желатине.
    barcode_doc = make_barcode_pdf("4627174095128")
    page.show_pdf_page(
        fitz.Rect(357.0, 98.0, 434.2, 139.5),
        barcode_doc,
        0,
        keep_proportion=True,
        overlay=True,
    )

    doc.subset_fonts()
    doc.save(output, garbage=4, deflate=True)
    barcode_doc.close()
    doc.close()
    return output


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # Берберин с хромом переносится без изменений.
    for index in (0,):
        source = FOUR_LABEL_DIR / SPECS[index]["output"]
        shutil.copy2(source, OUT_DIR / source.name)

    magnesium = build_magnesium_120()
    magnesium_60 = build_magnesium_60()
    berberin = build_berberin_60()
    gelatin = build_gelatin()

    outputs = [OUT_DIR / spec["output"] for spec in SPECS] + [gelatin]
    for index, output in enumerate(outputs, 1):
        doc = fitz.open(output)
        pix = doc[0].get_pixmap(dpi=300, alpha=False)
        pix.save(PREVIEW_DIR / f"{index:02d}_preview_300dpi.png")
        print(f"{index}. {output.name}: {pix.width}x{pix.height}px")
        doc.close()


if __name__ == "__main__":
    main()
