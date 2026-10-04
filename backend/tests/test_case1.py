import json
import time

from apexdefend.config import HANDOFF
from apexdefend.db import Job
from apexdefend.domain import adjusted_score, decision
from apexdefend.errors import AppError
from apexdefend.parsers import parse_invoice
from conftest import complete, key, new_case, ready, upload


def test_case1_pdf_to_seven_modules_to_low_result(system):
    client, worker, analyzer, service = system
    case_id, ws = ready(system)
    assert ws["invoice"]["total"] == "8000.00"
    assert ws["invoice"]["buyer"]["entity_id"] == "ent_meridianleaf"
    assert ws["invoice"]["consignee_same_as_buyer"] is True
    assert ws["invoice"]["declared_related"] is False
    assert len(analyzer.calls) == 7
    assert ws["initial_assessment_status"] == "settled"
    assert ws["navigation"]["target"] == "result"
    assert ws["aggregate"]["current_result"]["final_risk_score"] == 5
    assert ws["aggregate"]["current_result"]["risk_band"] == "LOW"
    assert ws["aggregate"]["decision"]["advance_amount"] == "6400.00"
    assert all(m["state"] == "succeeded" for m in ws["modules"])
    assert all(m["current_run"]["provenance"]["model"] == "gpt-6.1-sol" for m in ws["modules"])
    first = ws["modules"][0]
    run = client.get(
        f"/v1/cases/{case_id}/modules/{first['module_key']}/runs/{first['current_run']['run_id']}"
    ).json()
    assert run["provider"]["provider"] == "test_only"
    assert run["input"]["facts"]["invoice"]["invoice_number"] == "CV-2026-1002-001"
    assert client.get("/v1/cases").json()["items"][0]["risk_is_current"] is True


def test_note_save_invalidates_only_target_then_rerun_consumes_text(system):
    client, worker, analyzer, _ = system
    case_id, before = ready(system)
    target = next(m for m in before["modules"] if m["module_key"] == "payment_history")
    url = f"/v1/cases/{case_id}/modules/payment_history"
    body = {
        "expected_module_version": target["module_version"],
        "text": "补充说明：两次迟付已经结清。",
        "rerun": False,
    }
    headers = key()
    response = client.post(url + "/supplements", headers=headers, json=body)
    assert response.status_code == 202
    assert client.post(url + "/supplements", headers=headers, json=body).json() == response.json()
    saved = client.get(f"/v1/cases/{case_id}").json()
    assert saved["aggregate"]["current_result"] is None
    assert saved["aggregate"]["last_valid_result"]["final_risk_score"] == 5
    assert saved["aggregate"]["decision"]["status"] == "pending"
    assert not worker.run_once()
    module = client.get(url).json()
    assert len(module["supplements"]) == 1
    response = client.post(
        url + "/runs",
        headers=key(),
        json={"expected_module_version": module["module_version"], "reason": "核对新增说明"},
    )
    assert response.status_code == 202
    assert worker.run_once()
    after = client.get(f"/v1/cases/{case_id}").json()
    assert analyzer.calls[-1]["evidence"][0]["content"]["text"] == body["text"]
    for old, new in zip(before["modules"], after["modules"]):
        if old["module_key"] != "payment_history":
            assert old["current_run"]["run_id"] == new["current_run"]["run_id"]
            assert old["input_version"] == new["input_version"]
    assert after["aggregate"]["current_result"]["final_risk_score"] == 5


