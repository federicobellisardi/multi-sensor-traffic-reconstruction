import { useEffect, useState } from "react";
import { api } from "./api";
import { MapPage } from "./pages/MapPage";
import { RunsPage } from "./pages/RunsPage";
import { ScenariosPage } from "./pages/ScenariosPage";
import { useAsync } from "./useAsync";

function useHash() {
  const [hash, setHash] = useState(window.location.hash || "#/map");
  useEffect(() => {
    const f = () => setHash(window.location.hash || "#/map");
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return hash;
}

const navigate = (h: string) => { window.location.hash = h; };

export function App() {
  const [page, arg] = useHash().replace(/^#\//, "").split("/");
  const health = useAsync(api.health, [], 5000);
  const caps = useAsync(api.capabilities, []);
  const link = (id: string, text: string) => <a href={`#/${id}`} aria-current={page === id ? "page" : undefined}>{text}</a>;
  return (
    <div className="app">
      <header className="top">
        <h1>Regional Mobility <span className="tag">ALPHA</span></h1>
        <nav aria-label="Main">{link("map", "Map")}{link("runs", "Runs")}{link("scenarios", "Scenarios")}<a href="/docs" target="_blank" rel="noreferrer">API</a></nav>
      </header>
      <div className="disclaimer" role="note">{health.data?.disclaimer ?? "Research alpha: not a validated predictive digital twin."}</div>
      {health.error && <div className="notice critical" role="alert">The platform server cannot be reached.</div>}
      {health.data?.scheduler_note && <div className="notice" role="status">{health.data.scheduler_note}</div>}
      {caps.data?.engine_warnings.map((w) => <div className="notice" role="alert" key={w}>⚠ {w}</div>)}
      {caps.data && !caps.data.engine_available && <div className="notice" role="alert">⚠ Simulator not found at {caps.data.engine_path}. Existing results can be viewed; build it with hpc/setup.sh to launch runs.</div>}
      <main>
        {page === "runs" ? <RunsPage selected={arg ?? null} /> : page === "scenarios" ? <ScenariosPage navigate={navigate} /> : <MapPage key={arg ?? "map"} initialRun={arg ?? null} />}
      </main>
    </div>
  );
}
