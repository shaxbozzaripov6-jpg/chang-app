"""Havo sifati va ob-havoni sog'liq bilan bog'lash.

MUHIM: bu modul tashxis qo'ymaydi va dori tavsiya qilmaydi. U faqat ilmiy ma'lum bog'liqliklar
(PM2.5/PM10, chang, issiqlik, sovuq, UV) asosida taxminiy xavf darajasini va umumiy ehtiyot
choralarini ko'rsatadi. Har bir sahifada "shifokorga murojaat qiling" eslatmasi bo'ladi.
"""
import io
from collections import Counter
from datetime import date, datetime, timedelta

CATS = ["resp", "cardio", "eyes", "heat", "cold", "uv"]
ICONS = {"resp": "🫁", "cardio": "❤️", "eyes": "👁", "heat": "🌡", "cold": "🤧", "uv": "☀️"}
SENSITIVE = {"sensitive", "pregnant", "elderly", "child"}

# Profil qaysi toifalarga ko'proq sezgir (chegaralar 30% pastroq)
PROFILE_SENS = {
    "sensitive": {"resp", "eyes"},
    "pregnant": {"resp", "heat", "cardio"},
    "elderly": {"resp", "cardio", "heat", "cold"},
    "child": {"resp", "heat", "cold", "uv"},
    "athlete": {"resp", "heat"},
    "none": set(),
}

