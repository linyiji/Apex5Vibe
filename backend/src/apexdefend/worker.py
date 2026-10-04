import logging
import threading
import time

from sqlalchemy import and_, or_, select

from .analyzer import TeamRouterAnalyzer
from .config import Settings
from .db import Database, Evidence, Job, Run, now
from .domain import POLICY, REFERENCE_KINDS, score_analysis
from .errors import AppError
from .field_sheets import field_sheet
from .models import AIAnalysis
from .parsers import parse_evidence, parse_invoice
from .service import Service

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, service, analyzer):
        self.service, self.db, self.analyzer = service, service.db, analyzer

    def claim(self):
        with self.db.transaction() as s:
            current = time.time()
            job = s.scalar(
                select(Job)
                .where(
                    Job.kind != "initial_assessment",
                    or_(
                        and_(Job.status == "queued", Job.available_at <= current),
                        and_(Job.status == "running", Job.lease_until < current),
                    ),
                )
                .order_by(Job.created_at)
                .limit(1)
            )
            if not job:
                return None
            job.status = "running"
            job.attempt += 1
            job.fencing_token += 1
            job.lease_until = current + self.service.settings.lease_seconds
            case = self.service.case(s, job.case_id)
            if job.kind == "module_run":
                module = self.service.module(s, case.id, job.module_key)
                module.state = "running"
                module.version += 1
                s.get(Run, job.payload["run_id"]).status = "running"
            self.service.emit(
                s,
                case,
                "job_started",
                job.module_key,
                {"job_id": job.id, "attempt": job.attempt},
                actor="worker",
            )
            return job.id, job.fencing_token

    def owned(self, s, job_id, token):
        job = s.get(Job, job_id)
        if not job or job.status != "running" or job.fencing_token != token:
            return None
        return job

    def heartbeat(self, job_id, token, stop):
        while not stop.wait(20):
            try:
                with self.db.transaction() as s:
                    job = self.owned(s, job_id, token)
                    if not job:
                        return
                    job.lease_until = time.time() + self.service.settings.lease_seconds
            except Exception:
                logger.exception("Worker heartbeat failed")

    def run_once(self):
        claimed = self.claim()
        if not claimed:
            return False
        job_id, token = claimed
        stop = threading.Event()
        heartbeat = threading.Thread(target=self.heartbeat, args=(job_id, token, stop), daemon=True)
        heartbeat.start()
        try:
            self.process(job_id, token)
        except AppError as error:
            self.fail(job_id, token, error)
        except Exception:
            logger.exception("Unexpected job failure: %s", job_id)
            self.fail(
                job_id,
                token,
                AppError("JOB_FAILED", "The background job failed. Check the server logs.", 500),
            )
        finally:
            stop.set()
            heartbeat.join(timeout=2)
        return True

    def process(self, job_id, token):
        with self.db.transaction() as s:
            job = self.owned(s, job_id, token)
            if not job:
                return
            if job.attempt > 3:
                raise AppError("ATTEMPTS_EXHAUSTED", "Job recovery exceeded the retry limit.")
            kind, payload, case_id = job.kind, job.payload, job.case_id
            if kind == "module_run":
                case = self.service.case(s, case_id)
                module = self.service.module(s, case_id, job.module_key)
                run = s.get(Run, payload["run_id"])
                if run.input_version != module.input_version:
                    self.supersede(s, job, run, module, case)
                    return
                if run.input is None:
                    run.input = self.service.inputs(s, case, module)
                inputs = run.input
            else:
                evidence = s.get(Evidence, payload["evidence_id"])
                if not evidence or evidence.case_id != case_id:
                    raise AppError("FILE_NOT_FOUND", "The file for this job could not be found.", 404)
                path = self.service.storage / evidence.storage_key
                filename, evidence_id = evidence.filename, evidence.id
                group, target_module = evidence.evidence_group, job.module_key
                invoice_snapshot = self.service.case(s, case_id).invoice
        # File parsing and model calls are intentionally outside all DB transactions.
        if kind == "module_run":
            missing = set(REFERENCE_KINDS[inputs["module_key"]]) - {
                r["kind"] for r in inputs["reference_records"]
            }
            if missing:
                analysis = AIAnalysis(
                    status="needs_info",
                    summary="Required local reference data matching this invoice is missing.",
                    matched_rule_ids=[],
                    findings=[],
                    missing_inputs=sorted(missing),
                )
                provider = {
                    "provider": "local_validation",
                    "requested_model": self.service.settings.teamrouter_model,
                    "reported_model": None,
                }
            else:
                analysis, provider = self.analyzer.analyze(inputs, POLICY)
            output = score_analysis(
                analysis, inputs, payload["run_id"], self.service.settings.teamrouter_model
            )
            if missing:
                output["provenance"].update(analyzer="local_validation", model=None)
        else:
            data = path.read_bytes()
            output = (
                parse_invoice(data, evidence_id)
                if kind == "parse_invoice"
                else parse_evidence(filename, data)
            )
            provider = None
            if kind == "parse_evidence" and target_module == "invoice_integrity":
                mapped = field_sheet(output, evidence_id, invoice_snapshot)
                if group == "invoice_field_sheet" and not mapped:
                    raise AppError(
                        "INVALID_FIELD_SHEET", "The field sheet requires a worksheet named Invoice Fields."
                    )
                if mapped:
                    output["field_sheet"] = mapped
        with self.db.transaction() as s:
            job = self.owned(s, job_id, token)
            if not job:
                return
            case = self.service.case(s, case_id)
            if kind == "module_run":
                run = s.get(Run, payload["run_id"])
                module = self.service.module(s, case_id, job.module_key)
                run.output, run.provider, run.finished_at = output, provider, now()
                if module.input_version != run.input_version:
                    self.supersede(s, job, run, module, case)
                    return
                run.status = output["state"]
                module.state, module.error = output["state"], None
                module.version += 1
                if output["state"] == "succeeded":
                    module.current_run_id, module.evaluated_version = run.id, run.input_version
                    module.freshness = "current"
                    for adj in self.service.adjustments(s, module):
                        if adj.status == "active" and adj.run_id != run.id:
                            adj.status = "pending_review"
                else:
                    module.freshness = "stale" if module.current_run_id else "none"
                    module.error = AppError(
                        "MISSING_INPUTS",
                        output["summary"],
                        details={"missing_inputs": output["missing_inputs"], "run_id": run.id},
                    ).body()
            else:
                evidence = s.get(Evidence, payload["evidence_id"])
                evidence.content, evidence.parse_status, evidence.error = output, "ready", None
                if kind == "parse_invoice":
                    evidence.status = "active"
                    case.invoice, case.error, case.stage = output, None, "resolving"
                    self.service.resolve_parties(s, case)
                else:
                    module = self.service.module(s, case_id, job.module_key)
                    self.service.activate_evidence(s, evidence, module)
                    if module.rerun_requested:
                        s.flush()
                        if not s.scalar(
                            select(Evidence).where(
                                Evidence.case_id == case_id,
                                Evidence.module_key == module.key,
                                Evidence.status.in_(["pending", "failed"]),
                                Evidence.parse_status != "ready",
                            )
                        ):
                            self.service.queue(s, case, module, allow_defer=True)
            job.status, job.lease_until, job.error = "succeeded", None, None
            self.service.emit(s, case, "job_completed", job.module_key, {"job_id": job.id}, actor="worker")
            self.service.settle_initial(s, case)
            self.service.refresh(s, case)

    def supersede(self, s, job, run, module, case):
        job.status, job.lease_until = "superseded", None
        run.status, run.finished_at = "superseded", now()
        module.state = (
            "succeeded" if module.current_run_id else "needs_info" if run.initial else "not_started"
        )
        module.freshness = "stale" if module.current_run_id else "none"
        module.version += 1
        s.flush()
        if module.rerun_requested:
            self.service.queue(s, case, module, allow_defer=True)
        self.service.emit(s, case, "run_superseded", module.key, {"run_id": run.id}, actor="worker")
        self.service.settle_initial(s, case)
        self.service.refresh(s, case)

    def fail(self, job_id, token, error):
        with self.db.transaction() as s:
            job = self.owned(s, job_id, token)
            if not job:
                return
            case = self.service.case(s, job.case_id)
            if job.kind == "module_run":
                run = s.get(Run, job.payload["run_id"])
                module = self.service.module(s, case.id, job.module_key)
                if run.input_version != module.input_version:
                    run.error = error.body()
                    self.supersede(s, job, run, module, case)
                    return
            job.error = error.body()
            job.lease_until = None
            if error.retryable and job.attempt < 3:
                job.status, job.available_at = "queued", time.time() + (1 if job.attempt == 1 else 3)
                if job.kind == "module_run":
                    s.get(Run, job.payload["run_id"]).status = "queued"
                    module = self.service.module(s, case.id, job.module_key)
                    module.state = "queued"
                    module.version += 1
                self.service.emit(
                    s, case, "job_retry_scheduled", job.module_key, {"code": error.code}, actor="worker"
                )
                return
            job.status = "failed"
            if job.kind == "module_run":
                run = s.get(Run, job.payload["run_id"])
                run.error, run.status, run.finished_at = error.body(), "failed", now()
                module = self.service.module(s, case.id, job.module_key)
                module.state, module.error = "failed", error.body()
                module.freshness = "stale" if module.current_run_id else "none"
                module.version += 1
                s.flush()
                if module.rerun_requested:
                    self.service.queue(s, case, module, allow_defer=True)
            else:
                evidence = s.get(Evidence, job.payload["evidence_id"])
                evidence.error, evidence.parse_status = error.body(), "failed"
                evidence.status = "failed"
                if job.kind == "parse_invoice":
                    case.error, case.stage = error.body(), "draft"
                else:
                    module = self.service.module(s, case.id, job.module_key)
                    module.state, module.error, module.rerun_requested = "needs_info", error.body(), False
                    module.version += 1
            self.service.emit(s, case, "job_failed", job.module_key, {"code": error.code}, actor="worker")
            self.service.settle_initial(s, case)
            self.service.refresh(s, case)


def main():
    settings = Settings()
    database = Database(settings)
    worker = Worker(Service(database, settings), TeamRouterAnalyzer(settings))
    logging.basicConfig(level=logging.INFO)
    logger.info("Worker ready; model=%s; no provider fallback", settings.teamrouter_model)
    try:
        while True:
            if not worker.run_once():
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
