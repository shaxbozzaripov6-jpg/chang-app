"""SQLite: Mini App foydalanuvchilari va sozlamalari."""
import math
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")
DB_PATH = os.getenv("DB_PATH", "chang_app.db")
if os.path.dirname(DB_PATH):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("""
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
)""")
conn.commit()

FIELDS = ("city", "lat", "lon", "lang", "alerts", "daily")


def now_local() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def get_user(uid: int):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()


def ensure_user(uid: int, lang: str = "uz"):
    conn.execute("INSERT OR IGNORE INTO users(user_id, lang, created) VALUES(?, ?, ?)",
                 (uid, lang, now_local().isoformat(timespec="seconds")))
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


def count() -> int:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def distance_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
