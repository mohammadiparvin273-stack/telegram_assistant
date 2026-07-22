import re
from datetime import datetime
import dateparser
from telegram import Update
from telegram.ext import ContextTypes

import database as db
import ai as ai_module

WELCOME = """سلام 👋 من دستیار شخصی، منشی و مربی رشد توام!

از این به بعد می‌تونم:
📌 یادآوری‌ها و کارها رو مدیریت کنم
🗓 برنامه‌ها و قرارهات رو ثبت و پیگیری کنم
🎯 اهداف یادگیری/بیزینسی‌ت رو پیگیری کنم
☀️ هر روز یه بریف کوتاه از کارهات + یه نکته آموزشی بفرستم
📊 هر هفته یه گزارش پیشرفت و پیشنهاد بهبود بدم
🧠 هرچی بهم بگی به خاطر بسپارم و باهات درباره تخصصت گفتگو کنم

برای شروع بگو اسمت چیه؟"""

HELP = """📋 دستورات:

🗂 یادآوری و برنامه
/remind YYYY-MM-DD HH:MM متن   ثبت یادآوری
/reminders   لیست یادآوری‌های فعال
/delreminder ID   حذف یادآوری
/event YYYY-MM-DD HH:MM عنوان   ثبت رویداد/قرار
/events   لیست رویدادها

✅ کارها و اهداف
/task متن   افزودن کار به لیست
/tasks   لیست کارهای باز
/done ID   انجام‌شده علامت زدن کار
/deltask ID   حذف کار
/goal عنوان | ددلاین(YYYY-MM-DD) | توضیح   ثبت هدف
/goals   لیست اهداف
/delgoal ID   حذف هدف

🧠 حافظه و رشد
/note متن   ثبت یک نکته در حافظه
/notes   دیدن حافظه
/forget   پاک کردن کل حافظه
/roadmap   نقشه راه شخصی‌سازی‌شده برای تخصصت
/weekly   گزارش هفتگی فوری

⚙️ تنظیمات
/dailytime ساعت(0-23)   ساعت ارسال بریف روزانه
/weeklyday روز(0=دوشنبه...6=یکشنبه)   روز ارسال گزارش هفتگی
/help   همین راهنما

نکته: می‌تونی به زبان طبیعی هم بنویسی، مثلا: «فردا ساعت ۹ صبح یادم بنداز با علی تماس بگیرم»."""

TIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s+(.*)", re.DOTALL)
REMINDER_KEYWORDS = ["یادم بنداز", "یادآوری", "یاد آوری کن", "یادت باشه بگی"]
MEMORY_SUMMARY_THRESHOLD = 40
MEMORY_SUMMARY_KEEP_RECENT = 10


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.upsert_user(chat_id)
    await update.message.reply_text(WELCOME)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)


# ---------------- یادآوری‌ها ----------------
async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args_text = " ".join(context.args)
    m = TIME_RE.match(args_text)
    if not m:
        await update.message.reply_text("فرمت درست: /remind 2026-07-25 09:00 متن یادآوری")
        return
    date_s, time_s, text = m.groups()
    remind_time = f"{date_s}T{time_s}"
    try:
        datetime.fromisoformat(remind_time)
    except ValueError:
        await update.message.reply_text("تاریخ/ساعت نامعتبره.")
        return
    db.add_reminder(chat_id, text.strip(), remind_time)
    await update.message.reply_text(f"✅ یادآوری ثبت شد برای {date_s} {time_s}:\n{text.strip()}")


async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rows = db.list_reminders(chat_id)
    if not rows:
        await update.message.reply_text("یادآوری فعالی نداری.")
        return
    lines = [f"#{r_id} | {t.replace('T', ' ')} | {text}" for r_id, text, t in rows]
    await update.message.reply_text("\n".join(lines))


async def delreminder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("فرمت: /delreminder ID")
        return
    try:
        r_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID باید عدد باشه.")
        return
    ok = db.delete_reminder(r_id, chat_id)
    await update.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")


# ---------------- رویدادها ----------------
async def event_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args_text = " ".join(context.args)
    m = TIME_RE.match(args_text)
    if not m:
        await update.message.reply_text("فرمت درست: /event 2026-07-25 14:00 عنوان رویداد")
        return
    date_s, time_s, title = m.groups()
    db.add_event(chat_id, title.strip(), f"{date_s}T{time_s}")
    await update.message.reply_text(f"📅 رویداد ثبت شد: {title.strip()} در {date_s} {time_s}")


