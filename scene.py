"""Har bir shahar uchun o'ziga xos manzara chizadi, osmoni esa hozirgi ob-havoga mos keladi.

Rasm har safar kod orqali chiziladi (tayyor fotosurat ishlatilmaydi), shuning uchun
quyosh, oy, bulut, yomg'ir, qor, tuman yoki chang bo'roni doim hozirgi holatga mos bo'ladi.
"""
import io
import math
import os
import random
import zlib
from datetime import datetime

import matplotlib
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from texts import CITIES, LEVEL_COLORS, WEEKDAYS, level, level_index, t, weather_desc, wind_dir

W, H, K = 1000, 560, 2          # rasm o'lchami va sifat uchun ikki barobar chizish
HORIZON = 420                   # yer chizig'i

FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")

RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
THUNDER_CODES = {95, 96, 99}

# Shahar -> manzara turi va yer turi
CITY_STYLE = {
    "toshkent": "tashkent", "samarqand": "registan", "buxoro": "kalyan", "urganch": "khiva",
    "moynoq": "ships", "nukus": "chilpik", "navoiy": "rabat", "qarshi": "kokgumbaz",
    "termiz": "termez", "jizzax": "jizzakh", "guliston": "steppe", "namangan": "namangan",
    "andijon": "andijan", "fargona": "fergana",
}
DESERT = {"ships", "chilpik", "rabat", "kalyan", "khiva", "termez", "kokgumbaz"}


# ---------------- Yordamchi funksiyalar ----------------
def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size * K))


def mix(a, b, f):
    return tuple(int(round(a[i] + (b[i] - a[i]) * f)) for i in range(3))


def rgba(c, a=255):
    return (c[0], c[1], c[2], a)


def P(pts):
    return [(x * K, y * K) for x, y in pts]


def B(x0, y0, x1, y1):
    return [x0 * K, y0 * K, x1 * K, y1 * K]


class Canvas:
    def __init__(self):
        self.img = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 255))

    def layer(self):
        lay = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        return lay, ImageDraw.Draw(lay)

    def merge(self, lay, blur=0):
        if blur:
            lay = lay.filter(ImageFilter.GaussianBlur(blur * K))
        self.img.alpha_composite(lay)


def gradient(size, top, bottom):
    g = Image.new("RGB", (1, 256))
    g.putdata([mix(top, bottom, i / 255) for i in range(256)])
    return g.resize(size, Image.BILINEAR).convert("RGBA")


# ---------------- Ob-havo holatini aniqlash ----------------
def condition(weather, air):
    cur = (weather or {}).get("current", {})
    code = cur.get("weather_code")
    pm10 = (air or {}).get("pm10") or 0
    dust = (air or {}).get("dust") or 0
    if pm10 >= 250 or dust >= 200:
        cond = "dust"
    elif code in THUNDER_CODES:
        cond = "thunder"
    elif code in SNOW_CODES:
        cond = "snow"
    elif code in RAIN_CODES:
        cond = "rain"
    elif code in (45, 48):
        cond = "fog"
    elif code == 3:
        cond = "overcast"
    elif code in (1, 2):
        cond = "partly"
    else:
        cond = "clear"
    if "is_day" in cur:
        night = not cur["is_day"]
    else:
        time = (air or {}).get("time") or cur.get("time") or datetime.now().isoformat()
        hour = int(time[11:13]) if len(time) > 12 else 12
        night = not (6 <= hour < 19)
    haze = cond != "dust" and pm10 >= 100
    return cond, night, haze


SKY = {  # (kunduzi yuqori, kunduzi past, kechasi yuqori, kechasi past)
    "clear":    ((52, 120, 214), (172, 212, 246), (6, 12, 36), (36, 50, 94)),
    "partly":   ((74, 138, 218), (186, 214, 240), (12, 18, 40), (46, 56, 92)),
    "overcast": ((118, 128, 142), (186, 191, 199), (30, 33, 42), (66, 70, 82)),
    "rain":     ((78, 88, 102), (142, 150, 162), (22, 25, 33), (52, 57, 68)),
    "thunder":  ((42, 45, 60), (96, 99, 116), (16, 17, 26), (44, 46, 60)),
    "snow":     ((158, 170, 188), (226, 231, 239), (46, 54, 72), (108, 116, 134)),
    "fog":      ((186, 191, 197), (222, 224, 227), (60, 64, 72), (98, 102, 110)),
    "dust":     ((146, 92, 44), (218, 164, 98), (58, 36, 18), (112, 76, 40)),
}


# ---------------- Osmon elementlari ----------------
def draw_sun(cv, x, y, r, dusty=False):
    lay, d = cv.layer()
    if dusty:
        d.ellipse(B(x - r, y - r, x + r, y + r), fill=(255, 226, 170, 150))
        cv.merge(lay, blur=1.5)
        return
    for rr, a in ((r * 3.2, 45), (r * 2.1, 70), (r * 1.4, 110)):
        d.ellipse(B(x - rr, y - rr, x + rr, y + rr), fill=(255, 240, 180, a))
    cv.merge(lay, blur=18)
    lay, d = cv.layer()
    d.ellipse(B(x - r, y - r, x + r, y + r), fill=(255, 238, 172, 255))
    cv.merge(lay, blur=0.6)


