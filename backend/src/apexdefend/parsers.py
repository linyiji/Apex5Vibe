import csv
import re
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from pypdf import PdfReader

from .errors import AppError

PARSER_VERSION = "acroform-v1"


def money(value):
    try:
        d = Decimal(str(value).strip())
        if not d.is_finite() or d < 0 or d != d.quantize(Decimal(".01")):
            raise InvalidOperation
        return str(d.quantize(Decimal(".01")))
    except (InvalidOperation, ValueError):
        raise AppError(
            "INVALID_AMOUNT", "Amounts must be non-negative with at most two decimal places."
        ) from None


def validate_upload(filename, data, maximum):
    if not data or len(data) > maximum:
        raise AppError("FILE_TOO_LARGE", "The file is empty or exceeds the 20 MiB limit.", 413)
    ext = Path(filename).suffix.lower()
    if ext not in [".pdf", ".xlsx", ".csv"]:
        raise AppError("UNSUPPORTED_PARSER", "Only PDF, XLSX, and CSV parsing is available.", 415)
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise AppError("INVALID_FILE_SIGNATURE", "The file does not have a valid PDF signature.", 415)
    if ext == ".xlsx":
        if not zipfile.is_zipfile(BytesIO(data)):
            raise AppError("INVALID_FILE_SIGNATURE", "The file does not have a valid XLSX signature.", 415)
        with zipfile.ZipFile(BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 50 * 1024 * 1024:
                raise AppError("FILE_TOO_LARGE", "The expanded XLSX exceeds the 50 MiB limit.", 413)
            if "[Content_Types].xml" not in archive.namelist():
                raise AppError("INVALID_FILE_SIGNATURE", "The file is not a valid Office document.", 415)
    return ext


def parse_invoice(data, evidence_id):
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise AppError("ENCRYPTED_PDF", "Upload an unencrypted invoice PDF.")
        if len(reader.pages) > 100:
            raise AppError("FILE_TOO_LARGE", "The PDF exceeds the 100-page limit.", 413)
        fields = {k: str(v.get("/V", "")).strip() for k, v in (reader.get_fields() or {}).items()}
        required = [
            "invoice no",
            "exporter tax id",
            "consignee tax id",
            "invoice total",
            "exporter co name_address",
            "consignee co name_address",
            "unit value 1",
            "no of units 1",
            "if other___purpose of shipment",
        ]
        if not all(fields.get(k) for k in required):
            raise AppError(
                "UNSUPPORTED_INVOICE_TEMPLATE",
                "Use the supplied commercial invoice PDF form. This invoice template is not supported.",
            )
        # /no is this template's selected appearance, not a general false boolean.
        if fields.get("Check Box3") != "/no" or fields.get("Radio Button1") not in ["/yes", "/no"]:
            raise AppError("INVOICE_REVIEW_REQUIRED", "The buyer or related-party checkboxes require review.")
        # Verify the selected widget appearance, not just the canonical field value.
        for field_name in ["Check Box3", "Radio Button1"]:
            selected = []
            for item in reader.pages[0].get("/Annots", []):
                widget = item.get_object()
                parent = widget.get("/Parent")
                parent = parent.get_object() if parent else {}
                if widget.get("/T", parent.get("/T")) == field_name:
                    state = str(widget.get("/AS", "/Off"))
                    if state != "/Off":
                        selected.append(state)
            if selected != [fields[field_name]]:
                raise AppError(
                    "INVOICE_REVIEW_REQUIRED", "The PDF form value conflicts with the visible checkbox state."
                )

        def party(prefix):
            parts = fields[f"{prefix} co name_address"].splitlines()
            return {
                "entity_id": "",
                "legal_name": parts[0],
                "address": "\n".join(parts[1:]),
                "tax_id": fields[f"{prefix} tax id"],
                "country": fields[f"{prefix} country"],
            }

        date_text = fields["if other___purpose of shipment"]
        invoice_date = re.search(r"Invoice date:\s*(\d{4}-\d{2}-\d{2})", date_text)
        due_date = re.search(r"Payment due date:\s*(\d{4}-\d{2}-\d{2})", date_text)
        terms = re.search(r"Net\s+(\d+)\s+days", fields.get("payment terms", ""))
        if not invoice_date or not due_date or not terms:
            raise AppError(
                "MISSING_INVOICE_DATES",
                "The invoice date, due date, or payment terms could not be determined.",
            )
        invoice_date = date.fromisoformat(invoice_date[1]).isoformat()
        due_date = date.fromisoformat(due_date[1]).isoformat()
        description = fields.get("description of goods 01", "")
        sku = re.search(r"SKU:\s*([^;\s]+)", description)
        if not sku:
            raise AppError(
                "MISSING_SKU", "A product SKU is required to select comparable historical records."
            )
        quantity = Decimal(fields["no of units 1"])
        if quantity <= 0 or quantity != int(quantity):
            raise AppError("INVALID_QUANTITY", "Product quantity must be a positive whole number.")
        currency = fields.get("currency code name", "").upper()
        if not re.fullmatch("[A-Z]{3}", currency):
            raise AppError("INVALID_CURRENCY", "A valid currency is required.")
        source = {"source_id": evidence_id, "locator": "page=1; AcroForm", "kind": "user_pdf"}
        return {
            "invoice_id": f"invoice_{evidence_id}",
            "invoice_number": fields["invoice no"],
            "invoice_date": invoice_date,
            "ship_date": date.fromisoformat(fields["ship date"]).isoformat(),
            "due_date": due_date,
            "payment_terms": fields["payment terms"],
            "payment_term_days": int(terms[1]),
            "currency": currency,
            "seller": party("exporter"),
            "buyer": party("consignee"),
            "consignee_same_as_buyer": True,
            "declared_related": fields["Radio Button1"] == "/yes",
            "purchase_order_number": fields.get("purchase order no", ""),
            "air_waybill_number": fields.get("awb no", ""),
            "line_items": [
                {
                    "sku": sku[1],
                    "description": description,
                    "quantity": int(quantity),
                    "unit": fields["unit measure 1"],
                    "unit_price": money(fields["unit value 1"]),
                    "line_total": money(fields["total value 01"]),
                    "hs_code": fields["hs code"],
                    "country_of_manufacture": fields["ctry of origin 1"],
                }
            ],
            "subtotal": money(fields["subtotal"]),
            "charges": {
                key: money(fields.get("other cost" if key == "other" else key, "0"))
                for key in ["insurance", "freight", "packing", "handling", "other"]
            },
            "total": money(fields["invoice total"]),
            "trade_terms": fields.get("Combo Box1", "").split("=")[0],
            "delivery_location": fields.get("other fill in type", "").split(";")[0],
            "source_refs": [source],
            "extraction_method": "acroform_verified",
            "synthetic": "SYNTHETIC DEMO DATA" in fields.get("declarations statement", ""),
        }
    except AppError:
        raise
    except Exception:
        raise AppError(
            "PARSE_FAILED", "The invoice form could not be read. Check the file and upload it again."
        ) from None


def parse_evidence(filename, data):
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > 100:
                raise AppError("PDF_NOT_SUPPORTED", "The PDF is encrypted or exceeds the page limit.")
            pages = [{"page": i + 1, "text": p.extract_text() or ""} for i, p in enumerate(reader.pages)]
            if not any(p["text"].strip() for p in pages):
                raise AppError("OCR_NOT_CONFIGURED", "OCR for scanned PDFs is not configured.")
            return {"type": "pdf", "pages": pages}
        if ext == ".xlsx":
            workbook = load_workbook(BytesIO(data), read_only=True, data_only=False)
            cells = []
            for sheet in workbook:
                for row in sheet:
                    for cell in row:
                        if cell.value is not None:
                            if cell.data_type == "f":
                                raise AppError(
                                    "FORMULA_REQUIRES_VALUES",
                                    "Convert spreadsheet formulas to values before uploading.",
                                )
                            cells.append(
                                {"sheet": sheet.title, "cell": cell.coordinate, "value": str(cell.value)}
                            )
                            if len(cells) > 100000:
                                raise AppError(
                                    "FILE_TOO_LARGE", "The spreadsheet exceeds 100,000 populated cells.", 413
                                )
            workbook.close()
            return {"type": "xlsx", "cells": cells}
        if ext == ".csv":
            rows = list(csv.reader(data.decode("utf-8-sig").splitlines()))
            if sum(len(row) for row in rows) > 100000:
                raise AppError("FILE_TOO_LARGE", "The CSV exceeds the cell limit.", 413)
            return {"type": "csv", "rows": rows}
        raise AppError("UNSUPPORTED_PARSER", "Parsing is not available for this file type.", 415)
    except AppError:
        raise
    except Exception:
        raise AppError(
            "PARSE_FAILED", "Evidence could not be parsed. Check the format or use a UTF-8 CSV."
        ) from None
