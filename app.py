"""Chang Monitor App: Telegram Mini App (veb-ilova) + bot.

Bitta jarayonda ikkita ish bajariladi:
  1. aiohttp veb-server: ilova sahifasi (webapp/) va JSON API'ni beradi.
  2. aiogram bot: /start, "Ochish" tugmasi, ogohlantirishlar va kunlik hisobot.
"""
import asyncio
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

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.exceptions import TelegramForbiddenError  # noqa: E402
from aiogram.filters import Command, CommandStart  # noqa: E402
from aiogram.types import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,  # noqa: E402
                           MenuButtonWebApp, Message, WebAppInfo)
from aiogram.utils.web_app import safe_parse_webapp_init_data  # noqa: E402
from aiohttp import web  # noqa: E402

import api  # noqa: E402
import db  # noqa: E402
from scene import make_scene, nearest_city  # noqa: E402
from texts import (ALERT_DUST, ALERT_PM10, CITIES, CITY_EN, LANGS, LEVEL_COLORS,  # noqa: E402
                   LEVEL_LIMITS, LEVELS, T, WEATHER_CODES, WEATHER_EN, WIND_DIRS,
                   WIND_GUST_WARN, city_name, level, t)

TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT") or 8080)
DAILY_HOUR = int(os.getenv("DAILY_HOUR") or 7)
_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
WEBAPP_URL = (os.getenv("WEBAPP_URL") or (f"https://{_domain}" if _domain else "")).rstrip("/")
MOCK = os.getenv("MOCK_DATA") == "1"  # faqat sinov uchun: internetsiz soxta ma'lumot
TZ = ZoneInfo("Asia/Tashkent")
WEB_DIR = Path(__file__).parent / "webapp"
CACHE_TTL = 15 * 60  # ma'lumot 15 daqiqa saqlanadi

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("chang_app")

if MOCK:
    import mock_data
    api.get_air, api.get_weather = mock_data.get_air, mock_data.get_weather
    api.get_air_many, api.get_weather_many = mock_data.get_air_many, mock_data.get_weather_many


# ---------------- Kesh (bir xil ma'lumotni qayta-qayta so'ramaslik uchun) ----------------
_cache: dict = {}


async def cached(key, factory, ttl=CACHE_TTL):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    value = await factory()
    _cache[key] = (time.time(), value)
    if len(_cache) > 500:  # xotira to'lib ketmasligi uchun
        for k in sorted(_cache, key=lambda k: _cache[k][0])[:100]:
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


# ---------------- API ----------------
async def h_meta(request):
    """Ilova uchun doimiy ma'lumotlar: shaharlar, darajalar, ob-havo nomlari, maslahatlar."""
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
        "alert": {"pm10": ALERT_PM10, "dust": ALERT_DUST, "gust": WIND_GUST_WARN},
        "tips": {lang: T[lang]["tips"] for lang in LANGS},
        "info": {lang: T[lang]["info"] for lang in LANGS},
        "bot_ready": bool(TOKEN),
    })


async def h_overview(request):
    """Xarita va ro'yxat uchun 14 shaharning hozirgi holati (2 ta so'rov bilan)."""
    keys = list(CITIES)
    lats = [CITIES[k][2] for k in keys]
    lons = [CITIES[k][3] for k in keys]

    async def load():
        air, weather = await asyncio.gather(api.get_air_many(lats, lons),
                                            api.get_weather_many(lats, lons),
                                            return_exceptions=True)
        out = []
        for i, k in enumerate(keys):
            a = air[i]["current"] if not isinstance(air, Exception) else {}
            w = weather[i]["current"] if not isinstance(weather, Exception) else {}
            out.append({"key": k, "pm10": a.get("pm10"), "pm2_5": a.get("pm2_5"), "dust": a.get("dust"),
                        "temp": w.get("temperature_2m"), "code": w.get("weather_code"),
                        "wind": w.get("wind_speed_10m"), "wind_dir": w.get("wind_direction_10m"),
                        "is_day": w.get("is_day")})
        if isinstance(air, Exception):
            log.warning("Overview chang xatosi: %s", air)
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
        "warn": {
            "dust": dust_peak if (dust_peak["pm10"] >= ALERT_PM10 or dust_peak["dust"] >= ALERT_DUST) else None,
            "wind": gust if gust and gust["gust"] >= WIND_GUST_WARN else None,
        },
    })


