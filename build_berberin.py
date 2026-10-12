from pathlib import Path
# -*- coding: utf-8 -*-
"""
Пересборка этикетки БЕРБЕРИН на базе эталона «Берберин с пиколинатом хрома».
Метод: как в GRA-GELATIN handoff — минимальные зонные правки готового векторного PDF.
База (всё в кривых): 1787732042339-761820797.pdf (158x52 мм)
Тексты берутся из старого Берберина: 1787732042033-87530943.pdf
"""
import fitz

ETALON = str(Path(__file__).resolve().parent / "input" / '1787732042339-761820797.pdf')
OUT_PDF = str(Path(__file__).resolve().parent / 'BERBERIN_v2_158x52mm.pdf')
OUT_PNG = str(Path(__file__).resolve().parent / 'BERBERIN_v2_preview.png')

F_BEBAS = r"C:\Windows\Fonts\BebasNeueCyrillic.ttf"
F_PTN   = r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Regular.ttf"
F_PTNB  = r"C:\Windows\Fonts\PT_Sans-Narrow-Web-Bold.ttf"
F_ARIAL = r"C:\Windows\Fonts\arial.ttf"
F_ARIALBD = r"C:\Windows\Fonts\arialbd.ttf"
F_ARIALBLK = r"C:\Windows\Fonts\ariblk.ttf"

doc = fitz.open(ETALON)
page = doc[0]
W, H = page.rect.width, page.rect.height  # 447.87 x 147.40 pt

# ---------- 1. Вырезаем зоны ----------
# графика=1: удалить только объекты, целиком лежащие в зоне (фоновые градиенты уцелеют)
ZONES_SOFT = [
    fitz.Rect(158, 44.5, 296, 65.5),   # заголовок BERBERINE (буквы)
    fitz.Rect(157, 71.5, 296.5, 85.5), # текст +CHROMIUM PICOLINATE на серебр. плашке
]
ZONES_HARD = [
    fitz.Rect(5, 5, 148, 144),         # вся левая колонка (текст + таблица)
    fitz.Rect(357, 101, 434, 133),     # штрихкод с цифрами
]
for r in ZONES_SOFT:
    page.add_redact_annot(r)
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                      graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
for r in ZONES_HARD:
    page.add_redact_annot(r)
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE,
                      graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)

# ---------- 2. Шрифты ----------
page.insert_font(fontname="bebas", fontfile=F_BEBAS)
page.insert_font(fontname="ptn", fontfile=F_PTN)
page.insert_font(fontname="ptnb", fontfile=F_PTNB)
page.insert_font(fontname="ar", fontfile=F_ARIAL)
page.insert_font(fontname="arb", fontfile=F_ARIALBD)
page.insert_font(fontname="ablk", fontfile=F_ARIALBLK)

BLACK = (0.10, 0.10, 0.09)
CX = 227.0  # центр центральной панели