def draw_moon(cv, x, y, r, sky_color):
    lay, d = cv.layer()
    d.ellipse(B(x - r * 2.4, y - r * 2.4, x + r * 2.4, y + r * 2.4), fill=(220, 225, 255, 35))
    cv.merge(lay, blur=14)
    lay, d = cv.layer()
    d.ellipse(B(x - r, y - r, x + r, y + r), fill=(242, 240, 224, 255))
    d.ellipse(B(x - r + r * 0.55, y - r - r * 0.15, x + r + r * 0.55, y + r - r * 0.15),
              fill=rgba(sky_color))
    cv.merge(lay, blur=0.5)


def draw_stars(cv, rng, n=90):
    lay, d = cv.layer()
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, HORIZON * 0.75)
        r = rng.choice((0.6, 0.8, 1.0, 1.3))
        d.ellipse(B(x - r, y - r, x + r, y + r), fill=(255, 255, 240, rng.randint(120, 255)))
    cv.merge(lay)


PUFFS = [(-52, 8, 26), (-24, -8, 34), (12, -16, 40), (46, -2, 32), (72, 10, 22),
         (-76, 16, 18), (0, 10, 34), (30, 12, 30)]


def draw_clouds(cv, rng, n, color, alpha, y_range=(40, 200), scale=(0.7, 1.3), blur=2.0):
    lay, d = cv.layer()
    for _ in range(n):
        cx, cy = rng.uniform(-40, W + 40), rng.uniform(*y_range)
        s = rng.uniform(*scale)
        shade = mix(color, (90, 95, 110), 0.18)
        for dx, dy, r in PUFFS:  # pastki soya
            d.ellipse(B(cx + (dx - r) * s, cy + (dy - r + 6) * s, cx + (dx + r) * s, cy + (dy + r + 6) * s),
                      fill=rgba(shade, alpha))
        for dx, dy, r in PUFFS:
            d.ellipse(B(cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s),
                      fill=rgba(color, alpha))
    cv.merge(lay, blur=blur)


def draw_rain(cv, rng, n=320, color=(205, 214, 228)):
    lay, d = cv.layer()
    for _ in range(n):
        x, y = rng.uniform(-20, W + 40), rng.uniform(80, H)
        ln = rng.uniform(16, 30)
        d.line(P([(x, y), (x - ln * 0.3, y + ln)]), fill=rgba(color, rng.randint(90, 170)), width=K + 1)
    cv.merge(lay, blur=0.3)


def draw_snow(cv, rng, n=260):
    lay, d = cv.layer()
    for _ in range(n):
        x, y, r = rng.uniform(0, W), rng.uniform(40, H), rng.uniform(1.2, 3.6)
        d.ellipse(B(x - r, y - r, x + r, y + r), fill=(255, 255, 255, rng.randint(160, 240)))
    cv.merge(lay, blur=0.4)


def draw_lightning(cv, rng):
    x, y = rng.uniform(250, 420), 150
    pts = [(x, y)]
    while y < 340:
        x += rng.uniform(-28, 28)
        y += rng.uniform(22, 40)
        pts.append((x, y))
    for width, blur, a in ((14, 10, 90), (4, 0.6, 255)):
        lay, d = cv.layer()
        d.line(P(pts), fill=(255, 246, 190, a), width=int(width * K / 2), joint="curve")
        cv.merge(lay, blur=blur)


def draw_dust(cv, rng, night):
    lay, d = cv.layer()
    tint = (120, 78, 38) if night else (205, 145, 75)
    d.rectangle(B(0, 0, W, H), fill=rgba(tint, 120))
    cv.merge(lay)
    lay, d = cv.layer()
    for _ in range(70):  # shamol olib kelayotgan chang to'lqinlari
        x, y = rng.uniform(-200, W), rng.uniform(150, H)
        ln = rng.uniform(120, 380)
        d.line(P([(x, y), (x + ln, y - ln * 0.06)]), fill=rgba(mix(tint, (255, 230, 190), 0.3), 60),
               width=int(rng.uniform(3, 9) * K))
    cv.merge(lay, blur=6)
    lay, d = cv.layer()
    for _ in range(900):
        x, y, r = rng.uniform(0, W), rng.uniform(60, H), rng.uniform(0.5, 1.6)
        d.ellipse(B(x - r, y - r, x + r, y + r), fill=(235, 200, 150, rng.randint(60, 160)))
    cv.merge(lay, blur=0.4)


def draw_fog(cv, rng, night):
    col = (120, 124, 132) if night else (236, 238, 240)
    lay, d = cv.layer()
    d.rectangle(B(0, 0, W, H), fill=rgba(col, 70))
    for i in range(7):
        y = 250 + i * 36 + rng.uniform(-10, 10)
        d.rectangle(B(-50, y, W + 50, y + rng.uniform(16, 30)), fill=rgba(col, 120))
    cv.merge(lay, blur=14)


