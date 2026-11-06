"""Har kungi ma'lumotlar arxivi: 14 shahar bo'yicha chang, gazlar va ob-havo.

- Birinchi ishga tushishda o'tgan 92 kun avtomatik to'ldiriladi.
- Keyin har kuni (va bir necha soatda bir) so'nggi kunlar qayta hisoblanadi.
- Haqiqiy datchik o'lchovlari har soat sensor_obs jadvaliga yoziladi va kunlik o'rtachaga qo'shiladi.
- Arxiv ochiq: /api/archive (JSON) va /api/archive.csv (Excel) orqali istalgan odam yuklab oladi.
"""
import csv
import io
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import api
import db
from risk import _score
from texts import CITIES, CITY_EN

log = logging.getLogger("chang_app.archive")
TZ = ZoneInfo("Asia/Tashkent")

AIR_VARS = ("pm10,pm2_5,dust,aerosol_optical_depth,us_aqi,ozone,nitrogen_dioxide,sulphur_dioxide,"
            "carbon_monoxide,uv_index")
WX_VARS = "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,precipitation,soil_moisture_0_to_1cm"


async def fetch_many(lats: list, lons: list, past_days: int) -> tuple[list, list | None]:
    """Barcha shaharlar uchun o'tgan kunlarning soatlik ma'lumoti (2 ta so'rov)."""
    air = await api._get_many(api.URL, lats, lons, {"hourly": AIR_VARS, "past_days": past_days, "forecast_days": 1})
    try:
        wx = await api._get_many(api.WEATHER_URL, lats, lons, {"hourly": WX_VARS, "past_days": past_days,
                                                              "forecast_days": 1, "wind_speed_unit": "ms"})
    except Exception as e:  # noqa: BLE001
        log.warning("Arxiv ob-havo xatosi: %s", e)
        wx = None
    return air, wx


def _by_day(h: dict, var: str, today: str) -> dict:
    out: dict[str, list] = {}
    for t, v in zip(h.get("time") or [], h.get(var) or []):
        if v is not None and t[:10] < today:
            out.setdefault(t[:10], []).append(v)
    return out


def _mean(v):
    return round(sum(v) / len(v), 1) if v else None


def _max(v):
    return round(max(v), 1) if v else None


def _min(v):
    return round(min(v), 1) if v else None


def aggregate(air: dict, wx: dict | None, today: str) -> dict:
    """Soatlik ma'lumotni kunlik ko'rsatkichlarga aylantiradi (bugungi to'liq bo'lmagan kun kiritilmaydi)."""
    ah, wh = air.get("hourly") or {}, (wx or {}).get("hourly") or {}
    A = {v: _by_day(ah, v, today) for v in AIR_VARS.split(",")}
    W = {v: _by_day(wh, v, today) for v in WX_VARS.split(",")}
    days = {}
    for day in sorted(A["pm10"]):
        g = lambda src, k: src[k].get(day, [])  # noqa: E731
        risk = _score(g(W, "wind_gusts_10m"), g(W, "soil_moisture_0_to_1cm"), g(W, "relative_humidity_2m"),
                      g(W, "precipitation"), g(A, "dust"))["score"] if wh else None
        days[day] = {
            "pm10_mean": _mean(g(A, "pm10")), "pm10_max": _max(g(A, "pm10")),
            "pm25_mean": _mean(g(A, "pm2_5")), "pm25_max": _max(g(A, "pm2_5")),
            "dust_mean": _mean(g(A, "dust")), "dust_max": _max(g(A, "dust")),
            "aod_mean": (round(sum(g(A, "aerosol_optical_depth")) / len(g(A, "aerosol_optical_depth")), 3)
                         if g(A, "aerosol_optical_depth") else None),
            "aqi_max": _max(g(A, "us_aqi")), "o3_mean": _mean(g(A, "ozone")), "no2_mean": _mean(g(A, "nitrogen_dioxide")),
            "so2_mean": _mean(g(A, "sulphur_dioxide")), "co_mean": _mean(g(A, "carbon_monoxide")), "uv_max": _max(g(A, "uv_index")),
            "temp_min": _min(g(W, "temperature_2m")), "temp_max": _max(g(W, "temperature_2m")),
            "rh_mean": _mean(g(W, "relative_humidity_2m")), "wind_max": _max(g(W, "wind_speed_10m")),
            "gust_max": _max(g(W, "wind_gusts_10m")),
            "precip_sum": round(sum(g(W, "precipitation")), 1) if g(W, "precipitation") else (0.0 if wh else None),
            "risk": risk,
        }
    return days


