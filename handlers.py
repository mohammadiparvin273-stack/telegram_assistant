import re
from datetime import datetime
import dateparser
from telegram import Update
from telegram.ext import ContextTypes

import database as db
import ai as ai_module
import keyboards

WELCOME = """سلام 👋 من دستیار شخصی، منشی و مربی رشد توام!

از این به بعد می‌تونم:
📌 یادآوری‌ها و کارها رو مدیریت کنم
🗓 برنامه‌ها و قرارهات رو ثبت و پیگیری کنم
🎯 اهداف یادگیری/بیزینسی‌ت رو پیگیری کنم
☀️ هر روز یه بریف کوتاه از کارهات + یه نکته آموزشی بفرستم
📊 هر هفته یه گزارش پیشرفت و پیشنهاد بهبود بدم
🧠 هرچی بهم بگی به خاطر بسپارم و باهات درباره تخصصت گفتگو کنم

برای شروع بگو اسمت چیه؟"""

WELCOME_BACK = "خوش برگشتی 👋 از دکمه‌های پایین صفحه استفاده کن، یا هر دستوری که بلدی رو تایپ کن."

HELP = """📋 دستورات (یا از دکمه‌های پایین صفحه استفاده کن):

🗂 یادآوری و برنامه
/remind YYYY-MM-DD HH:MM متن   ثبت یادآوری
/reminders   لیست یادآوری‌های فعال
/delreminder ID   حذف یادآوری
/event YYYY-MM-DD HH:MM عنوان   ثبت رویداد/قرار
/events   لیست رویدادها
/delevent ID   حذف رویداد

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
/menu   نمایش دوباره دکمه‌ها
/help   همین راهنما

نکته: می‌تونی به زبان طبیعی هم بنویسی، مثلا: «فردا ساعت ۹ صبح یادم بنداز با علی تماس بگیرم»."""

TIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s+(.*)", re.DOTALL)
REMINDER_KEYWORDS = ["یادم بنداز", "یادآوری", "یاد آوری کن", "یادت باشه بگی"]
MEMORY_SUMMARY_THRESHOLD = 40
MEMORY_SUMMARY_KEEP_RECENT = 10


# ==================== شروع و راهنما ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)
    if user and user["name"] and user["specialty"]:
        db.upsert_user(chat_id)
        await update.message.reply_text(WELCOME_BACK, reply_markup=keyboards.main_menu_keyboard())
        return
    db.upsert_user(chat_id)
    await update.message.reply_text(WELCOME)


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)
    if not user or not user["name"] or not user["specialty"]:
        await update.message.reply_text("اول با /start شروع کن و اسم/تخصصت رو بگو.")
        return
    await update.message.reply_text("یکی از گزینه‌ها رو انتخاب کن 👇", reply_markup=keyboards.main_menu_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)


# ==================== توابع کمکی مشترک (برای دستور و دکمه) ====================
def _parse_and_add_reminder(chat_id, raw_text):
    m = TIME_RE.match(raw_text.strip())
    if not m:
        return "فرمت درست: 2026-08-01 09:00 متن یادآوری"
    date_s, time_s, text = m.groups()
    remind_time = f"{date_s}T{time_s}"
    try:
        datetime.fromisoformat(remind_time)
    except ValueError:
        return "تاریخ/ساعت نامعتبره."
    db.add_reminder(chat_id, text.strip(), remind_time)
    return f"✅ یادآوری ثبت شد برای {date_s} {time_s}:\n{text.strip()}"


def _parse_and_add_event(chat_id, raw_text):
    m = TIME_RE.match(raw_text.strip())
    if not m:
        return "فرمت درست: 2026-08-01 14:00 عنوان رویداد"
    date_s, time_s, title = m.groups()
    db.add_event(chat_id, title.strip(), f"{date_s}T{time_s}")
    return f"📅 رویداد ثبت شد: {title.strip()} در {date_s} {time_s}"


def _parse_and_add_goal(chat_id, raw_text):
    parts = [p.strip() for p in raw_text.split("|")]
    title = parts[0]
    if not title:
        return "فرمت: عنوان هدف | ددلاین(YYYY-MM-DD اختیاری) | توضیح(اختیاری)"
    deadline = parts[1] if len(parts) > 1 and parts[1] else None
    description = parts[2] if len(parts) > 2 else ""
    if deadline:
        try:
            datetime.fromisoformat(deadline)
        except ValueError:
            return "فرمت ددلاین باید YYYY-MM-DD باشه."
    goal_id = db.add_goal(chat_id, title, description, deadline)
    return f"🎯 هدف #{goal_id} ثبت شد: {title}"


async def _send_reminders_list(target, chat_id):
    rows = db.list_reminders(chat_id)
    if not rows:
        await target.reply_text("یادآوری فعالی نداری.")
        return
    lines = [f"{t.replace('T', ' ')} | {text}" for r_id, text, t in rows]
    await target.reply_text("\n".join(lines), reply_markup=keyboards.build_delete_keyboard(rows, "rem_del"))


