import type { ReactNode } from "react";
import type { Run, RunStatus } from "../api";

const STATUS: Record<RunStatus, { icon: string; text: string; tone: string }> = {
  queued: { icon: "◷", text: "Queued", tone: "neutral" },
  running: { icon: "▶", text: "Running", tone: "info" },
  cancelling: { icon: "◼", text: "Cancelling", tone: "warning" },
  completed: { icon: "✓", text: "Completed", tone: "good" },
  failed: { icon: "✕", text: "Failed", tone: "critical" },
  cancelled: { icon: "◼", text: "Cancelled", tone: "neutral" },
};

export const StatusPill = ({ status }: { status: RunStatus }) => {
  const s = STATUS[status];
  return <span className={`pill tone-${s.tone}`} data-testid="status"><span aria-hidden>{s.icon}</span> {s.text}</span>;
};

export const DataBadge = ({ run }: { run: Pick<Run, "data_class"> }) =>
  run.data_class === "synthetic"
    ? <span className="pill tone-warning">SYNTHETIC demo data</span>
    : <span className="pill tone-neutral" title="Derived from proprietary mobile-phone data. Do not redistribute.">Proprietary-derived</span>;

export const Loading = ({ what }: { what: string }) => <div className="state" role="status"><span className="spinner" aria-hidden /> Loading {what}…</div>;

export const ErrorBox = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="state state-error" role="alert">
    <strong>Something went wrong.</strong> <span>{message}</span>
    {onRetry && <button onClick={onRetry}>Retry</button>}
  </div>
);

export const Empty = ({ children }: { children: ReactNode }) => <div className="state">{children}</div>;

export const Progress = ({ value }: { value: number }) => (
  <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}>
    <div style={{ width: `${value * 100}%` }} />
  </div>
);

export const fmt = (x: number) => Math.round(x).toLocaleString("en-US");