def test_xlsx_contents_are_parsed_not_counted_and_duplicate_is_reused(system):
    client, worker, analyzer, _ = system
    case_id, ws = ready(system)
    target = next(m for m in ws["modules"] if m["module_key"] == "invoice_integrity")
    url = f"/v1/cases/{case_id}/modules/invoice_integrity"
    data = (HANDOFF / "source/ApexDefend_Case_1_Input_Fields.xlsx").read_bytes()
    response = client.post(
        url + "/evidence",
        headers=key(),
        files=[("files", ("fields.xlsx", data))],
        data={"expected_module_version": target["module_version"], "rerun": "true"},
    )
    assert response.status_code == 202, response.text
    assert worker.run_once()  # parse the spreadsheet
    assert worker.run_once()  # analyze only this module
    cells = analyzer.calls[-1]["evidence"][0]["content"]["cells"]
    assert any(c["cell"] == "C51" and c["value"] == "8000" for c in cells)
    target = client.get(url).json()
    version = target["input_version"]
    response = client.post(
        url + "/evidence",
        headers=key(),
        files=[("files", ("another-name.xlsx", data))],
        data={"expected_module_version": target["module_version"], "rerun": "false"},
    )
    assert response.status_code == 202
    assert client.get(url).json()["input_version"] == version
    assert not worker.run_once()


def test_manual_adjustment_preserves_ai_and_requires_reconfirmation_after_rerun(system):
    client, worker, _, _ = system
    case_id, ws = ready(system)
    url = f"/v1/cases/{case_id}/modules/payment_history"
    module = client.get(url).json()
    response = client.post(
        url + "/adjustments",
        headers=key(),
        json={
            "expected_module_version": module["module_version"],
            "applies_to_run_id": module["current_run"]["run_id"],
            "requested_adjustment": -10,
            "reason": "测试人工调整范围和审计",
        },
    )
    assert response.status_code == 201, response.text
    module = response.json()
    assert module["current_run"]["ai_score"] == 5
    assert module["final_score"] == 0 and module["effective_adjustment"] == -5
    response = client.post(
        url + "/runs",
        headers=key(),
        json={"expected_module_version": module["module_version"], "reason": "重新分析"},
    )
    assert response.status_code == 202
    assert worker.run_once()
    module = client.get(url).json()
    assert module["adjustment_status"] == "pending_review"
    assert module["effective_adjustment"] == 0
    assert client.get(f"/v1/cases/{case_id}").json()["aggregate"]["decision"]["status"] == "pending"
    response = client.post(
        url + "/adjustments",
        headers=key(),
        json={
            "expected_module_version": module["module_version"],
            "applies_to_run_id": module["current_run"]["run_id"],
            "requested_adjustment": 0,
            "reason": "按新的AI结果归零",
        },
    )
    assert response.status_code == 201
    assert client.get(f"/v1/cases/{case_id}").json()["aggregate"]["decision"]["status"] == "eligible"


def test_new_input_during_analysis_supersedes_old_run(system):
    client, worker, analyzer, service = system
    case_id, _ = ready(system)
    url = f"/v1/cases/{case_id}/modules/payment_history"
    module = client.get(url).json()
    first = client.post(
        url + "/runs",
        headers=key(),
        json={"expected_module_version": module["module_version"], "reason": "开始长评估"},
    )
    assert first.status_code == 202

    def concurrent_edit():
        latest = client.get(url).json()
        result = client.post(
            url + "/supplements",
            headers=key(),
            json={
                "expected_module_version": latest["module_version"],
                "text": "运行期间新增资料",
                "rerun": True,
            },
        )
        assert result.status_code == 202, result.text

    analyzer.on_call = concurrent_edit
    assert worker.run_once()
    assert client.get(f"/v1/jobs/{first.json()['job']['job_id']}").json()["status"] == "superseded"
    assert client.get(f"/v1/cases/{case_id}").json()["aggregate"]["current_result"] is None
    assert worker.run_once()
    module = client.get(url).json()
    assert module["input_version"] == module["evaluated_input_version"]
    assert module["freshness"] == "current"
    assert any(r["status"] == "superseded" for r in module["run_history"])


