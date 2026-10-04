"""Real Case 2: PDF -> errors spreadsheet -> explicit corrected replacement."""

import argparse
import json
import time
import uuid
from pathlib import Path

import httpx
from apexdefend.config import HANDOFF, ROOT
from apexdefend.db import now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--report", type=Path, default=ROOT / "runtime/live-case2.json")
    args = parser.parse_args()
    report = {"started_at": now(), "passed": False, "engine_mode": "llm", "model": "gpt-6.1-sol"}
    with httpx.Client(base_url=args.base_url, timeout=30, trust_env=False) as client:

        def request(method, path, **kwargs):
            if method != "GET":
                kwargs["headers"] = {"Idempotency-Key": uuid.uuid4().hex}
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

        def wait_case(predicate):
            end, previous = time.monotonic() + args.timeout, None
            while time.monotonic() < end:
                ws = request("GET", f"/v1/cases/{case_id}")
                report["latest_workspace"] = ws
                state = ", ".join(f"{m['module_key']}={m['state']}:{m['freshness']}" for m in ws["modules"])
                if state != previous:
                    print(state, flush=True)
                    previous = state
                if predicate(ws):
                    return ws
                if ws["error"]:
                    raise RuntimeError(ws["error"])
                time.sleep(1)
            raise TimeoutError("Case 2 exceeded timeout; check worker and persisted errors")

        def target(ws):
            return next(m for m in ws["modules"] if m["module_key"] == "invoice_integrity")

        def check(ws, expected):
            assert ws["invoice"]["total"] == "50000.00", ws["invoice"]
            result = ws["aggregate"]["current_result"]
            assert result and result["final_risk_score"] == expected, ws["aggregate"]
            assert result["risk_band"] == "HIGH"
            assert ws["aggregate"]["decision"]["status"] == "manual_review"
            assert ws["aggregate"]["decision"]["advance_amount"] is None

        def run_details(ws):
            result = []
            for m in ws["modules"]:
                detail = request(
                    "GET", f"/v1/cases/{case_id}/modules/{m['module_key']}/runs/{m['current_run']['run_id']}"
                )
                assert detail["provider"]["provider"] == "teamrouter"
                assert (
                    detail["provider"]["requested_model"]
                    == detail["provider"]["reported_model"]
                    == "gpt-6.1-sol"
                )
                result.append(detail)
            return result

        try:
            assert request("GET", "/health")["analyzer_configured"]
            case_id = request(
                "POST", "/v1/cases", json={"buyer": {"mode": "skip"}, "seller": {"mode": "skip"}}
            )["case_id"]
            report["case_id"] = case_id
            print(f"Case: {case_id}", flush=True)
            ws = request("GET", f"/v1/cases/{case_id}")
            with (HANDOFF / "source/ApexDefend_Case_2_Invoice.pdf").open("rb") as file:
                request(
                    "POST",
                    f"/v1/cases/{case_id}/invoice",
                    files={"file": ("invoice.pdf", file)},
                    data={"expected_case_revision": ws["case_revision"], "replace": "false"},
                )
            ws = wait_case(lambda w: w["stage"] == "resolving")
            request(
                "POST",
                f"/v1/cases/{case_id}/assessments",
                json={"expected_case_revision": ws["case_revision"]},
            )
            initial = ws = wait_case(lambda w: w["initial_assessment_status"] == "settled")
            report["initial_workspace"] = ws
            check(ws, 35)
            report["initial_runs"] = run_details(ws)
            previous_id = None
            for label, filename, expected in [
                ("errors", "ApexDefend_Case_2_Errors.xlsx", 50),
                ("corrected", "ApexDefend_Case_2_Corrected.xlsx", 35),
            ]:
                params = {
                    "expected_module_version": target(ws)["module_version"],
                    "rerun": "true",
                    "evidence_group": "invoice_field_sheet",
                }
                if previous_id:
                    params["supersedes_evidence_id"] = previous_id
                with (HANDOFF / f"source/{filename}").open("rb") as file:
                    accepted = request(
                        "POST",
                        f"/v1/cases/{case_id}/modules/invoice_integrity/evidence",
                        files=[("files", ("same-filename.xlsx", file))],
                        data=params,
                    )
                evidence_id = accepted["evidence_ids"][0]
                report[f"{label}_evidence_id"] = evidence_id
                pending = request("GET", f"/v1/cases/{case_id}")
                assert pending["aggregate"]["decision"]["status"] == "pending"
                ws = wait_case(
                    lambda w: (
                        target(w)["state"] in ["failed", "needs_info"]
                        or (target(w)["state"] == "succeeded" and target(w)["freshness"] == "current")
                    )
                )
                report[f"after_{label}_workspace"] = ws
                check(ws, expected)
                runs = report[f"after_{label}_runs"] = run_details(ws)
                integrity = next(r for r in runs if r["module_key"] == "invoice_integrity")
                assert [e["source_id"] for e in integrity["input"]["evidence"]] == [evidence_id]
                if label == "errors":
                    differences = integrity["input"]["evidence"][0]["content"]["field_sheet"]["differences"]
                    assert {d["cell"] for d in differences} == {"C25", "C51"}
                    statements = " ".join(f["statement"] for f in integrity["output"]["findings"])
                    assert "C25" in statements and "C51" in statements, statements
                else:
                    assert integrity["input"]["evidence"][0]["content"]["field_sheet"]["differences"] == []
                    assert (
                        next(e for e in target(ws)["evidence"] if e["evidence_id"] == previous_id)["status"]
                        == "superseded"
                    )
                for old, new in zip(initial["modules"], ws["modules"]):
                    if old["module_key"] != "invoice_integrity":
                        assert old["current_run"]["run_id"] == new["current_run"]["run_id"]
                previous_id = evidence_id
                print(f"{label}: {expected}/100 HIGH; main PDF remains GBP 50000.00", flush=True)
            report["passed"] = True
            print("PASS: Case 2 actual AI 35 -> 50 -> 35; only invoice_integrity reran.", flush=True)
        finally:
            report["finished_at"] = now()
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(f"Report: {args.report}", flush=True)


if __name__ == "__main__":
    main()
