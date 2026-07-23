import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
import database as db
from scheduler import setup_scheduler
import handlers

logging.basicConfig(level=logging.INFO)


async def post_init(app: Application):
    setup_scheduler(app.bot)


def main():
    db.init_db()

    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("menu", handlers.menu_cmd))
    app.add_handler(CommandHandler("help", handlers.help_cmd))
    app.add_handler(CommandHandler("remind", handlers.remind_cmd))
    app.add_handler(CommandHandler("reminders", handlers.reminders_cmd))
    app.add_handler(CommandHandler("delreminder", handlers.delreminder_cmd))
    app.add_handler(CommandHandler("event", handlers.event_cmd))
    app.add_handler(CommandHandler("events", handlers.events_cmd))
    app.add_handler(CommandHandler("delevent", handlers.delevent_cmd))
    app.add_handler(CommandHandler("task", handlers.task_cmd))
    app.add_handler(CommandHandler("tasks", handlers.tasks_cmd))
    app.add_handler(CommandHandler("done", handlers.done_cmd))
    app.add_handler(CommandHandler("deltask", handlers.deltask_cmd))
    app.add_handler(CommandHandler("goal", handlers.goal_cmd))
    app.add_handler(CommandHandler("goals", handlers.goals_cmd))
    app.add_handler(CommandHandler("delgoal", handlers.delgoal_cmd))
    app.add_handler(CommandHandler("note", handlers.note_cmd))
    app.add_handler(CommandHandler("notes", handlers.notes_cmd))
    app.add_handler(CommandHandler("forget", handlers.forget_cmd))
    app.add_handler(CommandHandler("roadmap", handlers.roadmap_cmd))
    app.add_handler(CommandHandler("weekly", handlers.weekly_cmd))
    app.add_handler(CommandHandler("dailytime", handlers.dailytime_cmd))
    app.add_handler(CommandHandler("weeklyday", handlers.weeklyday_cmd))
    app.add_handler(CallbackQueryHandler(handlers.handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.free_text))

    if config.WEBHOOK_URL:
        # حالت webhook: مناسب برای هاست رایگان مثل Render (چون باید روی PORT گوش بده)
        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}",
        )
    else:
        # حالت polling: مناسب برای اجرا روی سیستم شخصی
        app.run_polling()


if __name__ == "__main__":
    main()
