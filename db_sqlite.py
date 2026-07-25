import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
import config


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            specialty TEXT,
            created_at TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            text TEXT,
            remind_time TEXT,
            repeat TEXT DEFAULT 'once',
            done INTEGER DEFAULT 0,
            created_at TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            title TEXT,
            start_time TEXT,
            description TEXT,
            created_at TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            content TEXT,
            tag TEXT,
            created_at TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            title TEXT,
            goal_id INTEGER,
            priority TEXT DEFAULT 'normal',
            done INTEGER DEFAULT 0,
            created_at TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            title TEXT,
            description TEXT,
            deadline TEXT,
            created_at TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            authority TEXT PRIMARY KEY,
            chat_id INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )""")
        # مهاجرت ستون‌های جدید روی جدول قدیمی users (اگر از قبل وجود داشت)
        for stmt in [
            "ALTER TABLE users ADD COLUMN daily_hour INTEGER DEFAULT 8",
            "ALTER TABLE users ADD COLUMN weekly_day INTEGER DEFAULT 4",
            "ALTER TABLE users ADD COLUMN trial_start TEXT",
            "ALTER TABLE users ADD COLUMN subscription_until TEXT",
        ]:
            try:
                c.execute(stmt)
            except sqlite3.OperationalError:
                pass
        conn.commit()


# ---------------- users ----------------
def upsert_user(chat_id, name=None, specialty=None):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, trial_start FROM users WHERE chat_id=?", (chat_id,))
        row = c.fetchone()
        if row:
            if name is not None:
                c.execute("UPDATE users SET name=? WHERE chat_id=?", (name, chat_id))
            if specialty is not None:
                c.execute("UPDATE users SET specialty=? WHERE chat_id=?", (specialty, chat_id))
        else:
            c.execute(
                "INSERT INTO users (chat_id, name, specialty, created_at, daily_hour, weekly_day, trial_start) "
                "VALUES (?,?,?,?,8,4,?)",
                (chat_id, name, specialty, datetime.now().isoformat(), datetime.now().isoformat()),
            )
        conn.commit()


def get_user(chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT chat_id, name, specialty, daily_hour, weekly_day, trial_start, subscription_until "
            "FROM users WHERE chat_id=?",
            (chat_id,),
        )
        row = c.fetchone()
        if row:
            return {
                "chat_id": row[0],
                "name": row[1],
                "specialty": row[2],
                "daily_hour": row[3] if row[3] is not None else 8,
                "weekly_day": row[4] if row[4] is not None else 4,
                "trial_start": row[5],
                "subscription_until": row[6],
            }
        return None


def get_all_users():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, name, specialty, daily_hour, weekly_day FROM users")
        return c.fetchall()


def set_daily_hour(chat_id, hour):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET daily_hour=? WHERE chat_id=?", (hour, chat_id))
        conn.commit()


def set_weekly_day(chat_id, day):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET weekly_day=? WHERE chat_id=?", (day, chat_id))
        conn.commit()


def extend_subscription(chat_id, days=30):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT subscription_until FROM users WHERE chat_id=?", (chat_id,))
        row = c.fetchone()
        base = datetime.now()
        if row and row[0]:
            try:
                current = datetime.fromisoformat(row[0])
                if current > base:
                    base = current
            except ValueError:
                pass
        new_until = (base + timedelta(days=days)).isoformat()
        c.execute("UPDATE users SET subscription_until=? WHERE chat_id=?", (new_until, chat_id))
        conn.commit()
        return new_until


# ---------------- پرداخت‌ها (زرین‌پال) ----------------
def create_payment_record(authority, chat_id, amount):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO payments (authority, chat_id, amount, created_at) VALUES (?,?,?,?)",
            (authority, chat_id, amount, datetime.now().isoformat()),
        )
        conn.commit()


def get_payment(authority):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, amount, status FROM payments WHERE authority=?", (authority,))
        return c.fetchone()


def mark_payment_status(authority, status):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE payments SET status=? WHERE authority=?", (status, authority))
        conn.commit()


def list_active_subscriptions():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT chat_id, name, subscription_until FROM users "
            "WHERE subscription_until IS NOT NULL AND subscription_until > ? ORDER BY subscription_until",
            (datetime.now().isoformat(),),
        )
        return c.fetchall()


# ---------------- reminders ----------------
def add_reminder(chat_id, text, remind_time, repeat="once"):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO reminders (chat_id, text, remind_time, repeat, created_at) VALUES (?,?,?,?,?)",
            (chat_id, text, remind_time, repeat, datetime.now().isoformat()),
        )
        conn.commit()
        return c.lastrowid


def get_due_reminders(now_iso):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, chat_id, text, remind_time, repeat FROM reminders WHERE done=0 AND remind_time<=?",
            (now_iso,),
        )
        return c.fetchall()


def mark_reminder_done(reminder_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE reminders SET done=1 WHERE id=?", (reminder_id,))
        conn.commit()


def reschedule_reminder(reminder_id, new_time):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE reminders SET remind_time=? WHERE id=?", (new_time, reminder_id))
        conn.commit()


def list_reminders(chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, text, remind_time FROM reminders WHERE chat_id=? AND done=0 ORDER BY remind_time",
            (chat_id,),
        )
        return c.fetchall()


def delete_reminder(reminder_id, chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM reminders WHERE id=? AND chat_id=?", (reminder_id, chat_id))
        conn.commit()
        return c.rowcount > 0


# ---------------- events / schedule ----------------
def add_event(chat_id, title, start_time, description=""):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO events (chat_id, title, start_time, description, created_at) VALUES (?,?,?,?,?)",
            (chat_id, title, start_time, description, datetime.now().isoformat()),
        )
        conn.commit()
        return c.lastrowid


def list_events(chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, title, start_time, description FROM events WHERE chat_id=? ORDER BY start_time",
            (chat_id,),
        )
        return c.fetchall()


def delete_event(event_id, chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM events WHERE id=? AND chat_id=?", (event_id, chat_id))
        conn.commit()
        return c.rowcount > 0


# ---------------- tasks (کارها/تودو، جدا از یادآوری‌های زمان‌دار) ----------------
def add_task(chat_id, title, goal_id=None, priority="normal"):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO tasks (chat_id, title, goal_id, priority, created_at) VALUES (?,?,?,?,?)",
            (chat_id, title, goal_id, priority, datetime.now().isoformat()),
        )
        conn.commit()
        return c.lastrowid


def list_tasks(chat_id, only_open=True):
    with get_conn() as conn:
        c = conn.cursor()
        if only_open:
            c.execute(
                "SELECT id, title, priority, goal_id FROM tasks WHERE chat_id=? AND done=0 "
                "ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id",
                (chat_id,),
            )
        else:
            c.execute(
                "SELECT id, title, priority, goal_id, done FROM tasks WHERE chat_id=? ORDER BY id DESC",
                (chat_id,),
            )
        return c.fetchall()


def mark_task_done(task_id, chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE tasks SET done=1 WHERE id=? AND chat_id=?", (task_id, chat_id))
        conn.commit()
        return c.rowcount > 0


def delete_task(task_id, chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id=? AND chat_id=?", (task_id, chat_id))
        conn.commit()
        return c.rowcount > 0


def count_tasks_last_days(chat_id, days=7):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM tasks WHERE chat_id=? AND done=1 "
            "AND created_at >= datetime('now', ?)",
            (chat_id, f"-{days} days"),
        )
        done = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tasks WHERE chat_id=? AND done=0", (chat_id,))
        open_ = c.fetchone()[0]
        return done, open_


# ---------------- goals (اهداف تخصص/بیزینس) ----------------
def add_goal(chat_id, title, description="", deadline=None):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO goals (chat_id, title, description, deadline, created_at) VALUES (?,?,?,?,?)",
            (chat_id, title, description, deadline, datetime.now().isoformat()),
        )
        conn.commit()
        return c.lastrowid


def list_goals(chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, title, description, deadline FROM goals WHERE chat_id=? ORDER BY deadline IS NULL, deadline",
            (chat_id,),
        )
        return c.fetchall()


def delete_goal(goal_id, chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM goals WHERE id=? AND chat_id=?", (goal_id, chat_id))
        conn.commit()
        return c.rowcount > 0


# ---------------- memories (حافظه بلندمدت) ----------------
def add_memory(chat_id, content, tag="general"):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO memories (chat_id, content, tag, created_at) VALUES (?,?,?,?)",
            (chat_id, content, tag, datetime.now().isoformat()),
        )
        conn.commit()


def get_recent_memories(chat_id, limit=20):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT content, tag, created_at FROM memories WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        )
        return c.fetchall()


def get_memories_since(chat_id, days=7):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT content, tag FROM memories WHERE chat_id=? AND created_at >= datetime('now', ?) "
            "ORDER BY id DESC",
            (chat_id, f"-{days} days"),
        )
        return c.fetchall()


def list_memories(chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, content, tag FROM memories WHERE chat_id=? ORDER BY id DESC", (chat_id,))
        return c.fetchall()


def count_memories(chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM memories WHERE chat_id=?", (chat_id,))
        return c.fetchone()[0]


def get_oldest_memories(chat_id, limit=30):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, content FROM memories WHERE chat_id=? AND tag != 'summary' ORDER BY id ASC LIMIT ?",
            (chat_id, limit),
        )
        return c.fetchall()


def delete_memories_by_ids(ids):
    if not ids:
        return
    with get_conn() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" for _ in ids)
        c.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", ids)
        conn.commit()


def clear_memories(chat_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM memories WHERE chat_id=?", (chat_id,))
        conn.commit()
