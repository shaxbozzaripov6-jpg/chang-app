"""Chang Monitor App: Telegram Mini App (veb-ilova) + bot.

Bitta jarayonda ikkita ish bajariladi:
  1. aiohttp veb-server: ilova sahifasi (webapp/) va JSON API'ni beradi.
  2. aiogram bot: /start, "Ochish" tugmasi, ogohlantirishlar, kunlik hisobot va bo'ron rasmlari moderatsiyasi.
"""
import asyncio
import html
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()

from aiogram import Bot, Dispatcher, F  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.exceptions import TelegramForbiddenError  # noqa: E402
from aiogram.filters import Command, CommandStart  # noqa: E402
from aiogram.types import (BotCommand, BufferedInputFile, CallbackQuery,  # noqa: E402
                           InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message,
                           WebAppInfo)
from aiogram.utils.web_app import safe_parse_webapp_init_data  # noqa: E402
from aiohttp import web  # noqa: E402

import api  # noqa: E402
import db  # noqa: E402
from risk import storm_risk  # noqa: E402
from scene import make_scene, nearest_city  # noqa: E402
from texts import (ALERT_DUST, ALERT_PM10, CITIES, CITY_EN, LANGS, LEVEL_COLORS,  # noqa: E402
                   LEVEL_LIMITS, LEVELS, T, WEATHER_CODES, WEATHER_EN, WIND_DIRS,
                   WIND_GUST_WARN, city_name, level, t)

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
PORT = int(os.getenv("PORT") or 8080)
DAILY_HOUR = int(os.getenv("DAILY_HOUR") or 7)
_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
WEBAPP_URL = (os.getenv("WEBAPP_URL") or (f"https://{_domain}" if _domain else "")).rstrip("/")
MOCK = os.getenv("MOCK_DATA") == "1"  # faqat sinov uchun: internetsiz soxta ma'lumot
TZ = ZoneInfo("Asia/Tashkent")
WEB_DIR = Path(__file__).parent / "webapp"
CACHE_TTL = 15 * 60          # shahar ma'lumoti 15 daqiqa saqlanadi
GRID_TTL = 3 * 3600          # chang buluti xaritasi 3 soat saqlanadi (API limitini tejash uchun)
HISTORY_TTL = 6 * 3600       # tarix 6 soat saqlanadi
REPORT_LIMIT = 5             # bir kishi 24 soatda nechta rasm yubora oladi
REPORT_RADIUS = 100          # tasdiqlangan rasm necha km radiusdagilarga yuboriladi
SENSITIVE_PM10, SENSITIVE_DUST = 150, 120   # sezgir profillar uchun ogohlantirish chegarasi

# Chang buluti uchun nuqtalar to'ri (O'zbekiston va atrofi), 7 × 12 = 84 nuqta
GRID_LATS = [37.0 + 1.5 * i for i in range(7)]
GRID_LONS = [56.0 + 1.5 * j for j in range(12)]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("chang_app")

if MOCK:
    import mock_data
    for _name in ("get_air", "get_weather", "get_air_many", "get_weather_many", "get_history", "get_grid"):
        setattr(api, _name, getattr(mock_data, _name))


# ---------------- Kesh ----------------
_cache: dict = {}


async def cached(key, factory, ttl=CACHE_TTL):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    value = await factory()
    _cache[key] = (time.time(), value)
    if len(_cache) > 600:
        for k in sorted(_cache, key=lambda k: _cache[k][0])[:150]:
            _cache.pop(k, None)
    return value


async def point_data(lat: float, lon: float) -> dict:
    lat, lon = round(lat, 2), round(lon, 2)

    async def load():
        air, weather = await asyncio.gather(api.get_air(lat, lon), api.get_weather(lat, lon),
                                            return_exceptions=True)
        if isinstance(air, Exception):
            raise air
        if isinstance(weather, Exception):
            log.warning("Ob-havo xatosi: %s", weather)
            weather = None
        return {"air": air, "weather": weather}

    return await cached(("point", lat, lon), load)


