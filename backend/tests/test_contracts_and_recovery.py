import pytest
from apexdefend.api import create_app
from apexdefend.db import Snapshot
from apexdefend.domain import POLICY, score_analysis
from apexdefend.errors import AppError
from apexdefend.manage import initialize
from apexdefend.models import AIAnalysis
from conftest import complete, key, new_case, ready, upload
from fastapi.testclient import TestClient
from sqlalchemy import select


def test_read_contracts_and_pagination(system):
    client, _, _, _ = system
    case_id, ws = ready(system)
    assert client.get("/health").json()["model"] == "gpt-6.1-sol"
    capabilities = client.get("/v1/capabilities").json()
    assert capabilities["engine_mode"] == "llm"
    assert next(f for f in capabilities["formats"] if f["extension"] == ".xls")["status"] == "unavailable"
    first = client.get("/v1/entities?limit=1").json()
    second = client.get("/v1/entities", params={"cursor": first["next_cursor"]}).json()
    assert len(first["items"]) == len(second["items"]) == 1
    assert client.get("/v1/cases?risk_band=MEDIUM").status_code == 422
    assert client.get("/v1/cases?risk_band=HIGH").json()["items"] == []
    assert client.get("/v1/cases?cursor=unknown").status_code == 400
    page = client.get(f"/v1/cases/{case_id}/events?limit=2").json()
    following = client.get(f"/v1/cases/{case_id}/events", params={"after_seq": page["next_after_seq"]}).json()
    assert following["items"][0]["seq"] > page["next_after_seq"]
    for module in ws["modules"]:
        detail = client.get(
            f"/v1/cases/{case_id}/modules/{module['module_key']}/runs/{module['current_run']['run_id']}"
        ).json()
        assert detail["input"]["module_key"] == module["module_key"]


def test_persisted_case_survives_reinitialization(system):
    client, _, _, service = system
    case_id, before = ready(system)
    db = initialize(service.settings)
    with TestClient(create_app(service.settings, db)) as restarted:
        after = restarted.get(f"/v1/cases/{case_id}").json()
        assert after == before
    with db.sessions() as s:
        assert len(list(s.scalars(select(Snapshot).where(Snapshot.case_id == case_id)))) == 1
    db.engine.dispose()


def test_failed_obsolete_run_is_superseded_and_latest_input_runs(system):
    client, worker, analyzer, _ = system
    case_id, _ = ready(system)
    url = f"/v1/cases/{case_id}/modules/payment_history"
    module = client.get(url).json()
    started = client.post(
        url + "/runs",
        headers=key(),
        json={"expected_module_version": module["module_version"], "reason": "并发失败恢复"},
    ).json()

    def add_new_input():
        module = client.get(url).json()
        assert (
            client.post(
                url + "/supplements",
                headers=key(),
                json={
                    "expected_module_version": module["module_version"],
                    "text": "新增付款说明",
                    "rerun": True,
                },
            ).status_code
            == 202
        )

    analyzer.on_call, analyzer.fail_key = add_new_input, "payment_history"
    assert worker.run_once()
    assert client.get(f"/v1/jobs/{started['job']['job_id']}").json()["status"] == "superseded"
    analyzer.fail_key = None
    assert worker.run_once()
    assert client.get(url).json()["freshness"] == "current"


def test_untrusted_model_cannot_invent_source_or_emit_zero_for_missing_data(system):
    _, _, analyzer, _ = system
    ready(system)
    inputs = next(i for i in analyzer.calls if i["module_key"] == "payment_history")
    analysis, _ = analyzer.analyze(inputs, POLICY)
    analysis.findings[0].source_ids = ["invented_source"]
    with pytest.raises(AppError, match="本次输入快照之外"):
        score_analysis(analysis, inputs, "run_test", "gpt-6.1-sol")
    missing = AIAnalysis(
        status="needs_info",
        summary="缺少付款记录",
        matched_rule_ids=[],
        findings=[],
        missing_inputs=["payment_history"],
    )
    output = score_analysis(missing, inputs, "run_test", "gpt-6.1-sol")
    assert output["ai_score"] is None and output["state"] == "needs_info"


def test_invalid_upload_does_not_create_evidence_or_invalidate_module(system):
    client, worker, _, _ = system
    case_id, _ = ready(system)
    url = f"/v1/cases/{case_id}/modules/payment_history"
    before = client.get(url).json()
    response = client.post(
        url + "/evidence",
        headers=key(),
        files=[("files", ("not-a-pdf.pdf", b"fake bytes"))],
        data={"expected_module_version": before["module_version"], "rerun": "true"},
    )
    assert response.status_code == 415
    assert client.get(url).json() == before
    assert not worker.run_once()


def test_missing_information_is_visible_in_workspace(system, monkeypatch):
    client, worker, analyzer, _ = system
    original = analyzer.analyze

    def missing_history(inputs, policy):
        if inputs["module_key"] == "payment_history":
            return AIAnalysis(
                status="needs_info",
                summary="需要完整付款日期记录",
                matched_rule_ids=[],
                findings=[],
                missing_inputs=["payment_dates"],
            ), {"provider": "test_only"}
        return original(inputs, policy)

    monkeypatch.setattr(analyzer, "analyze", missing_history)
    case_id = new_case(client)
    upload(client, case_id, worker)
    ws = complete(client, worker, case_id)
    module = next(m for m in ws["modules"] if m["module_key"] == "payment_history")
    assert module["state"] == "needs_info"
    assert module["error"]["error"]["details"]["missing_inputs"] == ["payment_dates"]
    assert ws["navigation"]["target"] == "result"
    assert ws["aggregate"]["current_result"] is None
