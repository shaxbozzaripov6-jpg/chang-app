"""Open-Meteo Air Quality API (bepul, kalit talab qilinmaydi)."""
import aiohttp

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


async def get_air(lat: float, lon: float) -> dict:
    """Hozirgi holat va 3 kunlik soatlik prognozni qaytaradi."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ("pm10,pm2_5,dust,aerosol_optical_depth,us_aqi,ozone,nitrogen_dioxide,"
                    "carbon_monoxide,sulphur_dioxide,uv_index"),
        "hourly": "pm10,pm2_5,dust",
        "timezone": "Asia/Tashkent",
        "forecast_days": 7,
    }
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(URL, params=params) as r:
            r.raise_for_status()
            return await r.json()


def daily_summary(data: dict) -> list[dict]:
    """Soatlik prognozni kunlarga bo'lib, har kun uchun maksimumni hisoblaydi."""
    h = data["hourly"]
    days: dict[str, dict] = {}
    for i, t in enumerate(h["time"]):
        day, hour = t.split("T")
        d = days.setdefault(day, {"date": day, "pm10": None, "pm2_5": None, "dust": None, "peak": None})
        pm10 = h["pm10"][i]
        if pm10 is not None and (d["pm10"] is None or pm10 > d["pm10"]):
            d["pm10"], d["peak"] = pm10, hour
        for k in ("pm2_5", "dust"):
            v = h[k][i]
            if v is not None:
                d[k] = v if d[k] is None else max(d[k], v)
    # Chang prognozi ~5 kunga beriladi: qolgan kunlarda qiymat None bo'lib qoladi
    return list(days.values())


def next_hours_max(data: dict, hours: int = 24) -> dict:
    """Hozirdan keyingi N soat ichidagi eng yuqori qiymatlar."""
    h = data["hourly"]
    now = data["current"]["time"]
    start = next((i for i, t in enumerate(h["time"]) if t >= now), 0)
    sl = slice(start, start + hours)
    pm10 = [v or 0 for v in h["pm10"][sl]]
    dust = [v or 0 for v in h["dust"][sl]]
    if not pm10:
        return {"pm10": 0, "dust": 0, "time": now}
    i = max(range(len(pm10)), key=pm10.__getitem__)
    return {"pm10": max(pm10), "dust": max(dust), "time": h["time"][start + i]}


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather(lat: float, lon: float) -> dict:
    """Harorat, yog'in, shamol: hozirgi holat va 3 kunlik prognoz."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ("temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,"
                    "weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,is_day"),
        "hourly": ("wind_speed_10m,wind_gusts_10m,wind_direction_10m,temperature_2m,relative_humidity_2m,"
                   "precipitation,soil_moisture_0_to_1cm"),
        "daily": ("weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                  "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,"
                  "wind_direction_10m_dominant"),
        "wind_speed_unit": "ms",
        "timezone": "Asia/Tashkent",
        "forecast_days": 7,
    }
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(WEATHER_URL, params=params) as r:
            r.raise_for_status()
            return await r.json()


def weather_day(weather: dict | None, date: str) -> dict | None:
    """Kunlik ob-havo prognozidan bitta sanani qaytaradi."""
    if not weather or "daily" not in weather:
        return None
    d = weather["daily"]
    if date not in d["time"]:
        return None
    i = d["time"].index(date)
    return {k: d[k][i] for k in d if k != "time"}


def max_gust_24h(weather: dict | None) -> dict | None:
    """Keyingi 24 soatdagi eng kuchli shamol shiddati."""
    if not weather or "hourly" not in weather:
        return None
    h = weather["hourly"]
    now = weather["current"]["time"]
    start = next((i for i, t in enumerate(h["time"]) if t >= now), 0)
    gusts = [(v or 0, h["time"][start + k]) for k, v in enumerate(h["wind_gusts_10m"][start:start + 24])]
    if not gusts:
        return None
    g, t = max(gusts)
    return {"gust": g, "time": t}


async def _get_many(url: str, lats: list, lons: list, params: dict) -> list:
    """Bir nechta nuqta uchun bitta so'rov (Open-Meteo vergul bilan ajratilgan koordinatalarni qabul qiladi)."""
    q = dict(params, latitude=",".join(f"{x:.3f}" for x in lats),
             longitude=",".join(f"{x:.3f}" for x in lons), timezone="Asia/Tashkent")
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url, params=q) as r:
            r.raise_for_status()
            data = await r.json()
    return data if isinstance(data, list) else [data]


async def get_air_many(lats: list, lons: list) -> list:
    return await _get_many(URL, lats, lons, {"current": "pm10,pm2_5,dust"})


async def get_weather_many(lats: list, lons: list) -> list:
    return await _get_many(WEATHER_URL, lats, lons, {
        "current": "temperature_2m,weather_code,wind_speed_10m,wind_direction_10m,is_day",
        "wind_speed_unit": "ms"})


async def get_history(lat: float, lon: float, days: int = 92) -> dict:
    """O'tgan kunlar (92 kungacha) soatlik chang ma'lumoti."""
    params = {"latitude": lat, "longitude": lon, "hourly": "pm10,pm2_5,dust",
              "timezone": "Asia/Tashkent", "past_days": days, "forecast_days": 1}
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(URL, params=params) as r:
            r.raise_for_status()
            return await r.json()


def daily_history(data: dict, today: str) -> list[dict]:
    """Soatlik tarixni kunlik o'rtacha va maksimumga aylantiradi (bugungacha)."""
    h = data["hourly"]
    days: dict[str, dict] = {}
    for i, t in enumerate(h["time"]):
        day = t[:10]
        if day >= today:
            continue
        d = days.setdefault(day, {"pm10": [], "pm2_5": [], "dust": []})
        for k in d:
            if h[k][i] is not None:
                d[k].append(h[k][i])
    out = []
    for day in sorted(days):
        d = days[day]
        if not d["pm10"]:
            continue
        out.append({"date": day, "mean": round(sum(d["pm10"]) / len(d["pm10"]), 1),
                    "max": round(max(d["pm10"]), 1),
                    "pm25": round(sum(d["pm2_5"]) / len(d["pm2_5"]), 1) if d["pm2_5"] else None,
                    "dust": round(max(d["dust"]), 1) if d["dust"] else None})
    return out


async def get_grid(lats: list, lons: list) -> tuple[list, list]:
    """Chang buluti xaritasi uchun: har bir nuqtada 3 kunlik soatlik chang va shamol."""
    air = await _get_many(URL, lats, lons, {"hourly": "dust", "forecast_days": 3})
    try:
        wind = await _get_many(WEATHER_URL, lats, lons, {
            "hourly": "wind_speed_10m,wind_direction_10m", "forecast_days": 3, "wind_speed_unit": "ms"})
    except Exception:  # noqa: BLE001
        wind = None
    return air, wind
