import { useState, type FormEvent } from "react";
import { api, type Capabilities, type Scenario } from "../api";
import { Empty, ErrorBox, Loading } from "../components/ui";
import { useAsync } from "../useAsync";

export interface FormState {
  name: string; description: string; profile: string; hours: string; trips: string; day: string; variant: string; seed: string; factor: string;
}

const BLANK: FormState = { name: "", description: "", profile: "demo_synthetic", hours: "10", trips: "20000", day: "2020-02-10", variant: "V6_scaled", seed: "", factor: "1" };

/** Blank optional fields keep the configuration of the frozen model; a factor of 1 is no perturbation. */
export function formToParams(f: FormState): Record<string, unknown> {
  const params: Record<string, unknown> = { seed: f.seed === "" ? null : Number(f.seed), perturbations: Number(f.factor) === 1 ? [] : [{ kind: "demand_scale", factor: Number(f.factor) }] };
  if (f.profile === "demo_synthetic") return { ...params, hours: Number(f.hours), trips_per_day: Number(f.trips) };
  return { ...params, day: f.day, variant: f.variant, hours: f.hours === "" ? null : Number(f.hours) };
}

function scenarioToForm(s: Scenario): FormState {
  return {
    name: s.name, description: s.description, profile: s.profile, hours: s.params.hours == null ? "" : String(s.params.hours),
    trips: String(s.params.trips_per_day ?? 20000), day: s.params.day ?? "2020-02-10", variant: s.params.variant ?? "V6_scaled",
    seed: s.params.seed == null ? "" : String(s.params.seed), factor: String(s.params.perturbations?.[0]?.factor ?? 1),
  };
}

function ScenarioForm({ caps, editing, onDone }: { caps: Capabilities; editing: Scenario | null; onDone: () => void }) {
  const [f, setF] = useState<FormState>(editing ? scenarioToForm(editing) : BLANK);
  const [error, setError] = useState<string>();
  const set = (k: keyof FormState) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const research = f.profile === "research_frozen";
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(undefined);
    try {
      if (editing) await api.updateScenario(editing.id, { name: f.name, description: f.description, params: formToParams(f) });
      else await api.createScenario({ name: f.name, description: f.description, profile: f.profile, params: formToParams(f) });
      onDone();
    } catch (err: any) {
      setError(err.message);
    }
  };
  return (
    <form className="panel form" onSubmit={submit} aria-label="Scenario form">
      <h2>{editing ? `Edit ${editing.name}` : "New scenario"}</h2>
      <label className="field">Name <input required value={f.name} onChange={set("name")} /></label>
      <label className="field">Description <input value={f.description} onChange={set("description")} /></label>
      <label className="field">Profile
        <select value={f.profile} onChange={(e) => setF({ ...f, profile: e.target.value, hours: e.target.value === "research_frozen" ? "" : "10" })} disabled={!!editing}>
          <option value="demo_synthetic">Demo (synthetic demand)</option>
          <option value="research_frozen" disabled={!caps.profiles.research_frozen.available}>Frozen research model{caps.profiles.research_frozen.available ? "" : " (inputs not available)"}</option>
        </select>
      </label>
      <p className="muted small">{caps.profiles[f.profile].description}</p>
      {research ? (
        <>
          <label className="field">Day <select value={f.day} onChange={set("day")}>{caps.profiles.research_frozen.campaign_days?.map((d) => <option key={d}>{d}</option>)}</select></label>
          <label className="field">Route choice <select value={f.variant} onChange={set("variant")}><option value="V6_scaled">V6 (frozen model)</option><option value="V0_scaled">V0 (comparison)</option></select></label>
          <label className="field">Hours from midnight <input type="number" value={f.hours} placeholder="Full frozen window" onChange={set("hours")} /></label>
        </>
      ) : (
        <>
          <label className="field">Hours from midnight <input type="number" required value={f.hours} onChange={set("hours")} /></label>
          <label className="field">Synthetic trips per day <input type="number" required value={f.trips} onChange={set("trips")} /></label>
        </>
      )}
      <label className="field">Demand multiplier <input type="number" step="0.05" required value={f.factor} onChange={set("factor")} /></label>
      <label className="field">Seed <input type="number" value={f.seed} placeholder="Engine default" onChange={set("seed")} /></label>
      <fieldset className="field unavailable">
        <legend>Other perturbations</legend>
        <label className="check"><input type="checkbox" disabled /> Road closure: not available</label>
        <p className="muted small">{caps.perturbations.road_closure.note}</p>
      </fieldset>
      {research && (f.factor !== "1" || f.seed !== "" || f.hours !== "") && <p className="warn">⚠ These overrides make this run differ from the frozen model.</p>}
      {error && <ErrorBox message={error} />}
      <div className="actions"><button className="primary" type="submit">Save scenario</button><button type="button" onClick={onDone}>Cancel</button></div>
    </form>
  );
}

