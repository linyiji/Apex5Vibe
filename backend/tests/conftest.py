from copy import deepcopy

import pytest
from apexdefend.api import create_app
from apexdefend.config import HANDOFF, Settings
from apexdefend.errors import AppError
from apexdefend.manage import initialize
from apexdefend.models import AIAnalysis
from apexdefend.worker import Worker
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator


class TestAnalyzer:
    """Test-only transport substitute. Never installed as a runtime fallback."""

    __test__ = False

    def __init__(self):
        self.calls = []
        self.on_call = None
        self.fail_key = None
        self.rules = {}

    def analyze(self, inp, policy):
        self.calls.append(deepcopy(inp))
        if self.on_call:
            callback, self.on_call = self.on_call, None
            callback()
        if inp["module_key"] == self.fail_key:
            raise AppError("ANALYZER_UNAVAILABLE", "test provider unavailable", 503)
        key = inp["module_key"]
        index = 1 if key == "payment_history" else 0
        rule = self.rules.get(key, policy["rules"][key][index]["rule_id"])
        return AIAnalysis(
            status="complete",
            summary="测试替身返回结构化分析，非真实AI验收",
            matched_rule_ids=[rule],
            findings=[
                {
                    "code": rule,
                    "statement": "引用本次输入资料",
                    "source_ids": [r["source_id"] for r in inp["sources"]],
                }
            ],
            missing_inputs=[],
        ), {
            "provider": "test_only",
            "requested_model": "gpt-6.1-sol",
            "reported_model": "test_only",
            "response_id": "test_response",
        }


@pytest.fixture(autouse=True)
def validate_api_responses(monkeypatch):
    """Validate actual success AND error payloads against the exported OpenAPI."""
    original = TestClient.send

    def send(client, request, *args, **kwargs):
        response = original(client, request, *args, **kwargs)
        if response.headers.get("content-type", "").startswith("application/json"):
            for route in client.app.routes:
                if not hasattr(route, "methods") or request.method not in route.methods:
                    continue
                if not route.path_regex.fullmatch(request.url.path):
                    continue
                document = client.app.openapi()
                operation = document.get("paths", {}).get(route.path_format, {}).get(request.method.lower())
                if operation:
                    definition = operation["responses"].get(str(response.status_code))
                    assert definition, (request.url.path, response.status_code)
                    schema = definition["content"]["application/json"]["schema"]
                    Draft202012Validator({"components": document["components"], **schema}).validate(
                        response.json()
                    )
                break
        return response

    monkeypatch.setattr(TestClient, "send", send)


@pytest.fixture
def system(tmp_path):
    settings = Settings(data_dir=tmp_path, _env_file=None)
    db = initialize(settings)
    app = create_app(settings, db)
    analyzer = TestAnalyzer()
    worker = Worker(app.state.service, analyzer)
    with TestClient(app) as client:
        yield client, worker, analyzer, app.state.service
    db.engine.dispose()


def key():
    import uuid

    return {"Idempotency-Key": uuid.uuid4().hex}


def new_case(client, buyer=None, seller=None):
    result = client.post(
        "/v1/cases",
        headers=key(),
        json={"buyer": buyer or {"mode": "skip"}, "seller": seller or {"mode": "skip"}},
    )
    assert result.status_code == 201, result.text
    return result.json()["case_id"]


def upload(client, case_id, worker):
    ws = client.get(f"/v1/cases/{case_id}").json()
    pdf = (HANDOFF / "source/ApexDefend_Case_1_Invoice.pdf").read_bytes()
    response = client.post(
        f"/v1/cases/{case_id}/invoice",
        headers=key(),
        files={"file": ("renamed_random_invoice.pdf", pdf, "application/pdf")},
        data={"expected_case_revision": ws["case_revision"], "replace": "false"},
    )
    assert response.status_code == 202, response.text
    assert worker.run_once()
    ws = client.get(f"/v1/cases/{case_id}").json()
    assert ws["error"] is None, ws["error"]
    return ws


def complete(client, worker, case_id):
    ws = client.get(f"/v1/cases/{case_id}").json()
    result = client.post(
        f"/v1/cases/{case_id}/assessments",
        headers=key(),
        json={"expected_case_revision": ws["case_revision"]},
    )
    assert result.status_code == 202, result.text
    for _ in range(30):
        if not worker.run_once():
            break
    return client.get(f"/v1/cases/{case_id}").json()


def ready(system):
    client, worker, analyzer, service = system
    case_id = new_case(client)
    upload(client, case_id, worker)
    return case_id, complete(client, worker, case_id)
