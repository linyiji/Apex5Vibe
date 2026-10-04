import hashlib
import uuid
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, text

from .config import Settings
from .contracts import install_contracts
from .db import AuditEvent, Case, Database, Evidence, Job, Reference, Run
from .domain import POLICY
from .errors import AppError
from .models import Adjustment, CreateCase, ModuleKey, PartyPatch, Rerun, StartAssessment, Supplement
from .service import Service

KeyHeader = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)]


def create_app(settings=None, database=None):
    settings = settings or Settings()
    db = database or Database(settings)
    svc = Service(db, settings)
    app = FastAPI(
        title="Apex5Vibe Assessment Backend",
        version="0.1.0",
        description="Local TeamRouter assessment API. Higher scores mean higher invoice risk.",
    )
    app.state.service, app.state.db = svc, db
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return JSONResponse(exc.body(uuid.uuid4().hex), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = [{"loc": list(e["loc"]), "message": e["msg"]} for e in exc.errors()]
        error = AppError("VALIDATION_ERROR", "Request fields failed validation.", details={"fields": details})
        return JSONResponse(error.body(uuid.uuid4().hex), status_code=422)

    def command(scope, key, payload, action):
        status, result = svc.command(scope, key, payload, action)
        return JSONResponse(result, status_code=status)

    @app.get("/health", tags=["system"])
    def health():
        with db.sessions() as s:
            s.execute(text("SELECT 1 FROM alembic_version"))
        return {
            "status": "ok",
            "model": settings.teamrouter_model,
            "analyzer_configured": bool(settings.teamrouter_api_key.get_secret_value()),
        }

    @app.get("/v1/capabilities", tags=["system"])
    def capabilities():
        return {
            "api_version": "v1",
            "policy_version": POLICY["policy_version"],
            "engine_mode": "llm",
            "model": settings.teamrouter_model,
            "max_file_bytes": settings.max_file_bytes,
            "max_files_per_request": settings.max_files,
            "formats": [
                {
                    "extension": x,
                    "status": "ready" if x in [".pdf", ".xlsx", ".csv"] else "unavailable",
                    "parser": {".pdf": "acroform_or_text", ".xlsx": "openpyxl", ".csv": "csv"}.get(x),
                }
                for x in [".pdf", ".xlsx", ".csv", ".xls", ".docx", ".doc", ".png", ".jpg"]
            ],
        }

    @app.get("/v1/entities", tags=["entities"])
    def entities(q: str = "", limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        with db.sessions() as s:
            records = [
                r.document["data"]
                for r in s.scalars(
                    select(Reference).where(Reference.kind == "entity_profile").order_by(Reference.id)
                )
            ]
            records = [r for r in records if q.casefold() in r["legal_name"].casefold()]
            records = after_cursor(records, cursor, "entity_id")
            return {
                "items": [
                    {k: r[k] for k in ["entity_id", "legal_name", "tax_id", "country", "address"]}
                    for r in records[:limit]
                ],
                "next_cursor": records[limit - 1]["entity_id"] if len(records) > limit else None,
            }

    @app.post("/v1/cases", tags=["cases"], status_code=201)
    def create_case(body: CreateCase, idempotency_key: KeyHeader):
        return command("POST:/cases", idempotency_key, body.model_dump(), lambda s: svc.create(s, body))

    @app.get("/v1/cases", tags=["cases"])
    def list_cases(
        risk_band: str | None = Query(None, pattern="^(LOW|HIGH)$"),
        stage: str | None = Query(None, pattern="^(draft|extracting|resolving|assessing|result)$"),
        cursor: str | None = None,
        limit: int = Query(50, ge=1, le=100),
    ):
        with db.sessions() as s:
            results = []
            for case in s.scalars(select(Case).order_by(Case.created_at.desc(), Case.id)):
                ws = svc.workspace(s, case)
                aggregate = ws["aggregate"]
                current = aggregate["current_result"]
                display = current or aggregate["last_valid_result"]
                band = display["risk_band"] if display else None
                if risk_band and band != risk_band or stage and case.stage != stage:
                    continue
                results.append(
                    {
                        "case_id": case.id,
                        "invoice_number": case.invoice["invoice_number"] if case.invoice else None,
                        "amount": case.invoice["total"] if case.invoice else None,
                        "currency": case.invoice["currency"] if case.invoice else None,
                        "stage": case.stage,
                        "aggregate_status": aggregate["status"],
                        "risk_band": band,
                        "risk_is_current": bool(current),
                        "decision_status": aggregate["decision"]["status"],
                    }
                )
            results = after_cursor(results, cursor, "case_id")
            return {
                "items": results[:limit],
                "next_cursor": results[limit - 1]["case_id"] if len(results) > limit else None,
            }

    @app.get("/v1/cases/{case_id}", tags=["cases"])
    def workspace(case_id: str):
        with db.sessions() as s:
            return svc.workspace(s, svc.case(s, case_id))

    @app.post("/v1/cases/{case_id}/invoice", tags=["cases"], status_code=202)
    async def invoice(
        case_id: str,
        idempotency_key: KeyHeader,
        file: UploadFile = File(),
        expected_case_revision: int = Form(ge=1),
        replace: bool = Form(False),
    ):
        data = await file.read(settings.max_file_bytes + 1)
        await file.close()
        payload = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "filename": file.filename,
            "expected_case_revision": expected_case_revision,
            "replace": replace,
        }
        return command(
            f"POST:/cases/{case_id}/invoice",
            idempotency_key,
            payload,
            lambda s: svc.upload_invoice(
                s, case_id, file.filename or "", data, expected_case_revision, replace
            ),
        )

    @app.patch("/v1/cases/{case_id}/parties", tags=["entities"])
    def parties(case_id: str, body: PartyPatch, idempotency_key: KeyHeader):
        return command(
            f"PATCH:/cases/{case_id}/parties",
            idempotency_key,
            body.model_dump(),
            lambda s: svc.patch_party(s, case_id, body),
        )

    @app.post("/v1/cases/{case_id}/assessments", tags=["assessments"], status_code=202)
    def assess(case_id: str, body: StartAssessment, idempotency_key: KeyHeader):
        return command(
            f"POST:/cases/{case_id}/assessments",
            idempotency_key,
            body.model_dump(),
            lambda s: svc.start(s, case_id, body),
        )

    @app.get("/v1/cases/{case_id}/modules/{module_key}", tags=["modules"])
    def module_view(case_id: str, module_key: ModuleKey):
        with db.sessions() as s:
            return svc.module_view(s, svc.module(s, case_id, module_key))

    @app.post("/v1/cases/{case_id}/modules/{module_key}/evidence", tags=["modules"], status_code=202)
    async def evidence(
        case_id: str,
        module_key: ModuleKey,
        idempotency_key: KeyHeader,
        files: list[UploadFile] = File(),
        expected_module_version: int = Form(ge=1),
        rerun: bool = Form(False),
        evidence_group: str | None = Form(None, pattern=r"^[a-z][a-z0-9_]{0,63}$"),
        supersedes_evidence_id: str | None = Form(None),
    ):
        if len(files) > settings.max_files:
            raise AppError("INVALID_FILES", "Upload at most 10 files per request.")
        contents = []
        for file in files:
            contents.append((file.filename or "", await file.read(settings.max_file_bytes + 1)))
            await file.close()
        payload = {
            "files": [
                {"filename": name, "sha256": hashlib.sha256(data).hexdigest()} for name, data in contents
            ],
            "expected_module_version": expected_module_version,
            "rerun": rerun,
            "evidence_group": evidence_group,
            "supersedes_evidence_id": supersedes_evidence_id,
        }
        return command(
            f"POST:/cases/{case_id}/{module_key}/evidence",
            idempotency_key,
            payload,
            lambda s: svc.upload_evidence(
                s,
                case_id,
                module_key,
                contents,
                expected_module_version,
                rerun,
                evidence_group,
                supersedes_evidence_id,
            ),
        )

    @app.post("/v1/cases/{case_id}/modules/{module_key}/supplements", tags=["modules"], status_code=202)
    def supplement(case_id: str, module_key: ModuleKey, body: Supplement, idempotency_key: KeyHeader):
        return command(
            f"POST:/cases/{case_id}/{module_key}/supplements",
            idempotency_key,
            body.model_dump(),
            lambda s: svc.supplement(s, case_id, module_key, body),
        )

    @app.post("/v1/cases/{case_id}/modules/{module_key}/runs", tags=["modules"], status_code=202)
    def rerun(case_id: str, module_key: ModuleKey, body: Rerun, idempotency_key: KeyHeader):
        return command(
            f"POST:/cases/{case_id}/{module_key}/runs",
            idempotency_key,
            body.model_dump(),
            lambda s: svc.rerun(s, case_id, module_key, body),
        )

    @app.post("/v1/cases/{case_id}/modules/{module_key}/adjustments", tags=["modules"], status_code=201)
    def adjustment(case_id: str, module_key: ModuleKey, body: Adjustment, idempotency_key: KeyHeader):
        return command(
            f"POST:/cases/{case_id}/{module_key}/adjustments",
            idempotency_key,
            body.model_dump(),
            lambda s: svc.adjust(s, case_id, module_key, body),
        )

    @app.get("/v1/cases/{case_id}/modules/{module_key}/runs/{run_id}", tags=["modules"])
    def run_detail(case_id: str, module_key: ModuleKey, run_id: str):
        with db.sessions() as s:
            svc.module(s, case_id, module_key)
            run = s.get(Run, run_id)
            if not run or run.case_id != case_id or run.module_key != module_key:
                raise AppError("RUN_NOT_FOUND", "Assessment run not found.", 404)
            return {
                "run_id": run.id,
                "case_id": case_id,
                "module_key": module_key,
                "status": run.status,
                "input": run.input,
                "output": run.output,
                "provider": run.provider,
                "error": run.error,
                "created_at": run.created_at,
                "finished_at": run.finished_at,
            }

    @app.get("/v1/jobs/{job_id}", tags=["jobs"])
    def job_view(job_id: str):
        with db.sessions() as s:
            job = s.get(Job, job_id)
            if not job:
                raise AppError("JOB_NOT_FOUND", "Job not found.", 404)
            return svc.job_view(job)

    @app.get("/v1/cases/{case_id}/events", tags=["cases"])
    def events(case_id: str, after_seq: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
        with db.sessions() as s:
            svc.case(s, case_id)
            records = list(
                s.scalars(
                    select(AuditEvent)
                    .where(AuditEvent.case_id == case_id, AuditEvent.seq > after_seq)
                    .order_by(AuditEvent.seq)
                    .limit(limit)
                )
            )
            return {
                "items": [
                    {
                        "event_id": f"event_{e.seq}",
                        "case_id": case_id,
                        "seq": e.seq,
                        "module_key": e.module_key,
                        "type": e.type,
                        "actor_id": e.actor_id,
                        "occurred_at": e.occurred_at,
                        "payload": e.payload,
                    }
                    for e in records
                ],
                "next_after_seq": records[-1].seq if records else after_seq,
            }

    @app.get("/v1/cases/{case_id}/files/{file_id}", tags=["files"])
    def file_download(case_id: str, file_id: str):
        with db.sessions() as s:
            svc.case(s, case_id)
            evidence = s.get(Evidence, file_id)
            if not evidence or evidence.case_id != case_id or not evidence.storage_key:
                raise AppError("FILE_NOT_FOUND", "File not found.", 404)
            target = (svc.storage / evidence.storage_key).resolve()
            if not target.is_relative_to(svc.storage.resolve()) or not target.is_file():
                raise AppError("FILE_NOT_FOUND", "File not found.", 404)
            return FileResponse(target, filename=evidence.filename, content_disposition_type="attachment")

    install_contracts(app)
    return app


def after_cursor(records, cursor, key):
    if cursor is None:
        return records
    for index, record in enumerate(records):
        if record[key] == cursor:
            return records[index + 1 :]
    raise AppError("INVALID_CURSOR", "The list cursor is no longer valid. Reload the list.", 400)