export function ScenariosPage({ navigate }: { navigate: (hash: string) => void }) {
  const scenarios = useAsync(api.scenarios, []);
  const caps = useAsync(api.capabilities, []);
  const [form, setForm] = useState<{ editing: Scenario | null } | null>(null);
  const [dup, setDup] = useState<{ id: number; name: string } | null>(null);
  const [error, setError] = useState<string>();
  const guard = (p: Promise<unknown>) => p.catch((e) => setError(e.message));

  if (scenarios.error || caps.error) return <ErrorBox message={(scenarios.error ?? caps.error)!} onRetry={() => { scenarios.reload(); caps.reload(); }} />;
  if (!scenarios.data || !caps.data) return <Loading what="scenarios" />;
  const available = (s: Scenario) => caps.data!.profiles[s.profile]?.available;

  return (
    <div className="scenarios-page">
      <section className="panel">
        <div className="row-between"><h2>Scenarios</h2><button className="primary" onClick={() => setForm({ editing: null })}>New scenario</button></div>
        {error && <ErrorBox message={error} onRetry={() => setError(undefined)} />}
        {scenarios.data.length === 0 && <Empty>No scenarios.</Empty>}
        <ul className="scenario-list">
          {scenarios.data.map((s) => (
            <li key={s.id} data-testid={`scenario-${s.name}`}>
              <div className="row-between">
                <h3>{s.name}</h3>
                <span className="badges">{s.locked && <span className="pill tone-info">🔒 Baseline</span>}{s.profile === "demo_synthetic" && <span className="pill tone-warning">SYNTHETIC</span>}</span>
              </div>
              {s.description && <p className="muted">{s.description}</p>}
              <code className="small">{JSON.stringify(s.params)}</code>
              {!available(s) && <p className="muted small">Cannot run here: {caps.data!.profiles[s.profile]?.missing_inputs?.length ?? 0} required inputs are missing.</p>}
              {dup?.id === s.id ? (
                <form className="actions" onSubmit={(e) => { e.preventDefault(); guard(api.duplicateScenario(s.id, dup.name).then(() => { setDup(null); setError(undefined); scenarios.reload(); })); }}>
                  <input aria-label="Name of the copy" required value={dup.name} onChange={(e) => setDup({ ...dup, name: e.target.value })} />
                  <button className="primary" type="submit">Save copy</button><button type="button" onClick={() => setDup(null)}>Cancel</button>
                </form>
              ) : (
                <div className="actions">
                  <button className="primary" disabled={!available(s)} onClick={() => guard(api.launch(s.id).then((r) => navigate(`#/runs/${r.id}`)))}>Launch</button>
                  <button onClick={() => setDup({ id: s.id, name: `${s.name} copy` })}>Duplicate</button>
                  {!s.locked && <button onClick={() => setForm({ editing: s })}>Edit</button>}
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>
      {form && <ScenarioForm key={form.editing?.id ?? "new"} caps={caps.data} editing={form.editing} onDone={() => { setForm(null); scenarios.reload(); }} />}
    </div>
  );
}
