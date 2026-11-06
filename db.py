"""SQLite: Mini App foydalanuvchilari, sozlamalari va bo'ron rasmlari."""
import math
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")
DB_PATH = os.getenv("DB_PATH", "chang_app.db")
if os.path.dirname(DB_PATH):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    city       TEXT,
    lat        REAL,
    lon        REAL,
    lang       TEXT DEFAULT 'uz',
    alerts     INTEGER DEFAULT 1,
    daily      INTEGER DEFAULT 0,
    last_alert TEXT,
    created    TEXT
);
CREATE TABLE IF NOT EXISTS reports (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER,
    author   TEXT,
    city     TEXT,
    lat      REAL,
    lon      REAL,
    file_id  TEXT,
    caption  TEXT,
    status   TEXT,            -- pending / approved / rejected
    created  TEXT
);
""")
# Migratsiya: eski bazaga profil ustunini qo'shish
if "profile" not in {r["name"] for r in conn.execute("PRAGMA table_info(users)")}:
    conn.execute("ALTER TABLE users ADD COLUMN profile TEXT DEFAULT 'none'")
conn.commit()

FIELDS = ("city", "lat", "lon", "lang", "alerts", "daily", "profile")
PROFILES = ("none", "sensitive", "pregnant", "elderly", "child", "athlete")
SENSITIVE = ("sensitive", "pregnant", "elderly", "child")


def now_local() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def _now() -> str:
    return now_local().isoformat(timespec="seconds")


# ---------------- Foydalanuvchilar ----------------
def get_user(uid: int):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()


def ensure_user(uid: int, lang: str = "uz"):
    conn.execute("INSERT OR IGNORE INTO users(user_id, lang, created) VALUES(?, ?, ?)", (uid, lang, _now()))
    conn.commit()


def update_user(uid: int, **fields):
    fields = {k: v for k, v in fields.items() if k in FIELDS}
    if not fields:
        return
    ensure_user(uid)
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE users SET {sets} WHERE user_id=?", (*fields.values(), uid))
    conn.commit()


def user_dict(uid: int) -> dict:
    u = get_user(uid)
    return {k: u[k] for k in FIELDS} if u else {}


def users_with(field: str):
    assert field in ("alerts", "daily")
    return conn.execute(f"SELECT * FROM users WHERE {field}=1 AND lat IS NOT NULL").fetchall()


def set_last_alert(uid: int, ts: str):
    conn.execute("UPDATE users SET last_alert=? WHERE user_id=?", (ts, uid))
    conn.commit()


def delete_user(uid: int):
    conn.execute("DELETE FROM users WHERE user_id=?", (uid,))
    conn.commit()


def stats() -> dict:
    q = lambda s: conn.execute(s).fetchone()[0]  # noqa: E731
    return {"users": q("SELECT COUNT(*) FROM users"),
            "alerts": q("SELECT COUNT(*) FROM users WHERE alerts=1"),
            "reports": q("SELECT COUNT(*) FROM reports"),
            "pending": q("SELECT COUNT(*) FROM reports WHERE status='pending'")}


def count() -> int:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def distance_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def users_near(lat: float, lon: float, km: float, exclude: int):
    out = []
    for u in users_with("alerts"):
        if u["user_id"] != exclude:
            d = distance_km(lat, lon, u["lat"], u["lon"])
            if d <= km:
                out.append((d, u))
    return out


# ---------------- Bo'ron rasmlari ----------------
def reports_today(uid: int) -> int:
    since = (now_local() - timedelta(hours=24)).isoformat(timespec="seconds")
    return conn.execute("SELECT COUNT(*) FROM reports WHERE user_id=? AND created>=?", (uid, since)).fetchone()[0]


def add_report(uid, author, city, lat, lon, file_id, caption, status) -> int:
    cur = conn.execute(
        "INSERT INTO reports(user_id, author, city, lat, lon, file_id, caption, status, created) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", (uid, author, city, lat, lon, file_id, caption, status, _now()))
    conn.commit()
    return cur.lastrowid


def set_report_file(rid: int, file_id: str):
    conn.execute("UPDATE reports SET file_id=? WHERE id=?", (file_id, rid))
    conn.commit()


def get_report(rid: int):
    return conn.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()


def set_report_status(rid: int, status: str):
    conn.execute("UPDATE reports SET status=? WHERE id=?", (status, rid))
    conn.commit()


def delete_report(rid: int):
    conn.execute("DELETE FROM reports WHERE id=?", (rid,))
    conn.commit()


def recent_reports(hours: int = 48, limit: int = 60):
    since = (now_local() - timedelta(hours=hours)).isoformat(timespec="seconds")
    return conn.execute("SELECT * FROM reports WHERE status='approved' AND created>=? AND file_id IS NOT NULL "
                        "ORDER BY created DESC LIMIT ?", (since, limit)).fetchall()


# ---------------- Arxiv: har kungi ma'lumotlar ----------------
ARCHIVE_COLS = (
    "pm10_mean", "pm10_max", "pm25_mean", "pm25_max", "dust_mean", "dust_max", "aod_mean", "aqi_max",
    "o3_mean", "no2_mean", "so2_mean", "co_mean", "uv_max",
    "temp_min", "temp_max", "rh_mean", "wind_max", "gust_max", "precip_sum", "risk",
    "sensor_aqi", "sensor_pm25", "sensor_pm10", "sensor_n",
    "dust_aod", "soil_mean",
)
conn.executescript(f"""
CREATE TABLE IF NOT EXISTS daily_obs (
    city TEXT NOT NULL,
    date TEXT NOT NULL,
    {", ".join(c + " REAL" for c in ARCHIVE_COLS)},
    updated TEXT,
    PRIMARY KEY (city, date)
);
CREATE TABLE IF NOT EXISTS sensor_obs (
    city TEXT NOT NULL,
    time TEXT NOT NULL,
    aqi REAL, pm25 REAL, pm10 REAL, station TEXT,
    PRIMARY KEY (city, time)
);
""")
# Migratsiya: yangi ustunlar va import holati jadvali
_have = {r["name"] for r in conn.execute("PRAGMA table_info(daily_obs)")}
for _c in ARCHIVE_COLS:
    if _c not in _have:
        conn.execute(f"ALTER TABLE daily_obs ADD COLUMN {_c} REAL")
if "src" not in _have:
    conn.execute("ALTER TABLE daily_obs ADD COLUMN src TEXT")
conn.execute("""CREATE TABLE IF NOT EXISTS import_state (
    name TEXT PRIMARY KEY, status TEXT, detail TEXT, updated TEXT)""")
conn.commit()


def set_import(name: str, status: str, detail: str = ""):
    conn.execute("INSERT OR REPLACE INTO import_state(name, status, detail, updated) VALUES(?, ?, ?, ?)",
                 (name, status, detail, _now()))
    conn.commit()


def get_import(name: str) -> str | None:
    r = conn.execute("SELECT status FROM import_state WHERE name=?", (name,)).fetchone()
    return r[0] if r else None


def imports() -> dict:
    return {r["name"]: {"status": r["status"], "detail": r["detail"]}
            for r in conn.execute("SELECT * FROM import_state ORDER BY name")}


def upsert_daily(city: str, date: str, values: dict):
    """Kunlik yozuvni qo'shadi yoki yangilaydi (faqat berilgan ustunlar o'zgaradi)."""
    vals = {k: v for k, v in values.items() if k in ARCHIVE_COLS or k == "src"}
    if not vals:
        return
    cols = ", ".join(["city", "date", *vals, "updated"])
    marks = ", ".join(["?"] * (len(vals) + 3))
    sets = ", ".join(f"{k}=excluded.{k}" for k in [*vals, "updated"])
    conn.execute(f"INSERT INTO daily_obs({cols}) VALUES({marks}) ON CONFLICT(city, date) DO UPDATE SET {sets}",
                 (city, date, *vals.values(), _now()))


def commit():
    conn.commit()


def archive_rows(city: str | None = None, since: str | None = None, until: str | None = None) -> list[dict]:
    q, args = "SELECT * FROM daily_obs WHERE 1=1", []
    if city:
        q += " AND city=?"
        args.append(city)
    if since:
        q += " AND date>=?"
        args.append(since)
    if until:
        q += " AND date<=?"
        args.append(until)
    q += " ORDER BY city, date"
    return [dict(r) for r in conn.execute(q, args).fetchall()]


def archive_summary(city: str | None = None) -> dict:
    w = " WHERE city=?" if city else ""
    args = (city,) if city else ()
    n, first, last = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM daily_obs" + w, args).fetchone()
    pm_first = conn.execute("SELECT MIN(date) FROM daily_obs" + (w + " AND" if w else " WHERE") + " pm10_mean IS NOT NULL",
                            args).fetchone()[0]
    return {"days": n, "first": first, "last": last, "pm_first": pm_first}


def rows_missing_risk() -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT city, date, gust_max, soil_mean, rh_mean, precip_sum, dust_max, pm10_max FROM daily_obs "
        "WHERE risk IS NULL AND gust_max IS NOT NULL").fetchall()]


def add_sensor_obs(city: str, time: str, aqi, pm25, pm10, station: str):
    conn.execute("INSERT OR REPLACE INTO sensor_obs(city, time, aqi, pm25, pm10, station) VALUES(?, ?, ?, ?, ?, ?)",
                 (city, time, aqi, pm25, pm10, station))
    conn.commit()


def sensor_daily(city: str, date: str) -> dict | None:
    r = conn.execute("SELECT AVG(aqi), AVG(pm25), AVG(pm10), COUNT(*) FROM sensor_obs WHERE city=? AND time LIKE ?",
                     (city, date + "%")).fetchone()
    if not r or not r[3]:
        return None
    rnd = lambda v: None if v is None else round(v, 1)  # noqa: E731
    return {"sensor_aqi": rnd(r[0]), "sensor_pm25": rnd(r[1]), "sensor_pm10": rnd(r[2]), "sensor_n": r[3]}