# ---------------- Me'moriy shakllar ----------------
def dome(d, cx, base, w, h, fill, spire=True):
    pts = []
    for i in range(41):
        a = math.pi * i / 40
        x = cx - math.cos(a) * w / 2
        y = base - (math.sin(a) ** 0.75) * h
        pts.append((x, y))
    pts.append((cx, base - h * 1.12))  # biroz uchli gumbaz
    pts.sort(key=lambda p: p[0])
    top = [p for p in pts]
    d.polygon(P(top + [(cx + w / 2, base), (cx - w / 2, base)]), fill=fill)
    if spire:
        d.line(P([(cx, base - h * 1.1), (cx, base - h * 1.1 - 14)]), fill=fill, width=int(2 * K))
        d.ellipse(B(cx - 3, base - h * 1.1 - 10, cx + 3, base - h * 1.1 - 4), fill=fill)


def ribbed_dome(d, cx, base, w, h, fill, rib):
    dome(d, cx, base, w, h, fill)
    for i in range(1, 6):
        f = i / 6 - 0.5
        d.line(P([(cx + f * w * 0.95, base - 2), (cx + f * w * 0.35, base - h * 0.95)]),
               fill=rib, width=max(1, int(1.2 * K)))


def minaret(d, cx, base, wb, wt, h, fill, lantern=True):
    d.polygon(P([(cx - wb / 2, base), (cx + wb / 2, base), (cx + wt / 2, base - h), (cx - wt / 2, base - h)]),
              fill=fill)
    if lantern:
        lw = wt * 1.35
        d.rectangle(B(cx - lw / 2, base - h - wt * 0.9, cx + lw / 2, base - h), fill=fill)
        dome(d, cx, base - h - wt * 0.9, lw * 0.9, wt * 0.7, fill, spire=False)


def arch(d, cx, base, w, h, fill):
    """Uchli (sharqona) ark."""
    pts = [(cx - w / 2, base)]
    for i in range(16):
        a = math.pi / 2 * i / 15
        pts.append((cx - w / 2 + (w / 2) * (1 - math.cos(a)) * 0.92, base - h * 0.62 - h * 0.38 * math.sin(a)))
    pts.append((cx, base - h))
    for x, y in reversed(pts[1:-1]):
        pts.append((2 * cx - x, y))
    pts.append((cx + w / 2, base))
    d.polygon(P(pts), fill=fill)


def pishtaq(d, cx, base, w, h, fill, recess):
    d.rectangle(B(cx - w / 2, base - h, cx + w / 2, base), fill=fill)
    arch(d, cx, base, w * 0.58, h * 0.78, recess)


def poplar(d, x, base, h, w, fill):
    d.line(P([(x, base), (x, base - h * 0.2)]), fill=fill, width=int(2 * K))
    d.ellipse(B(x - w / 2, base - h, x + w / 2, base - h * 0.12), fill=fill)


def round_tree(d, x, base, r, fill):
    d.line(P([(x, base), (x, base - r)]), fill=fill, width=int(3 * K))
    for dx, dy, rr in ((0, -r * 1.7, r), (-r * 0.6, -r * 1.3, r * 0.75), (r * 0.6, -r * 1.35, r * 0.75)):
        d.ellipse(B(x + dx - rr, base + dy - rr, x + dx + rr, base + dy + rr), fill=fill)


def saxaul(d, rng, x, base, s, fill):
    for _ in range(3):
        d.line(P([(x, base), (x + rng.uniform(-14, 14) * s, base - rng.uniform(10, 22) * s)]),
               fill=fill, width=int(1.6 * K))
    for _ in range(6):
        cx, cy = x + rng.uniform(-18, 18) * s, base - rng.uniform(14, 30) * s
        r = rng.uniform(5, 9) * s
        d.ellipse(B(cx - r, cy - r * 0.7, cx + r, cy + r * 0.7), fill=fill)


def palm(d, x, base, h, fill):
    d.line(P([(x, base), (x + 6, base - h * 0.5), (x + 4, base - h)]), fill=fill, width=int(4 * K))
    top = (x + 4, base - h)
    for ang in (-160, -130, -100, -70, -40, -15):
        a = math.radians(ang)
        ex, ey = top[0] + math.cos(a) * 38, top[1] + math.sin(a) * 22 + 14
        mx, my = top[0] + math.cos(a) * 20, top[1] + math.sin(a) * 16 - 4
        d.line(P([top, (mx, my), (ex, ey)]), fill=fill, width=int(3 * K), joint="curve")


def ridge_points(rng, base, hmin, hmax, step=12, freq=1.0):
    p1, p2, p3 = rng.uniform(0, 6), rng.uniform(0, 6), rng.uniform(0, 6)
    pts = []
    for x in range(-20, W + 21, step):
        v = (0.55 * math.sin(x / (170 / freq) + p1) + 0.3 * math.sin(x / (63 / freq) + p2)
             + 0.15 * math.sin(x / (23 / freq) + p3))
        h = hmin + (hmax - hmin) * (0.5 + 0.5 * v) + rng.uniform(-4, 4)
        pts.append((x, base - h))
    return pts


