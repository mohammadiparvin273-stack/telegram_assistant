import logging
from aiohttp import web
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
import database as db
from scheduler import setup_scheduler
import handlers
import zarinpal as zarinpal_module

logging.basicConfig(level=logging.INFO)

# این دستورها همیشه آزادن، حتی وقتی اشتراک/دوره‌ی آزمایشی تموم شده
FREE_COMMANDS = {"start", "help", "subscribe", "menu", "admin"}


def gated(handler):
    """قبل از اجرای یه دستور پولی، وضعیت اشتراک/دوره‌ی آزمایشی رو چک می‌کنه."""
    async def wrapper(update, context):
        chat_id = update.effective_chat.id
        if not handlers.is_access_allowed(chat_id):
            user = db.get_user(chat_id)
            if not user:
                await update.message.reply_text("اول با /start شروع کن.")
                return
            await handlers._send_paywall(update.message, chat_id)
            return
        return await handler(update, context)
    return wrapper


async def _set_minimal_commands(bot):
    # فقط /start توی منوی "/" تلگرام نشون داده می‌شه؛ بقیه‌ی کارها با دکمه انجام می‌شه
    await bot.set_my_commands([BotCommand("start", "شروع / بازگشت به منو")])


async def _post_init(application):
    # فقط توی حالت polling استفاده می‌شه (حالت webhook خودش صریح scheduler رو استارت می‌کنه)
    setup_scheduler(application.bot)
    await _set_minimal_commands(application.bot)


def build_application():
    application = Application.builder().token(config.BOT_TOKEN).post_init(_post_init).build()

    command_map = {
        "start": handlers.start,
        "menu": handlers.menu_cmd,
        "help": handlers.help_cmd,
        "subscribe": handlers.subscribe_cmd,
        "admin": handlers.admin_cmd,
        "remind": handlers.remind_cmd,
        "reminders": handlers.reminders_cmd,
        "delreminder": handlers.delreminder_cmd,
        "event": handlers.event_cmd,
        "events": handlers.events_cmd,
        "delevent": handlers.delevent_cmd,
        "task": handlers.task_cmd,
        "tasks": handlers.tasks_cmd,
        "done": handlers.done_cmd,
        "deltask": handlers.deltask_cmd,
        "goal": handlers.goal_cmd,
        "goals": handlers.goals_cmd,
        "delgoal": handlers.delgoal_cmd,
        "note": handlers.note_cmd,
        "notes": handlers.notes_cmd,
        "forget": handlers.forget_cmd,
        "roadmap": handlers.roadmap_cmd,
        "weekly": handlers.weekly_cmd,
        "dailytime": handlers.dailytime_cmd,
        "weeklyday": handlers.weeklyday_cmd,
    }
    for name, func in command_map.items():
        handler_func = func if name in FREE_COMMANDS else gated(func)
        application.add_handler(CommandHandler(name, handler_func))

    application.add_handler(CallbackQueryHandler(handlers.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.free_text))
    return application


# ==================== مسیر webhook تلگرام + بازگشت از زرین‌پال (سرور سفارشی) ====================
async def telegram_webhook(request):
    application = request.app["bot_app"]
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response(text="OK")


PAYMENT_FAIL_HTML = "<html><body style='font-family:sans-serif;text-align:center;padding-top:60px'>" \
                     "<h2>پرداخت ناموفق بود ❌</h2><p>برگرد به تلگرام و دوباره تلاش کن.</p></body></html>"
PAYMENT_OK_HTML = "<html><body style='font-family:sans-serif;text-align:center;padding-top:60px'>" \
                   "<h2>پرداخت موفق بود 🎉</h2><p>برگرد به تلگرام، اشتراکت فعال شد.</p></body></html>"
PAYMENT_DUP_HTML = "<html><body style='font-family:sans-serif;text-align:center;padding-top:60px'>" \
                    "<h2>این پرداخت قبلاً تأیید شده ✅</h2></body></html>"


async def zarinpal_callback(request):
    application = request.app["bot_app"]
    authority = request.query.get("Authority")
    status = request.query.get("Status")

    if status != "OK" or not authority:
        return web.Response(text=PAYMENT_FAIL_HTML, content_type="text/html")

    payment = db.get_payment(authority)
    if not payment:
        return web.Response(text=PAYMENT_FAIL_HTML, content_type="text/html")

    chat_id, amount, pay_status = payment
    if pay_status == "verified":
        return web.Response(text=PAYMENT_DUP_HTML, content_type="text/html")

    result = zarinpal_module.verify_payment(amount, authority)
    if result["ok"]:
        db.mark_payment_status(authority, "verified")
        db.extend_subscription(chat_id, days=config.SUBSCRIPTION_DAYS)
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=f"🎉 پرداخت با موفقیت انجام شد! اشتراکت {config.SUBSCRIPTION_DAYS} روز تمدید شد.",
            )
        except Exception:
            pass
        return web.Response(text=PAYMENT_OK_HTML, content_type="text/html")

    db.mark_payment_status(authority, "failed")
    return web.Response(text=PAYMENT_FAIL_HTML, content_type="text/html")


async def health_check(request):
    return web.Response(text="OK")


async def on_startup(app):
    application = app["bot_app"]
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}")
    setup_scheduler(application.bot)
    await _set_minimal_commands(application.bot)


async def on_cleanup(app):
    application = app["bot_app"]
    await application.stop()
    await application.shutdown()


def run_with_webhook_server(application):
    web_app = web.Application()
    web_app["bot_app"] = application
    web_app.router.add_post(f"/{config.BOT_TOKEN}", telegram_webhook)
    web_app.router.add_get("/zarinpal/callback", zarinpal_callback)
    web_app.router.add_get("/", health_check)
    web_app.on_startup.append(on_startup)
    web_app.on_cleanup.append(on_cleanup)
    web.run_app(web_app, host="0.0.0.0", port=config.PORT)


def main():
    db.init_db()
    application = build_application()

    if config.WEBHOOK_URL:
        # حالت webhook: مناسب برای هاست رایگان مثل Render (لازمه چون زرین‌پال هم به آدرس عمومی نیاز داره)
        run_with_webhook_server(application)
    else:
        # حالت polling: فقط برای اجرای محلی/تست؛ پرداخت زرین‌پال در این حالت کار نمی‌کنه
        application.run_polling()


if __name__ == "__main__":
    main()