async def run(past_days: int = 3) -> int:
    """Arxivni yangilaydi. Qaytaradi: yozilgan kunlar soni."""
    keys = list(CITIES)
    lats = [CITIES[k][2] for k in keys]
    lons = [CITIES[k][3] for k in keys]
    air, wx = await fetch_many(lats, lons, past_days)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    n = 0
    for i, key in enumerate(keys):
        days = aggregate(air[i], wx[i] if wx else None, today)
        for day, vals in days.items():
            sensor = db.sensor_daily(key, day)
            if sensor:
                vals.update(sensor)
            db.upsert_daily(key, day, vals)
            n += 1
    db.commit()
    log.info("Arxiv yangilandi: %s ta kun yozildi (past_days=%s)", n, past_days)
    return n


def needs_backfill() -> bool:
    s = db.archive_summary()
    return s["days"] < len(CITIES) * 30


async def collect_sensors(nearest_fn, token: str):
    """Har soat: har bir shahar uchun eng yaqin datchik o'lchovini saqlaydi."""
    for key, (_, _, lat, lon) in CITIES.items():
        try:
            s = await nearest_fn(lat, lon, token)
        except Exception as e:  # noqa: BLE001
            log.warning("Datchik %s: %s", key, e)
            continue
        if s.get("available") and s["station"].get("time"):
            db.add_sensor_obs(key, s["station"]["time"], s.get("aqi"), s.get("pm25"), s.get("pm10"), s["station"]["name"])


# ---------------- CSV eksport ----------------
CSV_HEADERS = {
    "uz": ["Shahar", "Sana", "PM10 o'rtacha", "PM10 maks", "PM2.5 o'rtacha", "PM2.5 maks", "Chang o'rtacha", "Chang maks",
           "Aerozol (AOD)", "AQI maks (AQSH)", "Ozon O3", "NO2", "SO2", "CO", "UV maks",
           "Harorat min °C", "Harorat maks °C", "Namlik %", "Shamol maks m/s", "Shiddat maks m/s", "Yog'in mm",
           "Bo'ron xavfi (0-100)", "Datchik AQI", "Datchik PM2.5", "Datchik PM10", "Datchik o'lchovlari soni"],
    "ru": ["Город", "Дата", "PM10 среднее", "PM10 макс", "PM2.5 среднее", "PM2.5 макс", "Пыль среднее", "Пыль макс",
           "Аэрозоль (AOD)", "AQI макс (США)", "Озон O3", "NO2", "SO2", "CO", "УФ макс",
           "Темп. мин °C", "Темп. макс °C", "Влажность %", "Ветер макс м/с", "Порывы макс м/с", "Осадки мм",
           "Риск бури (0-100)", "Датчик AQI", "Датчик PM2.5", "Датчик PM10", "Число измерений датчика"],
    "en": ["City", "Date", "PM10 mean", "PM10 max", "PM2.5 mean", "PM2.5 max", "Dust mean", "Dust max",
           "Aerosol (AOD)", "AQI max (US)", "Ozone O3", "NO2", "SO2", "CO", "UV max",
           "Temp min °C", "Temp max °C", "Humidity %", "Wind max m/s", "Gust max m/s", "Precipitation mm",
           "Storm risk (0-100)", "Sensor AQI", "Sensor PM2.5", "Sensor PM10", "Sensor readings"],
}


def city_label(key: str, lang: str) -> str:
    if key not in CITIES:
        return key
    uz, ru, _, _ = CITIES[key]
    return {"ru": ru, "en": CITY_EN.get(key, uz)}.get(lang, uz)


def to_csv(rows: list[dict], lang: str = "uz") -> bytes:
    """Excel to'g'ri ochadigan CSV (UTF-8 BOM bilan)."""
    comma_decimal = lang in ("uz", "ru")  # o'zbek/rus Excel: ";" ajratuvchi va o'nlik vergul
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";" if comma_decimal else ",")
    w.writerow(CSV_HEADERS.get(lang, CSV_HEADERS["uz"]))

    def cell(r, c):
        v = r.get(c)
        if v is None:
            return ""
        if c in ("risk", "sensor_n"):
            return int(v)
        return str(v).replace(".", ",") if comma_decimal else str(v)

    for r in rows:
        w.writerow([city_label(r["city"], lang), r["date"], *[cell(r, c) for c in db.ARCHIVE_COLS]])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def csv_filename(city: str | None, since: str | None) -> str:
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    return f"chang_arxiv_{city or 'barcha_shaharlar'}_{since or 'boshidan'}_{today}.csv"


def since_date(days: int | None) -> str | None:
    if not days:
        return None
    return (datetime.now(TZ) - timedelta(days=days)).strftime("%Y-%m-%d")
