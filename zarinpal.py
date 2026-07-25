import requests
import config


def _base_url():
    return "https://sandbox.zarinpal.com" if config.ZARINPAL_SANDBOX else "https://payment.zarinpal.com"


def request_payment(amount_toman, description, callback_url, mobile=None):
    """یه لینک پرداخت می‌سازه. خروجی: {"ok": True, "authority": ..., "url": ...} یا {"ok": False, "error": ...}"""
    url = f"{_base_url()}/pg/v4/payment/request.json"
    payload = {
        "merchant_id": config.ZARINPAL_MERCHANT_ID,
        "amount": amount_toman,
        "description": description,
        "callback_url": callback_url,
    }
    if mobile:
        payload["metadata"] = {"mobile": mobile}
    try:
        r = requests.post(url, json=payload, timeout=15)
        data = r.json()
        d = data.get("data") or {}
        if d.get("code") == 100:
            authority = d["authority"]
            pay_url = f"{_base_url()}/pg/StartPay/{authority}"
            return {"ok": True, "authority": authority, "url": pay_url}
        return {"ok": False, "error": data.get("errors") or d}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def verify_payment(amount_toman, authority):
    """پرداخت رو تأیید می‌کنه. خروجی: {"ok": True, "ref_id": ...} یا {"ok": False, "error": ...}"""
    url = f"{_base_url()}/pg/v4/payment/verify.json"
    payload = {
        "merchant_id": config.ZARINPAL_MERCHANT_ID,
        "amount": amount_toman,
        "authority": authority,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        data = r.json()
        d = data.get("data") or {}
        # کد ۱۰۰ = تأیید موفق، ۱۰۱ = این پرداخت قبلاً تأیید شده
        if d.get("code") in (100, 101):
            return {"ok": True, "ref_id": d.get("ref_id")}
        return {"ok": False, "error": data.get("errors") or d}
    except Exception as e:
        return {"ok": False, "error": str(e)}
