# -*- coding: utf-8 -*-
"""
مولّد كارت العملات الاحترافي
ارفع صور العملة (وجه وظهر)، والبرنامج هيكتبلك نبذة عنها ويطلعلك كارت جاهز للنشر.
"""

import io
import base64
import math
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops
import arabic_reshaper
from bidi.algorithm import get_display
from groq import Groq

FONT_PATH = "Amiri-Regular.ttf"
LOGO_PATH = "logo.png"
WA_ICON_PATH = "whatsapp_icon.png"
ADDR_ICON_PATH = "address_icon.png"
POSTER_BG_PATH = "poster_bg.png"

# ---------- ألوان تصميم البوستر الفاخر ----------
POSTER_GOLD = (208, 168, 92)
POSTER_GOLD_LIGHT = (236, 208, 148)
POSTER_GOLD_DIM = (150, 120, 70)
POSTER_CREAM = (240, 233, 214)
POSTER_RIBBON_BG = (214, 195, 155, 255)
POSTER_RIBBON_BORDER = (150, 110, 45)
POSTER_RIBBON_TEXT = (35, 24, 14)
POSTER_SUB_BAR_BG = (15, 13, 11)
POSTER_SUB_TEXT_GOLD = (196, 160, 88)

# ---------- ثيمات الألوان ----------
THEMES = {
    "أسود وذهبي": dict(
        bg=(250, 247, 240), header=(20, 20, 20), accent=(186, 117, 23),
        text_dark=(44, 44, 42), text_muted=(95, 94, 90), line=(211, 209, 199),
        cond_bg=(239, 199, 117), cond_text=(65, 36, 2),
        price_bg=(93, 202, 165), price_text=(4, 52, 44),
    ),
    "كريمي وذهبي": dict(
        bg=(250, 247, 240), header=(186, 117, 23), accent=(186, 117, 23),
        text_dark=(44, 44, 42), text_muted=(95, 94, 90), line=(211, 209, 199),
        cond_bg=(239, 199, 117), cond_text=(65, 36, 2),
        price_bg=(93, 202, 165), price_text=(4, 52, 44),
    ),
    "كحلي وذهبي": dict(
        bg=(247, 247, 250), header=(16, 28, 46), accent=(196, 155, 74),
        text_dark=(24, 30, 42), text_muted=(90, 97, 110), line=(214, 217, 224),
        cond_bg=(224, 191, 122), cond_text=(60, 42, 6),
        price_bg=(150, 191, 210), price_text=(10, 40, 55),
    ),
    "أخضر زيتوني وذهبي": dict(
        bg=(248, 247, 240), header=(46, 58, 35), accent=(168, 140, 60),
        text_dark=(38, 42, 30), text_muted=(96, 98, 84), line=(216, 214, 198),
        cond_bg=(210, 200, 140), cond_text=(50, 44, 10),
        price_bg=(160, 190, 140), price_text=(20, 46, 16),
    ),
    "أبيض ورمادي أنيق": dict(
        bg=(255, 255, 255), header=(60, 60, 60), accent=(120, 120, 120),
        text_dark=(30, 30, 30), text_muted=(120, 120, 120), line=(224, 224, 224),
        cond_bg=(230, 230, 230), cond_text=(40, 40, 40),
        price_bg=(210, 210, 210), price_text=(30, 30, 30),
    ),
}

# ---------- إعداد الصفحة ----------
st.set_page_config(page_title="مولّد كارت العملات", page_icon="🪙", layout="centered")
st.markdown(
    "<style>body, .stApp {direction: rtl; text-align: right;}</style>",
    unsafe_allow_html=True,
)
st.title("🪙 مولّد كارت العملات الاحترافي")
st.caption("ارفع صور العملة (وجه وظهر)، واملأ التفاصيل، والبرنامج هيكتبلك نبذة عنها ويطلعلك كارت جاهز للنشر.")

# ---------- الشريط الجانبي: مفتاح API ----------
def get_saved_api_key():
    """يقرا المفتاح من secrets لو محفوظ (محليًا في .streamlit/secrets.toml أو أونلاين في إعدادات Streamlit Cloud)."""
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return ""


saved_key = get_saved_api_key()