def mountains(cv, rng, base, hmin, hmax, fill, snow=None, freq=1.0):
    pts = ridge_points(rng, base, hmin, hmax, freq=freq)
    poly = pts + [(W + 20, base + 2), (-20, base + 2)]
    lay, d = cv.layer()
    d.polygon(P(poly), fill=rgba(fill))
    cv.merge(lay)
    if snow:
        snow_y = base - (hmin + (hmax - hmin) * 0.68)
        lay, d = cv.layer()
        d.polygon(P(poly), fill=rgba(snow))
        mask = Image.new("L", lay.size, 0)
        md = ImageDraw.Draw(mask)
        jag = [(x, snow_y + rng.uniform(-6, 10)) for x in range(W + 20, -21, -15)]
        md.polygon(P([(-20, 0), (W + 20, 0)] + jag), fill=255)
        lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask))
        cv.merge(lay, blur=0.4)


# ---------------- Shaharlar manzarasi ----------------
def scene_registan(cv, c, rng):  # Samarqand: Registon
    lay, d = cv.layer()
    n, acc, rec = rgba(c["near"]), rgba(c["accent"]), rgba(c["recess"])
    ribbed_dome(d, 600, 300, 120, 78, acc, rgba(c["near"]))     # Tillakori gumbazi
    for cx in (735, 785):                                         # Sherdor gumbazlari
        ribbed_dome(d, cx, 318, 54, 44, acc, rgba(c["near"]))
    for x0, x1, pc in ((330, 500, 415), (500, 700, 600), (690, 860, 775)):
        d.rectangle(B(x0, 340, x1, HORIZON), fill=n)
        for i in range(int((x1 - x0) / 22)):                      # ikki qavatli hujralar
            ax = x0 + 12 + i * 22
            if abs(ax - pc) > 52:
                arch(d, ax, 380, 11, 22, rec)
                arch(d, ax, 412, 11, 22, rec)
        pishtaq(d, pc, HORIZON, 96, 160, n, rec)
    for mx in (335, 495, 695, 855):
        minaret(d, mx, HORIZON, 20, 15, 180, n)
    cv.merge(lay)


def scene_kalyan(cv, c, rng):  # Buxoro: Minorai Kalon va masjid
    lay, d = cv.layer()
    n, acc, rec = rgba(c["near"]), rgba(c["accent"]), rgba(c["recess"])
    d.rectangle(B(380, 352, 540, HORIZON), fill=n)                # Mir-i Arab
    for cx in (420, 500):
        d.rectangle(B(cx - 26, 330, cx + 26, 352), fill=n)
        dome(d, cx, 330, 52, 38, acc)
    pishtaq(d, 460, HORIZON, 70, 112, n, rec)
    minaret(d, 625, HORIZON, 40, 27, 232, n, lantern=False)       # Minorai Kalon
    d.rectangle(B(608, 166, 642, 190), fill=n)
    for i in range(4):
        arch(d, 613 + i * 8, 186, 5, 15, rec)
    dome(d, 625, 166, 30, 14, n, spire=False)
    for band in (230, 280, 330, 380):
        d.line(P([(602, band), (648, band)]), fill=rec, width=int(1.2 * K))
    d.rectangle(B(690, 360, 930, HORIZON), fill=n)                # Kalon masjidi
    d.rectangle(B(820, 322, 880, 360), fill=n)
    dome(d, 850, 322, 82, 54, acc)
    pishtaq(d, 735, HORIZON, 92, 132, n, rec)
    cv.merge(lay)


def scene_tashkent(cv, c, rng):  # Toshkent: teleminora va shahar
    lay, d = cv.layer()
    far = rgba(c["far"])
    x = 0
    while x < W:
        w, h = rng.uniform(26, 60), rng.uniform(26, 96)
        d.rectangle(B(x, HORIZON - h, x + w, HORIZON), fill=far)
        x += w + rng.uniform(2, 10)
    cv.merge(lay)
    lay, d = cv.layer()
    n, rec = rgba(c["near"]), rgba(c["recess"])
    for x0, w, h in ((420, 70, 70), (500, 46, 104), (720, 64, 84), (800, 90, 58), (900, 60, 92)):
        d.rectangle(B(x0, HORIZON - h, x0 + w, HORIZON), fill=n)
        for wy in range(int(HORIZON - h + 10), HORIZON - 6, 14):  # derazalar
            for wx in range(int(x0 + 8), int(x0 + w - 6), 12):
                if c["night"] and rng.random() < 0.45:
                    d.rectangle(B(wx, wy, wx + 5, wy + 6), fill=(255, 214, 140, 230))
    cx = 640                                                       # teleminora
    for lx in (cx - 34, cx + 34, cx):
        d.polygon(P([(lx - 4, HORIZON), (lx + 4, HORIZON), (cx + 3, 300), (cx - 3, 300)]), fill=n)
    d.polygon(P([(cx - 8, 304), (cx + 8, 304), (cx + 5, 120), (cx - 5, 120)]), fill=n)
    d.ellipse(B(cx - 30, 206, cx + 30, 226), fill=n)
    d.rectangle(B(cx - 24, 196, cx + 24, 216), fill=n)
    d.ellipse(B(cx - 19, 176, cx + 19, 190), fill=n)
    d.line(P([(cx, 120), (cx, 58)]), fill=n, width=int(3 * K))
    if c["night"]:
        d.ellipse(B(cx - 3, 54, cx + 3, 60), fill=(255, 70, 60, 255))
        d.rectangle(B(cx - 22, 203, cx + 22, 208), fill=(255, 214, 140, 230))
    cv.merge(lay)