T = {
    "uz": {
        "cats": {"resp": "Nafas yo'llari", "cardio": "Yurak va qon tomirlar", "eyes": "Ko'z va allergiya",
                 "heat": "Issiqlik", "cold": "Shamollash va gripp", "uv": "Quyosh (UV)"},
        "levels": ["Past", "O'rtacha", "Yuqori", "Juda yuqori"],
        "r_pm25": "PM2.5 {v} µg/m³", "r_pm10": "PM10 {v} µg/m³", "r_dust": "chang {v} µg/m³", "r_o3": "ozon {v} µg/m³",
        "r_gust": "shamol shiddati {v} m/s", "r_tmax": "eng yuqori harorat {v}°C", "r_tmin": "eng past harorat {v}°C",
        "r_drop": "harorat {v}°C ga pasayadi", "r_rh": "namlik {v}%", "r_season": "mavsum: kuz-qish", "r_uv": "UV indeksi {v}",
        "r_profile": "profilingiz hisobga olindi",
        "tips": {
            "resp": ["Tashqarida kam bo'ling, jismoniy mashqni yopiq joyda qiling", "N95/FFP2 niqob taqing",
                     "Astma bo'lsa, ingalyatorni yoningizda olib yuring", "Derazalarni yoping, havo tozalagich bo'lsa yoqing"],
            "cardio": ["Og'ir jismoniy ishdan saqlaning", "Qon bosimini kuzating, dorilarni o'z vaqtida iching",
                       "Ko'krakda og'riq yoki nafas qisishi bo'lsa, darhol 103 ga qo'ng'iroq qiling"],
            "eyes": ["Ko'zoynak taqing, linzadan voz keching", "Ko'z va burunni toza suv bilan yuving",
                     "Allergiyangiz bo'lsa, shifokor tayinlagan dorini oldindan iching", "Kiyimlarni uyga kirgach almashtiring"],
            "heat": ["Kuniga kamida 2–3 litr suv iching", "Soat 11:00–17:00 da quyoshda yurmang",
                     "Yengil, och rangli kiyim kiying", "Keksa qarindoshlar va bolalarni tez-tez tekshirib turing"],
            "cold": ["Issiq kiyining, oyoqni issiq tuting", "Qo'lni tez-tez yuving, olomonda niqob taqing",
                     "Xonani muntazam shamollating", "Isitma 3 kundan oshsa yoki nafas qiyinlashsa, shifokorga boring"],
            "uv": ["SPF 30+ quyoshdan himoya kremi suring", "Quyosh ko'zoynagi va bosh kiyim kiying",
                   "Soat 11:00–16:00 da soyada bo'ling"],
        },
        "disclaimer": "Bu tibbiy tashxis emas. Ilova faqat havo va ob-havo asosidagi taxminiy xavfni ko'rsatadi. Sog'lig'ingiz yomonlashsa, shifokorga murojaat qiling, favqulodda holatda 103 ga qo'ng'iroq qiling.",
        "seasons": {"dust": "Chang bo'ronlari mavsumi", "heat": "Issiqlik mavsumi", "cold": "Shamollash va gripp mavsumi",
                    "uv": "Kuchli quyosh (UV) mavsumi"},
        "sym": {"none": "O'zimni yaxshi his qilyapman", "cough": "Yo'tal", "breath": "Nafas qisishi", "wheeze": "Xirillash",
                "eyes": "Ko'z qichishi/qizarishi", "nose": "Burun bitishi, aksirish", "throat": "Tomoq og'rig'i",
                "headache": "Bosh og'rig'i", "fatigue": "Holsizlik", "skin": "Teri qichishi", "fever": "Isitma"},
        "ins_pm": "«{s}» ko'pincha chang yuqori kunlarda bo'lgan: o'rtacha PM10 {a} µg/m³ (boshqa kunlarda {b})",
        "ins_heat": "«{s}» ko'pincha issiq kunlarda bo'lgan: o'rtacha {a}°C (boshqa kunlarda {b}°C)",
        "ins_few": "Bog'liqlikni ko'rish uchun kamida 10 kun belgilang (hozir {n} kun).",
        "ins_none": "Hozircha simptomlar bilan havo o'rtasida aniq bog'liqlik ko'rinmadi.",
        "pdf_title": "Havo sifati va simptomlar hisoboti", "pdf_place": "Joy", "pdf_period": "Davr", "pdf_days": "Belgilangan kunlar",
        "pdf_top": "Eng ko'p uchragan simptomlar", "pdf_ins": "Kuzatuvlar", "pdf_chart": "Kunlik PM10 (µg/m³) va simptomli kunlar",
        "pdf_table": "Kundalik yozuvlari", "pdf_cols": ["Sana", "Simptomlar", "Og'irlik", "PM10", "PM2.5", "Harorat", "Izoh"],
        "pdf_sev": ["yo'q", "yengil", "o'rtacha", "og'ir"], "pdf_patient": "Bemor: ____________________",
        "pdf_src": "Manba: Chang Monitor (Open-Meteo / Copernicus CAMS). Ushbu hisobot tashxis emas, shifokor bilan suhbat uchun yordamchi ma'lumot.",
        "remind_title": "🩺 <b>Ertangi sog'liq ogohlantirishi</b> ({place})",
        "remind_diary": "📝 Bugun o'zingizni qanday his qildingiz? Kundalikka belgilab qo'ying — ilova simptomlaringizni havo bilan solishtiradi.",
        "season_start": "📅 <b>{place}: {season} boshlandi</b>\nArxiv bo'yicha bu oyda: {detail}\n\n💡 {tip}",
        "season_detail": {"dust": "changli kunlar {v}%", "heat": "35°C dan issiq kunlar {v}%", "cold": "sovuq kunlar {v}%", "uv": "o'rtacha UV {v}"},
    },
    "ru": {
        "cats": {"resp": "Дыхательные пути", "cardio": "Сердце и сосуды", "eyes": "Глаза и аллергия",
                 "heat": "Жара", "cold": "Простуда и грипп", "uv": "Солнце (УФ)"},
        "levels": ["Низкий", "Умеренный", "Высокий", "Очень высокий"],
        "r_pm25": "PM2.5 {v} µg/m³", "r_pm10": "PM10 {v} µg/m³", "r_dust": "пыль {v} µg/m³", "r_o3": "озон {v} µg/m³",
        "r_gust": "порывы ветра {v} м/с", "r_tmax": "макс. температура {v}°C", "r_tmin": "мин. температура {v}°C",
        "r_drop": "похолодание на {v}°C", "r_rh": "влажность {v}%", "r_season": "сезон: осень-зима", "r_uv": "УФ-индекс {v}",
        "r_profile": "учтён ваш профиль",
        "tips": {
            "resp": ["Меньше бывайте на улице, тренируйтесь в помещении", "Носите маску N95/FFP2",
                     "При астме держите ингалятор при себе", "Закройте окна, включите очиститель воздуха"],
            "cardio": ["Избегайте тяжёлой физической нагрузки", "Следите за давлением, принимайте лекарства вовремя",
                       "При боли в груди или одышке сразу звоните 103"],
            "eyes": ["Носите очки, откажитесь от линз", "Промывайте глаза и нос чистой водой",
                     "При аллергии заранее примите лекарство, назначенное врачом", "Переодевайтесь, придя домой"],
            "heat": ["Пейте не менее 2–3 литров воды в день", "Не находитесь на солнце с 11:00 до 17:00",
                     "Носите лёгкую светлую одежду", "Чаще проверяйте пожилых родственников и детей"],
            "cold": ["Одевайтесь тепло, держите ноги в тепле", "Чаще мойте руки, в толпе носите маску",
                     "Регулярно проветривайте комнату", "Если температура держится больше 3 дней или трудно дышать, обратитесь к врачу"],
            "uv": ["Используйте крем SPF 30+", "Носите солнцезащитные очки и головной убор", "С 11:00 до 16:00 будьте в тени"],
        },
        "disclaimer": "Это не медицинский диагноз. Приложение показывает лишь примерный риск по данным о воздухе и погоде. При ухудшении самочувствия обратитесь к врачу, в экстренном случае звоните 103.",
        "seasons": {"dust": "Сезон пыльных бурь", "heat": "Сезон жары", "cold": "Сезон простуды и гриппа", "uv": "Сезон сильного солнца (УФ)"},
        "sym": {"none": "Чувствую себя хорошо", "cough": "Кашель", "breath": "Одышка", "wheeze": "Хрипы",
                "eyes": "Зуд/покраснение глаз", "nose": "Заложенность носа, чихание", "throat": "Боль в горле",
                "headache": "Головная боль", "fatigue": "Слабость", "skin": "Зуд кожи", "fever": "Температура"},
        "ins_pm": "«{s}» чаще бывает в пыльные дни: средний PM10 {a} µg/m³ (в другие дни {b})",
        "ins_heat": "«{s}» чаще бывает в жаркие дни: в среднем {a}°C (в другие дни {b}°C)",
        "ins_few": "Чтобы увидеть связь, отметьте хотя бы 10 дней (сейчас {n}).",
        "ins_none": "Пока явной связи между симптомами и воздухом не видно.",
        "pdf_title": "Отчёт: качество воздуха и симптомы", "pdf_place": "Место", "pdf_period": "Период", "pdf_days": "Отмечено дней",
        "pdf_top": "Самые частые симптомы", "pdf_ins": "Наблюдения", "pdf_chart": "PM10 по дням (µg/m³) и дни с симптомами",
        "pdf_table": "Записи дневника", "pdf_cols": ["Дата", "Симптомы", "Тяжесть", "PM10", "PM2.5", "Темп.", "Заметка"],
        "pdf_sev": ["нет", "лёгкая", "средняя", "сильная"], "pdf_patient": "Пациент: ____________________",
        "pdf_src": "Источник: Chang Monitor (Open-Meteo / Copernicus CAMS). Отчёт не является диагнозом, это вспомогательная информация для беседы с врачом.",
        "remind_title": "🩺 <b>Предупреждение о здоровье на завтра</b> ({place})",
        "remind_diary": "📝 Как вы себя чувствовали сегодня? Отметьте в дневнике — приложение сравнит симптомы с воздухом.",
        "season_start": "📅 <b>{place}: начался {season}</b>\nПо архиву в этом месяце: {detail}\n\n💡 {tip}",
        "season_detail": {"dust": "пыльных дней {v}%", "heat": "дней жарче 35°C {v}%", "cold": "холодных дней {v}%", "uv": "средний УФ {v}"},
    },
    "en": {
        "cats": {"resp": "Airways", "cardio": "Heart and vessels", "eyes": "Eyes and allergy",
                 "heat": "Heat", "cold": "Colds and flu", "uv": "Sun (UV)"},
        "levels": ["Low", "Moderate", "High", "Very high"],
        "r_pm25": "PM2.5 {v} µg/m³", "r_pm10": "PM10 {v} µg/m³", "r_dust": "dust {v} µg/m³", "r_o3": "ozone {v} µg/m³",
        "r_gust": "wind gusts {v} m/s", "r_tmax": "max temperature {v}°C", "r_tmin": "min temperature {v}°C",
        "r_drop": "temperature drops by {v}°C", "r_rh": "humidity {v}%", "r_season": "season: autumn-winter", "r_uv": "UV index {v}",
        "r_profile": "your profile is taken into account",
        "tips": {
            "resp": ["Spend less time outdoors, exercise indoors", "Wear an N95/FFP2 mask",
                     "If you have asthma, keep your inhaler with you", "Close windows, run an air purifier if you have one"],
            "cardio": ["Avoid heavy physical exertion", "Monitor your blood pressure and take medicines on time",
                       "Call 103 immediately for chest pain or shortness of breath"],
            "eyes": ["Wear glasses instead of contact lenses", "Rinse your eyes and nose with clean water",
                     "If you have allergies, take the medicine your doctor prescribed in advance", "Change clothes when you get home"],
            "heat": ["Drink at least 2–3 litres of water a day", "Avoid the sun from 11:00 to 17:00",
                     "Wear light, light-coloured clothing", "Check on older relatives and children often"],
            "cold": ["Dress warmly and keep your feet warm", "Wash hands often, wear a mask in crowds",
                     "Air your room regularly", "See a doctor if fever lasts over 3 days or breathing gets hard"],
            "uv": ["Use SPF 30+ sunscreen", "Wear sunglasses and a hat", "Stay in the shade from 11:00 to 16:00"],
        },
        "disclaimer": "This is not a medical diagnosis. The app only shows an estimated risk based on air and weather data. If you feel worse, see a doctor; in an emergency call 103.",
        "seasons": {"dust": "Dust storm season", "heat": "Heat season", "cold": "Cold and flu season", "uv": "Strong sun (UV) season"},
        "sym": {"none": "I feel fine", "cough": "Cough", "breath": "Shortness of breath", "wheeze": "Wheezing",
                "eyes": "Itchy/red eyes", "nose": "Stuffy nose, sneezing", "throat": "Sore throat",
                "headache": "Headache", "fatigue": "Fatigue", "skin": "Itchy skin", "fever": "Fever"},
        "ins_pm": "“{s}” happened more on dusty days: mean PM10 {a} µg/m³ (other days {b})",
        "ins_heat": "“{s}” happened more on hot days: mean {a}°C (other days {b}°C)",
        "ins_few": "Log at least 10 days to see patterns (now {n}).",
        "ins_none": "No clear link between your symptoms and the air yet.",
        "pdf_title": "Air quality and symptoms report", "pdf_place": "Place", "pdf_period": "Period", "pdf_days": "Days logged",
        "pdf_top": "Most frequent symptoms", "pdf_ins": "Observations", "pdf_chart": "Daily PM10 (µg/m³) and symptom days",
        "pdf_table": "Diary entries", "pdf_cols": ["Date", "Symptoms", "Severity", "PM10", "PM2.5", "Temp", "Note"],
        "pdf_sev": ["none", "mild", "moderate", "severe"], "pdf_patient": "Patient: ____________________",
        "pdf_src": "Source: Chang Monitor (Open-Meteo / Copernicus CAMS). This report is not a diagnosis; it is supporting information for a conversation with a doctor.",
        "remind_title": "🩺 <b>Health alert for tomorrow</b> ({place})",
        "remind_diary": "📝 How did you feel today? Log it in your diary — the app will compare your symptoms with the air.",
        "season_start": "📅 <b>{place}: {season} has started</b>\nIn the archive for this month: {detail}\n\n💡 {tip}",
        "season_detail": {"dust": "dusty days {v}%", "heat": "days above 35°C {v}%", "cold": "cold days {v}%", "uv": "mean UV {v}"},
    },
}
SYMPTOMS = ["cough", "breath", "wheeze", "eyes", "nose", "throat", "headache", "fatigue", "skin", "fever"]


