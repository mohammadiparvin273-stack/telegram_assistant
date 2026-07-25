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

# ---------------- اشتراک و پرداخت (زرین‌پال) ----------------
ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID", "")
# تا وقتی کد پذیرندگی واقعی نگرفتی، حالت آزمایشی روشن بمونه (true/false)
ZARINPAL_SANDBOX = os.getenv("ZARINPAL_SANDBOX", "true").lower() == "true"
SUBSCRIPTION_PRICE_TOMAN = int(os.getenv("SUBSCRIPTION_PRICE_TOMAN", "49000"))
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "3"))
SUBSCRIPTION_DAYS = int(os.getenv("SUBSCRIPTION_DAYS", "31"))

# اسم مدل Gemini قابل تنظیم از بیرونه، چون گوگل مدل‌ها رو مرتب عوض می‌کنه.
# اگه خالی بذاریش، کد خودش چند تا مدل شناخته‌شده رو امتحان می‌کنه تا یکی جواب بده.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")

# ---------------- پرداخت کارت‌به‌کارت (به‌جای درگاه) ----------------
BANK_CARD_NUMBER = os.getenv("BANK_CARD_NUMBER", "6221061215388564")
BANK_SHABA = os.getenv("BANK_SHABA", "IR080540108247000782271605")
BANK_CARD_NAME = os.getenv("BANK_CARD_NAME", "ماهان بنابی‌فرد")
ADMIN_TELEGRAM_USERNAME = os.getenv("ADMIN_TELEGRAM_USERNAME", "Mahan_helper_admin")

# چت‌آیدی عددی خودت در تلگرام؛ فقط همین چت‌آیدی به پنل مدیریت دسترسی داره.
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
