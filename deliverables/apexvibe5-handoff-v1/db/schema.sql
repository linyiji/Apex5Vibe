PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE entity_profiles (
  entity_id TEXT PRIMARY KEY,
  legal_name TEXT NOT NULL,
  tax_id TEXT,
  jurisdiction TEXT,
  verification_status TEXT NOT NULL,
  source_id TEXT NOT NULL,
  profile_json TEXT NOT NULL CHECK(json_valid(profile_json)),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  UNIQUE(tax_id, jurisdiction)
);
CREATE TABLE reference_records (
  source_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  synthetic INTEGER NOT NULL CHECK(synthetic IN (0,1)),
  source_type TEXT NOT NULL,
  as_of TEXT NOT NULL,
  data_json TEXT NOT NULL CHECK(json_valid(data_json))
);
CREATE TABLE cases (
  case_id TEXT PRIMARY KEY,
  stage TEXT NOT NULL CHECK(stage IN ('draft','extracting','resolving','assessing','result')),
  initial_assessment_status TEXT NOT NULL CHECK(initial_assessment_status IN ('not_started','running','settled')),
  case_revision INTEGER NOT NULL CHECK(case_revision > 0),
  engine_mode TEXT NOT NULL CHECK(engine_mode IN ('demo_replay','llm')),
  policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE files (
  file_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  storage_key TEXT NOT NULL UNIQUE,
  original_filename TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
  status TEXT NOT NULL CHECK(status IN ('staged','ready','failed')),
  created_at TEXT NOT NULL,
  UNIQUE(case_id,sha256)
);
CREATE TABLE invoice_versions (
  invoice_version_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  revision INTEGER NOT NULL CHECK(revision > 0),
  source_file_id TEXT NOT NULL REFERENCES files(file_id),
  invoice_number TEXT NOT NULL,
  currency TEXT NOT NULL,
  total_minor INTEGER NOT NULL CHECK(total_minor >= 0),
  invoice_json TEXT NOT NULL CHECK(json_valid(invoice_json)),
  created_at TEXT NOT NULL,
  UNIQUE(case_id,revision)
);
CREATE TABLE case_parties (
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  side TEXT NOT NULL CHECK(side IN ('buyer','seller')),
  mode TEXT NOT NULL CHECK(mode IN ('skip','existing','manual')),
  selection_json TEXT NOT NULL CHECK(json_valid(selection_json)),
  extracted_json TEXT CHECK(extracted_json IS NULL OR json_valid(extracted_json)),
  resolved_entity_id TEXT REFERENCES entity_profiles(entity_id),
  status TEXT NOT NULL CHECK(status IN ('pending','matched','provisional','conflict')),
  PRIMARY KEY(case_id,side)
);
CREATE TABLE modules (
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  module_key TEXT NOT NULL CHECK(module_key IN ('invoice_integrity','buyer_verification','seller_verification','relationship','market_price','payment_history','duplicate_financing')),
  cap INTEGER NOT NULL CHECK(cap BETWEEN 1 AND 100),
  module_version INTEGER NOT NULL CHECK(module_version > 0),
  input_version INTEGER NOT NULL CHECK(input_version > 0),
  evaluated_input_version INTEGER,
  state TEXT NOT NULL CHECK(state IN ('not_started','queued','running','succeeded','needs_info','failed')),
  freshness TEXT NOT NULL CHECK(freshness IN ('none','current','stale')),
  adjustment_status TEXT NOT NULL CHECK(adjustment_status IN ('none','active','pending_review')),
  current_run_id TEXT,
  rerun_requested INTEGER NOT NULL DEFAULT 0 CHECK(rerun_requested IN (0,1)),
  PRIMARY KEY(case_id,module_key)
);
CREATE TABLE evidence (
  evidence_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  kind TEXT NOT NULL CHECK(kind IN ('file','note','reference')),
  file_id TEXT REFERENCES files(file_id),
  source_id TEXT NOT NULL,
  source_version INTEGER NOT NULL DEFAULT 1,
  text_content TEXT,
  parsed_json TEXT CHECK(parsed_json IS NULL OR json_valid(parsed_json)),
  parse_status TEXT NOT NULL CHECK(parse_status IN ('pending','ready','failed')),
  status TEXT NOT NULL CHECK(status IN ('active','withdrawn')),
  author_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE module_evidence (
  case_id TEXT NOT NULL,
  module_key TEXT NOT NULL,
  evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
  PRIMARY KEY(case_id,module_key,evidence_id),
  FOREIGN KEY(case_id,module_key) REFERENCES modules(case_id,module_key)
);
CREATE TABLE module_runs (
  run_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  module_key TEXT NOT NULL,
  input_version INTEGER NOT NULL,
  input_hash TEXT NOT NULL,
  input_json TEXT NOT NULL CHECK(json_valid(input_json)),
  status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','needs_info','failed','superseded')),
  output_json TEXT CHECK(output_json IS NULL OR json_valid(output_json)),
  error_json TEXT CHECK(error_json IS NULL OR json_valid(error_json)),
  policy_version TEXT NOT NULL,
  model_version TEXT,
  prompt_version TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  finished_at TEXT,
  FOREIGN KEY(case_id,module_key) REFERENCES modules(case_id,module_key)
);
CREATE TABLE manual_adjustments (
  adjustment_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  module_key TEXT NOT NULL,
  applies_to_run_id TEXT NOT NULL REFERENCES module_runs(run_id),
  requested_adjustment INTEGER NOT NULL CHECK(requested_adjustment BETWEEN -100 AND 100),
  effective_adjustment INTEGER NOT NULL CHECK(effective_adjustment BETWEEN -100 AND 100),
  reason TEXT NOT NULL CHECK(length(trim(reason)) > 0),
  actor_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('active','pending_review','superseded')),
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id,module_key) REFERENCES modules(case_id,module_key)
);
CREATE UNIQUE INDEX one_active_adjustment ON manual_adjustments(case_id,module_key) WHERE status='active';
CREATE TABLE assessment_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  aggregate_revision INTEGER NOT NULL CHECK(aggregate_revision > 0),
  final_risk_score INTEGER NOT NULL CHECK(final_risk_score BETWEEN 0 AND 100),
  risk_band TEXT NOT NULL CHECK(risk_band IN ('LOW','HIGH')),
  snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
  decision_json TEXT NOT NULL CHECK(json_valid(decision_json)),
  created_at TEXT NOT NULL,
  UNIQUE(case_id,aggregate_revision),
  CHECK((final_risk_score < 30 AND risk_band='LOW') OR (final_risk_score >= 30 AND risk_band='HIGH'))
);
CREATE TABLE jobs (
  job_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  module_key TEXT,
  kind TEXT NOT NULL CHECK(kind IN ('parse_invoice','parse_evidence','initial_assessment','module_run')),
  status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','superseded')),
  input_version INTEGER,
  attempt INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  lease_until TEXT,
  fencing_token INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX one_active_module_run ON jobs(case_id,module_key) WHERE kind='module_run' AND status IN ('queued','running');
CREATE TABLE audit_events (
  event_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  seq INTEGER NOT NULL CHECK(seq > 0),
  module_key TEXT,
  event_type TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  UNIQUE(case_id,seq)
);
CREATE TABLE idempotency_records (
  actor_id TEXT NOT NULL,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  request_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  http_status INTEGER NOT NULL,
  response_json TEXT NOT NULL CHECK(json_valid(response_json)),
  expires_at TEXT NOT NULL,
  PRIMARY KEY(actor_id,method,path,request_key)
);
CREATE INDEX jobs_claim ON jobs(status,created_at);
CREATE INDEX runs_by_module ON module_runs(case_id,module_key,created_at);
CREATE INDEX events_after ON audit_events(case_id,seq);
