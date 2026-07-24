from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import database as db
import ai as ai_module
import persian_date


def setup_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, "interval", seconds=30, args=[bot])
    scheduler.add_job(hourly_broadcast, "cron", minute=0, args=[bot])
    scheduler.start()
    return scheduler


async def check_reminders(bot):
    now_iso = datetime.now().isoformat(timespec="minutes")
    due = db.get_due_reminders(now_iso)
    for r_id, chat_id, text, remind_time, repeat in due:
        try:
            await bot.send_message(chat_id=chat_id, text=f"⏰ یادآوری: {text}")
        except Exception:
            pass

        if repeat == "daily":
            new_time = (datetime.fromisoformat(remind_time) + timedelta(days=1)).isoformat(timespec="minutes")
            db.reschedule_reminder(r_id, new_time)
        elif repeat == "weekly":
            new_time = (datetime.fromisoformat(remind_time) + timedelta(weeks=1)).isoformat(timespec="minutes")
            db.reschedule_reminder(r_id, new_time)
        else:
            db.mark_reminder_done(r_id)


async def hourly_broadcast(bot):
    """هر ساعت اجرا می‌شه؛ برای کاربرانی که ساعتشون با الان مطابقت داره، بریف روزانه
    (و در روز انتخابی‌شون، گزارش هفتگی) رو ارسال می‌کنه."""
    now = datetime.now()
    for chat_id, name, specialty, daily_hour, weekly_day in db.get_all_users():
        daily_hour = daily_hour if daily_hour is not None else 8
        weekly_day = weekly_day if weekly_day is not None else 4
        if now.hour != daily_hour:
            continue
        try:
            await send_daily_brief(bot, chat_id, name, specialty)
            if now.weekday() == weekly_day:
                await send_weekly_report(bot, chat_id, name, specialty)
        except Exception:
            pass


async def send_daily_brief(bot, chat_id, name, specialty):
    today = datetime.now().date().isoformat()
    reminders = [r for r in db.list_reminders(chat_id) if r[2].startswith(today)]
    events = [e for e in db.list_events(chat_id) if e[2].startswith(today)]
    tasks = db.list_tasks(chat_id, only_open=True)[:3]

    lines = [f"☀️ صبح بخیر {name or ''}! این خلاصه امروزته:"]
    if reminders:
        lines.append("\n⏰ یادآوری‌های امروز:")
        lines += [f"- {r[1]} ({persian_date.to_jalali_display(r[2]).split(' - ')[-1]})" for r in reminders]
    if events:
        lines.append("\n📅 رویدادهای امروز:")
        lines += [f"- {e[1]} ({persian_date.to_jalali_display(e[2]).split(' - ')[-1]})" for e in events]
    if tasks:
        lines.append("\n✅ اولویت‌های باز:")
        lines += [f"- #{t[0]} {t[1]}" for t in tasks]
    if not reminders and not events and not tasks:
        lines.append("\nامروز چیز خاصی ثبت نشده — وقت خوبیه برای یه هدف جدید 🎯")

    tip = ai_module.daily_tip(specialty)
    if tip:
        lines.append(f"\n💡 نکته امروز: {tip}")

    await bot.send_message(chat_id=chat_id, text="\n".join(lines))


async def send_weekly_report(bot, chat_id, name, specialty):
    done, open_ = db.count_tasks_last_days(chat_id, days=7)
    recent_memories = db.get_memories_since(chat_id, days=7)
    goals = db.list_goals(chat_id)

    stats_text = (
        f"کارهای انجام‌شده این هفته: {done}\n"
        f"کارهای باز فعلی: {open_}\n"
        f"تعداد اهداف فعال: {len(goals)}\n"
        f"نکات ثبت‌شده این هفته: {len(recent_memories)}"
    )
    report = ai_module.weekly_report(name, specialty, stats_text)
    await bot.send_message(chat_id=chat_id, text=f"📊 گزارش هفتگی:\n\n{report}")