def resolve_place(q) -> tuple:
    """So'rovdan joyni aniqlaydi: ?key=samarqand yoki ?lat=..&lon=.."""
    key = q.get("key")
    if key in CITIES:
        _, _, lat, lon = CITIES[key]
        return key, lat, lon, key
    try:
        lat, lon = float(q.get("lat")), float(q.get("lon"))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="key yoki lat/lon kerak")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise web.HTTPBadRequest(text="noto'g'ri koordinata")
    return None, lat, lon, nearest_city(lat, lon) or "generic"


def init_user(request) -> dict | None:
    """Telegram initData imzosini tekshiradi. Soxta so'rovlar rad etiladi."""
    raw = request.headers.get("X-Init-Data", "")
    if not raw or not TOKEN:
        return None
    try:
        data = safe_parse_webapp_init_data(TOKEN, raw)
    except ValueError:
        return None
    if not data.user or (data.auth_date and datetime.now(data.auth_date.tzinfo) - data.auth_date > timedelta(days=7)):
        return None
    return {"id": data.user.id, "lang": data.user.language_code, "name": data.user.first_name or ""}


# ---------------- API: asosiy ma'lumotlar ----------------
async def h_meta(request):
    weather_names = {
        "uz": {c: v[1] for c, v in WEATHER_CODES.items()},
        "ru": {c: v[2] for c, v in WEATHER_CODES.items()},
        "en": WEATHER_EN,
    }
    return web.json_response({
        "cities": [{"key": k, "lat": v[2], "lon": v[3],
                    "name": {"uz": v[0], "ru": v[1], "en": CITY_EN.get(k, v[0])}}
                   for k, v in CITIES.items()],
        "levels": {"limits": LEVEL_LIMITS[:-1], "colors": LEVEL_COLORS,
                   "names": {lang: [n for n, _ in LEVELS[lang]] for lang in LANGS},
                   "advice": {lang: [a for _, a in LEVELS[lang]] for lang in LANGS}},
        "weather_emoji": {c: v[0] for c, v in WEATHER_CODES.items()},
        "weather_names": weather_names,
        "wind_dirs": WIND_DIRS,
        "alert": {"pm10": ALERT_PM10, "dust": ALERT_DUST, "gust": WIND_GUST_WARN,
                  "sensitive_pm10": SENSITIVE_PM10},
        "tips": {lang: T[lang]["tips"] for lang in LANGS},
        "info": {lang: T[lang]["info"] for lang in LANGS},
        "bot_ready": bool(TOKEN),
        "moderated": bool(ADMIN_ID),
    })


async def h_overview(request):
    """Xarita, reyting va ro'yxat uchun 14 shaharning hozirgi holati (2 ta so'rov bilan)."""
    keys = list(CITIES)
    lats = [CITIES[k][2] for k in keys]
    lons = [CITIES[k][3] for k in keys]

    async def load():
        air, weather = await asyncio.gather(api.get_air_many(lats, lons),
                                            api.get_weather_many(lats, lons), return_exceptions=True)
        if isinstance(air, Exception):
            raise air
        out = []
        for i, k in enumerate(keys):
            a = air[i]["current"]
            w = weather[i]["current"] if not isinstance(weather, Exception) else {}
            out.append({"key": k, "pm10": a.get("pm10"), "pm2_5": a.get("pm2_5"), "dust": a.get("dust"),
                        "temp": w.get("temperature_2m"), "code": w.get("weather_code"),
                        "wind": w.get("wind_speed_10m"), "wind_dir": w.get("wind_direction_10m"),
                        "is_day": w.get("is_day")})
        return out

    try:
        return web.json_response({"cities": await cached("overview", load)})
    except Exception as e:  # noqa: BLE001
        log.warning("Overview xatosi: %s", e)
        raise web.HTTPBadGateway(text="data source error")


