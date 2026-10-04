"""Normalize the single-line Invoice Fields template by field key, never row number."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from .errors import AppError
from .parsers import money

MAPPING = {
    "invoice_number": "invoice_number",
    "invoice_date": "invoice_date",
    "ship_date": "ship_date",
    "payment_due_date": "due_date",
    "payment_term_days": "payment_term_days",
    "currency": "currency",
    "buyer_name": "buyer.legal_name",
    "buyer_address": "buyer.address",
    "buyer_tax_id": "buyer.tax_id",
    "buyer_country": "buyer.country",
    "exporter_name": "seller.legal_name",
    "exporter_address": "seller.address",
    "exporter_tax_id": "seller.tax_id",
    "exporter_country": "seller.country",
    "quantity": "line_items.0.quantity",
    "unit_price": "line_items.0.unit_price",
    "line_total": "line_items.0.line_total",
    "product_sku": "line_items.0.sku",
    "unit_of_measure": "line_items.0.unit",
    "subtotal": "subtotal",
    "invoice_total": "total",
    "insurance": "charges.insurance",
    "freight": "charges.freight",
    "packing": "charges.packing",
    "handling": "charges.handling",
    "other_charges": "charges.other",
    "parties_related": "declared_related",
}
MONEY_KEYS = {
    "unit_price",
    "line_total",
    "subtotal",
    "invoice_total",
    "insurance",
    "freight",
    "packing",
    "handling",
    "other_charges",
}


def normalize(key, raw):
    value = str(raw).strip()
    if not value:
        raise ValueError("missing value")
    if key in MONEY_KEYS:
        return money(value)
    if key in {"quantity", "payment_term_days"}:
        numeric = Decimal(value)
        if (
            not numeric.is_finite()
            or numeric != int(numeric)
            or numeric < 0
            or (key == "quantity" and numeric == 0)
        ):
            raise ValueError("invalid integer")
        return int(numeric)
    if key in {"invoice_date", "ship_date", "payment_due_date"}:
        return date.fromisoformat(value.split(" ")[0].split("T")[0]).isoformat()
    if key == "parties_related":
        if value.casefold() not in {"true", "false", "yes", "no", "1", "0"}:
            raise ValueError("invalid boolean")
        return value.casefold() in {"true", "yes", "1"}
    if key == "currency":
        if not re.fullmatch(r"[A-Za-z]{3}", value):
            raise ValueError("invalid currency")
        return value.upper()
    return " ".join(value.split())


def field_sheet(content, source_id, invoice):
    if content.get("type") != "xlsx":
        return None
    rows = {}
    for cell in content["cells"]:
        if cell["sheet"] == "Invoice Fields":
            match = re.fullmatch(r"([A-Z]+)(\d+)", cell["cell"])
            rows.setdefault(int(match[2]), {})[match[1]] = cell["value"]
    if not rows:
        return None
    header = next(
        (
            r
            for r, v in sorted(rows.items())
            if [v.get(c) for c in ["A", "B", "C", "D"]] == ["Section", "Field", "Value", "Unit"]
        ),
        None,
    )
    if header is None:
        raise AppError("INVALID_FIELD_SHEET", "Invoice Fields 缺少 Section / Field / Value / Unit 表头")
    fields, errors = {}, []
    for row, cells in sorted(rows.items()):
        if row <= header or not cells.get("B"):
            continue
        key = str(cells["B"]).strip()
        if key in fields:
            errors.append({"field": key, "cell": f"B{row}", "error": "duplicate_field"})
            continue
        raw = cells.get("C")
        entry = {
            "field": key,
            "sheet": "Invoice Fields",
            "cell": f"C{row}",
            "source_id": source_id,
            "raw_value": raw,
            "unit": cells.get("D"),
            "target": MAPPING.get(key),
            "normalized_value": None,
        }
        fields[key] = entry
        if key in MAPPING:
            try:
                if raw is None:
                    raise ValueError("missing value")
                entry["normalized_value"] = normalize(key, raw)
            except (AppError, ValueError, InvalidOperation, OverflowError):
                errors.append({"field": key, "cell": f"C{row}", "error": "invalid_or_missing_value"})
        else:
            entry["normalized_value"] = raw
    for key in MAPPING.keys() - fields.keys():
        errors.append({"field": key, "error": "missing_required_field"})
    if errors:
        raise AppError("INVALID_FIELD_SHEET", "字段表存在重复、缺失或类型错误", details={"fields": errors})
    differences = []
    for key, path in MAPPING.items():
        value = invoice
        for part in path.split("."):
            value = value[int(part)] if isinstance(value, list) else value[part]
        expected = normalize(key, value)
        if fields[key]["normalized_value"] != expected:
            differences.append(
                {
                    "field": key,
                    "target": path,
                    "pdf_value": value,
                    "sheet_value": fields[key]["normalized_value"],
                    "sheet": "Invoice Fields",
                    "cell": fields[key]["cell"],
                    "source_ids": [invoice["source_refs"][0]["source_id"], source_id],
                }
            )
    values = {k: f["normalized_value"] for k, f in fields.items()}
    checks = arithmetic_checks(values, source_id)
    return {
        "template": "single_line_invoice_fields_v1",
        "fields": fields,
        "differences": differences,
        "checks": checks,
    }


def arithmetic_checks(v, source_id):
    def amount(x):
        return str(x.quantize(Decimal(".01")))

    calculated_line = Decimal(v["quantity"]) * Decimal(v["unit_price"])
    calculated_total = Decimal(v["subtotal"]) + sum(
        Decimal(v[k]) for k in ["insurance", "freight", "packing", "handling", "other_charges"]
    )
    days = (date.fromisoformat(v["payment_due_date"]) - date.fromisoformat(v["invoice_date"])).days
    return [
        {
            "code": "quantity_times_unit_price",
            "expected": amount(calculated_line),
            "actual": v["line_total"],
            "passed": calculated_line == Decimal(v["line_total"]),
            "source_id": source_id,
        },
        {
            "code": "line_items_sum",
            "expected": v["line_total"],
            "actual": v["subtotal"],
            "passed": v["line_total"] == v["subtotal"],
            "source_id": source_id,
        },
        {
            "code": "subtotal_plus_charges",
            "expected": amount(calculated_total),
            "actual": v["invoice_total"],
            "passed": calculated_total == Decimal(v["invoice_total"]),
            "source_id": source_id,
        },
        {
            "code": "payment_term_days",
            "expected": v["payment_term_days"],
            "actual": days,
            "passed": days == v["payment_term_days"],
            "source_id": source_id,
        },
    ]


def invoice_checks(invoice):
    values = {}
    for key, path in MAPPING.items():
        value = invoice
        for part in path.split("."):
            value = value[int(part)] if isinstance(value, list) else value[part]
        values[key] = normalize(key, value)
    return arithmetic_checks(values, invoice["source_refs"][0]["source_id"])
