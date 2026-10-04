"""Exercise the running API + worker + real TeamRouter; never uses a test analyzer."""

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
    parser.add_argument("--verify-rerun", action="store_true")
    parser.add_argument("--report", type=Path, default=ROOT / "runtime/live-case1.json")
    args = parser.parse_args()
    report = {"started_at": now(), "model": "gpt-6.1-sol", "engine_mode": "llm", "passed": False}

    with httpx.Client(base_url=args.base_url, timeout=30, trust_env=False) as client:

        def request(method, path, **kwargs):
            if method != "GET":
                kwargs["headers"] = {"Idempotency-Key": str(uuid.uuid4())}
            result = client.request(method, path, **kwargs)
            result.raise_for_status()
            return result.json()

        def wait_case(case_id, predicate):
            deadline, last = time.monotonic() + args.timeout, None
            while time.monotonic() < deadline:
                workspace = request("GET", f"/v1/cases/{case_id}")
                report["latest_workspace"] = workspace
                state = ", ".join(f"{m['module_key']}={m['state']}" for m in workspace["modules"])
                if state != last:
                    print(state, flush=True)
                    last = state
                if predicate(workspace):
                    return workspace
                if workspace["error"]:
                    raise RuntimeError(workspace["error"]["error"]["message"])
                time.sleep(1)
            raise TimeoutError("Case did not finish. Check the separate worker process and job errors.")

        def assert_result(workspace):
            aggregate = workspace["aggregate"]
            assert aggregate["status"] == "current", aggregate
            assert aggregate["current_result"]["final_risk_score"] == 5, aggregate
            assert aggregate["current_result"]["risk_band"] == "LOW", aggregate
            assert aggregate["decision"]["status"] == "eligible", aggregate
            assert aggregate["decision"]["advance_amount"] == "6400.00", aggregate
            assert workspace["navigation"]["target"] == "result"

        def collect_runs(workspace):
            runs = []
            for module in workspace["modules"]:
                assert module["state"] == "succeeded", module
                run_id = module["current_run"]["run_id"]
                run = request(
                    "GET", f"/v1/cases/{workspace['case_id']}/modules/{module['module_key']}/runs/{run_id}"
                )
                assert run["provider"]["provider"] == "teamrouter", run["provider"]
                assert run["provider"]["requested_model"] == "gpt-6.1-sol", run["provider"]
                assert run["provider"]["reported_model"] == "gpt-6.1-sol", run["provider"]
                runs.append(run)
            return runs

        def assert_isolated(before, after, target):
            for old, new in zip(before["modules"], after["modules"]):
                if new["module_key"] == target:
                    assert new["input_version"] > old["input_version"]
                    assert new["current_run"]["run_id"] != old["current_run"]["run_id"]
                else:
                    assert new["current_run"]["run_id"] == old["current_run"]["run_id"]
                    assert new["input_version"] == old["input_version"]

        try:
            health = request("GET", "/health")
            assert health["analyzer_configured"], "Configure TEAMROUTER_API_KEY before the live test."
            assert health["model"] == "gpt-6.1-sol", health
            created = request(
                "POST", "/v1/cases", json={"buyer": {"mode": "skip"}, "seller": {"mode": "skip"}}
            )
            case_id = report["case_id"] = created["case_id"]
            print(f"Case: {case_id}", flush=True)
            workspace = request("GET", f"/v1/cases/{case_id}")
            with (HANDOFF / "source/ApexDefend_Case_1_Invoice.pdf").open("rb") as invoice:
                request(
                    "POST",
                    f"/v1/cases/{case_id}/invoice",
                    files={"file": ("live-invoice.pdf", invoice, "application/pdf")},
                    data={"expected_case_revision": workspace["case_revision"], "replace": "false"},
                )
            workspace = wait_case(case_id, lambda w: w["stage"] == "resolving")
            assert workspace["invoice"]["total"] == "8000.00"
            request(
                "POST",
                f"/v1/cases/{case_id}/assessments",
                json={"expected_case_revision": workspace["case_revision"]},
            )
            workspace = wait_case(case_id, lambda w: w["initial_assessment_status"] == "settled")
            report["initial_workspace"] = workspace
            assert_result(workspace)
            report["initial_runs"] = collect_runs(workspace)

            if args.verify_rerun:
                for target, kind in [("invoice_integrity", "xlsx"), ("payment_history", "note")]:
                    before = workspace
                    module = next(m for m in before["modules"] if m["module_key"] == target)
                    url = f"/v1/cases/{case_id}/modules/{target}"
                    if kind == "xlsx":
                        with (HANDOFF / "source/ApexDefend_Case_1_Input_Fields.xlsx").open("rb") as evidence:
                            request(
                                "POST",
                                url + "/evidence",
                                files=[("files", ("invoice-fields.xlsx", evidence))],
                                data={"expected_module_version": module["module_version"], "rerun": "true"},
                            )
                    else:
                        request(
                            "POST",
                            url + "/supplements",
                            json={
                                "expected_module_version": module["module_version"],
                                "text": "历史付款记录中的两次迟付分别为3天和6天，均已结清。这是分析师补充说明。",
                                "rerun": True,
                            },
                        )
                    workspace = wait_case(
                        case_id,
                        lambda w: (
                            next(m for m in w["modules"] if m["module_key"] == target)["state"]
                            in ["failed", "needs_info"]
                            or (
                                next(m for m in w["modules"] if m["module_key"] == target)["state"]
                                == "succeeded"
                                and next(m for m in w["modules"] if m["module_key"] == target)["freshness"]
                                == "current"
                            )
                        ),
                    )
                    report[f"after_{kind}_workspace"] = workspace
                    assert_result(workspace)
                    assert_isolated(before, workspace, target)
                    report[f"after_{kind}_runs"] = collect_runs(workspace)
            report["passed"] = True
            print(
                "PASS: Case 1 = 5/100 LOW, eligible, GBP 6400.00. Actual TeamRouter calls recorded.",
                flush=True,
            )
        finally:
            report["finished_at"] = now()
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(f"Report: {args.report}", flush=True)


if __name__ == "__main__":
    main()