async def h_city(request):
    key, lat, lon, scene_key = resolve_place(request.query)
    try:
        d = await point_data(lat, lon)
    except Exception as e:  # noqa: BLE001
        log.warning("Ma'lumot xatosi: %s", e)
        raise web.HTTPBadGateway(text="data source error")
    air, weather = d["air"], d["weather"]
    dust_peak = api.next_hours_max(air, 24)
    gust = api.max_gust_24h(weather)
    return web.json_response({
        "key": key, "lat": lat, "lon": lon, "scene_key": scene_key,
        "air": {"current": air["current"], "hourly": air["hourly"]},
        "weather": weather and {"current": weather.get("current"), "hourly": weather.get("hourly"),
                                "daily": weather.get("daily")},
        "days": api.daily_summary(air),
        "risk": storm_risk(air, weather),
        "warn": {
            "dust": dust_peak if (dust_peak["pm10"] >= ALERT_PM10 or dust_peak["dust"] >= ALERT_DUST) else None,
            "wind": gust if gust and gust["gust"] >= WIND_GUST_WARN else None,
        },
    })


async def h_scene(request):
    key, lat, lon, scene_key = resolve_place(request.query)
    lang = request.query.get("lang", "uz")
    lang = lang if lang in LANGS else "uz"
    place = city_name(key, lang) if key else T[lang]["my_location"]
    try:
        d = await point_data(lat, lon)
    except Exception:  # noqa: BLE001
        d = {"air": None, "weather": None}

    async def render():
        air_cur = d["air"]["current"] if d["air"] else None
        return await asyncio.to_thread(make_scene, scene_key, place, lang, d["weather"], air_cur)

    hour = datetime.now(TZ).strftime("%Y%m%d%H")
    img = await cached(("scene", scene_key, round(lat, 2), round(lon, 2), lang, hour), render)
    return web.Response(body=img, content_type="image/jpeg", headers={"Cache-Control": "public, max-age=900"})


# ---------------- API: chang buluti, tarix ----------------
async def h_grid(request):
    """Animatsiyali xarita uchun: har 3 soatlik kadrlar, har kadrda 84 nuqtadagi chang va shamol."""
    async def load():
        lats, lons = [], []
        for la in GRID_LATS:
            for lo in GRID_LONS:
                lats.append(la)
                lons.append(lo)
        air, wind = await api.get_grid(lats, lons)
        times = air[0]["hourly"]["time"]
        now = datetime.now(TZ).strftime("%Y-%m-%dT%H:00")
        start = next((i for i, x in enumerate(times) if x >= now), 0)
        frames = list(range(start, len(times), 3))

        def col(src, var, i):
            v = src["hourly"][var][i] if src and i < len(src["hourly"][var]) else None
            return None if v is None else round(v)

        return {
            "lats": GRID_LATS, "lons": GRID_LONS, "step": 1.5,
            "times": [times[i] for i in frames],
            "dust": [[col(p, "dust", i) for p in air] for i in frames],
            "wind_speed": [[col(p, "wind_speed_10m", i) for p in wind] for i in frames] if wind else None,
            "wind_dir": [[col(p, "wind_direction_10m", i) for p in wind] for i in frames] if wind else None,
        }

    try:
        return web.json_response(await cached("grid", load, ttl=GRID_TTL))
    except Exception as e:  # noqa: BLE001
        log.warning("Grid xatosi: %s", e)
        raise web.HTTPBadGateway(text="data source error")


async def h_history(request):
    key, lat, lon, _ = resolve_place(request.query)
    lat, lon = round(lat, 2), round(lon, 2)

    async def load():
        data = await api.get_history(lat, lon, 92)
        return api.daily_history(data, datetime.now(TZ).strftime("%Y-%m-%d"))

    try:
        return web.json_response({"days": await cached(("history", lat, lon), load, ttl=HISTORY_TTL)})
    except Exception as e:  # noqa: BLE001
        log.warning("Tarix xatosi: %s", e)
        raise web.HTTPBadGateway(text="data source error")


# ---------------- API: foydalanuvchi sozlamalari ----------------
async def h_me_get(request):
    user = init_user(request)
    if not user:
        raise web.HTTPUnauthorized(text="telegram only")
    guess = (user["lang"] or "")[:2]
    db.ensure_user(user["id"], guess if guess in LANGS else "uz")
    return web.json_response(db.user_dict(user["id"]))


