"""Arxivni 2015 yildan to'ldirish (tarixiy import).

Uch qatlam:
  1. Ob-havo 2015 → hozir: Open-Meteo Historical (ERA5), kalit kerak emas.
  2. Havo sifati 2022 → hozir: Open-Meteo Air Quality (CAMS), kalit kerak emas.
  3. Chang/PM 2015 → 2021: Copernicus CAMS global reanalizi (EAC4), bepul ADS kaliti kerak (ADS_KEY).

Har bir bo'lak (yil yoki chorak) bajarilgach import_state jadvaliga yoziladi, shuning uchun
server qayta ishga tushsa, import qolgan joyidan davom etadi.
"""
import asyncio
import logging
import os
import tempfile
import zipfile
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import api
import db
from archive import AIR_VARS, aggregate
from risk import _score
from texts import CITIES

log = logging.getLogger("chang_app.history")
TZ = ZoneInfo("Asia/Tashkent")
START_YEAR = 2015
AQ_START = date(2022, 1, 1)   # Open-Meteo havo sifati arxivi taxminan shu sanadan boshlanadi
RECENT_DAYS = 92              # so'nggi kunlarni archive.run() to'ldiradi
WX_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WX_DAILY = ("temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max,"
            "relative_humidity_2m_mean,soil_moisture_0_to_7cm_mean")
ADS_URL = os.getenv("ADS_URL", "https://ads.atmosphere.copernicus.eu/api")

_KEYS = list(CITIES)
_LATS = [CITIES[k][2] for k in _KEYS]
_LONS = [CITIES[k][3] for k in _KEYS]


def _today() -> date:
    return datetime.now(TZ).date()


def _clean(vals: dict) -> dict:
    return {k: v for k, v in vals.items() if v is not None}


# ---------------- 1. Ob-havo (ERA5) ----------------
async def fetch_weather_daily(start: str, end: str) -> list:
    return await api._get_many(WX_ARCHIVE_URL, _LATS, _LONS,
                               {"daily": WX_DAILY, "start_date": start, "end_date": end, "wind_speed_unit": "ms"})


async def import_weather():
    limit = _today() - timedelta(days=RECENT_DAYS)
    for year in range(START_YEAR, limit.year + 1):
        name = f"wx:{year}"
        final = year < limit.year
        if final and db.get_import(name) == "done":
            continue
        start, end = date(year, 1, 1), min(date(year, 12, 31), limit)
        db.set_import(name, "running")
        try:
            data = await fetch_weather_daily(start.isoformat(), end.isoformat())
        except Exception as e:  # noqa: BLE001
            db.set_import(name, "error", str(e)[:200])
            log.warning("Ob-havo arxivi %s: %s", year, e)
            continue
        n = 0
        for i, key in enumerate(_KEYS):
            d = data[i].get("daily") or {}
            for k, day in enumerate(d.get("time") or []):
                g = lambda v: (d.get(v) or [None] * (k + 1))[k]  # noqa: E731
                db.upsert_daily(key, day, _clean({
                    "temp_min": g("temperature_2m_min"), "temp_max": g("temperature_2m_max"),
                    "precip_sum": g("precipitation_sum"), "wind_max": g("wind_speed_10m_max"),
                    "gust_max": g("wind_gusts_10m_max"), "rh_mean": g("relative_humidity_2m_mean"),
                    "soil_mean": g("soil_moisture_0_to_7cm_mean"),
                }))
                n += 1
        db.commit()
        db.set_import(name, "done" if final else "partial", f"{n} kun")
        log.info("Ob-havo arxivi %s: %s kun", year, n)
        await asyncio.sleep(1)


# ---------------- 2. Havo sifati 2022+ (Open-Meteo / CAMS) ----------------
async def fetch_air_range(start: str, end: str) -> list:
    return await api._get_many(api.URL, _LATS, _LONS, {"hourly": AIR_VARS, "start_date": start, "end_date": end})


