import hashlib
import time
from pathlib import Path

from sqlalchemy import select

from .db import (
    AuditEvent,
    Case,
    Evidence,
    Idempotency,
    Job,
    ManualAdjustment,
    Module,
    Reference,
    Run,
    Snapshot,
    content_hash,
    now,
    uid,
)
from .domain import CAPS, DEPENDENCIES, POLICY, REFERENCE_KINDS, adjusted_score, decision, module_facts
from .errors import AppError
from .field_sheets import field_sheet, invoice_checks
from .models import MODULES
from .parsers import validate_upload
from .references import select_reference


class Service:
    def __init__(self, db, settings):
        self.db, self.settings = db, settings
        self.storage = settings.data_dir / "files"
        self.storage.mkdir(parents=True, exist_ok=True)

    def command(self, scope, key, payload, action):
        if not key or not 8 <= len(key) <= 128:
            raise AppError("INVALID_IDEMPOTENCY_KEY", "Idempotency-Key需要8到128个字符", 400)
        scope = f"local_demo_analyst:{scope}:{key}"
        request_hash = content_hash(payload)
        with self.db.transaction() as s:
            old = s.get(Idempotency, scope)
            if old and old.expires_at > time.time():
                if old.request_hash != request_hash:
                    raise AppError("IDEMPOTENCY_CONFLICT", "相同幂等键不能用于不同请求", 409)
                return old.status_code, old.response
            if old:
                s.delete(old)
                s.flush()
            status, response = action(s)
            s.add(
                Idempotency(
                    scope=scope,
                    request_hash=request_hash,
                    status_code=status,
                    response=response,
                    expires_at=time.time() + 86400,
                )
            )
            return status, response

    def case(self, s, case_id):
        case = s.get(Case, case_id)
        if not case:
            raise AppError("CASE_NOT_FOUND", "评估Case不存在", 404)
        return case

    def module(self, s, case_id, key):
        self.case(s, case_id)
        module = s.get(Module, (case_id, key))
        if not module:
            raise AppError("MODULE_NOT_FOUND", "评估模块不存在", 404)
        return module

    def expected_case(self, case, revision):
        if case.revision != revision:
            raise AppError(
                "VERSION_CONFLICT",
                "Case已更新，请刷新后重试",
                409,
                details={"current_case_revision": case.revision},
            )

    def expected_module(self, module, version):
        if module.version != version:
            raise AppError(
                "VERSION_CONFLICT",
                "模块已更新，请刷新后重试",
                409,
                details={"current_module_version": module.version},
            )

    def emit(self, s, case, type_, key=None, payload=None, actor="local_demo_analyst"):
        case.revision += 1
        case.updated_at = now()
        s.add(AuditEvent(case_id=case.id, module_key=key, type=type_, payload=payload or {}, actor_id=actor))

    def create(self, s, body):
        parties = body.model_dump(exclude_none=True)
        for selection in parties.values():
            self.validate_selection(s, selection)
        case = Case(id=uid("case"), parties=parties, revision=1)
        s.add(case)
        s.flush()
        for key in MODULES:
            s.add(Module(case_id=case.id, key=key))
        self.emit(s, case, "case_created")
        return 201, {"case_id": case.id, "case_revision": case.revision, "stage": "draft"}

    def validate_selection(self, s, selection):
        if selection["mode"] == "existing":
            if not self.entity(s, selection["entity_id"]):
                raise AppError("ENTITY_NOT_FOUND", "所选主体不存在", 404)

    def entity(self, s, entity_id):
        for r in s.scalars(select(Reference).where(Reference.kind == "entity_profile")):
            if r.document["data"]["entity_id"] == entity_id:
                return r.document["data"]
        return None

    def resolve_parties(self, s, case):
        invoice = dict(case.invoice)
        parties = dict(case.parties)
        for side in ["buyer", "seller"]:
            existing_context = parties[side]
            selection = existing_context.get("selection", existing_context)
            extracted = dict(invoice[side])
            matches = [
                r.document["data"]
                for r in s.scalars(select(Reference).where(Reference.kind == "entity_profile"))
                if r.document["data"].get("tax_id") == extracted["tax_id"]
                and r.document["data"].get("country") == extracted["country"]
            ]
            if len(matches) > 1:
                raise AppError("ENTITY_AMBIGUOUS", "主体注册号匹配到多个档案，请核对")
            profile = matches[0] if matches else None
            if profile is None:
                entity_id = uid("entity")
                profile = {**extracted, "entity_id": entity_id, "verification_status": "provisional"}
                source_id = uid("profile")
                s.add(
                    Reference(
                        id=source_id,
                        kind="entity_profile",
                        document={
                            "source_id": source_id,
                            "kind": "entity_profile",
                            "synthetic": invoice["synthetic"],
                            "source_type": "invoice_provisional",
                            "as_of": POLICY["as_of"],
                            "data": profile,
                        },
                    )
                )
            extracted["entity_id"] = profile["entity_id"]
            status = (
                "matched" if profile.get("verification_status") == "demo_local_verified" else "provisional"
            )
            if selection["mode"] == "existing" and selection["entity_id"] != profile["entity_id"]:
                status = "conflict"
            if selection["mode"] == "manual":
                if selection["legal_name"].casefold().strip() != extracted["legal_name"].casefold().strip():
                    status = "conflict"
                for field in ["tax_id", "country"]:
                    if selection.get(field) and selection[field].casefold() != extracted[field].casefold():
                        status = "conflict"
            if existing_context.get("resolution_action") == "use_invoice_entity":
                status = (
                    "matched"
                    if profile.get("verification_status") == "demo_local_verified"
                    else "provisional"
                )
            parties[side] = {
                "side": side,
                "selection": selection,
                "invoice_entity": extracted,
                "resolved_entity_id": None if status == "conflict" else profile["entity_id"],
                "status": status,
                "reason": "对照发票注册号与辖区匹配本地资料",
                "resolution_action": existing_context.get("resolution_action"),
            }
            invoice[side] = extracted
        case.invoice, case.parties = invoice, parties

    def upload_invoice(self, s, case_id, filename, data, revision, replace):
        case = self.case(s, case_id)
        self.expected_case(case, revision)
        if Path(filename).suffix.lower() != ".pdf":
            raise AppError("UNSUPPORTED_PARSER", "主发票请使用PDF", 415)
        validate_upload(filename, data, self.settings.max_file_bytes)
        if case.invoice and not replace:
            raise AppError("INVOICE_EXISTS", "已有主发票，替换需明确设置replace=true", 409)
        active = s.scalar(
            select(Job).where(
                Job.case_id == case_id,
                Job.kind != "initial_assessment",
                Job.status.in_(["queued", "running"]),
            )
        )
        if active:
            raise AppError("RUN_ALREADY_ACTIVE", "请等待当前任务完成再替换主发票", 409)
        evidence = self.store_file(s, case_id, None, filename, data, "invoice")
        case.error = None
        case.stage = "extracting"
        case.initial_status = "not_started"
        for module in s.scalars(select(Module).where(Module.case_id == case_id)):
            self.invalidate(module)
        job = Job(id=uid("job"), case_id=case_id, kind="parse_invoice", payload={"evidence_id": evidence.id})
        s.add(job)
        self.emit(s, case, "invoice_uploaded", payload={"evidence_id": evidence.id})
        s.flush()
        return 202, self.accepted(case_id, None, job, evidence_ids=[evidence.id])

    def patch_party(self, s, case_id, body):
        case = self.case(s, case_id)
        self.expected_case(case, body.expected_case_revision)
        if not case.invoice or case.stage == "extracting":
            raise AppError("INVOICE_NOT_READY", "请先等待主发票解析完成")
        selection = body.selection.model_dump(exclude_none=True)
        self.validate_selection(s, selection)
        case.parties = {
            **case.parties,
            body.side: {"selection": selection, "resolution_action": body.resolution_action},
        }
        self.resolve_parties(s, case)
        if case.initial_status != "not_started":
            for key in DEPENDENCIES["public_inputs"][f"{body.side}_identity"]:
                module = self.module(s, case_id, key)
                self.invalidate(module)
                if case.parties[body.side]["status"] != "conflict":
                    self.queue(s, case, module, allow_defer=True)
        self.emit(s, case, "party_resolved", payload={"side": body.side, "reason": body.reason})
        self.refresh(s, case)
        return 200, self.workspace(s, case)

    def start(self, s, case_id, body):
        case = self.case(s, case_id)
        self.expected_case(case, body.expected_case_revision)
        if not case.invoice or case.stage == "extracting" or case.error:
            raise AppError("INVOICE_NOT_READY", "主发票尚未解析成功")
        if any(p["status"] == "conflict" for p in case.parties.values()):
            raise AppError("ENTITY_CONFLICT", "请先解决买卖方主体冲突")
        if case.initial_status != "not_started":
            raise AppError("ASSESSMENT_ALREADY_STARTED", "初次评估已启动，请使用模块重跑", 409)
        case.initial_status, case.stage = "running", "assessing"
        run_ids = []
        for key in MODULES:
            job = self.queue(s, case, self.module(s, case_id, key), initial=True)
            run_ids.append(job.payload["run_id"])
        batch = Job(
            id=uid("job"),
            case_id=case_id,
            kind="initial_assessment",
            status="running",
            payload={"run_ids": run_ids},
        )
        s.add(batch)
        self.emit(s, case, "initial_assessment_started")
        s.flush()
        return 202, self.accepted(case_id, None, batch)

    def invalidate(self, module):
        module.input_version += 1
        module.version += 1
        module.freshness = "stale" if module.current_run_id else "none"

    def active_job(self, s, module):
        return s.scalar(
            select(Job).where(
                Job.case_id == module.case_id,
                Job.module_key == module.key,
                Job.kind == "module_run",
                Job.status.in_(["queued", "running"]),
            )
        )

    def queue(self, s, case, module, initial=False, allow_defer=False):
        active = self.active_job(s, module)
        if active:
            if not allow_defer:
                raise AppError("RUN_ALREADY_ACTIVE", "此模块正在评估", 409, details={"job_id": active.id})
            module.rerun_requested = True
            return active
        if not case.invoice or case.stage == "extracting" or case.error:
            raise AppError("INVOICE_NOT_READY", "主发票不可用于评估")
        if any(p.get("status") == "conflict" for p in case.parties.values()):
            if allow_defer:
                module.state, module.rerun_requested = "needs_info", False
                module.error = AppError("ENTITY_CONFLICT", "请先解决主体冲突").body()
                return None
            raise AppError("ENTITY_CONFLICT", "请先解决主体冲突")
        unparsed = s.scalar(
            select(Evidence).where(
                Evidence.case_id == case.id,
                Evidence.module_key == module.key,
                Evidence.status.in_(["pending", "failed"]),
                Evidence.parse_status != "ready",
            )
        )
        if unparsed:
            if allow_defer and unparsed.parse_status == "pending":
                module.rerun_requested = True
                return None
            if allow_defer:
                module.rerun_requested = False
                module.state, module.error = "needs_info", unparsed.error
                return None
            raise AppError("EVIDENCE_NOT_READY", "模块证据仍在解析或已解析失败")
        run = Run(
            id=uid("run"),
            case_id=case.id,
            module_key=module.key,
            input_version=module.input_version,
            initial=initial,
        )
        s.add(run)
        job = Job(
            id=uid("job"),
            case_id=case.id,
            module_key=module.key,
            kind="module_run",
            payload={"run_id": run.id},
        )
        s.add(job)
        module.state, module.error = "queued", None
        module.version += 1
        module.rerun_requested = False
        # An explicit rerun also suspends use of the previous score for financing.
        module.freshness = "stale" if module.current_run_id else "none"
        s.flush()
        return job

    def rerun(self, s, case_id, key, body):
        case, module = self.case(s, case_id), self.module(s, case_id, key)
        self.expected_module(module, body.expected_module_version)
        job = self.queue(s, case, module)
        self.emit(s, case, "module_rerun_requested", key, {"reason": body.reason})
        return 202, self.accepted(case_id, key, job, module)

    def supplement(self, s, case_id, key, body):
        case, module = self.case(s, case_id), self.module(s, case_id, key)
        self.expected_module(module, body.expected_module_version)
        evidence = Evidence(
            id=uid("note"),
            case_id=case_id,
            module_key=key,
            kind="note",
            content={"text": body.text},
            parse_status="ready",
        )
        s.add(evidence)
        self.invalidate(module)
        s.flush()
        job = self.queue(s, case, module, allow_defer=True) if body.rerun else None
        self.emit(s, case, "supplement_saved", key, {"evidence_id": evidence.id, "rerun": body.rerun})
        return 202, self.accepted(case_id, key, job, module, [evidence.id])

    def store_file(self, s, case_id, key, filename, data, kind="file"):
        evidence_id = uid("file")
        relative = f"{case_id}/{evidence_id}"
        target = self.storage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        evidence = Evidence(
            id=evidence_id,
            case_id=case_id,
            module_key=key,
            kind=kind,
            filename=Path(filename).name,
            sha256=hashlib.sha256(data).hexdigest(),
            storage_key=relative,
            status="pending",
        )
        s.add(evidence)
        return evidence

    def upload_evidence(
        self,
        s,
        case_id,
        key,
        files,
        expected_version,
        rerun,
        evidence_group=None,
        supersedes_evidence_id=None,
    ):
        case, module = self.case(s, case_id), self.module(s, case_id, key)
        self.expected_module(module, expected_version)
        if not 1 <= len(files) <= self.settings.max_files:
            raise AppError("INVALID_FILES", "每次请上传1到10个文件")
        for name, data in files:
            validate_upload(name, data, self.settings.max_file_bytes)
        if supersedes_evidence_id and not evidence_group:
            raise AppError("EVIDENCE_GROUP_REQUIRED", "替代上传必须指定evidence_group")
        if evidence_group and len(files) != 1:
            raise AppError("INVALID_FILES", "每个证据组一次只能上传一个版本")
        if evidence_group == "invoice_field_sheet" and (
            key != "invoice_integrity" or Path(files[0][0]).suffix.lower() != ".xlsx"
        ):
            raise AppError("INVALID_EVIDENCE_GROUP", "invoice_field_sheet需要invoice_integrity模块的XLSX文件")
        group_versions = (
            list(
                s.scalars(
                    select(Evidence).where(
                        Evidence.case_id == case_id,
                        Evidence.module_key == key,
                        Evidence.evidence_group == evidence_group,
                    )
                )
            )
            if evidence_group
            else []
        )
        active = next((e for e in group_versions if e.status == "active"), None)
        replacement = s.get(Evidence, supersedes_evidence_id) if supersedes_evidence_id else None
        if supersedes_evidence_id and (
            not replacement
            or replacement.case_id != case_id
            or replacement.module_key != key
            or replacement.evidence_group != evidence_group
            or replacement.status != "active"
        ):
            raise AppError("INVALID_REPLACEMENT", "只能替代同Case、同模块、同组的当前有效证据", 409)
        ids, job, added = [], None, False
        for name, data in files:
            sha = hashlib.sha256(data).hexdigest()
            duplicate = s.scalar(
                select(Evidence).where(
                    Evidence.case_id == case_id,
                    Evidence.module_key == key,
                    Evidence.kind == "file",
                    Evidence.evidence_group == evidence_group,
                    Evidence.status.in_(["active", "pending"]),
                    Evidence.sha256 == sha,
                )
            )
            if duplicate:
                ids.append(duplicate.id)
                continue
            if evidence_group:
                if any(e.status == "pending" for e in group_versions):
                    raise AppError("REPLACEMENT_PENDING", "此证据组的新版本仍在解析", 409)
                if active and not replacement:
                    raise AppError(
                        "REPLACEMENT_REQUIRED", "当前组已有有效证据，请显式指定supersedes_evidence_id", 409
                    )
            evidence = self.store_file(s, case_id, key, name, data)
            evidence.evidence_group = evidence_group
            evidence.version = max((e.version for e in group_versions), default=0) + 1
            evidence.supersedes_evidence_id = supersedes_evidence_id
            ids.append(evidence.id)
            job = Job(
                id=uid("job"),
                case_id=case_id,
                module_key=key,
                kind="parse_evidence",
                payload={"evidence_id": evidence.id},
            )
            s.add(job)
            added = True
            s.flush()
        if added:
            self.invalidate(module)
        if rerun:
            module.rerun_requested = True
            if not added:
                job = self.queue(s, case, module, allow_defer=True)
        self.emit(s, case, "evidence_uploaded", key, {"evidence_ids": ids, "deduplicated": not added})
        s.flush()
        return 202, self.accepted(case_id, key, job, module, ids)

    def activate_evidence(self, s, evidence, module):
        if evidence.evidence_group:
            old = (
                s.get(Evidence, evidence.supersedes_evidence_id) if evidence.supersedes_evidence_id else None
            )
            if old and old.status != "active":
                raise AppError("REPLACEMENT_CONFLICT", "被替代证据已不是有效版本", 409)
            for previous in s.scalars(
                select(Evidence).where(
                    Evidence.case_id == evidence.case_id,
                    Evidence.module_key == evidence.module_key,
                    Evidence.evidence_group == evidence.evidence_group,
                    Evidence.id != evidence.id,
                )
            ):
                if previous.status in ["active", "failed"]:
                    previous.status = "superseded"
            s.flush()
        evidence.status = "active"
        self.invalidate(module)

    def adjust(self, s, case_id, key, body):
        case, module = self.case(s, case_id), self.module(s, case_id, key)
        self.expected_module(module, body.expected_module_version)
        run = s.get(Run, module.current_run_id) if module.current_run_id else None
        if (
            not run
            or module.state != "succeeded"
            or module.freshness != "current"
            or self.active_job(s, module)
        ):
            raise AppError("ASSESSMENT_NOT_CURRENT", "请等待目标模块当前评估完成后再调整", 409)
        if body.applies_to_run_id != run.id:
            raise AppError("VERSION_CONFLICT", "人工调整必须绑定当前AI运行", 409)
        _, effective = adjusted_score(run.output["ai_score"], body.requested_adjustment, CAPS[key])
        for old in self.adjustments(s, module):
            if old.status in ["active", "pending_review"]:
                old.status = "superseded"
        s.flush()
        s.add(
            ManualAdjustment(
                id=uid("adjustment"),
                case_id=case_id,
                module_key=key,
                run_id=run.id,
                requested=body.requested_adjustment,
                effective=effective,
                reason=body.reason,
            )
        )
        module.version += 1
        self.emit(
            s,
            case,
            "manual_adjustment_set",
            key,
            {"requested": body.requested_adjustment, "effective": effective, "reason": body.reason},
        )
        self.refresh(s, case)
        return 201, self.module_view(s, module)

    def adjustments(self, s, module):
        return list(
            s.scalars(
                select(ManualAdjustment)
                .where(ManualAdjustment.case_id == module.case_id, ManualAdjustment.module_key == module.key)
                .order_by(ManualAdjustment.created_at)
            )
        )

    def module_view(self, s, module):
        run = s.get(Run, module.current_run_id) if module.current_run_id else None
        adjustments = self.adjustments(s, module)
        active = next((a for a in adjustments if a.status == "active"), None)
        pending = any(a.status == "pending_review" for a in adjustments)
        ai_score = run.output["ai_score"] if run and run.output else None
        requested = active.requested if active else 0
        final, effective = (
            adjusted_score(ai_score, requested, CAPS[module.key]) if ai_score is not None else (None, 0)
        )
        evidence = list(
            s.scalars(
                select(Evidence)
                .where(Evidence.case_id == module.case_id, Evidence.module_key == module.key)
                .order_by(Evidence.created_at)
            )
        )
        case = self.case(s, module.case_id)
        evidence_views = [self.evidence_view(e) for e in evidence if e.kind != "note"]
        if case.invoice:
            original = s.get(Evidence, case.invoice["source_refs"][0]["source_id"])
            if original:
                evidence_views.insert(0, self.evidence_view(original))
        if run and run.input:
            for record in run.input["reference_records"]:
                evidence_views.append(
                    {
                        "evidence_id": record["source_id"],
                        "source_id": record["source_id"],
                        "kind": "reference",
                        "file_id": None,
                        "filename": None,
                        "sha256": None,
                        "parse_status": "ready",
                        "status": "active",
                        "error": None,
                        "source_ref": {
                            "source_id": record["source_id"],
                            "locator": "local_reference",
                            "kind": "authored_demo_seed",
                        },
                    }
                )
        assessable = (
            bool(case.invoice)
            and case.stage != "extracting"
            and not case.error
            and not any(p.get("status") == "conflict" for p in case.parties.values())
        )
        actions = ["upload_evidence", "save_information", "full_view"]
        if assessable:
            actions.append("save_and_rerun")
        if (
            assessable
            and not self.active_job(s, module)
            and not any(e.status in ["pending", "failed"] for e in evidence)
        ):
            actions.append("rerun")
            if module.state == "succeeded" and module.freshness == "current":
                actions.append("adjust")
        return {
            "case_id": module.case_id,
            "module_key": module.key,
            "cap": CAPS[module.key],
            "module_version": module.version,
            "input_version": module.input_version,
            "evaluated_input_version": module.evaluated_version,
            "state": module.state,
            "freshness": module.freshness,
            "current_run": run.output if run else None,
            "adjustment_status": "pending_review" if pending else "active" if active else "none",
            "requested_adjustment": requested,
            "effective_adjustment": effective,
            "final_score": final,
            "allowed_actions": actions,
            "error": module.error,
            "evidence": evidence_views,
            "supplements": [
                {
                    "supplement_id": e.id,
                    "text": e.content["text"],
                    "author_id": "local_demo_analyst",
                    "created_at": e.created_at,
                    "source_ref": {"source_id": e.id, "locator": "text", "kind": "analyst_statement"},
                }
                for e in evidence
                if e.kind == "note"
            ],
            "manual_adjustments": [
                {
                    "adjustment_id": a.id,
                    "applies_to_run_id": a.run_id,
                    "requested_adjustment": a.requested,
                    "effective_adjustment": a.effective,
                    "reason": a.reason,
                    "actor_id": a.actor_id,
                    "status": a.status,
                    "created_at": a.created_at,
                }
                for a in adjustments
            ],
            "run_history": [
                {
                    "run_id": r.id,
                    "input_version": r.input_version,
                    "status": r.status,
                    "ai_score": r.output["ai_score"] if r.output else None,
                    "created_at": r.created_at,
                    "finished_at": r.finished_at,
                }
                for r in s.scalars(
                    select(Run)
                    .where(Run.case_id == module.case_id, Run.module_key == module.key)
                    .order_by(Run.created_at)
                )
            ],
        }

    def evidence_view(self, e):
        return {
            "evidence_id": e.id,
            "source_id": e.id,
            "kind": "file",
            "file_id": e.id,
            "filename": e.filename,
            "sha256": e.sha256,
            "parse_status": e.parse_status,
            "status": e.status,
            "evidence_group": e.evidence_group,
            "version": e.version,
            "supersedes_evidence_id": e.supersedes_evidence_id,
            "error": e.error,
            "source_ref": {
                "source_id": e.id,
                "locator": "parsed_content",
                "kind": "user_pdf" if e.kind == "invoice" else "uploaded_file",
            },
        }

    def module_views(self, s, case):
        return [self.module_view(s, self.module(s, case.id, key)) for key in MODULES]

    def current(self, case, views):
        return (
            bool(case.invoice)
            and not case.error
            and case.stage != "extracting"
            and not any(p.get("status") == "conflict" for p in case.parties.values())
            and all(
                m["state"] == "succeeded"
                and m["freshness"] == "current"
                and m["evaluated_input_version"] == m["input_version"]
                for m in views
            )
        )

    def refresh(self, s, case):
        s.flush()
        views = self.module_views(s, case)
        if not self.current(case, views):
            return
        total = sum(m["final_score"] for m in views)
        vector = [
            {
                "module_key": m["module_key"],
                "run_id": m["current_run"]["run_id"],
                "input_version": m["input_version"],
                "final_score": m["final_score"],
            }
            for m in views
        ]
        if case.last_result and case.last_result["module_versions"] == vector:
            return
        case.aggregate_revision += 1
        case.last_result = {
            "snapshot_id": uid("snapshot"),
            "aggregate_revision": case.aggregate_revision,
            "ai_total": sum(m["current_run"]["ai_score"] for m in views),
            "effective_adjustment_total": sum(m["effective_adjustment"] for m in views),
            "final_risk_score": total,
            "risk_band": "LOW" if total < POLICY["high_min_inclusive"] else "HIGH",
            "module_versions": vector,
            "policy_version": POLICY["policy_version"],
            "created_at": now(),
        }
        s.add(Snapshot(id=case.last_result["snapshot_id"], case_id=case.id, document=case.last_result))
        self.emit(s, case, "aggregate_updated", payload={"score": total}, actor="worker")

    def workspace(self, s, case):
        views = self.module_views(s, case)
        valid = self.current(case, views)
        current = case.last_result if valid else None
        failures = any(m["state"] in ["failed", "needs_info"] for m in views)
        status = (
            "current"
            if current
            else "incomplete"
            if failures
            else "stale"
            if case.last_result
            else "unavailable"
        )
        blockers = [flag for m in views if m["current_run"] for flag in m["current_run"]["blocking_flags"]]
        pending = any(m["adjustment_status"] == "pending_review" for m in views)
        return {
            "case_id": case.id,
            "case_revision": case.revision,
            "stage": case.stage,
            "initial_assessment_status": case.initial_status,
            "invoice": case.invoice,
            "parties": [case.parties[side] for side in ["seller", "buyer"]],
            "modules": views,
            "aggregate": {
                "status": status,
                "current_result": current,
                "last_valid_result": case.last_result,
                "decision": decision(
                    current["final_risk_score"] if current else None, case.invoice, blockers, pending
                ),
            },
            "engine_mode": "llm",
            "error": case.error,
            "navigation": {
                "target": "result"
                if case.initial_status == "settled"
                else "assessment"
                if case.initial_status == "running"
                else "resolve"
                if case.invoice
                else "upload",
                "reason": "initial_assessment_settled" if case.initial_status == "settled" else None,
            },
        }

    def inputs(self, s, case, module):
        records = []
        for reference in s.scalars(select(Reference).where(Reference.kind.in_(REFERENCE_KINDS[module.key]))):
            doc = select_reference(reference.document, module.key, case.invoice, POLICY["as_of"])
            if doc:
                records.append(doc)
        source = case.invoice["source_refs"][0]
        sources = [source] + [
            {"source_id": r["source_id"], "locator": "local_reference", "kind": "authored_demo_seed"}
            for r in records
        ]
        evidence = []
        for e in s.scalars(
            select(Evidence).where(
                Evidence.case_id == case.id, Evidence.module_key == module.key, Evidence.status == "active"
            )
        ):
            if e.parse_status != "ready":
                raise AppError("EVIDENCE_NOT_READY", "模块证据尚未解析成功")
            sources.append(
                {
                    "source_id": e.id,
                    "locator": "text" if e.kind == "note" else "parsed_content",
                    "kind": "analyst_statement" if e.kind == "note" else "uploaded_file",
                }
            )
            content = dict(e.content)
            if module.key == "invoice_integrity" and e.kind == "file":
                mapped = field_sheet(content, e.id, case.invoice)
                if mapped:
                    content["field_sheet"] = mapped
            evidence.append({"source_id": e.id, "kind": e.kind, "content": content})
        facts = module_facts(module.key, case.invoice)
        if module.key == "invoice_integrity":
            facts["deterministic_checks"] = invoice_checks(case.invoice)
        return {
            "case_id": case.id,
            "module_key": module.key,
            "input_version": module.input_version,
            "as_of": POLICY["as_of"],
            "policy_version": POLICY["policy_version"],
            "facts": facts,
            "reference_records": records,
            "sources": sources,
            "evidence": evidence,
        }

    def settle_initial(self, s, case):
        if case.initial_status != "running":
            return
        batches = list(
            s.scalars(
                select(Job).where(
                    Job.case_id == case.id, Job.kind == "initial_assessment", Job.status == "running"
                )
            )
        )
        for batch in batches:
            runs = [s.get(Run, r) for r in batch.payload["run_ids"]]
            if all(r.status in ["succeeded", "needs_info", "failed", "superseded"] for r in runs):
                batch.status = "succeeded"
                case.initial_status, case.stage = "settled", "result"
                self.emit(s, case, "initial_assessment_settled", actor="worker")

    def job_view(self, job):
        return {
            "job_id": job.id,
            "case_id": job.case_id,
            "module_key": job.module_key,
            "kind": job.kind,
            "status": job.status,
            "attempt": job.attempt,
            "error": job.error,
        }

    def accepted(self, case_id, key, job=None, module=None, evidence_ids=None):
        return {
            "case_id": case_id,
            "module_key": key,
            "job": self.job_view(job) if job else None,
            "input_version": module.input_version if module else None,
            "module_version": module.version if module else None,
            "evidence_ids": evidence_ids or [],
        }
