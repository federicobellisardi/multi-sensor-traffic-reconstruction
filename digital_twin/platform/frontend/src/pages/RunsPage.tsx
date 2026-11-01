import { useEffect, useRef, useState } from "react";
import { ACTIVE, api, type Run } from "../api";
import { DataBadge, Empty, ErrorBox, Loading, Progress, StatusPill } from "../components/ui";
import { useAsync } from "../useAsync";

const when = (s: string | null) => (s ? new Date(s).toLocaleString() : "–");

function RunDetail({ id, onChange }: { id: string; onChange: () => void }) {
  const [poll, setPoll] = useState(true);
  const { data: run, error, reload } = useAsync(() => api.run(id), [id], poll ? 1500 : undefined);
  const active = run ? ACTIVE.includes(run.status) : true;
  const logs = useAsync(() => api.logs(id), [id], active ? 2000 : undefined);
  const [actionError, setActionError] = useState<string>();
  const logBox = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (logBox.current) logBox.current.scrollTop = logBox.current.scrollHeight;
  }, [logs.data]);

  useEffect(() => {
    if (!run) return;
    setPoll(active);
    logs.reload();
    onChange();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.status]);

  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!run) return <Loading what="run" />;
  const cancel = () => api.cancel(id).then(reload).catch((e) => setActionError(e.message));

  return (
    <section className="panel run-detail" data-testid="run-detail">
      <header className="run-head">
        <div><h2>{run.label}</h2><code>{run.id}</code></div>
        <div className="actions">
          {run.has_results && <a className="button primary" href={`#/map/${run.id}`}>View on map</a>}
          {run.origin === "platform" && ACTIVE.includes(run.status) && <button className="danger" onClick={cancel} disabled={run.status === "cancelling"}>Cancel run</button>}
        </div>
      </header>
      <p className="badges"><StatusPill status={run.status} /> <DataBadge run={run} /> {run.frozen_model && <span className="pill tone-info">Frozen model</span>} {run.origin === "imported" && <span className="pill tone-neutral">Imported, read only</span>}</p>
      {ACTIVE.includes(run.status) && <Progress value={run.progress} />}
      {actionError && <ErrorBox message={actionError} />}
      {run.error && <div className="state state-error" role="alert"><strong>Run failed.</strong><pre>{run.error}</pre></div>}
      <dl className="stats wide">
        <dt>Started</dt><dd>{when(run.started_at)}</dd>
        <dt>Finished</dt><dd>{when(run.finished_at)}</dd>
        <dt>Seed</dt><dd>{run.seed ?? "engine default"}</dd>
        <dt>Parameters</dt><dd><code>{JSON.stringify(run.params)}</code></dd>
        <dt>Git commit</dt><dd><code>{run.git_commit ?? "not recorded"}</code></dd>
        <dt>Config SHA-256</dt><dd><code>{run.config_sha256 ?? "–"}</code></dd>
        <dt>Engine SHA-256</dt><dd><code>{run.engine_sha256 ?? "not recorded"}</code></dd>
        <dt>Output SHA-256</dt><dd><code>{run.output_sha256 ?? "–"}</code></dd>
        <dt>Files</dt><dd><code>{run.run_dir}</code></dd>
      </dl>
      <h3>Engine log</h3>
      <pre ref={logBox} className="log" data-testid="log" tabIndex={0}>{logs.data?.lines.join("\n") || "No log output yet."}</pre>
    </section>
  );
}

export function RunsPage({ selected }: { selected: string | null }) {
  const [scope, setScope] = useState<"all" | "platform" | "imported">("all");
  const { data: runs, error, loading, reload } = useAsync(api.runs, [], 3000);
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const shown = (runs ?? []).filter((r: Run) => scope === "all" || r.origin === scope);
  return (
    <div className="runs-page">
      <section className="panel">
        <div className="row-between">
          <h2>Runs</h2>
          <label className="inline">Show <select value={scope} onChange={(e) => setScope(e.target.value as typeof scope)}>
            <option value="all">All</option><option value="platform">Launched here</option><option value="imported">Imported</option>
          </select></label>
        </div>
        {loading && !runs ? <Loading what="runs" /> : shown.length === 0 ? <Empty>No runs yet. <a href="#/scenarios">Launch a scenario</a>.</Empty> : (
          <ul className="run-list">
            {shown.map((r) => (
              <li key={r.id} className={r.id === selected ? "current" : ""}>
                <a href={`#/runs/${r.id}`}>
                  <span className="run-title">{r.label}</span>
                  <span className="muted small">{new Date(r.created_at).toLocaleString()}</span>
                  <span className="badges"><StatusPill status={r.status} />{r.data_class === "synthetic" && <span className="pill tone-warning">SYNTHETIC</span>}</span>
                  {ACTIVE.includes(r.status) && <Progress value={r.progress} />}
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
      {selected ? <RunDetail key={selected} id={selected} onChange={reload} /> : <section className="panel"><Empty>Select a run to see its status, provenance and log.</Empty></section>}
    </div>
  );
}
