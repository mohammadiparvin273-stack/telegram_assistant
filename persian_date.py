import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import jdatetime
import dateparser
from dateparser.search import search_dates

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

NUMERIC_DATE_RE = re.compile(
    r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})(?:[\sT,،]+(\d{1,2}):(\d{2}))?"
)

DAY_OFFSETS = {
    "پس‌فردا": 2,
    "پس فردا": 2,
    "فردا": 1,
    "امروز": 0,
    "دیروز": -1,
    "پریروز": -2,
}

TIME_PHRASE_RE = re.compile(
    r"ساعت\s*(\d{1,2})(?:[:.٫](\d{2}))?\s*(?:دقیقه)?\s*(صبح|ظهر|بعدازظهر|عصر|شب)?"
)


def now_tehran() -> datetime:
    """ساعت الان رو به وقت تهران برمی‌گردونه (بدون تایم‌زون، برای مقایسه‌ی راحت با بقیه‌ی کد)."""
    return datetime.now(TEHRAN_TZ).replace(tzinfo=None)


def normalize_digits(text: str) -> str:
    """اعداد فارسی رو به انگلیسی تبدیل می‌کنه تا الگوهای regex درست کار کنن."""
    return text.translate(FA_DIGITS)


def to_jalali_display(iso_str: str, with_time: bool = True) -> str:
    """یه رشته‌ی تاریخ ذخیره‌شده در دیتابیس (ISO، به وقت تهران) رو به نمایش شمسی تبدیل می‌کنه."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return iso_str
    jd = jdatetime.datetime.fromgregorian(datetime=dt)
    if with_time:
        return jd.strftime("%Y/%m/%d - %H:%M")
    return jd.strftime("%Y/%m/%d")


def _parse_relative_day_and_time(text: str):
    """الگوی رایج فارسی: «امروز/فردا/پس‌فردا ساعت HH:MM». اگه پیدا بشه، دقیق و مطمئنه."""
    now = now_tehran()
    day_offset = None
    day_span = None
    for word, offset in DAY_OFFSETS.items():
        idx = text.find(word)
        if idx != -1:
            day_offset = offset
            day_span = (idx, idx + len(word))
            break

    tm = TIME_PHRASE_RE.search(text)
    if day_offset is None and not tm:
        return None, text
    if day_offset is None and tm and ("شنبه" in text or "جمعه" in text):
        # اسم روز هفته (سه‌شنبه، جمعه و...) رو بهتره پارسر عمومی‌تر (dateparser) حل کنه
        return None, text

    base_date = (now + timedelta(days=day_offset if day_offset is not None else 0)).date()
    hour, minute = 9, 0
    if tm:
        hour = int(tm.group(1))
        minute = int(tm.group(2)) if tm.group(2) else 0
        period = tm.group(3)
        if period in ("عصر", "شب", "بعدازظهر") and hour < 12:
            hour += 12
        if hour > 23:
            hour = 23

    dt = datetime(base_date.year, base_date.month, base_date.day, hour, minute)

    spans = []
    if day_span:
        spans.append(day_span)
    if tm:
        spans.append((tm.start(), tm.end()))
    spans.sort(key=lambda s: s[0], reverse=True)
    remaining = text
    for start, end in spans:
        remaining = remaining[:start] + " " + remaining[end:]
    remaining = re.sub(r"\s+", " ", remaining).strip(" -|:\n\t")

    return dt, remaining


def extract_datetime_and_text(raw_text: str, prefer_future: bool = True):
    """
    از یه متن آزاد (شمسی، میلادی، یا عبارت طبیعی فارسی) یه datetime (به وقت تهران) استخراج می‌کنه
    و بقیه‌ی متن رو به‌عنوان عنوان/توضیح برمی‌گردونه.
    خروجی: (datetime یا None, متن باقی‌مانده, روش تشخیص: "strong" | "fuzzy" | None)
    """
    text = normalize_digits(raw_text.strip())

    # ۱) الگوی رایج و مطمئن فارسی: امروز/فردا/پس‌فردا + ساعت
    dt, remaining = _parse_relative_day_and_time(text)
    if dt:
        return dt, remaining, "strong"

    # ۲) الگوی عددی صریح: 1405/05/10 14:00  یا  2026-08-01 09:00
    m = NUMERIC_DATE_RE.search(text)
    if m:
        y, mo, d, hh, mm = m.groups()
        y, mo, d = int(y), int(mo), int(d)
        hour = int(hh) if hh else 9
        minute = int(mm) if mm else 0
        try:
            if y > 1500:  # میلادیه
                dt = datetime(y, mo, d, hour, minute)
            else:  # شمسیه
                gd = jdatetime.date(y, mo, d).togregorian()
                dt = datetime(gd.year, gd.month, gd.day, hour, minute)
            remaining = (text[: m.start()] + " " + text[m.end():]).strip(" -|:\n\t")
            return dt, remaining, "strong"
        except ValueError:
            pass

    # ۳) عبارات طبیعی فارسی مبهم‌تر: سه‌شنبه بعد، هفته‌ی دیگه و ...
    settings = {"PREFER_DATES_FROM": "future", "RELATIVE_BASE": now_tehran()} if prefer_future else {
        "RELATIVE_BASE": now_tehran()
    }
    try:
        results = search_dates(text, languages=["fa"], settings=settings)
    except Exception:
        results = None
    if results:
        matched_text, dt = results[0]
        remaining = text.replace(matched_text, "").strip(" -|:\n\t")
        return dt, remaining, "fuzzy"

    return None, text, None


def parse_flexible_date_only(raw_text: str):
    """برای مواردی مثل ددلاین هدف که فقط تاریخ (بدون ساعت) لازمه. خروجی: date یا None."""
    if not raw_text or not raw_text.strip():
        return None
    dt, _, _ = extract_datetime_and_text(raw_text, prefer_future=True)
    return dt.date() if dt else None
