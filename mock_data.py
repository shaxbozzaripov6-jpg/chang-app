"""Faqat sinov uchun: internetsiz soxta, lekin real ko'rinishdagi ma'lumot (MOCK_DATA=1)."""
import math
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")


def _times():
    now = datetime.now(TZ).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    start = now.replace(hour=0)
    return now, [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(72)]


def _seed(lat, lon):
    return random.Random(int(lat * 1000) * 7 + int(lon * 1000))


def _storm(lat, lon):
    # G'arbiy hududlarda (Orol bo'yi) kuchli bo'ron
    return 330 if lon < 61 else (130 if lon < 66 else 40)


async def get_air(lat, lon):
    now, times = _times()
    r = _seed(lat, lon)
    peak = _storm(lat, lon)
    pm10 = [max(8, 45 + peak * math.exp(-((i - 30) / 5) ** 2) + 18 * math.sin(i / 4) + r.uniform(-6, 6))
            for i in range(72)]
    idx = times.index(now.strftime("%Y-%m-%dT%H:%M"))
    cur = pm10[idx]
    return {"current": {"time": times[idx], "pm10": round(cur, 1), "pm2_5": round(cur * 0.27, 1),
                        "dust": round(cur * 0.72, 1), "aerosol_optical_depth": round(0.2 + cur / 600, 2),
                        "us_aqi": round(min(500, cur * 0.9 + 20)), "ozone": round(60 + r.uniform(0, 40)),
                        "nitrogen_dioxide": round(8 + r.uniform(0, 25)), "carbon_monoxide": round(180 + r.uniform(0, 200)),
                        "sulphur_dioxide": round(2 + r.uniform(0, 10)), "uv_index": round(r.uniform(1, 6), 1)},
            "hourly": {"time": times, "pm10": [round(v, 1) for v in pm10],
                       "pm2_5": [round(v * 0.27, 1) for v in pm10], "dust": [round(v * 0.72, 1) for v in pm10]}}


async def get_weather(lat, lon):
    now, times = _times()
    r = _seed(lat, lon)
    idx = times.index(now.strftime("%Y-%m-%dT%H:%M"))
    speed = [max(0.5, 4 + 9 * math.exp(-((i - 28) / 5) ** 2) + r.uniform(-1, 1)) for i in range(72)]
    gust = [s * 1.6 for s in speed]
    dirs = [(250 + i * 2) % 360 for i in range(72)]
    temp = [14 + 7 * math.sin((i % 24 - 9) / 24 * 2 * math.pi) - (lat - 40) for i in range(72)]
    days = sorted({t[:10] for t in times})
    code = r.choice([0, 1, 2, 3])
    return {
        "current": {"time": times[idx], "temperature_2m": round(temp[idx], 1),
                    "apparent_temperature": round(temp[idx] - 2, 1), "relative_humidity_2m": r.randint(18, 60),
                    "precipitation": 0.0, "weather_code": code, "wind_speed_10m": round(speed[idx], 1),
                    "wind_direction_10m": dirs[idx], "wind_gusts_10m": round(gust[idx], 1),
                    "is_day": 1 if 6 <= now.hour < 19 else 0},
        "hourly": {"time": times, "wind_speed_10m": [round(v, 1) for v in speed],
                   "wind_gusts_10m": [round(v, 1) for v in gust], "wind_direction_10m": dirs,
                   "temperature_2m": [round(v, 1) for v in temp],
                   "relative_humidity_2m": [round(55 - 25 * math.sin((i % 24 - 9) / 24 * 2 * math.pi)) for i in range(72)],
                   "precipitation": [0.0] * 36 + [0.4] * 6 + [0.0] * 30,
                   "soil_moisture_0_to_1cm": [round(0.08 + 0.02 * math.sin(i / 10), 3) for i in range(72)]},
        "daily": {"time": days, "weather_code": [code, 63, 0],
                  "temperature_2m_max": [round(max(temp[i * 24:(i + 1) * 24]), 1) for i in range(3)],
                  "temperature_2m_min": [round(min(temp[i * 24:(i + 1) * 24]), 1) for i in range(3)],
                  "precipitation_sum": [0, 6.2, 0], "precipitation_probability_max": [5, 75, 0],
                  "wind_speed_10m_max": [9, 14, 5], "wind_gusts_10m_max": [15, 22, 8],
                  "wind_direction_10m_dominant": [290, 315, 90]},
    }


async def get_air_many(lats, lons):
    return [await get_air(a, b) for a, b in zip(lats, lons)]


async def get_weather_many(lats, lons):
    return [await get_weather(a, b) for a, b in zip(lats, lons)]


async def get_history(lat, lon, days=92):
    r = _seed(lat, lon)
    now = datetime.now(TZ).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    start = (now - timedelta(days=days)).replace(hour=0)
    times, pm = [], []
    storm_days = {r.randint(0, days - 1) for _ in range(9)}
    for h in range((days + 1) * 24):
        t = start + timedelta(hours=h)
        d = h // 24
        base = 40 + 25 * math.sin(d / 9) + (_storm(lat, lon) * 0.9 if d in storm_days else 0)
        times.append(t.strftime("%Y-%m-%dT%H:%M"))
        pm.append(max(5, round(base + 15 * math.sin(h / 4) + r.uniform(-8, 8), 1)))
    return {"hourly": {"time": times, "pm10": pm, "pm2_5": [round(v * 0.27, 1) for v in pm],
                       "dust": [round(v * 0.7, 1) for v in pm]}}