def scene_khiva(cv, c, rng):  # Xorazm: Ichan qal'a va Kalta minor
    lay, d = cv.layer()
    n, acc, rec = rgba(c["near"]), rgba(c["accent"]), rgba(c["recess"])
    minaret(d, 790, HORIZON, 30, 18, 236, n)                      # Islom Xo'ja
    for band in range(210, 410, 26):
        d.line(P([(777, band), (803, band)]), fill=rec, width=int(1.2 * K))
    dome(d, 430, 330, 70, 50, acc)
    d.rectangle(B(398, 330, 462, 372), fill=n)
    d.polygon(P([(500, 372), (620, 372), (606, 238), (514, 238)]), fill=acc)  # Kalta minor
    for band in (262, 290, 318, 346):
        d.line(P([(512, band), (608, band)]), fill=n, width=int(2 * K))
    d.rectangle(B(-10, 372, W + 10, HORIZON), fill=n)              # qal'a devori
    for x in range(-10, W + 10, 24):
        d.rectangle(B(x, 362, x + 12, 374), fill=n)
    for tx in (90, 300, 680, 920):
        d.ellipse(B(tx - 26, 350, tx + 26, 402), fill=n)
        d.rectangle(B(tx - 26, 376, tx + 26, HORIZON), fill=n)
    cv.merge(lay)


def scene_ships(cv, c, rng):  # Mo'ynoq: qumdagi kemalar
    lay, d = cv.layer()
    far = rgba(c["far"])
    d.rectangle(B(-10, HORIZON - 6, W + 10, HORIZON), fill=far)
    cv.merge(lay)
    lay, d = cv.layer()
    rust = rgba(c["rust"])
    for x0, s, tilt in ((360, 1.0, -0.04), (650, 1.25, 0.05), (880, 0.7, -0.02)):
        L = 220 * s
        hull = [(x0, HORIZON - 4), (x0 + L, HORIZON - 4 + tilt * L), (x0 + L + 26 * s, HORIZON - 52 * s + tilt * L),
                (x0 - 14 * s, HORIZON - 46 * s)]
        d.polygon(P(hull), fill=rust)
        cab_x = x0 + L * 0.55
        d.rectangle(B(cab_x, HORIZON - 86 * s + tilt * L * 0.55, cab_x + 54 * s, HORIZON - 46 * s + tilt * L * 0.55),
                    fill=rust)
        d.line(P([(x0 + L * 0.3, HORIZON - 46 * s), (x0 + L * 0.28, HORIZON - 130 * s)]), fill=rust,
               width=int(3 * K))
        for k in range(int(L / 30)):  # zanglagan teshiklar
            hx = x0 + 18 + k * 30
            d.ellipse(B(hx, HORIZON - 34 * s, hx + 6 * s, HORIZON - 28 * s), fill=rgba(c["recess"]))
    cv.merge(lay)


def scene_chilpik(cv, c, rng):  # Nukus: Chilpiq tepaligi va Mizdahkon
    lay, d = cv.layer()
    far = rgba(c["far"])
    for cx in (150, 205, 250):
        dome(d, cx, HORIZON - 4, 34, 24, far)
        d.rectangle(B(cx - 17, HORIZON - 6, cx + 17, HORIZON), fill=far)
    cv.merge(lay)
    lay, d = cv.layer()
    n, rec = rgba(c["near"]), rgba(c["recess"])
    d.polygon(P([(470, HORIZON), (850, HORIZON), (740, 318), (580, 318)]), fill=n)
    d.polygon(P([(586, 320), (734, 320), (728, 284), (592, 284)]), fill=n)
    for x in range(600, 726, 18):
        d.line(P([(x, 286), (x + 4, 318)]), fill=rec, width=int(1.2 * K))
    cv.merge(lay)


def scene_rabat(cv, c, rng):  # Navoiy: Rabati Malik karvonsaroyi
    mountains(cv, rng, HORIZON, 20, 60, c["far"])
    lay, d = cv.layer()
    n, rec = rgba(c["near"]), rgba(c["recess"])
    d.rectangle(B(330, 352, 860, HORIZON), fill=n)
    d.rectangle(B(500, 240, 700, HORIZON), fill=n)
    for x in range(338, 498, 18):                                 # gofrirlangan devor
        d.rectangle(B(x, 358, x + 7, HORIZON), fill=rec)
    for x in range(706, 856, 18):
        d.rectangle(B(x, 358, x + 7, HORIZON), fill=rec)
    arch(d, 600, HORIZON, 110, 150, rec)
    cv.merge(lay)