async def _send_events_list(target, chat_id):
    rows = db.list_events(chat_id)
    if not rows:
        await target.reply_text("رویدادی ثبت نشده.")
        return
    lines = [f"{t.replace('T', ' ')} | {title}" for e_id, title, t, desc in rows]
    kb_rows = [(e_id, title) for e_id, title, t, desc in rows]
    await target.reply_text("\n".join(lines), reply_markup=keyboards.build_delete_keyboard(kb_rows, "event_del"))


async def _send_tasks_list(target, chat_id):
    rows = db.list_tasks(chat_id, only_open=True)
    if not rows:
        await target.reply_text("کار بازی نداری.")
        return
    icons = {"high": "🔴", "normal": "🟡", "low": "🟢"}
    lines = [f"{icons.get(pr, '🟡')} {title}" for t_id, title, pr, goal_id in rows]
    await target.reply_text("\n".join(lines), reply_markup=keyboards.build_task_keyboard(rows))


async def _send_goals_list(target, chat_id):
    rows = db.list_goals(chat_id)
    if not rows:
        await target.reply_text("هدفی ثبت نشده.")
        return
    lines = []
    kb_rows = []
    for g_id, title, desc, deadline in rows:
        line = f"🎯 {title}"
        if deadline:
            line += f" (تا {deadline})"
        lines.append(line)
        kb_rows.append((g_id, title))
    await target.reply_text("\n".join(lines), reply_markup=keyboards.build_delete_keyboard(kb_rows, "goal_del"))


async def _send_notes_list(target, chat_id):
    rows = db.list_memories(chat_id)
    if not rows:
        await target.reply_text("چیزی به خاطر نسپردم.")
        return
    lines = [f"- {c}" for n_id, c, tag in rows]
    await target.reply_text("\n".join(lines)[:4000])


async def maybe_summarize_memories(chat_id):
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


async def _send_roadmap(target, chat_id):
    user = db.get_user(chat_id)
    await target.reply_text("⏳ در حال طراحی نقشه راه...")
    goals = db.list_goals(chat_id)
    goals_text = "\n".join(f"- {g[1]}" + (f" (تا {g[3]})" if g[3] else "") for g in goals)
    memories = db.get_recent_memories(chat_id, limit=20)
    memories_text = "\n".join(f"- {m[0]}" for m in memories)
    roadmap = ai_module.generate_roadmap(user["name"], user["specialty"], goals_text, memories_text)
    db.add_memory(chat_id, f"نقشه راه تولید شده: {roadmap[:300]}", tag="roadmap")
    await target.reply_text(f"🗺 نقشه راهت:\n\n{roadmap}")


async def _send_weekly(target, chat_id):
    user = db.get_user(chat_id)
    await target.reply_text("⏳ در حال آماده‌سازی گزارش هفتگی...")
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
    await target.reply_text(f"📊 گزارش هفتگی:\n\n{report}")


# ==================== یادآوری‌ها ====================
async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reply = _parse_and_add_reminder(chat_id, " ".join(context.args))
    await update.message.reply_text(reply)


async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_reminders_list(update.message, update.effective_chat.id)


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


# ==================== رویدادها ====================
async def event_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reply = _parse_and_add_event(chat_id, " ".join(context.args))
    await update.message.reply_text(reply)


async def events_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_events_list(update.message, update.effective_chat.id)


async def delevent_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("فرمت: /delevent ID")
        return
    try:
        e_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID باید عدد باشه.")
        return
    ok = db.delete_event(e_id, chat_id)
    await update.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")


# ==================== کارها ====================
async def task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("فرمت: /task متن کار")
        return
    task_id = db.add_task(chat_id, text)
    await update.message.reply_text(f"✅ کار #{task_id} اضافه شد: {text}")


async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_tasks_list(update.message, update.effective_chat.id)


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


# ==================== اهداف ====================
async def goal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    raw = " ".join(context.args)
    if not raw:
        await update.message.reply_text(
            "فرمت: /goal عنوان هدف | ددلاین(YYYY-MM-DD اختیاری) | توضیح(اختیاری)\n"
            "مثال: /goal یادگیری زبان انگلیسی سطح B2 | 2026-12-01 | برای مکالمه کاری"
        )
        return
    await update.message.reply_text(_parse_and_add_goal(chat_id, raw))


async def goals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_goals_list(update.message, update.effective_chat.id)


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


# ==================== حافظه ====================
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
    await _send_notes_list(update.message, update.effective_chat.id)


async def forget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.clear_memories(chat_id)
    await update.message.reply_text("حافظه پاک شد.")


# ==================== رشد و مربیگری ====================
async def roadmap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not db.get_user(chat_id):
        await update.message.reply_text("اول با /start شروع کن.")
        return
    await _send_roadmap(update.message, chat_id)


async def weekly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not db.get_user(chat_id):
        await update.message.reply_text("اول با /start شروع کن.")
        return
    await _send_weekly(update.message, chat_id)


# ==================== تنظیمات ====================
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


