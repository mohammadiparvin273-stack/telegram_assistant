from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

MAIN_MENU_ROWS = [
    ["📌 یادآوری‌ها", "🗓 رویدادها"],
    ["✅ کارها", "🎯 اهداف"],
    ["🧠 حافظه", "📊 رشد و گزارش"],
    ["⚙️ تنظیمات", "❓ راهنما"],
]

MAIN_MENU_LABELS = {label for row in MAIN_MENU_ROWS for label in row}


def main_menu_keyboard():
    return ReplyKeyboardMarkup(MAIN_MENU_ROWS, resize_keyboard=True)


def category_menu(label: str):
    if label == "📌 یادآوری‌ها":
        rows = [
            [InlineKeyboardButton("➕ یادآوری جدید", callback_data="m:remind_add")],
            [InlineKeyboardButton("📋 لیست یادآوری‌ها", callback_data="m:remind_list")],
        ]
    elif label == "🗓 رویدادها":
        rows = [
            [InlineKeyboardButton("➕ رویداد جدید", callback_data="m:event_add")],
            [InlineKeyboardButton("📋 لیست رویدادها", callback_data="m:event_list")],
        ]
    elif label == "✅ کارها":
        rows = [
            [InlineKeyboardButton("➕ کار جدید", callback_data="m:task_add")],
            [InlineKeyboardButton("📋 لیست کارها", callback_data="m:task_list")],
        ]
    elif label == "🎯 اهداف":
        rows = [
            [InlineKeyboardButton("➕ هدف جدید", callback_data="m:goal_add")],
            [InlineKeyboardButton("📋 لیست اهداف", callback_data="m:goal_list")],
        ]
    elif label == "🧠 حافظه":
        rows = [
            [InlineKeyboardButton("➕ ثبت نکته", callback_data="m:note_add")],
            [InlineKeyboardButton("📋 دیدن حافظه", callback_data="m:note_list")],
            [InlineKeyboardButton("🗑 پاک کردن کل حافظه", callback_data="m:note_clear")],
        ]
    elif label == "📊 رشد و گزارش":
        rows = [
            [InlineKeyboardButton("🗺 نقشه راه شخصی", callback_data="m:roadmap")],
            [InlineKeyboardButton("📊 گزارش هفتگی فوری", callback_data="m:weekly")],
        ]
    elif label == "⚙️ تنظیمات":
        rows = [
            [InlineKeyboardButton("⏰ ساعت بریف روزانه", callback_data="m:set_dailytime")],
            [InlineKeyboardButton("📅 روز گزارش هفتگی", callback_data="m:set_weeklyday")],
        ]
    else:
        rows = []
    return InlineKeyboardMarkup(rows) if rows else None


def build_delete_keyboard(rows, prefix, id_index=0, label_index=1):
    """rows: هر آیتم باید id رو در id_index و متن نمایشی رو در label_index داشته باشه."""
    buttons = []
    for row in rows:
        item_id = row[id_index]
        label = str(row[label_index])[:22]
        buttons.append([InlineKeyboardButton(f"🗑 حذف: {label}", callback_data=f"{prefix}:{item_id}")])
    return InlineKeyboardMarkup(buttons)


def build_task_keyboard(rows):
    """rows: (id, title, priority, goal_id)"""
    buttons = []
    for t_id, title, priority, goal_id in rows:
        short = str(title)[:18]
        buttons.append([
            InlineKeyboardButton(f"✅ {short}", callback_data=f"task_done:{t_id}"),
            InlineKeyboardButton("🗑", callback_data=f"task_del:{t_id}"),
        ])
    return InlineKeyboardMarkup(buttons)