def scene_kokgumbaz(cv, c, rng):  # Qarshi: Ko'k gumbaz va ko'prik
    lay, d = cv.layer()
    n, acc, rec = rgba(c["near"]), rgba(c["accent"]), rgba(c["recess"])
    d.rectangle(B(520, 286, 690, 332), fill=n)
    dome(d, 605, 288, 168, 104, acc)
    d.rectangle(B(480, 332, 740, HORIZON), fill=n)
    pishtaq(d, 470, HORIZON, 110, 150, n, rec)
    for x in range(560, 730, 26):
        arch(d, x, 400, 13, 34, rec)
    d.rectangle(B(40, 384, 400, 396), fill=n)                     # Qarshi ko'prigi
    for x in range(56, 400, 58):
        d.rectangle(B(x - 6, 384, x + 6, HORIZON), fill=n)
        d.pieslice(B(x + 6, 392, x + 52, 440), 180, 360, fill=n)
    cv.merge(lay)


def scene_termez(cv, c, rng):  # Termiz: buddaviy stupa va Sulton Saodat
    lay, d = cv.layer()
    n, acc, rec = rgba(c["near"]), rgba(c["accent"]), rgba(c["recess"])
    d.rectangle(B(330, 390, 560, HORIZON), fill=n)
    d.chord(B(352, 280, 538, 500), 180, 360, fill=n)
    d.rectangle(B(436, 270, 454, 292), fill=n)
    d.rectangle(B(426, 262, 464, 270), fill=n)
    d.rectangle(B(640, 350, 900, HORIZON), fill=n)
    for cx in (680, 860):
        dome(d, cx, 350, 64, 44, acc)
    pishtaq(d, 770, HORIZON, 100, 138, n, rec)
    palm(d, 240, HORIZON, 120, n)
    palm(d, 950, HORIZON, 100, n)
    cv.merge(lay)


def scene_jizzakh(cv, c, rng):  # Jizzax: Nurota tog'lari va dalalar
    mountains(cv, rng, HORIZON, 70, 170, c["far"], snow=c["snow_far"])
    mountains(cv, rng, HORIZON, 20, 70, mix(c["far"], c["near"], 0.5), freq=1.6)
    lay, d = cv.layer()
    n = rgba(c["near"])
    for x in range(330, 960, 34):
        poplar(d, x, HORIZON, rng.uniform(60, 90), 16, n)
    for x0 in (420, 700):
        d.rectangle(B(x0, 392, x0 + 56, HORIZON), fill=n)
        d.polygon(P([(x0 - 6, 392), (x0 + 62, 392), (x0 + 28, 372)]), fill=n)
    cv.merge(lay)


def scene_steppe(cv, c, rng):  # Guliston: Mirzacho'l dalalari
    lay, d = cv.layer()
    n, far = rgba(c["near"]), rgba(c["far"])
    for x in range(-10, W + 10, 22):
        poplar(d, x, HORIZON, rng.uniform(34, 52), 12, far)
    cv.merge(lay)
    lay, d = cv.layer()
    for x0 in (600,):
        d.rectangle(B(x0, 380, x0 + 90, HORIZON), fill=n)
        d.polygon(P([(x0 - 8, 380), (x0 + 98, 380), (x0 + 45, 352)]), fill=n)
    for x in (540, 760, 800):
        round_tree(d, x, HORIZON, 22, n)
    cv.merge(lay)


def scene_namangan(cv, c, rng):  # Namangan: Chotqol tog'lari va madrasa
    mountains(cv, rng, HORIZON, 110, 220, c["far"], snow=c["snow_far"])
    lay, d = cv.layer()
    n, acc, rec = rgba(c["near"]), rgba(c["accent"]), rgba(c["recess"])
    d.rectangle(B(500, 350, 800, HORIZON), fill=n)
    for cx in (560, 740):
        dome(d, cx, 350, 56, 40, acc)
    pishtaq(d, 650, HORIZON, 110, 150, n, rec)
    for mx in (505, 795):
        minaret(d, mx, HORIZON, 24, 18, 140, n)
    for x in (380, 420, 880, 920, 960):
        poplar(d, x, HORIZON, rng.uniform(80, 110), 18, n)
    cv.merge(lay)


def scene_andijan(cv, c, rng):  # Andijon: tog'lar va Jome majmuasi
    mountains(cv, rng, HORIZON, 90, 190, c["far"], snow=c["snow_far"])
    lay, d = cv.layer()
    n, acc, rec = rgba(c["near"]), rgba(c["accent"]), rgba(c["recess"])
    d.rectangle(B(480, 352, 860, HORIZON), fill=n)
    for x in range(500, 850, 26):
        if abs(x - 640) > 60:
            arch(d, x, 404, 13, 32, rec)
    pishtaq(d, 640, HORIZON, 120, 160, n, rec)
    dome(d, 790, 352, 64, 44, acc)
    minaret(d, 900, HORIZON, 26, 18, 210, n)
    for x in (360, 400, 440):
        poplar(d, x, HORIZON, rng.uniform(90, 120), 20, n)
    cv.merge(lay)


def scene_fergana(cv, c, rng):  # Farg'ona: Oloy tog'lari va chinorlar
    mountains(cv, rng, HORIZON, 150, 250, c["far"], snow=c["snow_far"], freq=0.8)
    mountains(cv, rng, HORIZON, 30, 80, mix(c["far"], c["near"], 0.55), freq=1.4)
    lay, d = cv.layer()
    n = rgba(c["near"])
    for x0, w, h in ((560, 80, 50), (650, 60, 70), (720, 90, 44)):
        d.rectangle(B(x0, HORIZON - h, x0 + w, HORIZON), fill=n)
    for x in (380, 470, 840, 930):
        round_tree(d, x, HORIZON, rng.uniform(26, 34), n)
    cv.merge(lay)