async def events_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rows = db.list_events(chat_id)
    if not rows:
        await update.message.reply_text("رویدادی ثبت نشده.")
        return
    lines = [f"#{e_id} | {t.replace('T', ' ')} | {title}" for e_id, title, t, desc in rows]
    await update.message.reply_text("\n".join(lines))


# ---------------- کارها (Tasks) ----------------
async def task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("فرمت: /task متن کار")
        return
    task_id = db.add_task(chat_id, text)
    await update.message.reply_text(f"✅ کار #{task_id} اضافه شد: {text}")


async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rows = db.list_tasks(chat_id, only_open=True)
    if not rows:
        await update.message.reply_text("کار بازی نداری. یکی اضافه کن با /task")
        return
    icons = {"high": "🔴", "normal": "🟡", "low": "🟢"}
    lines = [f"#{t_id} {icons.get(pr, '🟡')} {title}" for t_id, title, pr, goal_id in rows]
    await update.message.reply_text("\n".join(lines))


async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("فرمت: /done ID")
        return
    try:
        t_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID باید عدد باشه.")
        return
    ok = db.mark_task_done(t_id, chat_id)
    await update.message.reply_text("🎉 آفرین، انجام شد!" if ok else "پیدا نشد.")


async def deltask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("فرمت: /deltask ID")
        return
    try:
        t_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID باید عدد باشه.")
        return
    ok = db.delete_task(t_id, chat_id)
    await update.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")


# ---------------- اهداف (Goals) ----------------
async def goal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    raw = " ".join(context.args)
    if not raw:
        await update.message.reply_text(
            "فرمت: /goal عنوان هدف | ددلاین(YYYY-MM-DD اختیاری) | توضیح(اختیاری)\n"
            "مثال: /goal یادگیری زبان انگلیسی سطح B2 | 2026-12-01 | برای مکالمه کاری"
        )
        return
    parts = [p.strip() for p in raw.split("|")]
    title = parts[0]
    deadline = parts[1] if len(parts) > 1 and parts[1] else None
    description = parts[2] if len(parts) > 2 else ""
    if deadline:
        try:
            datetime.fromisoformat(deadline)
        except ValueError:
            await update.message.reply_text("فرمت ددلاین باید YYYY-MM-DD باشه.")
            return
    goal_id = db.add_goal(chat_id, title, description, deadline)
    await update.message.reply_text(f"🎯 هدف #{goal_id} ثبت شد: {title}")


async def goals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rows = db.list_goals(chat_id)
    if not rows:
        await update.message.reply_text("هدفی ثبت نشده. با /goal یکی اضافه کن.")
        return
    lines = []
    for g_id, title, desc, deadline in rows:
        line = f"#{g_id} 🎯 {title}"
        if deadline:
            line += f" (تا {deadline})"
        lines.append(line)
    await update.message.reply_text("\n".join(lines))


async def delgoal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("فرمت: /delgoal ID")
        return
    try:
        g_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID باید عدد باشه.")
        return
    ok = db.delete_goal(g_id, chat_id)
    await update.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")


# ---------------- حافظه ----------------
async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("فرمت: /note متنی که می‌خوای به خاطر بسپارم")
        return
    db.add_memory(chat_id, text)
    await maybe_summarize_memories(chat_id)
    await update.message.reply_text("🧠 ذخیره شد.")


async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rows = db.list_memories(chat_id)
    if not rows:
        await update.message.reply_text("چیزی به خاطر نسپردم.")
        return
    lines = [f"#{n_id} | {c}" for n_id, c, tag in rows]
    text = "\n".join(lines)
    await update.message.reply_text(text[:4000])


async def forget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.clear_memories(chat_id)
    await update.message.reply_text("حافظه پاک شد.")


async def maybe_summarize_memories(chat_id):
    """اگه تعداد نکات ذخیره‌شده زیاد شد، قدیمی‌ترها رو با AI خلاصه می‌کنه تا حافظه متورم نشه."""
    count = db.count_memories(chat_id)
    if count <= MEMORY_SUMMARY_THRESHOLD:
        return
    old = db.get_oldest_memories(chat_id, limit=count - MEMORY_SUMMARY_KEEP_RECENT)
    if len(old) < 15:
        return
    ids = [m[0] for m in old]
    text_block = "\n".join(f"- {m[1]}" for m in old)
    summary = ai_module.summarize_memories(text_block)
    db.delete_memories_by_ids(ids)
    db.add_memory(chat_id, summary, tag="summary")


