import json

import httpx
import pytest
from apexdefend.analyzer import TeamRouterAnalyzer
from apexdefend.config import Settings
from apexdefend.domain import POLICY
from apexdefend.errors import AppError


@pytest.mark.parametrize("style", ["chat", "responses"])
def test_exact_model_endpoint_and_provenance(monkeypatch, style):
    output = {
        "status": "complete",
        "summary": "测试响应",
        "matched_rule_ids": ["INTEGRITY_OK"],
        "findings": [{"code": "OK", "statement": "完整", "source_ids": ["source_pdf"]}],
        "missing_inputs": [],
    }
    captured = []

    def handler(request):
        captured.append(request)
        payload = {"id": "test_response", "model": "gpt-6.1-sol", "usage": {"total_tokens": 12}}
        if style == "chat":
            payload["choices"] = [{"message": {"content": json.dumps(output)}}]
        else:
            payload["output"] = [{"content": [{"type": "output_text", "text": json.dumps(output)}]}]
        return httpx.Response(200, json=payload, headers={"x-request-id": "test_request"})

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    settings = Settings(_env_file=None, teamrouter_api_key="test-only-key", teamrouter_api_style=style)
    analysis, provenance = TeamRouterAnalyzer(settings).analyze(
        {"module_key": "invoice_integrity", "case_id": "private_case", "input_version": 1}, POLICY
    )
    payload = json.loads(captured[0].content)
    assert payload["model"] == "gpt-6.1-sol"
    assert captured[0].url.path == ("/v1/chat/completions" if style == "chat" else "/v1/responses")
    assert "private_case" not in captured[0].content.decode()
    assert analysis.matched_rule_ids == ["INTEGRITY_OK"]
    assert provenance["response_id"] == "test_response" and provenance["request_id"] == "test_request"


def test_missing_key_has_no_network_call_or_fallback(monkeypatch):
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: pytest.fail("must not make a request"))
    with pytest.raises(AppError) as err:
        TeamRouterAnalyzer(Settings(_env_file=None, teamrouter_api_key="")).analyze({}, POLICY)
    assert err.value.code == "ANALYZER_NOT_CONFIGURED"
