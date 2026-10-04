import hashlib
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import JSON, Float, Integer, String, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(timezone.utc).isoformat()


def uid(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def content_hash(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(default=1)
    stage: Mapped[str] = mapped_column(default="draft")
    initial_status: Mapped[str] = mapped_column(default="not_started")
    invoice: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parties: Mapped[dict] = mapped_column(JSON)
    last_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    aggregate_revision: Mapped[int] = mapped_column(default=0)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class Module(Base):
    __tablename__ = "modules"
    case_id: Mapped[str] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(default=1)
    input_version: Mapped[int] = mapped_column(default=1)
    evaluated_version: Mapped[int | None] = mapped_column(nullable=True)
    state: Mapped[str] = mapped_column(default="not_started")
    freshness: Mapped[str] = mapped_column(default="none")
    current_run_id: Mapped[str | None] = mapped_column(nullable=True)
    rerun_requested: Mapped[bool] = mapped_column(default=False)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Run(Base):
    __tablename__ = "module_runs"
    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(index=True)
    module_key: Mapped[str]
    input_version: Mapped[int]
    input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(default="queued")
    initial: Mapped[bool] = mapped_column(default=False)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(default=now)
    finished_at: Mapped[str | None] = mapped_column(nullable=True)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(index=True)
    module_key: Mapped[str | None] = mapped_column(nullable=True)
    kind: Mapped[str]
    status: Mapped[str] = mapped_column(default="queued", index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    attempt: Mapped[int] = mapped_column(default=0)
    fencing_token: Mapped[int] = mapped_column(default=0)
    lease_until: Mapped[float | None] = mapped_column(Float, nullable=True)
    available_at: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(default=now)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(index=True)
    module_key: Mapped[str | None] = mapped_column(nullable=True)
    kind: Mapped[str]
    filename: Mapped[str | None] = mapped_column(nullable=True)
    sha256: Mapped[str | None] = mapped_column(nullable=True)
    storage_key: Mapped[str | None] = mapped_column(nullable=True)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parse_status: Mapped[str] = mapped_column(default="pending")
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(default=now)


class ManualAdjustment(Base):
    __tablename__ = "manual_adjustments"
    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(index=True)
    module_key: Mapped[str]
    run_id: Mapped[str]
    requested: Mapped[int]
    effective: Mapped[int]
    reason: Mapped[str]
    actor_id: Mapped[str] = mapped_column(default="local_demo_analyst")
    status: Mapped[str] = mapped_column(default="active")
    created_at: Mapped[str] = mapped_column(default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(index=True)
    module_key: Mapped[str | None] = mapped_column(nullable=True)
    type: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON)
    actor_id: Mapped[str] = mapped_column(default="local_demo_analyst")
    occurred_at: Mapped[str] = mapped_column(default=now)


class Reference(Base):
    __tablename__ = "reference_records"
    id: Mapped[str] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(index=True)
    document: Mapped[dict] = mapped_column(JSON)


class Snapshot(Base):
    __tablename__ = "assessment_snapshots"
    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(index=True)
    document: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)


class Idempotency(Base):
    __tablename__ = "idempotency_records"
    scope: Mapped[str] = mapped_column(String, primary_key=True)
    request_hash: Mapped[str]
    response: Mapped[dict] = mapped_column(JSON)
    status_code: Mapped[int]
    expires_at: Mapped[float] = mapped_column(Float)


class Database:
    def __init__(self, settings):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})

        @event.listens_for(self.engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=5000")

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self):
        with self.sessions() as session:
            try:
                session.execute(text("BEGIN IMMEDIATE"))
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    def seed(self, path):
        with self.transaction() as session:
            for record in json.loads(path.read_text())["records"]:
                if not session.get(Reference, record["source_id"]):
                    session.add(Reference(id=record["source_id"], kind=record["kind"], document=record))
