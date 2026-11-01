export type RunStatus = "queued" | "running" | "cancelling" | "completed" | "failed" | "cancelled";
export const ACTIVE: RunStatus[] = ["queued", "running", "cancelling"];

export interface Scenario {
  id: number;
  name: string;
  description: string;
  profile: string;
  params: Record<string, any>;
  locked: boolean;
  parent_id: number | null;
}

export interface Run {
  id: string;
  label: string;
  origin: "platform" | "imported";
  scenario_id: number | null;
  profile: string;
  params: Record<string, any>;
  data_class: "synthetic" | "proprietary-derived";
  status: RunStatus;
  progress: number;
  error: string | null;
  seed: number | null;
  config_sha256: string | null;
  engine_sha256: string | null;
  git_commit: string | null;
  output_sha256: string | null;
  run_dir: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  frozen_model: boolean;
  has_results: boolean;
}

export interface Capabilities {
  engine_available: boolean;
  engine_path: string;
  engine_warnings: string[];
  profiles: Record<string, { available: boolean; description: string; missing_inputs?: string[]; campaign_days?: string[] }>;
  perturbations: Record<string, { supported: boolean; note: string }>;
  limits: Record<string, number>;
}

export interface Flows { run_id: string; hour: string | null; direction: string; poly_cid: number[]; flow: number[]; max_flow: number }
export interface Series { run_id: string; poly_cid: number; hours: string[]; FT: number[]; TF: number[] }
export interface Profile { run_id: string; hours: string[]; total: number[]; road_class: string | null; partial_last_hour: boolean }
export interface Compare {
  a: string; b: string; common_hours: number; links: number; total_a: number; total_b: number;
  relative_total_change: number | null; mean_abs_link_diff: number | null; pearson_daily_volume: number | null;
  profile_a: number[]; profile_b: number[]; hours: string[]; warnings: string[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function errorText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((d: any) => `${(d.loc ?? []).filter((x: unknown) => x !== "body").join(".")}: ${d.msg}`).join("; ");
  return "Request failed";
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers: init?.body ? { "Content-Type": "application/json" } : undefined });
  } catch {
    throw new ApiError(0, "The platform server cannot be reached.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorText(body.detail) || res.statusText);
  }
  return res.json();
}

const post = <T,>(path: string, body?: unknown) => call<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => call<{ disclaimer: string; scheduler_note: string | null }>("/api/health"),
  capabilities: () => call<Capabilities>("/api/capabilities"),
  network: () => call<GeoJSON.FeatureCollection>("/api/network"),
  boundaries: () => call<GeoJSON.FeatureCollection>("/api/network/boundaries"),
  classes: () => call<string[]>("/api/network/classes"),
  scenarios: () => call<Scenario[]>("/api/scenarios"),
  createScenario: (s: { name: string; description: string; profile: string; params: object }) => post<Scenario>("/api/scenarios", s),
  updateScenario: (id: number, s: { name: string; description: string; params: object }) =>
    call<Scenario>(`/api/scenarios/${id}`, { method: "PATCH", body: JSON.stringify(s) }),
  duplicateScenario: (id: number, name: string) => post<Scenario>(`/api/scenarios/${id}/duplicate`, { name }),
  launch: (id: number) => post<Run>(`/api/scenarios/${id}/runs`),
  runs: () => call<Run[]>("/api/runs"),
  run: (id: string) => call<Run>(`/api/runs/${id}`),
  cancel: (id: string) => post<Run>(`/api/runs/${id}/cancel`),
  logs: (id: string) => call<{ lines: string[] }>(`/api/runs/${id}/logs?lines=300`),
  flows: (id: string, hour: number | null, direction: string) =>
    call<Flows>(`/api/runs/${id}/flows?direction=${direction}${hour === null ? "" : `&hour=${hour}`}`),
  series: (id: string, cid: number) => call<Series>(`/api/runs/${id}/links/${cid}`),
  profile: (id: string, cls?: string) => call<Profile>(`/api/runs/${id}/profile${cls ? `?road_class=${cls}` : ""}`),
  compare: (a: string, b: string, cls?: string) =>
    call<Compare>(`/api/runs/compare?a=${a}&b=${b}${cls ? `&road_class=${cls}` : ""}`),
};