def scene_generic(cv, c, rng):  # Boshqa joylar: adirlar va teraklar
    mountains(cv, rng, HORIZON, 40, 110, c["far"], freq=0.7)
    lay, d = cv.layer()
    n = rgba(c["near"])
    for x in range(420, 980, 40):
        poplar(d, x, HORIZON, rng.uniform(60, 100), 16, n)
    cv.merge(lay)


SCENES = {
    "registan": scene_registan, "kalyan": scene_kalyan, "tashkent": scene_tashkent,
    "khiva": scene_khiva, "ships": scene_ships, "chilpik": scene_chilpik, "rabat": scene_rabat,
    "kokgumbaz": scene_kokgumbaz, "termez": scene_termez, "jizzakh": scene_jizzakh,
    "steppe": scene_steppe, "namangan": scene_namangan, "andijan": scene_andijan,
    "fergana": scene_fergana, "generic": scene_generic,
}


# ---------------- Ma'lumot paneli ----------------
def rounded(d, box, r, fill):
    d.rounded_rectangle(B(*box), radius=int(r * K), fill=fill)


def text_w(d, s, f):
    return d.textlength(s, font=f) / K


def draw_info(cv, place, lang, weather, air):
    lay, d = cv.layer()
    cur = (weather or {}).get("current") or {}
    time = cur.get("time") or (air or {}).get("time") or datetime.now().strftime("%Y-%m-%dT%H:%M")
    dt = datetime.fromisoformat(time)
    days = WEEKDAYS.get(lang, WEEKDAYS["uz"])
    date_line = f"{days[dt.weekday()]}, {dt:%d.%m} • {dt:%H:%M}"

    f_city, f_small, f_temp, f_desc = font(38, True), font(17), font(70, True), font(22, True)
    white, soft = (255, 255, 255, 255), (230, 236, 245, 230)

    temp = cur.get("temperature_2m")
    _, wdesc = weather_desc(cur.get("weather_code"), lang)
    feels = cur.get("apparent_temperature")
    temp_s = f"{temp:.0f}°" if temp is not None else ""
    feels_s = f"{t(lang, 'feels')} {feels:.0f}°" if feels is not None else ""

    width = max(text_w(d, place, f_city), text_w(d, date_line, f_small))
    if temp_s:
        width = max(width, text_w(d, temp_s, f_temp) + 16 + max(text_w(d, wdesc, f_desc),
                                                             text_w(d, feels_s, f_small)))
    width = min(width, 560)
    height = 196 if temp_s else 100
    rounded(d, (22, 22, 22 + width + 40, 22 + height), 18, (8, 14, 26, 120))
    d.text((42 * K, 34 * K), place, font=f_city, fill=white)
    d.text((44 * K, 84 * K), date_line, font=f_small, fill=soft)
    if temp_s:
        d.text((40 * K, 104 * K), temp_s, font=f_temp, fill=white)
        tx = 40 + text_w(d, temp_s, f_temp) + 16
        d.text((tx * K, 128 * K), wdesc, font=f_desc, fill=white)
        d.text((tx * K, 162 * K), feels_s, font=f_small, fill=soft)

    # Pastki chiplar: chang darajasi, shamol, namlik
    band = Image.new("L", (1, 256))
    band.putdata([int(225 * (i / 255) ** 1.1) for i in range(256)])
    shade = Image.new("RGBA", (W * K, 110 * K), (6, 10, 20, 255))
    shade.putalpha(band.resize(shade.size))
    lay.alpha_composite(shade, (0, (H - 110) * K))

    chips = []
    pm10 = (air or {}).get("pm10")
    if pm10 is not None:
        _, name, _ = level(pm10, lang)
        chips.append((f"PM10 {pm10:.0f} µg/m³ · {name}", LEVEL_COLORS[level_index(pm10)]))
    if cur.get("wind_speed_10m") is not None:
        arrow, wdir = wind_dir(cur.get("wind_direction_10m"), lang)
        chips.append((f"{t(lang, 'wind')} {cur['wind_speed_10m']:.0f} {t(lang, 'ms')} {arrow} {wdir}", None))
    if cur.get("relative_humidity_2m") is not None:
        chips.append((f"{t(lang, 'humidity')} {cur['relative_humidity_2m']:.0f}%", None))

    f_chip = font(17, True)
    x, y = 22, H - 52
    for label, color in chips:
        w = text_w(d, label, f_chip) + (44 if color else 28)
        if x + w > W - 16:
            break
        rounded(d, (x, y, x + w, y + 34), 17, (255, 255, 255, 46))
        tx = x + 14
        if color:
            c = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
            d.ellipse(B(x + 12, y + 10, x + 26, y + 24), fill=rgba(c))
            tx = x + 32
        d.text((tx * K, (y + 7) * K), label, font=f_chip, fill=white)
        x += w + 10
    cv.merge(lay)