def _quarters(first: date, last: date):
    d = date(first.year, 3 * ((first.month - 1) // 3) + 1, 1)
    while d <= last:
        nxt = date(d.year + (d.month + 3 > 12), (d.month + 2) % 12 + 1, 1)
        yield d, min(nxt - timedelta(days=1), last)
        d = nxt


async def import_air():
    limit = _today() - timedelta(days=RECENT_DAYS)
    for qs, qe in _quarters(AQ_START, limit):
        name = f"aq:{qs.isoformat()[:7]}"
        final = qe < limit
        if final and db.get_import(name) in ("done", "nodata"):
            continue
        db.set_import(name, "running")
        try:
            data = await fetch_air_range(qs.isoformat(), qe.isoformat())
        except Exception as e:  # noqa: BLE001
            # Arxiv boshlanishidan oldingi davrlar uchun API xato qaytaradi
            db.set_import(name, "nodata" if "400" in str(e) else "error", str(e)[:200])
            log.warning("Havo sifati arxivi %s: %s", name, e)
            continue
        today = (qe + timedelta(days=1)).isoformat()
        n = 0
        for i, key in enumerate(_KEYS):
            for day, vals in aggregate(data[i], None, today).items():
                vals.pop("risk", None)
                vals = _clean(vals)
                if vals:
                    vals["src"] = "open-meteo"
                    db.upsert_daily(key, day, vals)
                    n += 1
        db.commit()
        db.set_import(name, ("done" if n else "nodata") if final else "partial", f"{n} kun")
        log.info("Havo sifati arxivi %s: %s kun", name, n)
        await asyncio.sleep(1)


# ---------------- 3. CAMS EAC4 reanalizi 2015–2021 (ADS kaliti bilan) ----------------
EAC4_VARS = {  # ADS nomi: (netCDF qisqa nomi, ko'paytiruvchi)
    "particulate_matter_10um": ("pm10", 1e9),        # kg/m³ → µg/m³
    "particulate_matter_2.5um": ("pm2p5", 1e9),
    "total_aerosol_optical_depth_550nm": ("aod550", 1),
    "dust_aerosol_optical_depth_550nm": ("duaod550", 1),
}


def _eac4_year(year: int, key: str) -> dict:
    """Bitta yil uchun EAC4 ma'lumotini yuklab, shaharlar bo'yicha kunlik qiymatlarni qaytaradi (bloklovchi)."""
    import cdsapi

    client = cdsapi.Client(url=ADS_URL, key=key, quiet=True, progress=False)
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "eac4.dat")
        client.retrieve("cams-global-reanalysis-eac4", {
            "variable": list(EAC4_VARS),
            "date": [f"{year}-01-01/{year}-12-31"],
            "time": [f"{h:02d}:00" for h in range(0, 24, 3)],
            "area": [46.5, 55.0, 36.5, 74.5],  # shimol, g'arb, janub, sharq
            "data_format": "netcdf",
        }, target)
        files = []
        if zipfile.is_zipfile(target):
            with zipfile.ZipFile(target) as z:
                for n in z.namelist():
                    if n.endswith(".nc"):
                        z.extract(n, tmp)
                        files.append(os.path.join(tmp, n))
        else:
            files = [target]
        return parse_eac4(files)


def parse_eac4(files: list) -> dict:
    """EAC4 netCDF fayllarini o'qib, shaharlar bo'yicha kunlik qiymatlarni qaytaradi."""
    import netCDF4
    import numpy as np

    series: dict = {}  # (city, sana) -> {qisqa_nom: [qiymatlar]}
    for f in files:
        ds = netCDF4.Dataset(f)
        tname = "valid_time" if "valid_time" in ds.variables else "time"
        tv = ds.variables[tname]
        times = netCDF4.num2date(tv[:], tv.units, only_use_cftime_datetimes=False)
        lats, lons = np.asarray(ds.variables["latitude"][:]), np.asarray(ds.variables["longitude"][:])
        idx = {k: (int(np.abs(lats - CITIES[k][2]).argmin()), int(np.abs(lons - CITIES[k][3]).argmin())) for k in _KEYS}
        for short, mult in EAC4_VARS.values():
            if short not in ds.variables:
                continue
            arr = np.ma.filled(ds.variables[short][:].astype(float), np.nan)
            arr = arr.reshape((arr.shape[0], -1, arr.shape[-2], arr.shape[-1]))[:, 0]  # (vaqt, lat, lon)
            for k, (i, j) in idx.items():
                for t, ts in enumerate(times):
                    v = arr[t, i, j]
                    if np.isnan(v):
                        continue
                    day = (ts + timedelta(hours=5)).strftime("%Y-%m-%d")  # UTC → Toshkent sanasi
                    series.setdefault((k, day), {}).setdefault(short, []).append(float(v) * mult)
        ds.close()

    out = {}
    for (k, day), vals in series.items():
        mean = lambda s: round(sum(vals[s]) / len(vals[s]), 3 if "aod" in s else 1) if vals.get(s) else None  # noqa: E731
        mx = lambda s: round(max(vals[s]), 1) if vals.get(s) else None  # noqa: E731
        out[(k, day)] = _clean({"pm10_mean": mean("pm10"), "pm10_max": mx("pm10"),
                                "pm25_mean": mean("pm2p5"), "pm25_max": mx("pm2p5"),
                                "aod_mean": mean("aod550"), "dust_aod": mean("duaod550"), "src": "cams-eac4"})
    return out


async def import_eac4(key: str):
    last_year = AQ_START.year - 1
    for year in range(START_YEAR, last_year + 1):
        name = f"eac4:{year}"
        if db.get_import(name) == "done":
            continue
        db.set_import(name, "running", "ADS navbatida kutilmoqda")
        log.info("EAC4 %s: so'rov yuborildi (ADS navbati bir necha daqiqadan bir necha soatgacha bo'lishi mumkin)", year)
        try:
            data = await asyncio.to_thread(_eac4_year, year, key)
        except Exception as e:  # noqa: BLE001
            db.set_import(name, "error", str(e)[:300])
            log.warning("EAC4 %s xatosi: %s", year, e)
            continue
        for (k, day), vals in data.items():
            db.upsert_daily(k, day, vals)
        db.commit()
        db.set_import(name, "done", f"{len(data)} qator")
        log.info("EAC4 %s: %s qator", year, len(data))


# ---------------- Bo'ron xavfini qayta hisoblash ----------------
def recompute_risk():
    n = 0
    for r in db.rows_missing_risk():
        dust = r["dust_max"] if r["dust_max"] is not None else (r["pm10_max"] * 0.7 if r["pm10_max"] else None)
        score = _score([r["gust_max"]], [r["soil_mean"]] if r["soil_mean"] is not None else [],
                       [r["rh_mean"]] if r["rh_mean"] is not None else [], [r["precip_sum"] or 0],
                       [dust] if dust is not None else [])["score"]
        db.upsert_daily(r["city"], r["date"], {"risk": score})
        n += 1
    db.commit()
    if n:
        log.info("Bo'ron xavfi qayta hisoblandi: %s kun", n)


async def run_all(ads_key: str = ""):
    """Barcha tarixiy importlarni ketma-ket bajaradi (fon vazifasi)."""
    db.set_import("history", "running")
    for step in (import_weather, import_air):
        try:
            await step()
        except Exception:  # noqa: BLE001
            log.exception("Tarixiy import xatosi: %s", step.__name__)
    if ads_key:
        try:
            await import_eac4(ads_key)
        except Exception:  # noqa: BLE001
            log.exception("EAC4 import xatosi")
    recompute_risk()
    db.set_import("history", "done", "ads" if ads_key else "no_ads")


def status() -> dict:
    """Ilova uchun import holati."""
    imp = db.imports()
    eac4 = {k[5:]: v for k, v in imp.items() if k.startswith("eac4:")}
    running = [y for y, v in eac4.items() if v["status"] == "running"]
    done = sorted(y for y, v in eac4.items() if v["status"] == "done")
    errors = [y for y, v in eac4.items() if v["status"] == "error"]
    return {
        "history": (imp.get("history") or {}).get("status"),
        "weather_done": any(k.startswith("wx:") and v["status"] in ("done", "partial") for k, v in imp.items()),
        "eac4": {"key": bool(os.getenv("ADS_KEY")), "running": running[0] if running else None,
                 "done": done, "errors": errors,
                 "error_detail": (eac4[errors[0]]["detail"] if errors else None)},
    }
