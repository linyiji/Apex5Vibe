import json
from decimal import ROUND_HALF_UP, Decimal

from .config import HANDOFF
from .db import content_hash, now
from .errors import AppError

POLICY = json.loads((HANDOFF / "contracts/risk-policy.json").read_text())
DEPENDENCIES = json.loads((HANDOFF / "contracts/dependency-map.json").read_text())
CAPS = POLICY["module_caps"]
REFERENCE_KINDS = {
    "invoice_integrity": [],
    "buyer_verification": ["entity_profile"],
    "seller_verification": ["entity_profile"],
    "relationship": ["trade_history"],
    "market_price": ["market_benchmark"],
    "payment_history": ["payment_history"],
    "duplicate_financing": ["financing_registry"],
}


def module_facts(key, invoice):
    i = invoice
    return {
        "invoice_integrity": {"invoice": i},
        "buyer_verification": {"entity": i["buyer"]},
        "seller_verification": {"entity": i["seller"]},
        "relationship": {
            "seller_id": i["seller"]["entity_id"],
            "buyer_id": i["buyer"]["entity_id"],
            "currency": i["currency"],
            "amount": i["total"],
            "sku": i["line_items"][0]["sku"],
            "invoice_date": i["invoice_date"],
            "declared_related": i["declared_related"],
        },
        "market_price": {
            "line_items": i["line_items"],
            "currency": i["currency"],
            "trade_terms": i["trade_terms"],
            "delivery_location": i["delivery_location"],
        },
        "payment_history": {
            "buyer_id": i["buyer"]["entity_id"],
            "invoice_date": i["invoice_date"],
            "amount": i["total"],
            "currency": i["currency"],
        },
        "duplicate_financing": {
            "invoice_number": i["invoice_number"],
            "seller_tax_id": i["seller"]["tax_id"],
            "buyer_tax_id": i["buyer"]["tax_id"],
            "currency": i["currency"],
            "total": i["total"],
            "invoice_date": i["invoice_date"],
        },
    }[key]


def score_analysis(analysis, inputs, run_id, model):
    key = inputs["module_key"]
    allowed_sources = {
        r["source_id"]: {"source_id": r["source_id"], "locator": r["locator"], "kind": r["kind"]}
        for r in inputs["sources"]
    }
    rules = {r["rule_id"]: r for r in POLICY["rules"][key]}
    source_ids = [s for f in analysis.findings for s in f.source_ids]
    if any(s not in allowed_sources for s in source_ids):
        raise AppError("INVALID_AI_CITATION", "AI引用了本次输入快照之外的来源")
    if analysis.status == "complete":
        missing = set(REFERENCE_KINDS[key]) - {r["kind"] for r in inputs["reference_records"]}
        if missing:
            raise AppError("INVALID_AI_OUTPUT", "缺少必需参考资料时不能生成完成结果")
        if len(analysis.matched_rule_ids) != 1 or analysis.matched_rule_ids[0] not in rules:
            raise AppError("INVALID_AI_RULE", "AI未选择有效的模块计分规则")
        if (
            analysis.missing_inputs
            or not analysis.findings
            or any(not f.source_ids for f in analysis.findings)
        ):
            raise AppError("INVALID_AI_OUTPUT", "完成的评估必须有事实、引用且无缺失输入")
        ai_score = rules[analysis.matched_rule_ids[0]]["points"]
        state = "succeeded"
    else:
        if not analysis.missing_inputs or analysis.matched_rule_ids:
            raise AppError("INVALID_AI_OUTPUT", "缺资料结果必须说明缺失项且不计分")
        ai_score, state = None, "needs_info"
    blocking_map = {
        "ACTIVE_FINANCING_MATCH": "confirmed_duplicate_financing",
        "BUYER_CONFLICT": "entity_mismatch",
        "SELLER_CONFLICT": "entity_mismatch",
        "INTEGRITY_CONFLICT": "invoice_integrity_conflict",
    }
    return {
        "case_id": inputs["case_id"],
        "module_key": key,
        "run_id": run_id,
        "input_version": inputs["input_version"],
        "state": state,
        "ai_score": ai_score,
        "summary": analysis.summary,
        "matched_rule_ids": analysis.matched_rule_ids,
        "findings": [
            {
                "code": f.code,
                "statement": f.statement,
                "source_refs": [allowed_sources[s] for s in f.source_ids],
            }
            for f in analysis.findings
        ],
        "blocking_flags": [blocking_map[r] for r in analysis.matched_rule_ids if r in blocking_map],
        "missing_inputs": analysis.missing_inputs,
        "provenance": {
            "engine_mode": "llm",
            "analyzer": "teamrouter",
            "model": model,
            "prompt_version": "module-analysis-v2",
            "policy_version": POLICY["policy_version"],
            "parser_version": "acroform-v1",
            "input_hash": content_hash(inputs),
            "generated_at": now(),
        },
    }


def adjusted_score(ai_score, requested, cap):
    if not -cap <= requested <= cap:
        raise AppError("INVALID_ADJUSTMENT", f"人工调整必须在{-cap}到{cap}之间")
    final = max(0, min(cap, ai_score + requested))
    return final, final - ai_score


def decision(score, invoice, blockers, pending_adjustments=False):
    base = {
        "status": "pending",
        "advance_rate": None,
        "advance_amount": None,
        "currency": invoice["currency"] if invoice else "GBP",
        "reasons": [],
    }
    if score is None or pending_adjustments:
        base["reasons"] = ["assessment_not_current" if score is None else "manual_adjustment_pending_review"]
    elif blockers or score >= POLICY["high_min_inclusive"]:
        base.update(status="manual_review", reasons=sorted(set(blockers)) or ["high_risk_score"])
    else:
        amount = (Decimal(invoice["total"]) * Decimal(POLICY["advance_rate"])).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )
        base.update(
            status="eligible",
            advance_rate=float(POLICY["advance_rate"]),
            advance_amount=str(amount),
            reasons=["current_low_risk"],
        )
    return base