def tt(lang: str) -> dict:
    return T.get(lang, T["uz"])


def _lvl(v, limits):
    if v is None:
        return 0
    for i, lim in enumerate(limits):
        if v < lim:
            return i
    return len(limits)


def _f(v):
    return None if v is None else round(v)


# ---------------- 1. Kunlik sog'liq xavfi ----------------
def _day_values(air: dict, weather: dict | None, day: str | None) -> dict:
    """Bugungi (keyingi 24 soat) yoki berilgan kun uchun kerakli qiymatlar."""
    ah, wh = air["hourly"], (weather or {}).get("hourly") or {}
    wd = (weather or {}).get("daily") or {}
    now = air["current"]["time"]
    if day is None:
        sel = lambda times: [i for i, t in enumerate(times) if t >= now][:24]  # noqa: E731
        target = now[:10]
    else:
        sel = lambda times: [i for i, t in enumerate(times) if t.startswith(day)]  # noqa: E731
        target = day
    ai, wi = sel(ah["time"]), sel(wh.get("time") or [])
    vals = lambda arr, idx: [arr[i] for i in idx if arr and i < len(arr) and arr[i] is not None]  # noqa: E731
    mx = lambda v: max(v) if v else None  # noqa: E731
    di = wd.get("time", []).index(target) if target in wd.get("time", []) else -1
    dv = lambda k, i=di: (wd.get(k) or [None] * (i + 1))[i] if i >= 0 and k in wd else None  # noqa: E731
    cur = air["current"] if day is None else {}
    tmin = dv("temperature_2m_min")
    prev_tmin = dv("temperature_2m_min", di - 1) if di > 0 else None
    rh = vals(wh.get("relative_humidity_2m"), wi)
    return {
        "pm25": mx(vals(ah.get("pm2_5"), ai)), "pm10": mx(vals(ah.get("pm10"), ai)), "dust": mx(vals(ah.get("dust"), ai)),
        "o3": cur.get("ozone"), "gust": mx(vals(wh.get("wind_gusts_10m"), wi)),
        "tmax": dv("temperature_2m_max") if dv("temperature_2m_max") is not None else mx(vals(wh.get("temperature_2m"), wi)),
        "tmin": tmin, "drop": (prev_tmin - tmin) if (prev_tmin is not None and tmin is not None) else None,
        "rh": sum(rh) / len(rh) if rh else None,
        "uv": dv("uv_index_max") if dv("uv_index_max") is not None else cur.get("uv_index"),
        "month": int(target[5:7]), "date": target,
    }


