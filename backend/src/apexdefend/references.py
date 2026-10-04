"""Select comparable local records before constructing the immutable AI snapshot."""

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation


def same_amount(value, expected):
    try:
        return Decimal(str(value)) == Decimal(expected)
    except InvalidOperation:
        return False


def select_reference(document, key, invoice, as_of):
    doc = deepcopy(document)
    data, kind = doc["data"], doc["kind"]
    if doc["as_of"] > as_of:
        return None
    cutoff = min(as_of, (date.fromisoformat(invoice["invoice_date"]) - timedelta(days=1)).isoformat())
    start = data.get("window_start", as_of[:4] + "-01-01")
    end = min(data.get("window_end", cutoff), cutoff)
    if kind == "entity_profile":
        side = "buyer" if key == "buyer_verification" else "seller"
        return (
            doc
            if data["entity_id"] == invoice[side]["entity_id"]
            and data.get("verification_status") == "demo_local_verified"
            else None
        )
    if kind == "trade_history":
        data["trades"] = [
            t
            for t in data["trades"]
            if t.get("seller_id") == invoice["seller"]["entity_id"]
            and t.get("buyer_id") == invoice["buyer"]["entity_id"]
            and t.get("currency") == invoice["currency"]
            and t.get("sku") in {item["sku"] for item in invoice["line_items"]}
            and t.get("status") == "completed"
            and start <= t.get("invoice_date", "") <= end
            and t.get("invoice_number") != invoice["invoice_number"]
        ]
        if not data["trades"]:
            return None
        data.update(window_start=start, window_end=end)
    elif kind == "market_benchmark":
        if not any(
            data.get("sku") == item["sku"] and data.get("unit") == item["unit"]
            for item in invoice["line_items"]
        ):
            return None
        if any(
            data.get(field) != invoice[field] for field in ["currency", "trade_terms", "delivery_location"]
        ):
            return None
        if (
            not data.get("valid_from", "0001-01-01")
            <= invoice["invoice_date"]
            <= data.get("valid_to", "9999-12-31")
        ):
            return None
    elif kind == "payment_history":
        data["records"] = [
            r
            for r in data["records"]
            if r.get("buyer_id") == invoice["buyer"]["entity_id"]
            and r.get("currency") == invoice["currency"]
            and start <= r.get("due_date", "") <= end
            and (not r.get("paid_date") or r["paid_date"] <= end)
        ]
        if not data["records"]:
            return None
        data.update(window_start=start, window_end=end)
    elif kind == "financing_registry":
        data["records"] = [
            r
            for r in data["records"]
            if r.get("status") in {"active", "outstanding"}
            and r.get("invoice_number") == invoice["invoice_number"]
            and r.get("seller_tax_id") == invoice["seller"]["tax_id"]
            and r.get("buyer_tax_id") == invoice["buyer"]["tax_id"]
            and r.get("currency") == invoice["currency"]
            and same_amount(r.get("total", r.get("amount")), invoice["total"])
            and r.get("invoice_date") == invoice["invoice_date"]
            and not r.get("settled_at")
            and (r.get("financed_at") or "0001-01-01")[:10] <= as_of
        ]
        if not data["records"] and not data.get("coverage_complete_for_demo"):
            return None
    return doc
