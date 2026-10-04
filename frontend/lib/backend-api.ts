import type {
  Accepted,
  Capabilities,
  Entity,
  EventPage,
  Module,
  ModuleKey,
  PartySelection,
  QueuePage,
  RunDetail,
  Workspace,
} from "./backend-types";

export const BACKEND_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:18080"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string,
    public requestId?: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (init.method && init.method !== "GET")
    headers.set("Idempotency-Key", crypto.randomUUID());
  for (let attempt = 0; attempt < 2; attempt++) {
    let response: Response;
    try {
      const timeout = AbortSignal.timeout(30000);
      response = await fetch(BACKEND_URL + path, {
        ...init,
        headers,
        cache: "no-store",
        signal: init.signal ? AbortSignal.any([init.signal, timeout]) : timeout,
      });
    } catch (error) {
      if (init.signal?.aborted) throw error;
      // A transport retry retains the same key and body. Never retry a 409 with a new version.
      if (attempt === 0) continue;
      throw new ApiError(
        "Cannot reach the assessment service. Your saved work stays on the server; retry when connected.",
        0,
        "NETWORK_ERROR",
      );
    }
    const body = await response.json();
    if (!response.ok)
      throw new ApiError(
        body.error?.message ?? `Service error (${response.status})`,
        response.status,
        body.error?.code ?? "SERVICE_ERROR",
        body.request_id,
      );
    return body as T;
  }
  throw new Error("Request failed");
}

const casePath = (id: string) => `/v1/cases/${encodeURIComponent(id)}`;
const modulePath = (id: string, key: ModuleKey) =>
  `${casePath(id)}/modules/${key}`;
const json = (value: unknown) => JSON.stringify(value);

export const backend = {
  capabilities: (signal?: AbortSignal) =>
    request<Capabilities>("/v1/capabilities", { signal }),
  entities: (signal?: AbortSignal) =>
    request<{ items: Entity[]; next_cursor: string | null }>("/v1/entities", {
      signal,
    }),
  queue: (band = "", cursor?: string, signal?: AbortSignal) =>
    request<QueuePage>(
      `/v1/cases?limit=20${band ? `&risk_band=${band}` : ""}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
      { signal },
    ),
  workspace: (id: string, signal?: AbortSignal) =>
    request<Workspace>(casePath(id), { signal }),
  module: (id: string, key: ModuleKey) => request<Module>(modulePath(id, key)),
  create: (buyer: PartySelection, seller: PartySelection) =>
    request<{ case_id: string; case_revision: number }>("/v1/cases", {
      method: "POST",
      body: json({ buyer, seller }),
    }),
  uploadInvoice: (id: string, version: number, file: File, replace = false) => {
    const body = new FormData();
    body.append("file", file);
    body.append("expected_case_revision", String(version));
    body.append("replace", String(replace));
    return request<Accepted>(`${casePath(id)}/invoice`, {
      method: "POST",
      body,
    });
  },
  start: (id: string, revision: number) =>
    request<Accepted>(`${casePath(id)}/assessments`, {
      method: "POST",
      body: json({ expected_case_revision: revision }),
    }),
  resolve: (
    id: string,
    revision: number,
    side: "buyer" | "seller",
    selection: PartySelection,
    action: "use_invoice_entity" | "compare_selection",
  ) =>
    request<Workspace>(`${casePath(id)}/parties`, {
      method: "PATCH",
      body: json({
        expected_case_revision: revision,
        side,
        selection,
        resolution_action: action,
        reason: "Analyst reviewed the extracted invoice entity",
      }),
    }),
  evidence: (
    id: string,
    key: ModuleKey,
    version: number,
    files: File[],
    rerun: boolean,
    group?: string,
    supersedes?: string,
  ) => {
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    body.append("expected_module_version", String(version));
    body.append("rerun", String(rerun));
    if (group) body.append("evidence_group", group);
    if (supersedes) body.append("supersedes_evidence_id", supersedes);
    return request<Accepted>(`${modulePath(id, key)}/evidence`, {
      method: "POST",
      body,
    });
  },
  supplement: (
    id: string,
    key: ModuleKey,
    version: number,
    text: string,
    rerun: boolean,
  ) =>
    request<Accepted>(`${modulePath(id, key)}/supplements`, {
      method: "POST",
      body: json({ expected_module_version: version, text, rerun }),
    }),
  rerun: (id: string, key: ModuleKey, version: number) =>
    request<Accepted>(`${modulePath(id, key)}/runs`, {
      method: "POST",
      body: json({
        expected_module_version: version,
        reason: "Analyst requested a module reassessment",
      }),
    }),
  adjust: (
    id: string,
    key: ModuleKey,
    version: number,
    runId: string,
    adjustment: number,
    reason: string,
  ) =>
    request<Module>(`${modulePath(id, key)}/adjustments`, {
      method: "POST",
      body: json({
        expected_module_version: version,
        applies_to_run_id: runId,
        requested_adjustment: adjustment,
        reason,
      }),
    }),
  run: (id: string, key: ModuleKey, runId: string) =>
    request<RunDetail>(
      `${modulePath(id, key)}/runs/${encodeURIComponent(runId)}`,
    ),
  events: (id: string, after = 0) =>
    request<EventPage>(`${casePath(id)}/events?after_seq=${after}&limit=100`),
  fileUrl: (id: string, fileId: string) =>
    BACKEND_URL + `${casePath(id)}/files/${encodeURIComponent(fileId)}`,
};
