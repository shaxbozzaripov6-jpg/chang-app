"""Haqiqiy havo sifati datchiklari: World Air Quality Index (aqicn.org) API.

Bepul token: https://aqicn.org/data-platform/token/ → Railway'da WAQI_TOKEN o'zgaruvchisiga yoziladi.
WAQI qiymatlarni AQSH AQI shkalasida beradi. PM2.5/PM10 konsentratsiyasi (µg/m³) shu indeksdan
taxminan qayta hisoblanadi.
"""
import math

import aiohttp

FEED_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/"
BOUNDS_URL = "https://api.waqi.info/map/bounds"
MAX_KM = 60  # shundan uzoq stansiya "yaqin" hisoblanmaydi

# AQSH EPA chegaralari: (konsentratsiya past, yuqori, AQI past, yuqori)
PM25_BP = [(0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150), (55.5, 150.4, 151, 200),
           (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400), (350.5, 500.4, 401, 500)]
PM10_BP = [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150), (255, 354, 151, 200),
           (355, 424, 201, 300), (425, 504, 301, 400), (505, 604, 401, 500)]


def aqi_to_conc(aqi, table):
    """AQI qiymatini konsentratsiyaga (µg/m³) aylantiradi."""
    if aqi is None:
        return None
    for c_lo, c_hi, i_lo, i_hi in table:
        if aqi <= i_hi:
            return round(c_lo + (aqi - i_lo) * (c_hi - c_lo) / (i_hi - i_lo), 1)
    return table[-1][1]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


async def _get(url: str, params: dict) -> dict:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url, params=params) as r:
            r.raise_for_status()
            return await r.json(content_type=None)


async def nearest(lat: float, lon: float, token: str) -> dict:
    """Eng yaqin stansiyaning so'nggi o'lchovi."""
    data = await _get(FEED_URL.format(lat=f"{lat:.3f}", lon=f"{lon:.3f}"), {"token": token})
    if data.get("status") != "ok":
        return {"available": False, "reason": "error", "detail": str(data.get("data"))[:100]}
    d = data["data"]
    geo = (d.get("city") or {}).get("geo") or [None, None]
    if geo[0] is None:
        return {"available": False, "reason": "error"}
    km = _km(lat, lon, float(geo[0]), float(geo[1]))
    iaqi = d.get("iaqi") or {}
    pm25_aqi = _num((iaqi.get("pm25") or {}).get("v"))
    pm10_aqi = _num((iaqi.get("pm10") or {}).get("v"))
    station = {"name": (d.get("city") or {}).get("name") or "—", "lat": float(geo[0]), "lon": float(geo[1]),
               "km": round(km), "url": (d.get("city") or {}).get("url"),
               "time": ((d.get("time") or {}).get("s") or "")[:16]}
    if km > MAX_KM:
        return {"available": False, "reason": "far", "station": station}
    return {
        "available": True, "station": station,
        "aqi": _num(d.get("aqi")), "dominant": d.get("dominentpol"),
        "pm25_aqi": pm25_aqi, "pm10_aqi": pm10_aqi,
        "pm25": aqi_to_conc(pm25_aqi, PM25_BP), "pm10": aqi_to_conc(pm10_aqi, PM10_BP),
        "temp": _num((iaqi.get("t") or {}).get("v")), "humidity": _num((iaqi.get("h") or {}).get("v")),
    }


async def in_bounds(token: str, lat1=37.0, lon1=55.5, lat2=45.8, lon2=73.5) -> list:
    """O'zbekiston va atrofidagi barcha stansiyalar (xarita uchun)."""
    data = await _get(BOUNDS_URL, {"latlng": f"{lat1},{lon1},{lat2},{lon2}", "networks": "all", "token": token})
    if data.get("status") != "ok":
        return []
    out = []
    for s in data.get("data") or []:
        aqi = _num(s.get("aqi"))
        if aqi is None:
            continue
        st = s.get("station") or {}
        out.append({"lat": s.get("lat"), "lon": s.get("lon"), "aqi": aqi,
                    "name": st.get("name") or "—", "time": (st.get("time") or "")[:16]})
    return out