def center_text(y, text, fontname, fontfile, size, color=BLACK, tracking=0.0):
    """Нарисовать текст по центру CX с межбуквенным трекингом (pt)."""
    font = fitz.Font(fontfile=fontfile)
    widths = [font.glyph_advance(ord(c)) * size for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = CX - total / 2
    for c, w in zip(text, widths):
        page.insert_text((x, y), c, fontname=fontname, fontsize=size, color=color)
        x += w + tracking
    return total

# ---------- 3. Заголовок ----------
center_text(63.0, "БЕРБЕРИН", "bebas", F_BEBAS, 30.0, tracking=1.2)

# ---------- 4. Текст на серебряной плашке ----------
center_text(81.4, "РАСТИТЕЛЬНЫЙ ЭКСТРАКТ", "ptnb", F_PTNB, 9.0, tracking=1.5)

# ---------- 5. Левая колонка ----------
LX0, LX1 = 19.0, 135.5
def para(y, label, rest, size=6.4, lh=7.4):
    """Абзац: жирный лейбл + обычный текст с переносом по ширине."""
    fontb, fontr = fitz.Font(fontfile=F_PTNB), fitz.Font(fontfile=F_PTN)
    words = ([("b", w) for w in label.split()] if label else []) + [("r", w) for w in rest.split()]
    x = LX0
    space_b = fontb.glyph_advance(32) * size
    space_r = fontr.glyph_advance(32) * size
    for style, w in words:
        f = fontb if style == "b" else fontr
        fname = "ptnb" if style == "b" else "ptn"
        ww = sum(f.glyph_advance(ord(c)) for c in w) * size
        sp = space_b if style == "b" else space_r
        if x + ww > LX1:
            x = LX0; y += lh
        page.insert_text((x, y), w, fontname=fname, fontsize=size, color=BLACK)
        x += ww + sp
    return y + lh

y = 22.0
y = para(y, "Область применения:", "для реализации населению в качестве биологически "
              "активной добавки к пище — источника берберина.", size=6.6, lh=7.6) + 2.5
y = para(y, "Рекомендации по применению:", "взрослым по 1 капсуле в день во время еды.",
         size=6.6, lh=7.6) + 2.5
y = para(y, "Состав:", "берберин, микрокристаллическая целлюлоза, агент антислеживающий — "
                       "диоксид кремния аморфный, оболочка капсулы (желатин).", size=6.6, lh=7.6) + 2.5
y = para(y, "Срок годности:", "2 года от даты изготовления.", size=6.6, lh=7.6)

# --- таблица «Пищевая ценность» ---
TY = 95.0
page.draw_rect(fitz.Rect(LX0, TY, LX1, TY + 40), color=BLACK, width=1.4)
page.insert_text((LX0 + 4, TY + 12.5), "Пищевая ценность", fontname="ablk", fontsize=10.4, color=BLACK)
page.draw_rect(fitz.Rect(LX0 + 3, TY + 15.5, LX1 - 3, TY + 18.2), color=BLACK, fill=BLACK)
f_ptn = fitz.Font(fontfile=F_PTN)
t = "Содержание в одной капсуле"
tw = sum(f_ptn.glyph_advance(ord(c)) for c in t) * 6.4
page.insert_text((LX1 - 3 - tw, TY + 24.5), t, fontname="ptn", fontsize=6.4, color=BLACK)
page.draw_line((LX0 + 3, TY + 27.5), (LX1 - 3, TY + 27.5), color=BLACK, width=0.5)
page.insert_text((LX0 + 4, TY + 34.5), "Берберин", fontname="ptn", fontsize=7.0, color=BLACK)
t = "500 мг"
tw = sum(f_ptn.glyph_advance(ord(c)) for c in t) * 7.0
page.insert_text((LX1 - 4 - tw, TY + 34.5), t, fontname="ptn", fontsize=7.0, color=BLACK)

# ---------- 6. Штрихкод EAN-13 4627174095128 ----------
EAN = "4627174095128"
L = {"0":"0001101","1":"0011001","2":"0010011","3":"0111101","4":"0100011",
     "5":"0110001","6":"0101111","7":"0111011","8":"0110111","9":"0001011"}
G = {k: v[::-1].translate(str.maketrans("01","10"))[::-1] for k, v in
     {k: L[k] for k in L}.items()}
G = {k: "".join("1" if b=="0" else "0" for b in L[k][::-1]) for k in L}
R = {k: "".join("1" if b=="0" else "0" for b in L[k]) for k in L}
FIRST = {"0":"LLLLLL","1":"LLGLGG","2":"LLGGLG","3":"LLGGGL","4":"LGLLGG",
         "5":"LGGLLG","6":"LGGGLL","7":"LGLGLG","8":"LGLGGL","9":"LGGLGL"}
bits = "101"
pat = FIRST[EAN[0]]
for i, d in enumerate(EAN[1:7]):
    bits += (L if pat[i] == "L" else G)[d]
bits += "01010"
for d in EAN[7:]:
    bits += R[d]
bits += "101"
BX0, BY0, BY1 = 362.0, 101.5, 124.0   # зона полос
module = 66.0 / 95.0                   # ширина модуля ~0.69pt
guard_ext = 3.5
for i, b in enumerate(bits):
    if b == "1":
        is_guard = i < 3 or 45 <= i < 50 or i >= 92
        y1 = BY1 + (guard_ext if is_guard else 0)
        page.draw_rect(fitz.Rect(BX0 + i*module, BY0, BX0 + (i+1)*module, y1),
                       color=None, fill=(0, 0, 0), width=0)
# цифры под штрихкодом
digits_y = BY1 + 8.0
t = EAN
f_ar = fitz.Font(fontfile=F_ARIAL)
tw = sum(f_ar.glyph_advance(ord(c)) for c in t) * 6.8
page.insert_text((BX0 + (66.0 - tw)/2, digits_y), t, fontname="ar", fontsize=6.8, color=(0,0,0))

# ---------- 7. Сохранение ----------
doc.subset_fonts()
doc.save(OUT_PDF, garbage=4, deflate=True)
pix = doc[0].get_pixmap(dpi=200)
pix.save(OUT_PNG)
print("OK:", OUT_PDF)
print("PNG:", OUT_PNG, pix.width, "x", pix.height)