def test_provider_failure_never_becomes_zero_or_low_and_initial_batch_settles(system):
    client, worker, analyzer, _ = system
    analyzer.fail_key = "payment_history"
    case_id = new_case(client)
    upload(client, case_id, worker)
    ws = complete(client, worker, case_id)
    assert ws["initial_assessment_status"] == "settled"
    assert ws["navigation"]["target"] == "result"
    assert ws["aggregate"]["status"] == "incomplete"
    assert ws["aggregate"]["current_result"] is None
    assert client.get("/v1/cases").json()["items"][0]["risk_band"] is None


def test_conflicts_idempotency_and_cross_case_file_access(system):
    client, worker, _, _ = system
    case_id = new_case(client, buyer={"mode": "manual", "legal_name": "Different company"})
    ws = upload(client, case_id, worker)
    assert next(p for p in ws["parties"] if p["side"] == "buyer")["status"] == "conflict"
    response = client.post(
        f"/v1/cases/{case_id}/assessments",
        headers=key(),
        json={"expected_case_revision": ws["case_revision"]},
    )
    assert response.status_code == 422
    headers = key()
    payload = {
        "expected_case_revision": ws["case_revision"],
        "side": "buyer",
        "selection": {"mode": "skip"},
        "resolution_action": "use_invoice_entity",
        "reason": "以发票为准",
    }
    response = client.patch(f"/v1/cases/{case_id}/parties", headers=headers, json=payload)
    assert response.status_code == 200
    altered = {**payload, "reason": "different body"}
    assert client.patch(f"/v1/cases/{case_id}/parties", headers=headers, json=altered).status_code == 409
    second = new_case(client)
    evidence_id = response.json()["invoice"]["source_refs"][0]["source_id"]
    assert client.get(f"/v1/cases/{second}/files/{evidence_id}").status_code == 404
    assert client.get(f"/v1/cases/{case_id}/files/{evidence_id}").status_code == 200


def test_expired_lease_can_be_recovered_and_old_worker_cannot_commit(system):
    client, worker, _, service = system
    case_id, _ = ready(system)
    url = f"/v1/cases/{case_id}/modules/payment_history"
    module = client.get(url).json()
    response = client.post(
        url + "/runs",
        headers=key(),
        json={"expected_module_version": module["module_version"], "reason": "lease test"},
    )
    assert response.status_code == 202
    job_id, old_token = worker.claim()
    with service.db.transaction() as s:
        s.get(Job, job_id).lease_until = time.time() - 1
    recovered_id, token = worker.claim()
    assert recovered_id == job_id and token > old_token
    worker.process(job_id, old_token)
    assert client.get(f"/v1/jobs/{job_id}").json()["status"] == "running"
    worker.process(job_id, token)
    worker.fail(job_id, old_token, AppError("OLD_WORKER", "must not commit"))
    assert client.get(f"/v1/jobs/{job_id}").json()["status"] == "succeeded"
    assert client.get(url).json()["freshness"] == "current"


def test_actual_pdf_values_match_independent_excel_ground_truth():
    for n in [1, 2]:
        invoice = parse_invoice(
            (HANDOFF / f"source/ApexDefend_Case_{n}_Invoice.pdf").read_bytes(), "source_pdf"
        )
        expected = json.loads((HANDOFF / f"fixtures/case_{n}-raw-field-map.json").read_text())["fields"]
        assert invoice["invoice_number"] == expected["invoice_number"]
        assert invoice["total"] == f"{expected['invoice_total']:.2f}"
        assert invoice["line_items"][0]["quantity"] == expected["quantity"]
        assert invoice["due_date"] == expected["payment_due_date"][:10]


def test_score_boundaries_and_hard_blocks():
    invoice = {"total": "8000.00", "currency": "GBP"}
    assert decision(29, invoice, [])["status"] == "eligible"
    assert decision(30, invoice, [])["status"] == "manual_review"
    assert decision(5, invoice, ["confirmed_duplicate_financing"])["status"] == "manual_review"
    assert adjusted_score(5, -10, 15) == (0, -5)
