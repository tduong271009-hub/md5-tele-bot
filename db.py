import aiosqlite
import asyncio
from datetime import datetime, date

class DB:
    def __init__(self, path):
        self.path = path
        self._init_lock = asyncio.Lock()

    async def init(self):
        async with self._init_lock:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    daily_limit INTEGER,
                    banned_until INTEGER
                )""")
                await db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    text TEXT,
                    md5 TEXT,
                    result TEXT,
                    created_at INTEGER
                )""")
                await db.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    count INTEGER,
                    UNIQUE(user_id, date)
                )""")
                await db.commit()

    async def ensure_user(self, user_id, username="", first_name="", last_name=""):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            if not row:
                await db.execute(
                    "INSERT INTO users(user_id, username, first_name, last_name, daily_limit, banned_until) VALUES(?,?,?,?,?,?)",
                    (user_id, username, first_name, last_name, None, 0)
                )
                await db.commit()

    async def set_daily_limit(self, user_id, limit):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET daily_limit = ? WHERE user_id = ?", (limit, user_id))
            await db.commit()

    async def set_banned_until(self, user_id, ts):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET banned_until = ? WHERE user_id = ?", (ts, user_id))
            await db.commit()

    async def get_user(self, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id, username, first_name, last_name, daily_limit, banned_until FROM users WHERE user_id = ?", (user_id,))
            return await cur.fetchone()

    async def log_request(self, user_id, username, text, md5, result):
        ts = int(datetime.utcnow().timestamp())
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO logs(user_id, username, text, md5, result, created_at) VALUES(?,?,?,?,?,?)",
                (user_id, username, text, md5, result, ts)
            )
            # update usage
            today = date.today().isoformat()
            cur = await db.execute("SELECT count FROM usage WHERE user_id = ? AND date = ?", (user_id, today))
            r = await cur.fetchone()
            if r:
                await db.execute("UPDATE usage SET count = count + 1 WHERE user_id = ? AND date = ?", (user_id, today))
            else:
                await db.execute("INSERT INTO usage(user_id, date, count) VALUES(?,?,1)", (user_id, today))
            await db.commit()

    async def get_usage_today(self, user_id):
        today = date.today().isoformat()
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT count FROM usage WHERE user_id = ? AND date = ?", (user_id, today))
            r = await cur.fetchone()
            return r[0] if r else 0

    async def total_users(self):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            r = await cur.fetchone()
            return r[0] if r else 0

    async def requests_today(self):
        today = date.today().isoformat()
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT SUM(count) FROM usage WHERE date = ?", (today,))
            r = await cur.fetchone()
            return r[0] or 0

    async def top_users(self, limit=10):
        today = date.today().isoformat()
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT u.user_id, u.username, IFNULL(us.count,0) as cnt FROM users u LEFT JOIN usage us ON u.user_id = us.user_id AND us.date = ? ORDER BY cnt DESC LIMIT ?",
                (today, limit)
            )
            return await cur.fetchall()