async def get_grid(lats, lons):
    now, times = _times()
    air, wind = [], []
    for la, lo in zip(lats, lons):
        dust = []
        for i in range(72):
            # Orol tomondan sharqqa siljiydigan chang buluti
            cx, cy = 58 + i * 0.16, 44 - i * 0.04
            v = 260 * math.exp(-(((lo - cx) / 3.2) ** 2 + ((la - cy) / 2.2) ** 2)) + 15
            dust.append(round(v, 1))
        air.append({"hourly": {"time": times, "dust": dust}})
        wind.append({"hourly": {"time": times, "wind_speed_10m": [round(6 + 6 * math.exp(-((i - 28) / 8) ** 2), 1) for i in range(72)],
                                "wind_direction_10m": [(280 + i) % 360 for i in range(72)]}})
    return air, wind


async def sensor_nearest(lat, lon, token):
    from sensors import PM10_BP, PM25_BP, aqi_to_conc
    if lon < 62:  # g'arbda stansiya yo'q deb faraz qilamiz
        return {"available": False, "reason": "far",
                "station": {"name": "Tashkent US Embassy", "lat": 41.30, "lon": 69.27, "km": 820, "url": None, "time": ""}}
    now, _ = _times()
    return {"available": True,
            "station": {"name": "Tashkent US Embassy", "lat": 41.30, "lon": 69.27, "km": round(abs(lon - 69.27) * 85),
                        "url": "https://aqicn.org/city/uzbekistan/tashkent/us-embassy/", "time": now.strftime("%Y-%m-%d %H:%M")},
            "aqi": 78, "dominant": "pm25", "pm25_aqi": 78, "pm10_aqi": 41,
            "pm25": aqi_to_conc(78, PM25_BP), "pm10": aqi_to_conc(41, PM10_BP), "temp": 18, "humidity": 40}


async def sensor_bounds(token):
    return [{"lat": 41.30, "lon": 69.27, "aqi": 78, "name": "Tashkent US Embassy", "time": ""},
            {"lat": 41.34, "lon": 69.33, "aqi": 64, "name": "Tashkent, Yunusobod", "time": ""},
            {"lat": 41.28, "lon": 69.20, "aqi": 92, "name": "Tashkent, Chilonzor", "time": ""},
            {"lat": 39.65, "lon": 66.96, "aqi": 55, "name": "Samarkand", "time": ""},
            {"lat": 40.38, "lon": 71.78, "aqi": 121, "name": "Fergana", "time": ""},
            {"lat": 43.24, "lon": 76.89, "aqi": 160, "name": "Almaty (KZ)", "time": ""}]


async def archive_fetch_many(lats, lons, past_days):
    """Arxiv sinovi uchun: o'tgan kunlarning soatlik ma'lumoti."""
    now = datetime.now(TZ).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    start = (now - timedelta(days=past_days)).replace(hour=0)
    hours = (past_days + 1) * 24
    times = [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(hours)]
    air, wx = [], []
    for la, lo in zip(lats, lons):
        r = _seed(la, lo)
        storm = {r.randint(0, past_days - 1) for _ in range(max(1, past_days // 10))}
        pm = []
        for h in range(hours):
            d = h // 24
            base = 40 + 25 * math.sin(d / 9) + (_storm(la, lo) * 0.9 if d in storm else 0)
            pm.append(max(5, round(base + 15 * math.sin(h / 4) + r.uniform(-8, 8), 1)))
        air.append({"hourly": {"time": times, "pm10": pm, "pm2_5": [round(v * 0.27, 1) for v in pm],
                               "dust": [round(v * 0.7, 1) for v in pm],
                               "aerosol_optical_depth": [round(0.15 + v / 700, 3) for v in pm],
                               "us_aqi": [round(min(500, v * 0.9 + 15)) for v in pm],
                               "ozone": [round(60 + 25 * math.sin(h / 24 * 6.28)) for h in range(hours)],
                               "nitrogen_dioxide": [round(15 + 8 * math.sin(h / 5)) for h in range(hours)],
                               "sulphur_dioxide": [round(4 + 2 * math.sin(h / 7)) for h in range(hours)],
                               "carbon_monoxide": [round(220 + 60 * math.sin(h / 6)) for h in range(hours)],
                               "uv_index": [max(0, round(5 * math.sin(((h % 24) - 6) / 12 * 3.14), 1)) for h in range(hours)]}})
        wx.append({"hourly": {"time": times,
                              "temperature_2m": [round(14 + 8 * math.sin(((h % 24) - 9) / 24 * 6.28) - (h // 24) * 0.1, 1) for h in range(hours)],
                              "relative_humidity_2m": [round(45 + 20 * math.cos(h / 24 * 6.28)) for h in range(hours)],
                              "wind_speed_10m": [round(4 + 3 * abs(math.sin(h / 11)), 1) for h in range(hours)],
                              "wind_gusts_10m": [round(7 + 6 * abs(math.sin(h / 11)), 1) for h in range(hours)],
                              "precipitation": [0.3 if (h // 24) % 9 == 0 and h % 24 in (14, 15, 16) else 0.0 for h in range(hours)],
                              "soil_moisture_0_to_1cm": [0.1] * hours}})
    return air, wx
