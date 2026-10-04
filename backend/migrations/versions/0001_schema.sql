CREATE TABLE audit_events (
	seq INTEGER NOT NULL,
	case_id VARCHAR NOT NULL,
	module_key VARCHAR,
	type VARCHAR NOT NULL,
	payload JSON NOT NULL,
	actor_id VARCHAR NOT NULL,
	occurred_at VARCHAR NOT NULL,
	PRIMARY KEY (seq)
);

CREATE INDEX ix_audit_events_case_id ON audit_events (case_id);

CREATE TABLE cases (
	id VARCHAR NOT NULL,
	revision INTEGER NOT NULL,
	stage VARCHAR NOT NULL,
	initial_status VARCHAR NOT NULL,
	invoice JSON,
	parties JSON NOT NULL,
	last_result JSON,
	aggregate_revision INTEGER NOT NULL,
	error JSON,
	created_at VARCHAR NOT NULL,
	updated_at VARCHAR NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE evidence (
	id VARCHAR NOT NULL,
	case_id VARCHAR NOT NULL,
	module_key VARCHAR,
	kind VARCHAR NOT NULL,
	filename VARCHAR,
	sha256 VARCHAR,
	storage_key VARCHAR,
	content JSON,
	parse_status VARCHAR NOT NULL,
	error JSON,
	created_at VARCHAR NOT NULL,
	PRIMARY KEY (id)
);

CREATE INDEX ix_evidence_case_id ON evidence (case_id);

CREATE TABLE idempotency_records (
	scope VARCHAR NOT NULL,
	request_hash VARCHAR NOT NULL,
	response JSON NOT NULL,
	status_code INTEGER NOT NULL,
	expires_at FLOAT NOT NULL,
	PRIMARY KEY (scope)
);

CREATE TABLE jobs (
	id VARCHAR NOT NULL,
	case_id VARCHAR NOT NULL,
	module_key VARCHAR,
	kind VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	payload JSON NOT NULL,
	attempt INTEGER NOT NULL,
	fencing_token INTEGER NOT NULL,
	lease_until FLOAT,
	available_at FLOAT NOT NULL,
	error JSON,
	created_at VARCHAR NOT NULL,
	PRIMARY KEY (id)
);

CREATE INDEX ix_jobs_case_id ON jobs (case_id);

CREATE INDEX ix_jobs_status ON jobs (status);

CREATE TABLE manual_adjustments (
	id VARCHAR NOT NULL,
	case_id VARCHAR NOT NULL,
	module_key VARCHAR NOT NULL,
	run_id VARCHAR NOT NULL,
	requested INTEGER NOT NULL,
	effective INTEGER NOT NULL,
	reason VARCHAR NOT NULL,
	actor_id VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	created_at VARCHAR NOT NULL,
	PRIMARY KEY (id)
);

CREATE INDEX ix_manual_adjustments_case_id ON manual_adjustments (case_id);

CREATE TABLE module_runs (
	id VARCHAR NOT NULL,
	case_id VARCHAR NOT NULL,
	module_key VARCHAR NOT NULL,
	input_version INTEGER NOT NULL,
	input JSON,
	output JSON,
	provider JSON,
	status VARCHAR NOT NULL,
	initial BOOLEAN NOT NULL,
	error JSON,
	created_at VARCHAR NOT NULL,
	finished_at VARCHAR,
	PRIMARY KEY (id)
);

CREATE INDEX ix_module_runs_case_id ON module_runs (case_id);

CREATE TABLE modules (
	case_id VARCHAR NOT NULL,
	"key" VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	input_version INTEGER NOT NULL,
	evaluated_version INTEGER,
	state VARCHAR NOT NULL,
	freshness VARCHAR NOT NULL,
	current_run_id VARCHAR,
	rerun_requested BOOLEAN NOT NULL,
	error JSON,
	PRIMARY KEY (case_id, "key")
);

CREATE TABLE reference_records (
	id VARCHAR NOT NULL,
	kind VARCHAR NOT NULL,
	document JSON NOT NULL,
	PRIMARY KEY (id)
);

CREATE INDEX ix_reference_records_kind ON reference_records (kind);