# ==================== دکمه‌های اینلاین (زیر پیام‌ها) ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id
    user = db.get_user(chat_id)
    if not user:
        await query.message.reply_text("اول با /start شروع کن.")
        return

    if data == "m:remind_add":
        context.user_data["awaiting"] = "remind_add"
        await query.message.reply_text("فرمت بفرست: 2026-08-01 09:00 متن یادآوری")
    elif data == "m:remind_list":
        await _send_reminders_list(query.message, chat_id)
    elif data == "m:event_add":
        context.user_data["awaiting"] = "event_add"
        await query.message.reply_text("فرمت بفرست: 2026-08-01 14:00 عنوان رویداد")
    elif data == "m:event_list":
        await _send_events_list(query.message, chat_id)
    elif data == "m:task_add":
        context.user_data["awaiting"] = "task_add"
        await query.message.reply_text("متن کار رو بفرست:")
    elif data == "m:task_list":
        await _send_tasks_list(query.message, chat_id)
    elif data == "m:goal_add":
        context.user_data["awaiting"] = "goal_add"
        await query.message.reply_text("فرمت بفرست: عنوان هدف | ددلاین(YYYY-MM-DD اختیاری) | توضیح(اختیاری)")
    elif data == "m:goal_list":
        await _send_goals_list(query.message, chat_id)
    elif data == "m:note_add":
        context.user_data["awaiting"] = "note_add"
        await query.message.reply_text("چی رو به خاطر بسپارم؟")
    elif data == "m:note_list":
        await _send_notes_list(query.message, chat_id)
    elif data == "m:note_clear":
        db.clear_memories(chat_id)
        await query.message.reply_text("حافظه پاک شد.")
    elif data == "m:roadmap":
        await _send_roadmap(query.message, chat_id)
    elif data == "m:weekly":
        await _send_weekly(query.message, chat_id)
    elif data == "m:set_dailytime":
        context.user_data["awaiting"] = "set_dailytime"
        await query.message.reply_text("ساعت رو بین 0 تا 23 بفرست (مثلا 8):")
    elif data == "m:set_weeklyday":
        context.user_data["awaiting"] = "set_weeklyday"
        await query.message.reply_text("روز رو بفرست، عددی بین 0(دوشنبه) تا 6(یکشنبه):")
    elif data.startswith("rem_del:"):
        ok = db.delete_reminder(int(data.split(":")[1]), chat_id)
        await query.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")
    elif data.startswith("event_del:"):
        ok = db.delete_event(int(data.split(":")[1]), chat_id)
        await query.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")
    elif data.startswith("task_done:"):
        ok = db.mark_task_done(int(data.split(":")[1]), chat_id)
        await query.message.reply_text("🎉 آفرین، انجام شد!" if ok else "پیدا نشد.")
    elif data.startswith("task_del:"):
        ok = db.delete_task(int(data.split(":")[1]), chat_id)
        await query.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")
    elif data.startswith("goal_del:"):
        ok = db.delete_goal(int(data.split(":")[1]), chat_id)
        await query.message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")


# ==================== گفتگوی آزاد و ورودی‌های در انتظار ====================
async def free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    user = db.get_user(chat_id)

    # ورودی‌هایی که از طریق دکمه منتظرشون هستیم
    awaiting = context.user_data.get("awaiting")
    if awaiting and user:
        context.user_data["awaiting"] = None
        reply = None
        if awaiting == "remind_add":
            reply = _parse_and_add_reminder(chat_id, text)
        elif awaiting == "event_add":
            reply = _parse_and_add_event(chat_id, text)
        elif awaiting == "task_add":
            task_id = db.add_task(chat_id, text)
            reply = f"✅ کار #{task_id} اضافه شد: {text}"
        elif awaiting == "goal_add":
            reply = _parse_and_add_goal(chat_id, text)
        elif awaiting == "note_add":
            db.add_memory(chat_id, text)
            await maybe_summarize_memories(chat_id)
            reply = "🧠 ذخیره شد."
        elif awaiting == "set_dailytime":
            try:
                hour = int(text)
                assert 0 <= hour <= 23
                db.set_daily_hour(chat_id, hour)
                reply = f"✅ بریف روزانه از این به بعد ساعت {hour} ارسال می‌شه."
            except (ValueError, AssertionError):
                reply = "عدد باید بین 0 تا 23 باشه، دوباره امتحان کن."
        elif awaiting == "set_weeklyday":
            try:
                day = int(text)
                assert 0 <= day <= 6
                db.set_weekly_day(chat_id, day)
                reply = "✅ روز گزارش هفتگی به‌روزرسانی شد."
            except (ValueError, AssertionError):
                reply = "عدد باید بین 0 تا 6 باشه، دوباره امتحان کن."
        if reply:
            await update.message.reply_text(reply)
            return

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
            "عالی، از این به بعد آماده کمکم 🙌 از دکمه‌های پایین صفحه استفاده کن:",
            reply_markup=keyboards.main_menu_keyboard(),
        )
        return

    # اگه یکی از دکمه‌های منوی اصلی زده شده باشه
    if text in keyboards.MAIN_MENU_LABELS:
        if text == "❓ راهنما":
            await update.message.reply_text(HELP)
            return
        kb = keyboards.category_menu(text)
        await update.message.reply_text(f"{text} — یکی رو انتخاب کن:", reply_markup=kb)
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
