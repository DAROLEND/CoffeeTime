"""
LiqPay signing/verification helper, plus a shared verify+status-mapping
helper used by both the server-to-server webhook and the browser payment
redirect target, so there's exactly one place that decides what a LiqPay
status string means.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json


class LiqPay:
    def __init__(self, public_key: str, private_key: str):
        self.public_key = public_key
        self.private_key = private_key

    def cnb_data(self, params: dict) -> str:
        params = dict(params)
        params["public_key"] = self.public_key
        params.setdefault("version", 3)
        params.setdefault("currency", "UAH")
        # ensure_ascii=True (the default) \uXXXX-escapes non-ASCII — the
        # exact byte content of this JSON is what gets signed, so it must
        # be produced consistently for the signature to verify.
        raw = json.dumps(params)
        return base64.b64encode(raw.encode("utf-8")).decode("ascii")

    def str_to_sign(self, s: str) -> str:
        return base64.b64encode(hashlib.sha1(s.encode("utf-8")).digest()).decode("ascii")

    def cnb_signature(self, data: str) -> str:
        return self.str_to_sign(self.private_key + data + self.private_key)

    def decode_data_str(self, data: str) -> dict:
        return json.loads(base64.b64decode(data))

    def verify_signature(self, data: str, signature: str) -> bool:
        return hmac.compare_digest(self.cnb_signature(data), signature)


def map_liqpay_status(status: str) -> tuple[str, str | None]:
    """Returns (payment_status, order_status_or_None)."""
    if status in ("success", "sandbox"):
        return "paid", "new"
    if status in ("failure", "error"):
        return "failed", "cancelled"
    if status == "reversed":
        return "failed", None
    return "pending", None


def verify_and_decode(liqpay: LiqPay, data: str, signature: str) -> dict | None:
    """Verify signature and extract {order_id (int), payment_status,
    order_status} from a LiqPay POST payload. Returns None if the
    signature doesn't verify or the order_id can't be parsed."""
    if not liqpay.verify_signature(data, signature):
        return None
    resp = liqpay.decode_data_str(data)
    liqpay_order_id = resp.get("order_id", "") or ""
    if not liqpay_order_id.startswith("coffeetime_"):
        return None
    try:
        order_id = int(liqpay_order_id.removeprefix("coffeetime_"))
    except ValueError:
        return None
    if order_id <= 0:
        return None
    payment_status, order_status = map_liqpay_status(resp.get("status", ""))
    return {"order_id": order_id, "payment_status": payment_status, "order_status": order_status}