def assess(air: dict, weather: dict | None, profile: str = "none", lang: str = "uz", day: str | None = None) -> dict:
    """Har bir toifa uchun xavf darajasi (0–3), sabablar va maslahatlar."""
    t = tt(lang)
    v = _day_values(air, weather, day)
    sens = PROFILE_SENS.get(profile, set())
    k = lambda cat: 1 / 0.7 if cat in sens else 1.0  # noqa: E731  sezgir profil: qiymat 30% "kattaroq" hisoblanadi
    res = {}

    def add(cat, level, reasons):
        level = max(0, min(3, level))
        if cat in sens and level > 0:
            reasons.append(t["r_profile"])
        res[cat] = {"level": level, "name": t["cats"][cat], "icon": ICONS[cat], "level_name": t["levels"][level],
                    "reasons": reasons[:3], "tips": t["tips"][cat][: (4 if level >= 2 else 2)] if level >= 1 else []}

    # Nafas yo'llari: PM2.5, PM10, ozon
    pm25, pm10, o3 = v["pm25"], v["pm10"], v["o3"]
    lv = max(_lvl((pm25 or 0) * k("resp"), [15, 35, 55]), _lvl((pm10 or 0) * k("resp"), [50, 100, 250]),
             2 if (o3 or 0) * k("resp") >= 180 else 0)
    r = []
    if pm25 is not None and pm25 >= 15:
        r.append(t["r_pm25"].format(v=_f(pm25)))
    if pm10 is not None and pm10 >= 50:
        r.append(t["r_pm10"].format(v=_f(pm10)))
    if o3 is not None and o3 >= 120:
        r.append(t["r_o3"].format(v=_f(o3)))
    add("resp", lv, r)

    # Yurak: PM2.5 + haddan tashqari issiq/sovuq
    lv = _lvl((pm25 or 0) * k("cardio"), [25, 50, 75])
    r = [t["r_pm25"].format(v=_f(pm25))] if lv and pm25 is not None else []
    if v["tmax"] is not None and v["tmax"] >= (35 if "cardio" in sens else 38):
        lv = max(lv, 2)
        r.append(t["r_tmax"].format(v=_f(v["tmax"])))
    if v["tmin"] is not None and v["tmin"] <= (-5 if "cardio" in sens else -10):
        lv = max(lv, 2)
        r.append(t["r_tmin"].format(v=_f(v["tmin"])))
    add("cardio", lv, r)

    # Ko'z va allergiya: chang, PM10, kuchli shamol
    dust = v["dust"]
    lv = max(_lvl((dust or 0) * k("eyes"), [50, 100, 200]), _lvl((pm10 or 0) * k("eyes"), [100, 150, 300]))
    r = [t["r_dust"].format(v=_f(dust))] if dust is not None and dust >= 50 else []
    if v["gust"] is not None and v["gust"] >= 12 and (dust or 0) >= 30:
        lv = max(lv, 1 if v["gust"] < 17 else 2)
        r.append(t["r_gust"].format(v=_f(v["gust"])))
    add("eyes", lv, r)

    # Issiqlik
    tmax = v["tmax"]
    lv = _lvl((tmax or 0) + (3 if "heat" in sens else 0), [30, 35, 40])
    add("heat", lv, [t["r_tmax"].format(v=_f(tmax))] if lv and tmax is not None else [])

    # Shamollash va gripp: sovuq, keskin sovish, namlik, mavsum
    lv, r = 0, []
    tmin = v["tmin"]
    if tmin is not None and tmin <= 5:
        lv = 1
        r.append(t["r_tmin"].format(v=_f(tmin)))
        if tmin <= 0 and (v["rh"] or 0) >= 70:
            lv = 2
            r.append(t["r_rh"].format(v=_f(v["rh"])))
        if tmin <= -8:
            lv = max(lv, 2)
    if v["drop"] is not None and v["drop"] >= 8:
        lv += 1
        r.append(t["r_drop"].format(v=_f(v["drop"])))
    if v["month"] in (11, 12, 1, 2, 3):
        lv = max(lv, 1)
        r.append(t["r_season"])
    if "cold" in sens and lv >= 1:
        lv += 1
    add("cold", lv, r)

    # UV
    uv = v["uv"]
    lv = _lvl((uv or 0) * (1.3 if "uv" in sens else 1), [3, 6, 8])
    add("uv", lv, [t["r_uv"].format(v=round(uv, 1))] if lv and uv is not None else [])

    overall = max(c["level"] for c in res.values())
    return {"date": v["date"], "overall": overall, "overall_name": t["levels"][overall],
            "cats": [res[c] for c in CATS], "disclaimer": t["disclaimer"]}


