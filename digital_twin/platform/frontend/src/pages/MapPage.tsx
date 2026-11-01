import { useEffect, useMemo, useState } from "react";
import { api, type Run } from "../api";
import { HourlyChart } from "../components/Chart";
import { RoadMap, type MapValues } from "../components/RoadMap";
import { DataBadge, Empty, ErrorBox, fmt, Loading } from "../components/ui";
import { useAsync } from "../useAsync";
import { diffNorm, flowNorm } from "../mapScale";

const runOption = (r: Run) => `${r.label} · ${r.id}`;

function RunSelect({ label, value, runs, onChange, allowNone }: { label: string; value: string; runs: Run[]; onChange: (v: string) => void; allowNone?: boolean }) {
  return (
    <label className="field">{label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {allowNone && <option value="">None</option>}
        {runs.map((r) => <option key={r.id} value={r.id}>{runOption(r)}</option>)}
      </select>
    </label>
  );
}

export function MapPage({ initialRun }: { initialRun: string | null }) {
  const runs = useAsync(api.runs, []);
  const allClasses = useAsync(api.classes, []);
  const done = useMemo(() => (runs.data ?? []).filter((r) => r.has_results), [runs.data]);
  const [runId, setRunId] = useState(initialRun ?? "");
  const [compareId, setCompareId] = useState("");
  const [hour, setHour] = useState<number | null>(8);
  const [direction, setDirection] = useState("both");
  const [hidden, setHidden] = useState<string[]>([]);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (done.length && !done.some((r) => r.id === runId)) {
      const synthetic = done.find((r) => r.origin === "platform");
      setRunId((synthetic ?? done[0]).id);
    }
  }, [done, runId]);

  const run = done.find((r) => r.id === runId);
  const other = done.find((r) => r.id === compareId);
  const classes = useMemo(() => (allClasses.data ?? []).filter((c) => !hidden.includes(c)), [allClasses.data, hidden]);

  const profile = useAsync(() => (runId ? api.profile(runId) : Promise.resolve(undefined)), [runId]);
  const nHours = profile.data?.hours.length ?? 24;
  const safeHour = hour === null ? null : Math.min(hour, nHours - 1);

  const flows = useAsync(async () => {
    if (!runId) return undefined;
    const a = await api.flows(runId, safeHour, direction);
    const b = compareId ? await api.flows(compareId, safeHour !== null ? safeHour : null, direction).catch(() => null) : null;
    return { a, b, comparedMissing: !!compareId && !b };
  }, [runId, compareId, safeHour, direction]);

  const scale = useMemo(() => {
    const d = flows.data;
    if (!d) return null;
    const { norm, max } = d.b ? diffNorm(d.a.flow, d.b.flow) : flowNorm(d.a.flow);
    return { values: { cids: d.a.poly_cid, norm } as MapValues, max, diverging: !!d.b };
  }, [flows.data]);

  const series = useAsync(() => (runId && selected !== null ? api.series(runId, selected) : Promise.resolve(undefined)), [runId, selected]);
  const compare = useAsync(() => (runId && compareId ? api.compare(runId, compareId) : Promise.resolve(undefined)), [runId, compareId]);

  if (runs.error) return <ErrorBox message={runs.error} onRetry={runs.reload} />;
  const fullWindow = safeHour === null;

  return (
    <div className="map-page">
      <aside className="panel controls">
        <h2>View</h2>
        {runs.loading && !runs.data ? <Loading what="runs" /> : done.length === 0 ? (
          <Empty>No completed runs yet. The network is shown without flows. <a href="#/scenarios">Launch a scenario</a>.</Empty>
        ) : (
          <>
            <RunSelect label="Simulation" value={runId} runs={done} onChange={(v) => { setRunId(v); if (v === compareId) setCompareId(""); }} />
            {run && <p className="badges"><DataBadge run={run} /> {run.frozen_model && <span className="pill tone-info">Frozen model</span>}</p>}
            <RunSelect label="Compare with (B − A)" value={compareId} runs={done.filter((r) => r.id !== runId)} onChange={setCompareId} allowNone />
            <fieldset className="field">
              <legend>Time</legend>
              <label className="check"><input type="checkbox" checked={fullWindow} onChange={(e) => setHour(e.target.checked ? null : 8)} /> Whole simulated window</label>
              <label className="field">Hour starting {fullWindow ? "–" : `${String(safeHour).padStart(2, "0")}:00`}
                <input aria-label="Hour" type="range" min={0} max={Math.max(nHours - 1, 0)} value={safeHour ?? 0} disabled={fullWindow} onChange={(e) => setHour(Number(e.target.value))} />
              </label>
            </fieldset>
            <label className="field">Direction
              <select value={direction} onChange={(e) => setDirection(e.target.value)}>
                <option value="both">Both directions</option>
                <option value="FT">From → To (FT)</option>
                <option value="TF">To → From (TF)</option>
              </select>
            </label>
          </>
        )}
        <fieldset className="field">
          <legend>Road class</legend>
          {(allClasses.data ?? []).map((c) => (
            <label className="check" key={c}>
              <input type="checkbox" checked={!hidden.includes(c)} onChange={(e) => setHidden(e.target.checked ? hidden.filter((x) => x !== c) : [...hidden, c])} /> {c}
            </label>
          ))}
        </fieldset>
      </aside>

      <section className="map-column">
        <RoadMap values={scale?.values ?? null} diverging={!!scale?.diverging} classes={classes} selected={selected} onSelect={setSelected} />
        {run?.data_class === "synthetic" && <div className="map-stamp">SYNTHETIC DEMAND. Not real traffic.</div>}
        {flows.error && <ErrorBox message={flows.error} onRetry={flows.reload} />}
        {flows.data?.comparedMissing && <ErrorBox message="This hour is not available in the comparison run." />}
        {scale && (
          <div className="legend" data-testid="legend">
            {scale.diverging
              ? <><span>−{fmt(scale.max)}</span><span className="ramp ramp-div" /><span>+{fmt(scale.max)}</span><span className="muted">B − A, vehicles (square-root scale)</span></>
              : <><span>0</span><span className="ramp ramp-seq" /><span>{fmt(scale.max)}</span><span className="muted">vehicles {fullWindow ? "in window" : "per hour"} (square-root scale). Raw simulator flows.</span></>}
          </div>
        )}
      </section>

      <aside className="panel results">
        <h2>{selected === null ? "Region" : `Road ${selected}`}</h2>
        {selected === null ? (
          <>
            <p className="muted">Network total. Select a road on the map for its hourly flow.</p>
            {profile.error && <ErrorBox message={profile.error} onRetry={profile.reload} />}
            {profile.data && <HourlyChart label="Hourly vehicle passages summed over all links" hours={profile.data.hours} series={[{ name: "All links", values: profile.data.total, slot: 1 }]} />}
            {profile.data?.partial_last_hour && <p className="muted note">The 23:00 bin covers 45 minutes: the frozen model stops at 23:45.</p>}
          </>
        ) : (
          <>
            <button className="link-button" onClick={() => setSelected(null)}>← Back to region</button>
            {series.error && <ErrorBox message={series.error} onRetry={series.reload} />}
            {series.loading && !series.data && <Loading what="hourly flow" />}
            {series.data && <div data-testid="link-chart"><HourlyChart label={`Hourly flow of road ${selected}`} hours={series.data.hours} series={[{ name: "FT", values: series.data.FT, slot: 1 }, { name: "TF", values: series.data.TF, slot: 2 }]} /></div>}
          </>
        )}
        {compareId && other && (
          <div className="compare" data-testid="compare">
            <h2>A vs B</h2>
            {compare.error && <ErrorBox message={compare.error} />}
            {compare.data && (
              <>
                {compare.data.warnings.map((w) => <p className="warn" key={w}>⚠ {w}</p>)}
                <dl className="stats">
                  <dt>Total A</dt><dd>{fmt(compare.data.total_a)}</dd>
                  <dt>Total B</dt><dd>{fmt(compare.data.total_b)}</dd>
                  <dt>Total change</dt><dd data-testid="total-change">{compare.data.relative_total_change === null ? "n/a" : `${(compare.data.relative_total_change * 100).toFixed(1)}%`}</dd>
                  <dt>Pearson r, link volumes</dt><dd>{compare.data.pearson_daily_volume?.toFixed(3) ?? "n/a"}</dd>
                </dl>
                <HourlyChart label="Hourly network total of the two runs" hours={compare.data.hours} series={[{ name: "A", values: compare.data.profile_a, slot: 1 }, { name: "B", values: compare.data.profile_b, slot: 2 }]} />
                <p className="muted note">Descriptive differences between simulations, with no uncertainty estimate.</p>
              </>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
