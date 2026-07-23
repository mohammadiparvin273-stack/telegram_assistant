"""
واسط انتخاب دیتابیس:
- اگر متغیر محیطی DATABASE_URL ست شده باشه (مثلا آدرس Postgres رایگان Supabase)،
  از db_postgres استفاده می‌کنه (دائمی، حتی بعد از redeploy روی Render پاک نمی‌شه).
- در غیر این صورت از db_sqlite استفاده می‌کنه (ساده، فقط برای اجرای محلی/تست مناسبه).

بقیه فایل‌های پروژه فقط با `import database as db` کار می‌کنن و لازم نیست چیزی عوض بشه.
"""
import config

if config.DATABASE_URL:
    from db_postgres import *  # noqa: F401,F403
else:
    from db_sqlite import *  # noqa: F401,F403