# ---------------- 2. Mavsumiy taqvim (arxivdan) ----------------
def seasons(rows: list[dict], lang: str = "uz") -> dict:
    t = tt(lang)
    by = {m: [] for m in range(1, 13)}
    years = set()
    for r in rows:
        by[int(r["date"][5:7])].append(r)
        years.add(r["date"][:4])
    months = []
    for m in range(1, 13):
        rs = by[m]
        pm = [r["pm10_mean"] for r in rs if r.get("pm10_mean") is not None]
        tx = [r["temp_max"] for r in rs if r.get("temp_max") is not None]
        tn = [r["temp_min"] for r in rs if r.get("temp_min") is not None]
        uv = [r["uv_max"] for r in rs if r.get("uv_max") is not None]
        rk = [r["risk"] for r in rs if r.get("risk") is not None]
        pc = [r["precip_sum"] for r in rs if r.get("precip_sum") is not None]
        pct = lambda arr, cond: round(100 * sum(1 for x in arr if cond(x)) / len(arr)) if arr else None  # noqa: E731
        avg = lambda arr, d=0: round(sum(arr) / len(arr), d) if arr else None  # noqa: E731
        o = {"month": m, "pm10_avg": avg(pm), "dusty_pct": pct(pm, lambda x: x > 100), "heat_pct": pct(tx, lambda x: x >= 35),
             "cold_pct": pct(tn, lambda x: x <= 0), "tmax_avg": avg(tx), "tmin_avg": avg(tn), "uv_avg": avg(uv, 1),
             "risk_avg": avg(rk), "precip_avg": avg(pc, 1), "days": len(rs)}
        tags = []
        if (o["dusty_pct"] or 0) >= 12 or (o["pm10_avg"] or 0) >= 80:
            tags.append("dust")
        if (o["heat_pct"] or 0) >= 20:
            tags.append("heat")
        if (o["cold_pct"] or 0) >= 20 or (o["tmin_avg"] is not None and o["tmin_avg"] <= 3):
            tags.append("cold")
        if (o["uv_avg"] or 0) >= 8:
            tags.append("uv")
        o["tags"] = tags
        months.append(o)
    return {"months": months, "years": sorted(years), "names": t["seasons"]}