# ---------------- Asosiy funksiya ----------------
def palette(cond, night, desert):
    sky = SKY[cond]
    top, bottom = (sky[2], sky[3]) if night else (sky[0], sky[1])
    dark = (10, 12, 22) if night else (34, 40, 58)
    if cond == "dust":
        dark = (40, 26, 16) if night else (92, 58, 32)
    far = mix(bottom, dark, 0.38)
    near = mix(bottom, dark, 0.78)
    sunny = cond in ("clear", "partly") and not night
    accent = mix(near, (38, 158, 172), 0.65) if sunny else (mix(near, (38, 158, 172), 0.3) if not night else near)
    if desert:
        g1, g2 = (222, 186, 128), (176, 136, 84)
    else:
        g1, g2 = (128, 156, 86), (88, 116, 60)
    if cond == "snow":
        g1, g2 = (236, 240, 245), (200, 208, 218)
    shade = 0.62 if night else (0.25 if cond in ("overcast", "rain", "thunder", "fog") else 0.0)
    g1, g2 = mix(g1, dark, shade), mix(g2, dark, shade)
    if cond == "dust":
        g1, g2 = mix(g1, (200, 140, 70), 0.4), mix(g2, (150, 100, 50), 0.4)
    return {
        "top": top, "bottom": bottom, "far": far, "near": near, "accent": accent,
        "recess": mix(near, bottom, 0.32), "rust": mix(near, (120, 58, 30), 0.0 if night else 0.5),
        "ground1": g1, "ground2": g2, "night": night,
        "snow_far": None if cond == "dust" else mix((246, 248, 252), far, 0.35 if not night else 0.6),
    }


def nearest_city(lat, lon, max_km=60):
    from db import distance_km
    best = min(CITIES, key=lambda k: distance_km(lat, lon, CITIES[k][2], CITIES[k][3]))
    return best if distance_km(lat, lon, CITIES[best][2], CITIES[best][3]) <= max_km else None


def make_scene(city_key, place, lang="uz", weather=None, air=None) -> bytes:
    """Shahar manzarasi + ob-havo + ma'lumot paneli. JPEG baytlarini qaytaradi."""
    style = CITY_STYLE.get(city_key, "generic")
    cond, night, haze = condition(weather, air)
    rng = random.Random(zlib.crc32(f"{city_key}".encode()))
    c = palette(cond, night, style in DESERT)
    cv = Canvas()

    cv.img.alpha_composite(gradient(cv.img.size, c["top"], c["bottom"]))
    if night and cond in ("clear", "partly"):
        draw_stars(cv, rng)
    if cond in ("clear", "partly"):
        if night:
            sky_at = mix(c["top"], c["bottom"], 92 / H)
            draw_moon(cv, 860, 92, 30, sky_at)
        else:
            draw_sun(cv, 860, 96, 40)
    elif cond == "dust" and not night:
        draw_sun(cv, 820, 120, 38, dusty=True)

    cloud_rng = random.Random(rng.random())
    if cond == "partly":
        col = (90, 98, 122) if night else (255, 255, 255)
        draw_clouds(cv, cloud_rng, 4, col, 225, y_range=(50, 190))
    elif cond in ("overcast", "snow"):
        col = (70, 74, 88) if night else ((214, 218, 224) if cond == "overcast" else (226, 230, 236))
        draw_clouds(cv, cloud_rng, 12, col, 235, y_range=(10, 200), scale=(1.0, 1.7), blur=3)
    elif cond in ("rain", "thunder"):
        col = (52, 55, 66) if (night or cond == "thunder") else (120, 126, 140)
        draw_clouds(cv, cloud_rng, 14, col, 245, y_range=(0, 190), scale=(1.1, 1.8), blur=3)
        if cond == "thunder":
            draw_lightning(cv, cloud_rng)

    # Yer
    cv.img.alpha_composite(gradient((W * K, (H - HORIZON) * K), c["ground1"], c["ground2"]),
                           (0, HORIZON * K))
    SCENES[style](cv, c, rng)
    lay, d = cv.layer()                                              # yer bo'yicha soya chizig'i
    d.rectangle(B(0, HORIZON, W, HORIZON + 3), fill=rgba(c["near"], 90))
    if style in DESERT:
        for _ in range(5):
            saxaul(d, rng, rng.uniform(20, W - 20), rng.uniform(HORIZON + 30, H - 70), rng.uniform(0.6, 1.1),
                   rgba(mix(c["near"], c["ground2"], 0.2)))
    cv.merge(lay, blur=0.3)

    weather_rng = random.Random(7)
    if cond in ("rain", "thunder"):
        draw_rain(cv, weather_rng)
    elif cond == "snow":
        draw_snow(cv, weather_rng)
    elif cond == "fog":
        draw_fog(cv, weather_rng, night)
    elif cond == "dust":
        draw_dust(cv, weather_rng, night)
    if haze:
        lay, d = cv.layer()
        d.rectangle(B(0, 0, W, H), fill=(214, 178, 118, 60))
        cv.merge(lay)

    draw_info(cv, place, lang, weather, air)
    out = cv.img.resize((W, H), Image.LANCZOS).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue()