async def h_me_post(request):
    user = init_user(request)
    if not user:
        raise web.HTTPUnauthorized(text="telegram only")
    body = await request.json()
    upd = {}
    if body.get("lang") in LANGS:
        upd["lang"] = body["lang"]
    if body.get("profile") in db.PROFILES:
        upd["profile"] = body["profile"]
    if body.get("city") in CITIES:
        upd.update(city=body["city"], lat=CITIES[body["city"]][2], lon=CITIES[body["city"]][3])
    elif body.get("city") == "loc":
        try:
            upd.update(city="loc", lat=float(body["lat"]), lon=float(body["lon"]))
        except (KeyError, TypeError, ValueError):
            raise web.HTTPBadRequest(text="lat/lon")
    for f in ("alerts", "daily"):
        if f in body:
            upd[f] = 1 if body[f] else 0
    db.update_user(user["id"], **upd)
    return web.json_response(db.user_dict(user["id"]))


# ---------------- API: bo'ron rasmlari ----------------
_photo_cache: dict = {}


async def h_reports(request):
    q = request.query
    lat = lon = None
    try:
        lat, lon = float(q["lat"]), float(q["lon"])
    except (KeyError, ValueError):
        pass
    out = []
    for r in db.recent_reports(48):
        item = {"id": r["id"], "lat": r["lat"], "lon": r["lon"], "city": r["city"],
                "caption": r["caption"] or "", "created": r["created"]}
        if lat is not None:
            item["km"] = round(db.distance_km(lat, lon, r["lat"], r["lon"]))
        out.append(item)
    if lat is not None:
        out.sort(key=lambda x: x["km"])
    return web.json_response({"reports": out})


