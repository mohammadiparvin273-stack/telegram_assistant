import google.generativeai as genai
import config

genai.configure(api_key=config.GEMINI_API_KEY)

# اگر این مدل در دسترس نبود، اسم مدل رایگان فعلی را از Google AI Studio بردار
MODEL_NAME = "gemini-2.5-flash-lite"

SYSTEM_PROMPT_TEMPLATE = """تو دستیار شخصی و منشی حرفه‌ای کاربر هستی. اسمت «دستیار» است.

اطلاعات کاربر:
- نام: {name}
- تخصص/حرفه: {specialty}

نکات و حافظه‌ای که کاربر قبلاً درباره خودش یا کارهایش گفته:
{memories}

وظیفه‌ات:
۱. با لحنی محترمانه، حرفه‌ای، گرم و فارسی روان پاسخ بده.
۲. در حوزه تخصص کاربر، دانش، نکات به‌روز و راهنمایی عملی برای رشد و ارتقای مهارتش بده.
۳. اگر کاربر درخواست یادآوری، رویداد یا برنامه‌ریزی داشت ولی خودکار پردازش نشد، بهش بگو از دستورات /remind یا /event استفاده کند.
۴. پاسخ‌ها را کوتاه و کاربردی نگه دار مگر کاربر توضیح مفصل بخواهد.
"""


def build_system_prompt(name, specialty, memories):
    mem_text = "\n".join(f"- {m}" for m in memories) if memories else "(هنوز چیزی ثبت نشده)"
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=name or "کاربر",
        specialty=specialty or "نامشخص",
        memories=mem_text,
    )


def ask_gemini(system_prompt, user_message):
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=system_prompt)
    try:
        response = model.generate_content(user_message)
        return (response.text or "").strip() or "متوجه نشدم، می‌شه دوباره بگی؟"
    except Exception as e:
        return f"⚠️ خطا در ارتباط با هوش مصنوعی: {e}"


def daily_tip(specialty):
    """یک نکته کوتاه آموزشی/بیزینسی مرتبط با تخصص کاربر برای بریف صبحگاهی."""
    prompt = (
        f"یک نکته کوتاه، عملی و الهام‌بخش (حداکثر ۲ جمله، به فارسی) درباره یادگیری یا رشد "
        f"در حوزه «{specialty or 'رشد فردی'}» بده. فقط خود نکته رو بنویس، بدون مقدمه."
    )
    model = genai.GenerativeModel(MODEL_NAME)
    try:
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception:
        return ""


def weekly_report(name, specialty, stats_text):
    """گزارش هفتگی کوچی درباره پیشرفت کاربر بر اساس آمار کارها/اهداف/یادداشت‌های هفته اخیر."""
    prompt = f"""تو یک مربی حرفه‌ای (کوچ) در حوزه «{specialty or 'رشد فردی و بیزینس'}» برای {name or 'کاربر'} هستی.
بر اساس اطلاعات هفته اخیر زیر، یک گزارش هفتگی کوتاه (حداکثر ۸-۱۰ خط) به فارسی بنویس شامل:
۱. جمع‌بندی پیشرفت هفته
۲. یک یا دو نقطه قوت
۳. یک یا دو پیشنهاد مشخص برای هفته بعد

اطلاعات هفته:
{stats_text}
"""
    model = genai.GenerativeModel(MODEL_NAME)
    try:
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as e:
        return f"⚠️ خطا در تولید گزارش هفتگی: {e}"


def generate_roadmap(name, specialty, goals_text, memories_text):
    """نقشه راه شخصی‌سازی‌شده یادگیری/بیزینس بر اساس تخصص، اهداف و حافظه کاربر."""
    prompt = f"""تو یک مربی حرفه‌ای در حوزه «{specialty or 'نامشخص'}» برای {name or 'کاربر'} هستی.
با توجه به اهداف و نکاتی که کاربر تا الان گفته، یک نقشه راه عملی (roadmap) کوتاه و مرحله‌به‌مرحله
(حداکثر ۶-۸ مرحله) به فارسی بنویس تا در مسیر یادگیری/رشد این تخصص و اهدافش قدم برداره.
هر مرحله باید یک اقدام مشخص و قابل انجام باشد، نه توصیه کلی.

اهداف کاربر:
{goals_text or '(هنوز هدفی ثبت نشده)'}

نکات و زمینه قبلی کاربر:
{memories_text or '(اطلاعات بیشتری موجود نیست)'}
"""
    model = genai.GenerativeModel(MODEL_NAME)
    try:
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as e:
        return f"⚠️ خطا در تولید نقشه راه: {e}"


def summarize_memories(memories_text):
    """چند نکته/جمله پراکنده را به یک خلاصه فشرده تبدیل می‌کند تا حافظه متورم نشود."""
    prompt = (
        "متن زیر شامل چند نکته پراکنده‌ای است که کاربر قبلاً گفته. آن‌ها را در حداکثر ۵ نکته "
        "کوتاه و خلاصه (bullet) به فارسی جمع‌بندی کن، فقط مهم‌ترین‌ها را نگه دار:\n\n"
        f"{memories_text}"
    )
    model = genai.GenerativeModel(MODEL_NAME)
    try:
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception:
        return memories_text[:1000]
