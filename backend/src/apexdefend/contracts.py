"""Attach explicit response contracts to FastAPI's generated request schemas."""

import json
from copy import deepcopy

from fastapi.openapi.utils import get_openapi

from .config import HANDOFF


def install_contracts(app):
    definitions = deepcopy(
        json.loads((HANDOFF / "contracts/schemas/common.schema.json").read_text())["$defs"]
    )

    def ref(name):
        return {"$ref": f"#/components/schemas/{name}"}

    def nullable(schema):
        return {"anyOf": [schema, {"type": "null"}]}

    definitions["Finding"]["required"].remove("confidence")
    definitions["ModuleView"]["properties"]["error"] = nullable(ref("ErrorBody"))
    definitions["Evidence"]["properties"]["error"] = nullable(ref("ErrorBody"))
    definitions["Evidence"]["properties"]["status"] = {
        "type": "string",
        "enum": ["active", "pending", "failed", "superseded", "withdrawn"],
    }
    definitions["Evidence"]["properties"]["evidence_group"] = nullable({"type": "string"})
    definitions["Evidence"]["properties"]["version"] = {"type": "integer", "minimum": 1}
    definitions["Evidence"]["properties"]["supersedes_evidence_id"] = nullable({"type": "string"})
    definitions["Workspace"]["properties"]["error"] = nullable(ref("ErrorBody"))
    definitions["Workspace"]["properties"]["parties"]["items"] = {
        "anyOf": [ref("PartyResolution"), ref("PartySelection")]
    }
    definitions["PartyResolution"]["properties"]["resolution_action"] = nullable(
        {"type": "string", "enum": ["use_invoice_entity", "compare_selection"]}
    )
    definitions["Capabilities"]["properties"]["model"] = {"type": "string"}
    definitions["RuntimeModuleInput"] = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id",
            "module_key",
            "input_version",
            "as_of",
            "policy_version",
            "facts",
            "reference_records",
            "sources",
            "evidence",
        ],
        "properties": {
            "case_id": {"type": "string"},
            "module_key": ref("ModuleKey"),
            "input_version": {"type": "integer", "minimum": 1},
            "as_of": {"type": "string", "format": "date"},
            "policy_version": {"type": "string"},
            "facts": {"type": "object"},
            "reference_records": {"type": "array", "items": ref("ReferenceRecord")},
            "sources": {"type": "array", "items": ref("SourceRef")},
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["source_id", "kind", "content"],
                    "properties": {
                        "source_id": {"type": "string"},
                        "kind": {"type": "string", "enum": ["note", "file"]},
                        "content": {"type": "object"},
                    },
                },
            },
        },
    }
    definitions["RunDetail"]["properties"]["input"] = nullable(ref("RuntimeModuleInput"))
    definitions["RunDetail"]["properties"]["provider"] = nullable(
        {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "requested_model": {"type": "string"},
                "reported_model": nullable({"type": "string"}),
                "response_id": nullable({"type": "string"}),
                "request_id": nullable({"type": "string"}),
                "usage": {"type": ["object", "null"]},
            },
        }
    )
    definitions["Health"] = {
        "type": "object",
        "required": ["status", "model", "analyzer_configured"],
        "properties": {
            "status": {"const": "ok"},
            "model": {"type": "string"},
            "analyzer_configured": {"type": "boolean"},
        },
    }

    def rewrite(node):
        if isinstance(node, dict):
            return {
                k: (v.replace("#/$defs/", "#/components/schemas/") if k == "$ref" else rewrite(v))
                for k, v in node.items()
            }
        if isinstance(node, list):
            return [rewrite(v) for v in node]
        return node

    response_types = {
        ("get", "/health"): ("200", "Health"),
        ("get", "/v1/capabilities"): ("200", "Capabilities"),
        ("get", "/v1/entities"): ("200", "EntityList"),
        ("get", "/v1/cases"): ("200", "QueuePage"),
        ("post", "/v1/cases"): ("201", "CaseCreated"),
        ("get", "/v1/cases/{case_id}"): ("200", "Workspace"),
        ("post", "/v1/cases/{case_id}/invoice"): ("202", "MutationAccepted"),
        ("patch", "/v1/cases/{case_id}/parties"): ("200", "Workspace"),
        ("post", "/v1/cases/{case_id}/assessments"): ("202", "MutationAccepted"),
        ("get", "/v1/cases/{case_id}/modules/{module_key}"): ("200", "ModuleView"),
        ("post", "/v1/cases/{case_id}/modules/{module_key}/evidence"): ("202", "MutationAccepted"),
        ("post", "/v1/cases/{case_id}/modules/{module_key}/supplements"): ("202", "MutationAccepted"),
        ("post", "/v1/cases/{case_id}/modules/{module_key}/runs"): ("202", "MutationAccepted"),
        ("post", "/v1/cases/{case_id}/modules/{module_key}/adjustments"): ("201", "ModuleView"),
        ("get", "/v1/cases/{case_id}/modules/{module_key}/runs/{run_id}"): ("200", "RunDetail"),
        ("get", "/v1/jobs/{job_id}"): ("200", "Job"),
        ("get", "/v1/cases/{case_id}/events"): ("200", "EventPage"),
    }

    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title, version=app.version, description=app.description, routes=app.routes
        )
        schema["components"]["schemas"].update(rewrite(definitions))
        for (method, path), (code, name) in response_types.items():
            op = schema["paths"][path][method]
            op["responses"][code] = {
                "description": "Success",
                "content": {"application/json": {"schema": ref(name)}},
            }
        for path in schema["paths"].values():
            for op in path.values():
                for status in ["400", "404", "409", "413", "415", "422", "500", "503"]:
                    op["responses"][status] = {
                        "description": "Structured error",
                        "content": {"application/json": {"schema": ref("ErrorBody")}},
                    }
        schema["paths"]["/v1/cases/{case_id}/files/{file_id}"]["get"]["responses"]["200"] = {
            "description": "Original evidence file",
            "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
        }
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