async def h_report_photo(request):
    bot: Bot | None = request.app.get("bot")
    try:
        rid = int(request.match_info["rid"])
    except ValueError:
        raise web.HTTPNotFound()
    r = db.get_report(rid)
    if not r or r["status"] != "approved" or not r["file_id"] or not bot:
        raise web.HTTPNotFound()
    data = _photo_cache.get(rid)
    if data is None:
        try:
            f = await bot.get_file(r["file_id"])
            buf = await bot.download_file(f.file_path)
            data = buf.read()
        except Exception as e:  # noqa: BLE001
            log.warning("Rasm yuklanmadi %s: %s", rid, e)
            raise web.HTTPNotFound()
        _photo_cache[rid] = data
        if len(_photo_cache) > 80:
            _photo_cache.pop(next(iter(_photo_cache)))
    return web.Response(body=data, content_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


async def h_report_post(request):
    user = init_user(request)
    if not user:
        raise web.HTTPUnauthorized(text="telegram only")
    bot: Bot | None = request.app.get("bot")
    if not bot:
        raise web.HTTPServiceUnavailable(text="bot off")
    if db.reports_today(user["id"]) >= REPORT_LIMIT:
        return web.json_response({"error": "limit", "limit": REPORT_LIMIT}, status=429)

    form = await request.post()
    photo = form.get("photo")
    if photo is None or not hasattr(photo, "file"):
        raise web.HTTPBadRequest(text="photo kerak")
    content = photo.file.read()
    if not content or len(content) > 10 * 1024 * 1024:
        raise web.HTTPBadRequest(text="rasm hajmi noto'g'ri")
    caption = (form.get("caption") or "").strip()[:300]
    key, lat, lon, _ = resolve_place(form)

    status = "pending" if ADMIN_ID else "approved"
    rid = db.add_report(user["id"], user["name"], key or "loc", lat, lon, None, caption, status)
    place = city_name(key, "uz") if key else f"({lat:.2f}, {lon:.2f})"
    if ADMIN_ID:
        chat, kb = ADMIN_ID, moderation_kb(rid)
        cap = (f"🆕 <b>Bo'ron xabari #{rid}</b> (ilovadan)\n👤 {html.escape(user['name'])} "
               f"(id {user['id']})\n📍 {place}")
    else:
        chat, kb = user["id"], None
        cap = "📸 " + t(db.get_user(user["id"])["lang"] if db.get_user(user["id"]) else "uz", "report_saved")
    if caption:
        cap += f"\n💬 {html.escape(caption, quote=False)}"
    try:
        msg = await bot.send_photo(chat, BufferedInputFile(content, "storm.jpg"), caption=cap, reply_markup=kb)
    except Exception as e:  # noqa: BLE001
        log.warning("Rasm yuborilmadi: %s", e)
        db.delete_report(rid)
        raise web.HTTPBadGateway(text="telegram error")
    db.set_report_file(rid, msg.photo[-1].file_id)
    return web.json_response({"id": rid, "status": status})


async def h_index(request):
    return web.FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


async def h_health(request):
    return web.json_response({"ok": True, "users": db.count(), "webapp": WEBAPP_URL or None})


def make_web_app(bot: Bot | None = None) -> web.Application:
    app = web.Application(client_max_size=12 * 1024 * 1024)
    app["bot"] = bot
    app.router.add_get("/", h_index)
    app.router.add_get("/health", h_health)
    app.router.add_get("/api/meta", h_meta)
    app.router.add_get("/api/overview", h_overview)
    app.router.add_get("/api/city", h_city)
    app.router.add_get("/api/scene", h_scene)
    app.router.add_get("/api/grid", h_grid)
    app.router.add_get("/api/history", h_history)
    app.router.add_get("/api/me", h_me_get)
    app.router.add_post("/api/me", h_me_post)
    app.router.add_get("/api/reports", h_reports)
    app.router.add_post("/api/report", h_report_post)
    app.router.add_get("/api/report_photo/{rid}", h_report_photo)
    app.router.add_static("/static/", WEB_DIR)
    return app


# ---------------- Bot ----------------
dp = Dispatcher()

BOT_T = {
    "uz": {
        "start": ("Assalomu alaykum, {name}! 👋\n\n"
                  "<b>Chang Monitor</b> ilovasiga xush kelibsiz 🌪\n"
                  "Chang darajasi, bo'ron xavfi, ob-havo, animatsiyali chang xaritasi, statistika "
                  "va eng toza soatlar: barchasi bitta ilovada.\n\n"
                  "👇 Ilovani ochish uchun tugmani bosing."),
        "open": "📱 Ilovani ochish",
        "details": "📱 Ilovada batafsil",
        "no_url": "⚙️ Ilova manzili hali sozlanmagan. Admin Railway'da domen yaratishi kerak.",
        "help": "Ilovani ochish uchun pastdagi tugmani yoki chap pastdagi menyu tugmasini bosing.",
    },
    "ru": {
        "start": ("Здравствуйте, {name}! 👋\n\n"
                  "Добро пожаловать в приложение <b>Chang Monitor</b> 🌪\n"
                  "Уровень пыли, риск бури, погода, анимированная карта пыли, статистика "
                  "и самые чистые часы: всё в одном приложении.\n\n"
                  "👇 Нажмите кнопку, чтобы открыть приложение."),
        "open": "📱 Открыть приложение",
        "details": "📱 Подробнее в приложении",
        "no_url": "⚙️ Адрес приложения ещё не настроен. Админу нужно создать домен в Railway.",
        "help": "Чтобы открыть приложение, нажмите кнопку ниже или кнопку меню слева внизу.",
    },
    "en": {
        "start": ("Hello, {name}! 👋\n\n"
                  "Welcome to the <b>Chang Monitor</b> app 🌪\n"
                  "Dust levels, storm risk, weather, an animated dust map, statistics "
                  "and the cleanest hours: all in one app.\n\n"
                  "👇 Tap the button to open the app."),
        "open": "📱 Open the app",
        "details": "📱 Details in the app",
        "no_url": "⚙️ The app address isn't set up yet. The admin needs to create a domain on Railway.",
        "help": "To open the app, tap the button below or the menu button at the bottom left.",
    },
}


def bt(lang, key, **kw):
    s = BOT_T.get(lang, BOT_T["uz"])[key]
    return s.format(**kw) if kw else s


def open_kb(lang: str, key: str = "open"):
    if not WEBAPP_URL:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=bt(lang, key), web_app=WebAppInfo(url=WEBAPP_URL))]])