with st.sidebar:
    st.header("الإعدادات")
    if saved_key:
        api_key = saved_key
        st.success("مفتاح Groq API مفعّل تلقائيًا ✓")
    else:
        api_key = st.text_input("مفتاح Groq API", type="password",
                                 help="محتاج مفتاح API من console.groq.com عشان يكتب النبذة التاريخية تلقائيًا.")
        st.caption("عايز المفتاح يتقرا تلقائيًا من غير ما تدخله كل مرة؟ شوف ملف secrets.toml.example.")
    st.markdown("---")
    st.caption("لو مش عايز تحط مفتاح، تقدر تكتب النبذة بنفسك يدويًا تحت.")


# ---------- دوال مساعدة ----------
def ar(text: str) -> str:
    """تجهيز النص العربي للعرض الصحيح (تشكيل + اتجاه) داخل الصورة."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def wrap_arabic(draw, text, font, max_width):
    """تقسيم نص طويل على أسطر بحيث ميتعداش عرض معين."""
    text = " ".join(text.split())  # يشيل أي أسطر جديدة أو مسافات زيادة
    if not text:
        return []
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        w = draw.textlength(ar(test), font=font)
        if w <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def load_transparent_icon(path):
    """يشيل الخلفية البيضا/الرمادية الفاتحة من أيقونة PNG عادية ويحولها لخلفية شفافة."""
    img = Image.open(path).convert("RGB")
    r, g, b = img.split()
    min_rgb = ImageChops.darker(ImageChops.darker(r, g), b)
    alpha = min_rgb.point(lambda x: min(255, int((255 - x) * 3)))
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def get_coin_story(image_bytes: bytes, api_key: str, coin_name_hint: str = "") -> str:
    """يبعت صورة العملة لموديل Groq (Vision) ويرجع نبذة تاريخية قصيرة بالعربي."""
    client = Groq(api_key=api_key)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"
    prompt = (
        "انت خبير نوميزماتيك (جامع عملات قديمة). اتفرج على صورة العملة دي واكتب نبذة قصيرة "
        "بالعربي الفصحى (3-4 جمل بس، من غير عناوين أو نقط) تشمل: الحقبة أو الدولة المحتملة اللي العملة منها بناءً على الشكل والنقوش، "
        "ومعلومة تاريخية مثيرة عن الفترة دي لو أمكن. لو مش متأكد من الهوية الدقيقة، قول إن ده تقدير "
        "بناءً على الشكل الظاهر ونصح بمراجعة خبير نوميزماتيك للتأكيد. "
        f"{'اسم العملة اللي المستخدم كتبه: ' + coin_name_hint if coin_name_hint else ''} "
        "اكتب بأسلوب جذاب ومناسب لعرضه في بوست تسويقي، من غير مقدمات زي 'بالطبع' أو 'إليك'. "
        "مهم جدًا: جاوب بالعربي بس، ومن غير أي خطوات تفكير أو وسوم think، النص النهائي بس."
    )
    completion = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
        max_completion_tokens=700,
        temperature=0.7,
        reasoning_effort="none",
        reasoning_format="hidden",
    )
    result = completion.choices[0].message.content.strip()
    if "<think>" in result:
        result = result.split("</think>")[-1].strip() if "</think>" in result else ""
    return result


def build_card(front_img, back_img, name, origin, condition, price, story,
               left_line1="", left_line2="", right_text="",
               item_type="معدنية", theme_name="أسود وذهبي"):
    """بناء كارت احترافي بارتفاع ديناميكي حسب طول النبذة."""
    T = THEMES.get(theme_name, THEMES["أسود وذهبي"])
    W = 1080
    MAX_H = 2600  # كانفاس مؤقت هيتقص على القد المستخدم فعليًا
    margin = 60
    coin_d = 400

    card = Image.new("RGB", (W, MAX_H), T["bg"])
    draw = ImageDraw.Draw(card)

    f_title = ImageFont.truetype(FONT_PATH, 50)
    f_sub = ImageFont.truetype(FONT_PATH, 28)
    f_badge = ImageFont.truetype(FONT_PATH, 28)
    f_body = ImageFont.truetype(FONT_PATH, 30)
    f_tag = ImageFont.truetype(FONT_PATH, 26)
    f_side = ImageFont.truetype(FONT_PATH, 50) ## تغيير فونت نص حر يمين الكارت (البسيط)
    f_addr = ImageFont.truetype(FONT_PATH, 30)

    # ===== شريط علوي =====
    draw.rectangle([margin, 50, W - margin, 106], fill=T["header"])
    tag_label = "عملة ورقية" if item_type == "ورقة نقدية" else "عملة معدنية"
    tag_text = ar(tag_label)
    tw = draw.textlength(tag_text, font=f_tag)
    draw.text((W - margin - tw - 20, 62), tag_text, font=f_tag, fill=(255, 255, 255))

    # ===== منطقة العملة: نص للوجه (يمين) ونص للظهر (شمال) =====
    region_top = 140
    half_w = (W - 2 * margin) // 2

    if item_type == "ورقة نقدية":
        frame_w = half_w - 40
        frame_h = int(frame_w * 0.55)

        def paste_note(img, x0):
            note = ImageOps.fit(img.convert("RGB"), (frame_w, frame_h), Image.LANCZOS)
            ring_pad = 10
            draw.rounded_rectangle(
                [x0 - ring_pad, region_top - ring_pad, x0 + frame_w + ring_pad, region_top + frame_h + ring_pad],
                radius=14, outline=T["accent"], width=4
            )
            card.paste(note, (x0, region_top))

        face_x0 = W - margin - frame_w
        back_x0 = margin
        paste_note(front_img, face_x0)
        paste_note(back_img, back_x0)
        region_h = frame_h
    else:
        mask = Image.new("L", (coin_d, coin_d), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, coin_d, coin_d), fill=255)

        def paste_coin(img, cx):
            cy = region_top + coin_d // 2
            sq = ImageOps.fit(img.convert("RGB"), (coin_d, coin_d), Image.LANCZOS)
            draw.ellipse([cx - coin_d // 2 - 10, cy - coin_d // 2 - 10,
                          cx + coin_d // 2 + 10, cy + coin_d // 2 + 10], outline=T["accent"], width=4)
            card.paste(sq, (cx - coin_d // 2, cy - coin_d // 2), mask)

        face_cx = W - margin - half_w // 2
        back_cx = margin + half_w // 2
        paste_coin(front_img, face_cx)
        paste_coin(back_img, back_cx)
        region_h = coin_d

    y = region_top + region_h + 40
    draw.line([margin, y, W - margin, y], fill=T["line"], width=2)
    y += 35

    # ===== اسم العملة + السنة =====
    name_disp = ar(name or "اسم العملة")
    nw = draw.textlength(name_disp, font=f_title)
    draw.text((W - margin - nw, y), name_disp, font=f_title, fill=T["text_dark"])
    y += 65
    origin_disp = ar(origin or "السنة — بلد الإصدار")
    ow = draw.textlength(origin_disp, font=f_sub)
    draw.text((W - margin - ow, y), origin_disp, font=f_sub, fill=T["text_muted"])
    y += 55

    draw.line([margin, y, W - margin, y], fill=T["line"], width=2)
    y += 35

    # ===== النبذة =====
    if story:
        lines = wrap_arabic(draw, story, f_body, W - 2 * margin)
        for line in lines:
            disp = ar(line)
            lw2 = draw.textlength(disp, font=f_body)
            draw.text((W - margin - lw2, y), disp, font=f_body, fill=T["text_dark"])
            y += 44
        y += 20

    # ===== بادجات الحالة والسعر =====
    badge_h = 64
    cond_disp = ar(f"الحالة: {condition or 'غير محددة'}")
    cw = draw.textlength(cond_disp, font=f_badge) + 50
    draw.rounded_rectangle([W - margin - cw, y, W - margin, y + badge_h], radius=14, fill=T["cond_bg"])
    draw.text((W - margin - cw + 25, y + 16), cond_disp, font=f_badge, fill=T["cond_text"])

    price_disp = ar(f"السعر: {price or '---'}")
    pw2 = draw.textlength(price_disp, font=f_badge) + 50
    draw.rounded_rectangle([margin, y, margin + pw2, y + badge_h], radius=14, fill=T["price_bg"])
    draw.text((margin + 25, y + 16), price_disp, font=f_badge, fill=T["price_text"])

    y += badge_h + 45

    # ===== فوتر: لوجو في النص (ضعف حجم العملة) + منطقتين نص حر =====
    draw.line([margin, y, W - margin, y], fill=T["line"], width=2)
    y += 40

    icon_size = 48
    row_h = icon_size + 10
    ADDR_COL_W = 300  # عرض ثابت لعمود العنوان (شامل الأيقونة)، أي عنوان أطول هيتلف على أكتر من سطر

    try:
        wa_icon = load_transparent_icon(WA_ICON_PATH).resize((icon_size, icon_size), Image.LANCZOS)
    except FileNotFoundError:
        wa_icon = None
    try:
        addr_icon = load_transparent_icon(ADDR_ICON_PATH).resize((icon_size, icon_size), Image.LANCZOS)
    except FileNotFoundError:
        addr_icon = None

    # الشمال: صف رقم الواتساب (سطر واحد) + صفوف العنوان (ملفوفة على عرض ثابت)
    left_rows = []  # كل عنصر: (icon_or_None, text, font)
    if left_line1:
        left_rows.append((wa_icon, left_line1, f_side))
    if left_line2:
        addr_text_w = ADDR_COL_W - icon_size - 12
        addr_lines = wrap_arabic(draw, left_line2, f_addr, addr_text_w)
        for i, line in enumerate(addr_lines):
            left_rows.append((addr_icon if i == 0 else None, line, f_addr))

    # نقيس عرض كل سطر شمال (أيقونة + مسافة + نص) عشان نعرف نحجز مساحة كافية قبل ما نحط اللوجو
    left_w = 0
    for icon_img, text, fnt in left_rows:
        extra = icon_size + 12 if icon_img is not None else 0
        row_w = extra + draw.textlength(ar(text), font=fnt)
        left_w = max(left_w, row_w, ADDR_COL_W if left_line2 else 0)

    # نقيس أقصى عرض سطر يمين (بافتراض عرض مبدئي عشان نلف النص لو طويل)
    right_lines_probe = wrap_arabic(draw, right_text, f_side, 340) if right_text else []
    right_w = max([draw.textlength(ar(l), font=f_side) for l in right_lines_probe], default=0)

    gap = 40
    left_reserved = (left_w + gap) if left_w else 0
    right_reserved = (right_w + gap) if right_w else 0
    available_for_logo = W - 2 * margin - left_reserved - right_reserved

    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        desired_box = coin_d * 2
        # المساحة المتاحة للوجو بين نص الشمال ونص اليمين (لو موجودين)
        logo_box = max(100, min(desired_box, available_for_logo))
        ratio = min(logo_box / logo.width, logo_box / logo.height)
        lw, lh = int(logo.width * ratio), int(logo.height * ratio)
        logo_resized = logo.resize((lw, lh), Image.LANCZOS)
        # نمركزه في المنطقة الفاضية بين الشمال واليمين (مش في نص الكارت كله بالضرورة)
        zone_left = margin + left_reserved
        zone_right = W - margin - right_reserved
        logo_x = int(zone_left + max(0, (zone_right - zone_left - lw) // 2))
        logo_x = max(margin, min(logo_x, W - margin - lw))  # حماية إضافية: يفضل جوه حدود الكارت دايمًا
        logo_y = y
        card.paste(logo_resized, (logo_x, logo_y), logo_resized)
    except FileNotFoundError:
        lw, lh = 0, 0
        logo_x = W // 2
        logo_y = y

    left_block_h = len(left_rows) * row_h
    left_y = logo_y + (lh - left_block_h) // 2 if lh else y

    cur_y = left_y
    for icon_img, text, fnt in left_rows:
        if icon_img is not None:
            card.paste(icon_img, (margin, int(cur_y)), icon_img)
            text_x = margin + icon_size + 12
        else:
            text_x = margin + icon_size + 12  # نحافظ على نفس محاذاة النص حتى لو مفيش أيقونة (سطر تاني من العنوان)
        disp = ar(text)
        draw.text((text_x, cur_y + icon_size / 2 - fnt.size // 2), disp, font=fnt, fill=T["text_dark"])
        cur_y += row_h

    # اليمين: نص حر بدون أيقونة (ممكن أكتر من سطر)
    right_lines = right_lines_probe
    line_h = 58
    right_h = len(right_lines) * line_h
    right_start_y = logo_y + (lh - right_h) // 2 if lh else y
    for i, line in enumerate(right_lines):
        disp = ar(line)
        rw = draw.textlength(disp, font=f_side)
        draw.text((W - margin - rw, right_start_y + i * line_h), disp, font=f_side, fill=T["text_dark"])

    bottom_candidates = [logo_y + lh, cur_y, right_start_y + right_h]
    y = max(bottom_candidates) + 40

    card = card.crop((0, 0, W, y))
    return card


# ---------- تصميم البوستر الفاخر (خلفية صورة) ----------
def _centered_text(draw, cx, cy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = cx - w / 2 - bbox[0]
    y = cy - h / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)
    return w, h


def _draw_bold(draw, cx, cy, text, font, fill, bold_offset=1):
    """بولد وهمي (رسم متكرر بإزاحة بسيطة) بدون letter-spacing عشان الحروف العربية تفضل متصلة صح."""
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = cx - w / 2 - bbox[0]
    y = cy - h / 2 - bbox[1]
    for dx in range(-bold_offset, bold_offset + 1):
        for dy in range(-bold_offset, bold_offset + 1):
            draw.text((x + dx, y + dy), text, font=font, fill=fill)
    return w, h


def build_poster(front_img, back_img, name, origin, condition, price,
                  tagline, subtitle_text,
                  left_line1="", left_line2="", right_text="",
                  item_type="معدنية", logo_size=550): #حجم اللوجو
    """بوستر فاخر بخلفية صورة جاهزة (poster_bg.png) + عناصر ديناميكية فوقها."""
    bg_src = Image.open(POSTER_BG_PATH).convert("RGB")
    W = 1080
    H = int(bg_src.height * (W / bg_src.width))
    bg = bg_src.resize((W, H), Image.LANCZOS)

    # فيجنيت + تعتيم خفيف عشان النص يبان فوق أي تفصيلة في الخلفية
    from PIL import ImageFilter
    vign = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vign)
    for i in range(40):
        a = int(90 * (i / 40))
        vd.rectangle([i * 4, i * 4, W - i * 4, H - i * 4], outline=a)
    vign = vign.filter(ImageFilter.GaussianBlur(40))
    dark_full = Image.new("RGB", (W, H), (8, 6, 4))
    bg = Image.composite(dark_full, bg, vign.point(lambda p: int(p * 0.40)))

    card = bg.convert("RGBA")
    draw = ImageDraw.Draw(card, "RGBA")
    margin = 50

    def soft_panel(box, radius=18, opacity=140):
        x0, y0, x1, y1 = box
        panel = Image.new("RGBA", (int(x1 - x0), int(y1 - y0)), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        pd.rounded_rectangle([0, 0, x1 - x0, y1 - y0], radius=radius, fill=(10, 8, 6, opacity))
        card.paste(panel, (int(x0), int(y0)), panel)

    def ribbon(cx, y0, text, font, pad_x=46, h=64, notch=14):
        disp = ar(text)
        tw = draw.textlength(disp, font=font)
        w = tw + pad_x * 2
        x0 = cx - w / 2
        x1 = cx + w / 2
        y1 = y0 + h
        body = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        draw.polygon(body, fill=POSTER_RIBBON_BG)
        draw.polygon(body, outline=POSTER_RIBBON_BORDER, width=2)
        draw.polygon([(x0 - notch, y0 + h / 2), (x0, y0), (x0, y1)], fill=POSTER_RIBBON_BG, outline=POSTER_RIBBON_BORDER)
        draw.polygon([(x1 + notch, y0 + h / 2), (x1, y0), (x1, y1)], fill=POSTER_RIBBON_BG, outline=POSTER_RIBBON_BORDER)
        _centered_text(draw, cx, y0 + h / 2, disp, font, POSTER_RIBBON_TEXT)
        return y1

    def diamond(cx, cy, r=5, color=POSTER_GOLD):
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=color)

    f_tag = ImageFont.truetype(FONT_PATH, 28)
    f_sub = ImageFont.truetype(FONT_PATH, 46)
    f_price = ImageFont.truetype(FONT_PATH, 58)
    f_cond = ImageFont.truetype(FONT_PATH, 34)
    f_contact = ImageFont.truetype(FONT_PATH, 40) ## تغيير فونت العنوان والتليفون (الفاخر)

    y = 40
    y = ribbon(W / 2, y, tagline or "فرصة لا تعوض للهواة والجامعين", f_tag)
    y += 260

    # ===== صور الوجه والظهر: دائرية للمعدنية، مستطيلة للورقية =====
    if item_type == "معدنية":
        coin_d = 240
        gap = 30
        total_w = coin_d * 2 + gap
        px0 = (W - total_w) / 2
        mask = Image.new("L", (coin_d, coin_d), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, coin_d, coin_d), fill=255)
        for i, img in enumerate([back_img, front_img]):
            cx_ = px0 + coin_d / 2 + i * (coin_d + gap)
            cy_ = y + coin_d / 2
            sq = ImageOps.fit(img.convert("RGB"), (coin_d, coin_d), Image.LANCZOS)
            shadow = Image.new("RGBA", (coin_d + 30, coin_d + 30), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).ellipse([15, 18, coin_d + 15, coin_d + 18], fill=(0, 0, 0, 150))
            shadow = shadow.filter(ImageFilter.GaussianBlur(8))
            card.paste(shadow, (int(cx_ - coin_d / 2 - 15), int(cy_ - coin_d / 2 - 15)), shadow)
            draw.ellipse([cx_ - coin_d / 2 - 6, cy_ - coin_d / 2 - 6, cx_ + coin_d / 2 + 6, cy_ + coin_d / 2 + 6],
                         fill=(250, 249, 246, 255))
            draw.ellipse([cx_ - coin_d / 2 - 6, cy_ - coin_d / 2 - 6, cx_ + coin_d / 2 + 6, cy_ + coin_d / 2 + 6],
                         outline=POSTER_GOLD, width=3)
            card.paste(sq, (int(cx_ - coin_d / 2), int(cy_ - coin_d / 2)), mask)
        y += coin_d + 30
    else:
        photo_h = 215
        photo_w = 430
        gap = 20
        total_w = photo_w * 2 + gap
        px0 = (W - total_w) / 2
        for i, img in enumerate([back_img, front_img]):
            x0 = px0 + i * (photo_w + gap)
            fitted = ImageOps.fit(img.convert("RGB"), (photo_w - 18, photo_h - 18), Image.LANCZOS)
            shadow = Image.new("RGBA", (photo_w + 16, photo_h + 16), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rounded_rectangle([8, 10, photo_w + 8, photo_h + 10], radius=6, fill=(0, 0, 0, 150))
            shadow = shadow.filter(ImageFilter.GaussianBlur(8))
            card.paste(shadow, (int(x0 - 8), int(y - 4)), shadow)
            draw.rounded_rectangle([x0, y, x0 + photo_w, y + photo_h], radius=4, fill=(250, 249, 246, 255))
            draw.rounded_rectangle([x0, y, x0 + photo_w, y + photo_h], radius=4, outline=POSTER_GOLD, width=2)
            card.paste(fitted, (int(x0 + 9), int(y + 9)))
            for cx_, cy_ in [(x0 + 6, y + 6), (x0 + photo_w - 6, y + 6),
                              (x0 + 6, y + photo_h - 6), (x0 + photo_w - 6, y + photo_h - 6)]:
                draw.ellipse([cx_ - 3, cy_ - 3, cx_ + 3, cy_ + 3], fill=POSTER_GOLD)
        y += photo_h + 26

    line_w = 220
    draw.line([(W / 2 - line_w / 2, y), (W / 2 + line_w / 2, y)], fill=POSTER_GOLD_DIM, width=1)
    diamond(W / 2, y, 5)
    y += 22

    # ===== اسم العملة والسنة/بلد الإصدار =====
    if name or origin:
        f_name = ImageFont.truetype(FONT_PATH, 34)
        name_line = " — ".join([p for p in [name, origin] if p])
        name_disp = ar(name_line)
        nbbox = draw.textbbox((0, 0), name_disp, font=f_name)
        nw = nbbox[2] - nbbox[0]
        nh = nbbox[3] - nbbox[1]
        soft_panel((W / 2 - nw / 2 - 18, y - 6, W / 2 + nw / 2 + 18, y + nh + 14), radius=8, opacity=90)
        _centered_text(draw, W / 2, y + nh / 2 + 4, name_disp, f_name, POSTER_GOLD_LIGHT)
        y += nh + 26

    # ===== السطر الفرعي: شريط أسود + خط بولد دهبي =====
    sub_disp = ar(subtitle_text or "عملة مصرية أثرية نادرة")
    sbbox = draw.textbbox((0, 0), sub_disp, font=f_sub)
    sw = sbbox[2] - sbbox[0]
    sh = sbbox[3] - sbbox[1]
    bar_w = sw + 70
    bar_h = sh + 40
    bx0 = W / 2 - bar_w / 2
    by0 = y
    draw.rectangle([bx0, by0, bx0 + bar_w, by0 + bar_h], fill=POSTER_SUB_BAR_BG)
    _draw_bold(draw, W / 2, by0 + bar_h / 2, sub_disp, f_sub, POSTER_SUB_TEXT_GOLD, bold_offset=1)
    y += bar_h + 26

    # ===== السعر =====
    price_label = ar(price or "السعر عند الطلب")
    pw = draw.textlength(price_label, font=f_price)
    frame_w = pw + 110
    frame_h = 86
    fx0 = (W - frame_w) / 2
    fx1 = fx0 + frame_w
    fy0 = y
    fy1 = y + frame_h
    soft_panel((fx0, fy0, fx1, fy1), radius=14, opacity=150)
    draw.rounded_rectangle([fx0, fy0, fx1, fy1], radius=14, outline=POSTER_GOLD, width=2)
    inset = 8
    draw.rounded_rectangle([fx0 + inset, fy0 + inset, fx1 - inset, fy1 - inset], radius=8, outline=POSTER_GOLD_DIM, width=1)
    for cx_, cy_ in [(fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)]:
        diamond(cx_, cy_, 6)
    _centered_text(draw, W / 2, (fy0 + fy1) / 2, price_label, f_price, POSTER_GOLD_LIGHT)
    y = fy1 + 20

    # ===== الحالة =====
    cond_disp = ar(f"بحالة {condition}" if condition else "بحالة غير محددة")
    cbbox = draw.textbbox((0, 0), cond_disp, font=f_cond)
    cw = cbbox[2] - cbbox[0]
    ch = cbbox[3] - cbbox[1]
    soft_panel((W / 2 - cw / 2 - 18, y - 8, W / 2 + cw / 2 + 18, y + ch + 16), radius=8, opacity=90)
    _centered_text(draw, W / 2, y + ch / 2 + 6, cond_disp, f_cond, POSTER_CREAM)
    y += ch + 34

    # ===== بيانات التواصل (شمال) =====
    try:
        wa_icon = load_transparent_icon(WA_ICON_PATH)
    except FileNotFoundError:
        wa_icon = None
    try:
        addr_icon = load_transparent_icon(ADDR_ICON_PATH)
    except FileNotFoundError:
        addr_icon = None

    icon_size = 30
    rows = []
    if left_line1:
        rows.append((wa_icon, left_line1))
    if left_line2:
        rows.append((addr_icon, left_line2))

    row_h = icon_size + 10
    block_h = len(rows) * row_h
    panel_w = 280
    if rows:
        soft_panel((margin - 14, y - 10, margin + panel_w, y + block_h + 8), radius=12, opacity=120)
    cur_y = y
    for icon_img, text in rows:
        if icon_img is not None:
            ic = icon_img.resize((icon_size, icon_size), Image.LANCZOS)
            card.paste(ic, (margin, int(cur_y)), ic)
            tx = margin + icon_size + 10
        else:
            tx = margin
        disp = ar(text)
        tb = draw.textbbox((0, 0), disp, font=f_contact)
        draw.text((tx, cur_y + icon_size / 2 - (tb[3] - tb[1]) / 2 - tb[1]), disp, font=f_contact, fill=POSTER_CREAM)
        cur_y += row_h

    # ===== النص الحر (يمين) + اللوجو تحته =====
    right_bottom = y
    if right_text:
        right_disp = ar(right_text)
        rb = draw.textbbox((0, 0), right_disp, font=f_contact)
        rw = rb[2] - rb[0]
        rh = rb[3] - rb[1]
        soft_panel((W - margin - rw - 28, y - 10, W - margin + 14, y + row_h + 2), radius=12, opacity=120)
        draw.text((W - margin - rw, y + row_h / 2 - rh / 2 - rb[1] - 7), right_disp, font=f_contact, fill=POSTER_CREAM)
        right_bottom = y + row_h

    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        ratio = min(logo_size / logo.width, logo_size / logo.height)
        lw, lh = int(logo.width * ratio), int(logo.height * ratio)
        logo_r = logo.resize((lw, lh), Image.LANCZOS)
        edge_margin = 1 # المسافة من حافة الكارت (يمين وتحت)
        lx = (W - lw) // 2 # الموقع الأفقي: أقرب/أبعد عن الحافة اليمين
        ly = right_bottom + 34 # الموقع الرأسي: المسافة تحت النص اللي فوقه (right_text)
        ly = min(H - edge_margin - lh, ly) # حماية عشان مايخرجش برة الكارت من تحت

        card.paste(logo_r, (lx, ly), logo_r)
    except FileNotFoundError:
        pass

    return card.convert("RGB")


# ---------- واجهة المستخدم ----------
st.subheader("صور العملة")
col_up1, col_up2 = st.columns(2)
with col_up1:
    front_upload = st.file_uploader("صورة الوجه", type=["jpg", "jpeg", "png"], key="front")
with col_up2:
    back_upload = st.file_uploader("صورة الظهر (اختياري)", type=["jpg", "jpeg", "png"], key="back")

item_type = st.radio("نوع العملة", ["معدنية", "ورقة نقدية"], horizontal=True)

design_mode = st.radio("نوع التصميم", ["كارت بسيط", "بوستر فاخر"], horizontal=True)

if design_mode == "كارت بسيط":
    theme_name = st.selectbox("لون الكارت", list(THEMES.keys()))
else:
    theme_name = None
    st.markdown("---")
    st.subheader("نصوص البوستر (اختياري)")
    tagline = st.text_input("الشريط العلوي", placeholder="فرصة لا تعوض للهواة والجامعين")
    subtitle_text = st.text_input("السطر الفرعي فوق السعر", placeholder="عملة مصرية أثرية نادرة")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("اسم العملة", placeholder="مثال: دينار إسلامي فضي")
    origin = st.text_input("السنة / بلد الإصدار", placeholder="مثال: القرن الثالث الهجري")
with col2:
    condition = st.selectbox("حالة الحفظ", ["البنك","ممتازة", "جيدة جدًا", "جيدة", "متوسطة", "أثرية نادرة"])
    price = st.text_input("السعر", placeholder="مثال: 1500 جنيه")

st.markdown("---")
st.subheader("بيانات التواصل (اختياري)")
col3, col4 = st.columns(2)
with col3:
    left_line1 = st.text_input("رقم التليفون", placeholder="مثال: 01xxxxxxxxx")
    left_line2 = st.text_input("العنوان", placeholder="مثال: القاهرة، مصر")
with col4:
    right_text = st.text_area("نص حر (يمين الكارت)", height=90,
                               placeholder="أي حاجة تحب تكتبها: متاح للتقسيط، ضمان الأصالة...")

manual_story = ""
auto_story = False
if design_mode == "كارت بسيط":
    st.markdown("---")
    st.subheader("النبذة التاريخية")
    story_mode = st.radio(
        "طريقة كتابة النبذة",
        ["اكتبها بنفسي", "اكتبها تلقائيًا بالذكاء الاصطناعي (يحتاج مفتاح Groq API)"],
        horizontal=False,
    )
    if story_mode == "اكتبها بنفسي":
        manual_story = st.text_area("اكتب النبذة هنا", height=100,
                                     placeholder="مثال: عملة نادرة تعود لسنة كذا، وبتتميز بـ...")
    auto_story = story_mode.startswith("اكتبها تلقائيًا")

generate = st.button("🎨 ولّد الكارت", type="primary", use_container_width=True)

if generate:
    if not front_upload:
        st.error("لازم ترفع صورة وجه العملة على الأقل.")
    else:
        front_img = Image.open(front_upload)
        back_img = Image.open(back_upload) if back_upload else front_img
        story_text = manual_story

        if auto_story:
            if not api_key:
                st.warning("محتاج تحط مفتاح Groq API في الشريط الجانبي عشان يكتب النبذة تلقائيًا، أو اختار 'اكتبها بنفسي'.")
            else:
                with st.spinner("بيدور على قصة العملة..."):
                    try:
                        buf = io.BytesIO()
                        front_img.convert("RGB").save(buf, format="JPEG")
                        story_text = get_coin_story(buf.getvalue(), api_key, name)
                        if story_text:
                            st.success("تمت كتابة النبذة.")
                        else:
                            st.warning("الموديل رجع رد فاضي، جرب تاني أو اكتب النبذة بنفسك.")
                    except Exception as e:
                        st.error(f"حصل خطأ أثناء كتابة النبذة: {e}")

        with st.spinner("بيصمم الكارت..."):
            if design_mode == "بوستر فاخر":
                card = build_poster(
                    front_img, back_img, name, origin, condition, price,
                    tagline, subtitle_text,
                    left_line1=left_line1, left_line2=left_line2, right_text=right_text,
                    item_type=item_type,
                )
            else:
                card = build_card(
                    front_img, back_img, name, origin, condition, price, story_text,
                    left_line1=left_line1, left_line2=left_line2, right_text=right_text,
                    item_type=item_type, theme_name=theme_name,
                )

        st.image(card, caption="الكارت النهائي", use_container_width=True)

        if story_text:
            with st.expander("النبذة التاريخية (نص)"):
                st.write(story_text)

        buf_out = io.BytesIO()
        card.save(buf_out, format="PNG")
        st.download_button(
            "⬇️ تحميل الكارت",
            data=buf_out.getvalue(),
            file_name="coin_card.png",
            mime="image/png",
            use_container_width=True,
        )
