import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # مثال: https://your-app.onrender.com  (بدون / انتهایی)
PORT = int(os.getenv("PORT", "8080"))
DB_PATH = os.getenv("DB_PATH", "assistant.db")

# اگر ست بشه، دیتابیس Postgres (مثلا Supabase) استفاده می‌شه؛ در غیر این صورت SQLite محلی.
DATABASE_URL = os.getenv("DATABASE_URL", "")
