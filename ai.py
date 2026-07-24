import google.generativeai as genai
import config

genai.configure(api_key=config.GEMINI_API_KEY)

# لیست مدل‌های جایگزین به ترتیب اولویت (چون گوگل مدل‌ها رو مرتب retire می‌کنه).
# اگه GEMINI_MODEL توی تنظیمات ست شده باشه، اول اون امتحان می‌شه.
FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]

_working_model_name = None  # کش می‌کنیم که دیگه هر بار همه رو تست نکنیم


def _candidate_models():
    if config.GEMINI_MODEL:
        return [config.GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != config.GEMINI_MODEL]
    return FALLBACK_MODELS


def _get_working_model_name(force_recheck=False):
    global _working_model_name
    if _working_model_name and not force_recheck:
        return _working_model_name
    for name in _candidate_models():
        _working_model_name = name
        return name
    return _candidate_models()[0]


def _generate_with_fallback(build_prompt_fn):
    """build_prompt_fn(model) -> response.text ; اگه مدل جواب نداد (404)، مدل بعدی رو امتحان می‌کنه."""
    candidates = _candidate_models()
    last_error = None
    for name in candidates:
        try:
            model = genai.GenerativeModel(name)
            text = build_prompt_fn(model)
            global _working_model_name
            _working_model_name = name
            return text
        except Exception as e:
            last_error = e
            if "404" in str(e) or "not found" in str(e).lower() or "no longer available" in str(e).lower():
                continue
            else:
                break
    raise last_error


SYSTEM_PROMPT_TEMPLATE = """تو دستیار شخصی و منشی حرفه‌ای کاربر هستی. اسمت «دستیار» است.

اطلاعات کاربر:
- نام: {name}
- تخصص/حرفه: {specialty}

حافظه و نکات مهمی که کاربر قبلاً درباره خودش یا کارهایش گفته:
{memories}

وظیفه‌ات:
۱. با لحنی محترمانه، حرفه‌ای، گرم و فارسی روان پاسخ بده.
۲. در حوزه تخصص کاربر، دانش، نکات به‌روز و راهنمایی عملی برای رشد و ارتقای مهارتش بده.
۳. اگر کاربر درخواست یادآوری، رویداد یا برنامه‌ریزی داشت ولی خودکار پردازش نشد، بهش بگو از دستورات /remind یا /event استفاده کند.
۴. همیشه تاریخ‌ها رو به صورت شمسی بیان کن، نه میلادی.
۵. پاسخ‌ها را کوتاه و کاربردی نگه دار مگر کاربر توضیح مفصل بخواهد.
"""


def build_system_prompt(name, specialty, memories):
    mem_text = "\n".join(f"- {m}" for m in memories) if memories else "(هنوز چیزی ثبت نشده)"
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=name or "کاربر",
        specialty=specialty or "نامشخص",
        memories=mem_text,
    )


def ask_gemini(system_prompt, user_message):
    def run(model):
        m = genai.GenerativeModel(model.model_name, system_instruction=system_prompt)
        r = m.generate_content(user_message)
        return (r.text or "").strip() or "متوجه نشدم، می‌شه دوباره بگی؟"
    try:
        return _generate_with_fallback(run)
    except Exception as e:
        return f"⚠️ خطا در ارتباط با هوش مصنوعی: {e}"


def daily_tip(specialty):
    prompt = (
        f"یک نکته کوتاه، عملی و الهام‌بخش (حداکثر ۲ جمله، به فارسی) درباره یادگیری یا رشد "
        f"در حوزه «{specialty or 'رشد فردی'}» بده. فقط خود نکته رو بنویس، بدون مقدمه."
    )
    try:
        return _generate_with_fallback(lambda model: (model.generate_content(prompt).text or "").strip())
    except Exception:
        return ""


def weekly_report(name, specialty, stats_text):
    prompt = f"""تو یک مربی حرفه‌ای (کوچ) در حوزه «{specialty or 'رشد فردی و بیزینس'}» برای {name or 'کاربر'} هستی.
بر اساس اطلاعات هفته اخیر زیر، یک گزارش هفتگی کوتاه (حداکثر ۸-۱۰ خط) به فارسی بنویس شامل:
۱. جمع‌بندی پیشرفت هفته
۲. یک یا دو نقطه قوت
۳. یک یا دو پیشنهاد مشخص برای هفته بعد

اطلاعات هفته:
{stats_text}
"""
    try:
        return _generate_with_fallback(lambda model: (model.generate_content(prompt).text or "").strip())
    except Exception as e:
        return f"⚠️ خطا در تولید گزارش هفتگی: {e}"


def generate_roadmap(name, specialty, goals_text, memories_text):
    prompt = f"""تو یک مربی حرفه‌ای در حوزه «{specialty or 'نامشخص'}» برای {name or 'کاربر'} هستی.
با توجه به اهداف و نکاتی که کاربر تا الان گفته، یک نقشه راه عملی (roadmap) کوتاه و مرحله‌به‌مرحله
(حداکثر ۶-۸ مرحله) به فارسی بنویس تا در مسیر یادگیری/رشد این تخصص و اهدافش قدم برداره.
هر مرحله باید یک اقدام مشخص و قابل انجام باشد، نه توصیه کلی.

اهداف کاربر:
{goals_text or '(هنوز هدفی ثبت نشده)'}

نکات و زمینه قبلی کاربر:
{memories_text or '(اطلاعات بیشتری موجود نیست)'}
"""
    try:
        return _generate_with_fallback(lambda model: (model.generate_content(prompt).text or "").strip())
    except Exception as e:
        return f"⚠️ خطا در تولید نقشه راه: {e}"


def summarize_memories(memories_text):
    prompt = (
        "متن زیر شامل چند نکته پراکنده‌ای است که کاربر قبلاً گفته. آن‌ها را در حداکثر ۵ نکته "
        "کوتاه و خلاصه (bullet) به فارسی جمع‌بندی کن، فقط مهم‌ترین‌ها را نگه دار:\n\n"
        f"{memories_text}"
    )
    try:
        return _generate_with_fallback(lambda model: (model.generate_content(prompt).text or "").strip())
    except Exception:
        return memories_text[:1000]
