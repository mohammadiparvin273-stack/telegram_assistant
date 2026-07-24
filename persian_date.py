import re
from datetime import datetime
import jdatetime
import dateparser
from dateparser.search import search_dates

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

NUMERIC_DATE_RE = re.compile(
    r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})(?:[\sT,،]+(\d{1,2}):(\d{2}))?"
)


def normalize_digits(text: str) -> str:
    """اعداد فارسی رو به انگلیسی تبدیل می‌کنه تا الگوهای regex درست کار کنن."""
    return text.translate(FA_DIGITS)


def to_jalali_display(iso_str: str, with_time: bool = True) -> str:
    """یه رشته‌ی تاریخ گرگوری ذخیره‌شده در دیتابیس (ISO) رو به نمایش شمسی تبدیل می‌کنه."""
    if not iso_str:
        return ""
    try:
        clean = iso_str.replace("T", " ")
        dt = datetime.fromisoformat(clean) if " " in clean else datetime.fromisoformat(iso_str)
    except ValueError:
        try:
            dt = datetime.fromisoformat(iso_str)
        except ValueError:
            return iso_str
    jd = jdatetime.datetime.fromgregorian(datetime=dt)
    if with_time:
        return jd.strftime("%Y/%m/%d - %H:%M")
    return jd.strftime("%Y/%m/%d")


def extract_datetime_and_text(raw_text: str, prefer_future: bool = True):
    """
    از یه متن آزاد (شمسی، میلادی، یا عبارت طبیعی فارسی مثل «فردا ساعت ۹») یه datetime
    گرگوری استخراج می‌کنه و بقیه‌ی متن رو به‌عنوان عنوان/توضیح برمی‌گردونه.
    خروجی: (datetime یا None, متن باقی‌مانده)
    """
    text = normalize_digits(raw_text.strip())

    # ۱) الگوی عددی صریح: 1405/05/10 14:00  یا  2026-08-01 09:00
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
            return dt, remaining
        except ValueError:
            pass

    # ۲) عبارات طبیعی فارسی: فردا، پس‌فردا، سه‌شنبه بعد، ساعت ۵ عصر و ...
    settings = {"PREFER_DATES_FROM": "future"} if prefer_future else {}
    try:
        results = search_dates(text, languages=["fa"], settings=settings)
    except Exception:
        results = None
    if results:
        matched_text, dt = results[0]
        remaining = text.replace(matched_text, "").strip(" -|:\n\t")
        return dt, remaining

    return None, text


def parse_flexible_date_only(raw_text: str):
    """برای مواردی مثل ددلاین هدف که فقط تاریخ (بدون ساعت) لازمه. خروجی: date گرگوری یا None."""
    if not raw_text or not raw_text.strip():
        return None
    dt, _ = extract_datetime_and_text(raw_text, prefer_future=True)
    return dt.date() if dt else None
