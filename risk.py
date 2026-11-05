"""Chang bo'roni xavfi indeksi (0–100).

Shamol shiddati, tuproq quruqligi, havo namligi, yog'in va chang prognozini birlashtiradi.
Bu rasmiy ko'rsatkich emas, balki ilovaning o'z taxminiy indeksi.
"""


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _vals(h: dict, key: str, idx: list) -> list:
    arr = (h or {}).get(key) or []
    return [arr[i] for i in idx if i < len(arr) and arr[i] is not None]


def _score(gusts, soil, rh, rain, dust) -> dict:
    gust = max(gusts) if gusts else 0
    wind = _clamp((gust - 6) / 14)
    min_rh = min(rh) if rh else None
    dry_rh = _clamp((55 - min_rh) / 40) if min_rh is not None else 0.5
    if soil:
        s = sum(soil) / len(soil)
        dry = 0.6 * _clamp((0.25 - s) / 0.20) + 0.4 * dry_rh
    else:
        s = None
        dry = dry_rh
    rain_sum = sum(rain) if rain else 0
    rain_factor = 1.0 if rain_sum < 0.3 else (0.75 if rain_sum < 2 else 0.45)
    max_dust = max(dust) if dust else 0
    dust_s = _clamp(max_dust / 250)
    base = max(0.45 * wind + 0.25 * dry + 0.30 * dust_s, 0.9 * dust_s)
    score = round(100 * base * rain_factor)
    level = 0 if score < 25 else 1 if score < 50 else 2 if score < 75 else 3
    return {
        "score": score, "level": level,
        "factors": {
            "wind": {"value": round(gust, 1), "score": round(wind * 100)},
            "dry": {"soil": None if s is None else round(s, 3), "rh": min_rh, "score": round(dry * 100)},
            "dust": {"value": round(max_dust), "score": round(dust_s * 100)},
            "rain": {"value": round(rain_sum, 1), "factor": rain_factor},
        },
    }


def storm_risk(air: dict, weather: dict | None) -> dict:
    """Keyingi 24 soat uchun indeks va har kun uchun alohida indeks."""
    ah = air["hourly"]
    wh = (weather or {}).get("hourly") or {}
    now = air["current"]["time"]
    a_idx = [i for i, t in enumerate(ah["time"]) if t >= now][:24]
    w_times = wh.get("time") or []
    w_idx = [i for i, t in enumerate(w_times) if t >= now][:24]

    def at(day_times, day):
        return [i for i, t in enumerate(day_times) if t.startswith(day)]

    result = _score(_vals(wh, "wind_gusts_10m", w_idx), _vals(wh, "soil_moisture_0_to_1cm", w_idx),
                    _vals(wh, "relative_humidity_2m", w_idx), _vals(wh, "precipitation", w_idx),
                    _vals(ah, "dust", a_idx))
    days = []
    for day in sorted({t[:10] for t in ah["time"]}):
        ai, wi = at(ah["time"], day), at(w_times, day)
        d = _score(_vals(wh, "wind_gusts_10m", wi), _vals(wh, "soil_moisture_0_to_1cm", wi),
                   _vals(wh, "relative_humidity_2m", wi), _vals(wh, "precipitation", wi),
                   _vals(ah, "dust", ai))
        days.append({"date": day, "score": d["score"], "level": d["level"]})
    result["days"] = days
    result["has_weather"] = bool(wh)
    return result