# ---------------- رشد و مربیگری ----------------
async def roadmap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)
    if not user:
        await update.message.reply_text("اول با /start شروع کن.")
        return
    await update.message.reply_text("⏳ در حال طراحی نقشه راه...")
    goals = db.list_goals(chat_id)
    goals_text = "\n".join(f"- {g[1]}" + (f" (تا {g[3]})" if g[3] else "") for g in goals)
    memories = db.get_recent_memories(chat_id, limit=20)
    memories_text = "\n".join(f"- {m[0]}" for m in memories)
    roadmap = ai_module.generate_roadmap(user["name"], user["specialty"], goals_text, memories_text)
    db.add_memory(chat_id, f"نقشه راه تولید شده: {roadmap[:300]}", tag="roadmap")
    await update.message.reply_text(f"🗺 نقشه راهت:\n\n{roadmap}")


async def weekly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)
    if not user:
        await update.message.reply_text("اول با /start شروع کن.")
        return
    await update.message.reply_text("⏳ در حال آماده‌سازی گزارش هفتگی...")
    done, open_ = db.count_tasks_last_days(chat_id, days=7)
    recent_memories = db.get_memories_since(chat_id, days=7)
    goals = db.list_goals(chat_id)
    stats_text = (
        f"کارهای انجام‌شده این هفته: {done}\n"
        f"کارهای باز فعلی: {open_}\n"
        f"تعداد اهداف فعال: {len(goals)}\n"
        f"نکات ثبت‌شده این هفته: {len(recent_memories)}"
    )
    report = ai_module.weekly_report(user["name"], user["specialty"], stats_text)
    await update.message.reply_text(f"📊 گزارش هفتگی:\n\n{report}")


# ---------------- تنظیمات ----------------
async def dailytime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("فرمت: /dailytime 8  (ساعت بین 0 تا 23)")
        return
    try:
        hour = int(context.args[0])
        assert 0 <= hour <= 23
    except (ValueError, AssertionError):
        await update.message.reply_text("ساعت باید عددی بین 0 تا 23 باشه.")
        return
    db.set_daily_hour(chat_id, hour)
    await update.message.reply_text(f"✅ بریف روزانه از این به بعد ساعت {hour} ارسال می‌شه.")


async def weeklyday_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("فرمت: /weeklyday 4  (0=دوشنبه ... 6=یکشنبه)")
        return
    try:
        day = int(context.args[0])
        assert 0 <= day <= 6
    except (ValueError, AssertionError):
        await update.message.reply_text("روز باید عددی بین 0 تا 6 باشه.")
        return
    db.set_weekly_day(chat_id, day)
    await update.message.reply_text("✅ روز گزارش هفتگی به‌روزرسانی شد.")


# ---------------- گفتگوی آزاد ----------------
async def free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    user = db.get_user(chat_id)

    # مرحله ثبت‌نام اولیه: اسم و تخصص
    if user is None:
        db.upsert_user(chat_id, name=text[:50])
        await update.message.reply_text("خوشبختم! تخصص یا حرفه‌ات چیه؟ (مثلا: برنامه‌نویسی، حسابداری، بازاریابی...)")
        return
    if not user["name"]:
        db.upsert_user(chat_id, name=text[:50])
        await update.message.reply_text("خوشبختم! تخصص یا حرفه‌ات چیه؟")
        return
    if not user["specialty"]:
        db.upsert_user(chat_id, specialty=text[:100])
        await update.message.reply_text(
            "عالی، از این به بعد آماده کمکم 🙌\n"
            "برای دیدن دستورات /help رو بزن، یا با /goal یه هدف اول ثبت کن تا شروع کنیم."
        )
        return

    # تلاش برای تشخیص یادآوری با زبان طبیعی
    if any(k in text for k in REMINDER_KEYWORDS):
        dt = dateparser.parse(text, languages=["fa"], settings={"PREFER_DATES_FROM": "future"})
        if dt:
            db.add_reminder(chat_id, text, dt.isoformat(timespec="minutes"))
            await update.message.reply_text(f"✅ یادآوری ثبت شد برای {dt.strftime('%Y-%m-%d %H:%M')}")
            return
        else:
            await update.message.reply_text(
                "زمانش رو دقیق متوجه نشدم 🙏 لطفاً با این فرمت بفرست:\n/remind YYYY-MM-DD HH:MM متن"
            )
            return

    # در غیر این صورت: گفتگوی هوشمند + ذخیره خودکار در حافظه
    memories = [m[0] for m in db.get_recent_memories(chat_id, limit=15)]
    system_prompt = ai_module.build_system_prompt(user["name"], user["specialty"], memories)
    reply = ai_module.ask_gemini(system_prompt, text)
    db.add_memory(chat_id, text, tag="chat")
    await maybe_summarize_memories(chat_id)
    await update.message.reply_text(reply)