def moderation_kb(rid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"rep:ok:{rid}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rep:no:{rid}"),
    ]])


def user_lang(uid: int, code: str | None = None) -> str:
    u = db.get_user(uid)
    if u and u["lang"]:
        return u["lang"]
    code = (code or "")[:2]
    return code if code in LANGS else "uz"


def place_of(row, lang):
    if row["city"] in CITIES:
        return city_name(row["city"], lang)
    return f"{T[lang]['my_location']} ({row['lat']:.2f}, {row['lon']:.2f})"


@dp.message(CommandStart())
async def cmd_start(m: Message, bot: Bot):
    lang = user_lang(m.from_user.id, m.from_user.language_code)
    db.ensure_user(m.from_user.id, lang)
    if not WEBAPP_URL:
        return await m.answer(bt(lang, "no_url"))
    await m.answer(bt(lang, "start", name=html.escape(m.from_user.first_name or "")), reply_markup=open_kb(lang))
    try:  # chap pastdagi menyu tugmasi foydalanuvchi tilida
        await bot.set_chat_menu_button(chat_id=m.chat.id, menu_button=MenuButtonWebApp(
            text=bt(lang, "open")[2:], web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception as e:  # noqa: BLE001
        log.warning("Menyu tugmasi: %s", e)


@dp.message(Command("stat"))
async def cmd_stat(m: Message):
    if ADMIN_ID and m.from_user.id == ADMIN_ID:
        s = db.stats()
        await m.answer(f"👥 Foydalanuvchilar: {s['users']}\n🔔 Ogohlantirish yoqilgan: {s['alerts']}\n"
                       f"📸 Bo'ron rasmlari: {s['reports']} (tekshiruvda: {s['pending']})")


@dp.message(Command("help"))
@dp.message()
async def cmd_help(m: Message):
    lang = user_lang(m.from_user.id, m.from_user.language_code)
    await m.answer(bt(lang, "help") if WEBAPP_URL else bt(lang, "no_url"), reply_markup=open_kb(lang))


@dp.callback_query(F.data.startswith("rep:"))
async def on_moderate(c: CallbackQuery, bot: Bot):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("⛔")
    _, action, rid = c.data.split(":")
    r = db.get_report(int(rid))
    if not r or r["status"] != "pending":
        await c.answer("Allaqachon ko'rib chiqilgan")
        return await c.message.edit_reply_markup(reply_markup=None)
    approved = action == "ok"
    db.set_report_status(r["id"], "approved" if approved else "rejected")
    await c.answer("Tasdiqlandi ✅" if approved else "Rad etildi ❌")
    mark = "\n\n✅ <b>Tasdiqlandi</b>" if approved else "\n\n❌ <b>Rad etildi</b>"
    await c.message.edit_caption(caption=(c.message.html_text or "") + mark, reply_markup=None)
    author_lang = user_lang(r["user_id"])
    await safe_send(bot, r["user_id"], t(author_lang, "report_approved" if approved else "report_rejected"))
    if not approved:
        return
    sent = 0
    for km, u in db.users_near(r["lat"], r["lon"], REPORT_RADIUS, exclude=r["user_id"]):
        lang = u["lang"] or "uz"
        cap = t(lang, "report_nearby", km=f"{km:.0f}", place=place_of(r, lang), time=r["created"][11:16])
        if r["caption"]:
            cap += f"\n💬 {html.escape(r['caption'], quote=False)}"
        try:
            await bot.send_photo(u["user_id"], r["file_id"], caption=cap, reply_markup=open_kb(lang, "details"))
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramForbiddenError:
            db.delete_user(u["user_id"])
        except Exception as e:  # noqa: BLE001
            log.warning("Rasm yuborilmadi %s: %s", u["user_id"], e)
    await c.message.answer(f"📤 #{r['id']} xabar {sent} ta foydalanuvchiga yuborildi.")


async def safe_send(bot: Bot, uid: int, text: str, kb=None):
    try:
        await bot.send_message(uid, text, reply_markup=kb)
        await asyncio.sleep(0.05)
    except TelegramForbiddenError:
        db.delete_user(uid)
    except Exception as e:  # noqa: BLE001
        log.warning("Xabar yuborilmadi %s: %s", uid, e)


async def check_alerts(bot: Bot):
    now = datetime.now(TZ)
    for u in db.users_with("alerts"):
        try:
            air = (await point_data(u["lat"], u["lon"]))["air"]
        except Exception:  # noqa: BLE001
            continue
        sensitive = u["profile"] in db.SENSITIVE
        lim_pm10 = SENSITIVE_PM10 if sensitive else ALERT_PM10
        lim_dust = SENSITIVE_DUST if sensitive else ALERT_DUST
        nxt = api.next_hours_max(air, 24)
        if nxt["pm10"] < lim_pm10 and nxt["dust"] < lim_dust:
            continue
        if u["last_alert"] and now - datetime.fromisoformat(u["last_alert"]) < timedelta(hours=12):
            continue
        lang = u["lang"] or "uz"
        emoji, name, advice = level(nxt["pm10"], lang)
        day, hour = nxt["time"].split("T")
        when = t(lang, "today") if day == now.strftime("%Y-%m-%d") else t(lang, "tomorrow")
        text = t(lang, "alert", place=place_of(u, lang), when=when, hour=hour, emoji=emoji,
                 pm10=f"{nxt['pm10']:.0f}", level=name, dust=f"{nxt['dust']:.0f}", advice=advice)
        await safe_send(bot, u["user_id"], text, open_kb(lang, "details"))
        db.set_last_alert(u["user_id"], now.isoformat())


async def send_daily(bot: Bot):
    for u in db.users_with("daily"):
        try:
            d = await point_data(u["lat"], u["lon"])
        except Exception:  # noqa: BLE001
            continue
        lang = u["lang"] or "uz"
        c = d["air"]["current"]
        emoji, name, advice = level(c.get("pm10"), lang)
        w = (d["weather"] or {}).get("current") or {}
        temp = f"🌡 {w['temperature_2m']:.0f}°C\n" if w.get("temperature_2m") is not None else ""
        risk = storm_risk(d["air"], d["weather"])
        text = (t(lang, "morning") + f"📍 <b>{place_of(u, lang)}</b>\n{temp}"
                f"{emoji} PM10: <b>{c.get('pm10') or 0:.0f}</b> µg/m³ ({name})\n"
                f"🎯 {risk['score']}/100\n💡 {advice}")
        await safe_send(bot, u["user_id"], text, open_kb(lang, "details"))


async def scheduler(bot: Bot):
    while True:
        now = datetime.now(TZ)
        nxt = (now + timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
        await asyncio.sleep((nxt - now).total_seconds())
        try:
            if nxt.hour == DAILY_HOUR:
                await send_daily(bot)
            await check_alerts(bot)
        except Exception:  # noqa: BLE001
            log.exception("Scheduler xatosi")


async def setup_bot(bot: Bot):
    await bot.set_my_commands([BotCommand(command="start", description="Chang Monitor ilovasi"),
                               BotCommand(command="help", description="Yordam")])
    if WEBAPP_URL:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Ilova", web_app=WebAppInfo(url=WEBAPP_URL)))
        log.info("Ilova manzili: %s", WEBAPP_URL)
    else:
        log.warning("WEBAPP_URL yo'q! Railway'da Settings → Networking → Generate Domain qiling.")


# ---------------- Ishga tushirish ----------------
async def main():
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML")) if TOKEN else None
    runner = web.AppRunner(make_web_app(bot))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Veb-server %s-portda ishga tushdi", PORT)

    if not bot:
        log.warning("BOT_TOKEN yo'q: faqat veb-ilova ishlaydi (bot o'chiq).")
        await asyncio.Event().wait()
    try:
        await setup_bot(bot)
    except Exception as e:  # noqa: BLE001
        log.warning("Bot sozlamalari: %s", e)
    asyncio.create_task(scheduler(bot))
    log.info("Bot ishga tushdi")
    await dp.start_polling(bot, handle_signals=False)


if __name__ == "__main__":
    asyncio.run(main())