async def h_scene(request):
    """Shahar manzarasi rasmi (ob-havoga mos)."""
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
    return web.Response(body=img, content_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=900"})


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
    return {"id": data.user.id, "lang": data.user.language_code}


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


async def h_index(request):
    return web.FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


async def h_health(request):
    return web.json_response({"ok": True, "users": db.count(), "webapp": WEBAPP_URL or None})


def make_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", h_index)
    app.router.add_get("/health", h_health)
    app.router.add_get("/api/meta", h_meta)
    app.router.add_get("/api/overview", h_overview)
    app.router.add_get("/api/city", h_city)
    app.router.add_get("/api/scene", h_scene)
    app.router.add_get("/api/me", h_me_get)
    app.router.add_post("/api/me", h_me_post)
    app.router.add_static("/static/", WEB_DIR, append_version=True)
    return app


# ---------------- Bot ----------------
dp = Dispatcher()

BOT_T = {
    "uz": {
        "start": ("Assalomu alaykum, {name}! 👋\n\n"
                  "<b>Chang Monitor</b> ilovasiga xush kelibsiz 🌪\n"
                  "Chang darajasi, ob-havo, shamol, 3 kunlik prognoz, grafiklar va "
                  "O'zbekiston xaritasi: barchasi bitta ilovada.\n\n"
                  "👇 Ilovani ochish uchun tugmani bosing."),
        "open": "📱 Ilovani ochish",
        "details": "📱 Ilovada batafsil",
        "no_url": "⚙️ Ilova manzili hali sozlanmagan. Admin Railway'da domen yaratishi kerak.",
        "help": "Ilovani ochish uchun pastdagi tugmani yoki chap pastdagi menyu tugmasini bosing.",
    },
    "ru": {
        "start": ("Здравствуйте, {name}! 👋\n\n"
                  "Добро пожаловать в приложение <b>Chang Monitor</b> 🌪\n"
                  "Уровень пыли, погода, ветер, прогноз на 3 дня, графики и карта "
                  "Узбекистана: всё в одном приложении.\n\n"
                  "👇 Нажмите кнопку, чтобы открыть приложение."),
        "open": "📱 Открыть приложение",
        "details": "📱 Подробнее в приложении",
        "no_url": "⚙️ Адрес приложения ещё не настроен. Админу нужно создать домен в Railway.",
        "help": "Чтобы открыть приложение, нажмите кнопку ниже или кнопку меню слева внизу.",
    },
    "en": {
        "start": ("Hello, {name}! 👋\n\n"
                  "Welcome to the <b>Chang Monitor</b> app 🌪\n"
                  "Dust levels, weather, wind, a 3-day forecast, charts and a map of "
                  "Uzbekistan: all in one app.\n\n"
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


def user_lang(m: Message) -> str:
    u = db.get_user(m.from_user.id)
    if u and u["lang"]:
        return u["lang"]
    code = (m.from_user.language_code or "")[:2]
    return code if code in LANGS else "uz"


@dp.message(CommandStart())
async def cmd_start(m: Message, bot: Bot):
    lang = user_lang(m)
    db.ensure_user(m.from_user.id, lang)
    if not WEBAPP_URL:
        return await m.answer(bt(lang, "no_url"))
    import html
    await m.answer(bt(lang, "start", name=html.escape(m.from_user.first_name or "")),
                   reply_markup=open_kb(lang))
    try:  # chap pastdagi menyu tugmasi foydalanuvchi tilida
        await bot.set_chat_menu_button(chat_id=m.chat.id, menu_button=MenuButtonWebApp(
            text=bt(lang, "open")[2:], web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception as e:  # noqa: BLE001
        log.warning("Menyu tugmasi: %s", e)


@dp.message(Command("help"))
@dp.message()
async def cmd_help(m: Message):
    lang = user_lang(m)
    await m.answer(bt(lang, "help") if WEBAPP_URL else bt(lang, "no_url"), reply_markup=open_kb(lang))


def place_of(u, lang):
    if u["city"] in CITIES:
        return city_name(u["city"], lang)
    return f"{T[lang]['my_location']} ({u['lat']:.2f}, {u['lon']:.2f})"


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
        nxt = api.next_hours_max(air, 24)
        if nxt["pm10"] < ALERT_PM10 and nxt["dust"] < ALERT_DUST:
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
        text = (t(lang, "morning") + f"📍 <b>{place_of(u, lang)}</b>\n{temp}"
                f"{emoji} PM10: <b>{c.get('pm10') or 0:.0f}</b> µg/m³ ({name})\n💡 {advice}")
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
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
            text="Ilova", web_app=WebAppInfo(url=WEBAPP_URL)))
        log.info("Ilova manzili: %s", WEBAPP_URL)
    else:
        log.warning("WEBAPP_URL yo'q! Railway'da Settings → Networking → Generate Domain qiling.")


# ---------------- Ishga tushirish ----------------
async def main():
    runner = web.AppRunner(make_web_app())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Veb-server %s-portda ishga tushdi", PORT)

    if not TOKEN:
        log.warning("BOT_TOKEN yo'q: faqat veb-ilova ishlaydi (bot o'chiq).")
        await asyncio.Event().wait()
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        await setup_bot(bot)
    except Exception as e:  # noqa: BLE001
        log.warning("Bot sozlamalari: %s", e)
    asyncio.create_task(scheduler(bot))
    log.info("Bot ishga tushdi")
    await dp.start_polling(bot, handle_signals=False)


if __name__ == "__main__":
    asyncio.run(main())