def season_detail(month: dict, tag: str, lang: str) -> str:
    t = tt(lang)
    v = {"dust": month.get("dusty_pct"), "heat": month.get("heat_pct"), "cold": month.get("cold_pct"), "uv": month.get("uv_avg")}[tag]
    return t["season_detail"][tag].format(v=v if v is not None else "—")


# ---------------- 3. Kundalik tahlili ----------------
def insights(entries: list[dict], lang: str = "uz") -> dict:
    """Simptomli va simptomsiz kunlarda chang/haroratni solishtiradi."""
    t = tt(lang)
    n = len(entries)
    counts = Counter(s for e in entries for s in e["symptoms"] if s != "none")
    out = {"days": n, "top": [{"key": s, "name": t["sym"].get(s, s), "count": c} for s, c in counts.most_common(5)], "notes": []}
    if n < 10:
        out["notes"].append(t["ins_few"].format(n=n))
        return out
    for s, c in counts.most_common(6):
        if c < 3:
            continue
        on = [e for e in entries if s in e["symptoms"]]
        off = [e for e in entries if s not in e["symptoms"]]
        for field, key, ratio, diff in (("pm10", "ins_pm", 1.3, 15), ("temp", "ins_heat", 1.15, 4)):
            a = [e[field] for e in on if e.get(field) is not None]
            b = [e[field] for e in off if e.get(field) is not None]
            if len(a) >= 3 and len(b) >= 3:
                ma, mb = sum(a) / len(a), sum(b) / len(b)
                if mb > 0 and ma >= mb * ratio and ma - mb >= diff:
                    out["notes"].append(t[key].format(s=t["sym"].get(s, s), a=round(ma), b=round(mb)))
    if not out["notes"]:
        out["notes"].append(t["ins_none"])
    return out


