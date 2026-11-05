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