# ---------------- 5. Shifokor uchun PDF ----------------
def report_pdf(entries: list[dict], daily: list[dict], place: str, lang: str = "uz") -> bytes:
    """Matplotlib bilan 2 sahifali PDF: xulosa + grafik, keyin yozuvlar jadvali."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    t = tt(lang)
    ins = insights(entries, lang)
    first = min([e["date"] for e in entries] + [d["date"] for d in daily]) if (entries or daily) else "—"
    last = max([e["date"] for e in entries] + [d["date"] for d in daily]) if (entries or daily) else "—"
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))  # A4
        fig.text(0.08, 0.95, t["pdf_title"], fontsize=17, weight="bold")
        fig.text(0.08, 0.925, t["pdf_patient"], fontsize=10)
        fig.text(0.08, 0.905, f"{t['pdf_place']}: {place}    {t['pdf_period']}: {first} — {last}    {t['pdf_days']}: {ins['days']}", fontsize=10)
        y = 0.87
        fig.text(0.08, y, t["pdf_top"], fontsize=12, weight="bold")
        for item in ins["top"] or [{"name": "—", "count": ""}]:
            y -= 0.022
            fig.text(0.1, y, f"• {item['name']}: {item['count']}", fontsize=10)
        y -= 0.035
        fig.text(0.08, y, t["pdf_ins"], fontsize=12, weight="bold")
        for note in ins["notes"]:
            y -= 0.022
            fig.text(0.1, y, "• " + note, fontsize=9.5, wrap=True)
        ax = fig.add_axes([0.1, 0.12, 0.82, 0.32])
        if daily:
            xs = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily]
            ax.fill_between(xs, [d.get("pm10") or 0 for d in daily], color="#e0a85a", alpha=.35)
            ax.plot(xs, [d.get("pm10") for d in daily], color="#c2562a", lw=1.6)
            ax.axhline(45, color="#e53935", ls="--", lw=1)
        sym = [e for e in entries if any(s != "none" for s in e["symptoms"])]
        if sym:
            ax.scatter([datetime.strptime(e["date"], "%Y-%m-%d") for e in sym], [e.get("pm10") or 0 for e in sym],
                       s=[30 + 30 * (e.get("severity") or 0) for e in sym], color="#2c5aa8", zorder=5)
        ax.set_title(t["pdf_chart"], fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax.grid(alpha=.3)
        fig.text(0.08, 0.05, t["pdf_src"], fontsize=8, color="#555", wrap=True)
        fig.text(0.08, 0.03, t["disclaimer"], fontsize=8, color="#555", wrap=True)
        pdf.savefig(fig)
        plt.close(fig)

        rows = sorted(entries, key=lambda e: e["date"], reverse=True)
        for start in range(0, max(1, len(rows)), 38):
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.06, 0.96, t["pdf_table"], fontsize=14, weight="bold")
            ax = fig.add_axes([0.04, 0.04, 0.92, 0.9])
            ax.axis("off")
            data = [[e["date"], ", ".join(t["sym"].get(s, s) for s in e["symptoms"])[:48], t["pdf_sev"][min(3, e.get("severity") or 0)],
                     "" if e.get("pm10") is None else round(e["pm10"]), "" if e.get("pm25") is None else round(e["pm25"]),
                     "" if e.get("temp") is None else round(e["temp"]), (e.get("note") or "")[:28]] for e in rows[start:start + 38]]
            if data:
                tbl = ax.table(cellText=data, colLabels=t["pdf_cols"], loc="upper center", cellLoc="left",
                               colWidths=[.13, .36, .09, .07, .07, .07, .21])
                tbl.auto_set_font_size(False)
                tbl.set_fontsize(7.5)
                tbl.scale(1, 1.25)
            pdf.savefig(fig)
            plt.close(fig)
    return buf.getvalue()


def week_ago(days: int = 30) -> str:
    return (date.today() - timedelta(days=days)).isoformat()
