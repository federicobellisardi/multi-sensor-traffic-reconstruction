import maplibregl, { type Map as LibreMap } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { ErrorBox, Loading } from "./ui";

export interface MapValues { cids: number[]; norm: number[] }

const CITIES: [string, number, number][] = [
  ["Piacenza", 9.696, 45.047], ["Parma", 10.328, 44.8015], ["Reggio Emilia", 10.63, 44.699], ["Modena", 10.925, 44.647],
  ["Bologna", 11.343, 44.495], ["Ferrara", 11.62, 44.838], ["Ravenna", 12.2035, 44.418], ["Forlì", 12.041, 44.223], ["Rimini", 12.57, 44.068],
];
const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/** v in [0, 1] for flows; v in [-1, 1] for differences. No external tiles: the network is the map. */
function colorExpression(diverging: boolean): any {
  const stateV = ["coalesce", ["feature-state", "v"], diverging ? 0 : -1];
  if (diverging)
    return ["interpolate", ["linear"], stateV, -1, css("--div-neg"), -0.25, css("--div-neg-soft"), 0, css("--div-mid"), 0.25, css("--div-pos-soft"), 1, css("--div-pos")];
  return ["case", ["<", stateV, 0], css("--no-data"),
    ["interpolate", ["linear"], stateV, 0, css("--seq-0"), 0.33, css("--seq-1"), 0.66, css("--seq-2"), 1, css("--seq-3")]];
}

export function RoadMap({ values, diverging, classes, selected, onSelect }: {
  values: MapValues | null; diverging: boolean; classes: string[]; selected: number | null; onSelect: (cid: number | null) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<LibreMap | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string>();
  const [attempt, setAttempt] = useState(0);
  const painted = useRef<number[]>([]);
  const select = useRef(onSelect);
  select.current = onSelect;

  useEffect(() => {
    if (!box.current) return;
    let live = true;
    setError(undefined);
    setReady(false);
    const m = new maplibregl.Map({
      container: box.current, center: [11.1, 44.55], zoom: 7.3, attributionControl: false,
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": css("--map-bg") } }] },
    });
    map.current = m;
    (window as any).__alphaMap = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Road network © OpenStreetMap contributors" }));
    m.on("error", (e) => console.warn(e.error));
    m.on("load", async () => {
      try {
        const [net, bounds] = await Promise.all([api.network(), api.boundaries()]);
        if (!live) return;
        m.addSource("provinces", { type: "geojson", data: bounds });
        m.addLayer({ id: "province-fill", type: "fill", source: "provinces", paint: { "fill-color": css("--map-land") } });
        m.addLayer({ id: "province-line", type: "line", source: "provinces", paint: { "line-color": css("--grid"), "line-width": 1 } });
        m.addSource("roads", { type: "geojson", data: net, promoteId: "poly_cid" });
        const width = ["interpolate", ["linear"], ["zoom"], 7, ["match", ["get", "road_class"], "motorway", 1.6, "trunk", 1.3, "primary", 1, 0.6], 12, ["match", ["get", "road_class"], "motorway", 5, "trunk", 4, "primary", 3, 2]];
        m.addLayer({ id: "roads", type: "line", source: "roads", layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": colorExpression(false), "line-width": width as any } });
        m.addLayer({ id: "road-selected", type: "line", source: "roads", filter: ["==", ["get", "poly_cid"], -1], paint: { "line-color": css("--text-primary"), "line-width": 5, "line-opacity": 0.9 } });
        for (const [name, lon, lat] of CITIES) {
          const el = document.createElement("div");
          el.className = "city-label";
          el.textContent = name;
          new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).addTo(m);
        }
        m.on("click", (e) => {
          // the road exactly under the pointer first; a small box only makes thin roads easier to hit
          const p = 6;
          const exact = m.queryRenderedFeatures(e.point, { layers: ["roads"] });
          const hits = exact.length ? exact : m.queryRenderedFeatures([[e.point.x - p, e.point.y - p], [e.point.x + p, e.point.y + p]], { layers: ["roads"] });
          select.current(hits.length ? Number(hits[0].properties!.poly_cid) : null);
        });
        m.on("mousemove", (e) => {
          const p = 6;
          m.getCanvas().style.cursor = m.queryRenderedFeatures([[e.point.x - p, e.point.y - p], [e.point.x + p, e.point.y + p]], { layers: ["roads"] }).length ? "pointer" : "";
        });
        setReady(true);
      } catch (e: any) {
        if (live) setError(e.message);
      }
    });
    return () => { live = false; m.remove(); map.current = null; painted.current = []; };
  }, [attempt]);

  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    for (const cid of painted.current) m.removeFeatureState({ source: "roads", id: cid });
    painted.current = values?.cids ?? [];
    values?.cids.forEach((cid, i) => m.setFeatureState({ source: "roads", id: cid }, { v: values.norm[i] }));
    m.setPaintProperty("roads", "line-color", colorExpression(diverging));
  }, [ready, values, diverging]);

  useEffect(() => {
    if (ready) map.current?.setFilter("roads", ["in", ["get", "road_class"], ["literal", classes]]);
  }, [ready, classes]);

  useEffect(() => {
    if (ready) map.current?.setFilter("road-selected", ["==", ["get", "poly_cid"], selected ?? -1]);
  }, [ready, selected]);

  return (
    <div className="map-wrap">
      <div ref={box} className="map" data-testid="map" data-ready={ready} aria-label="Road network map of Emilia-Romagna" />
      {!ready && !error && <div className="map-overlay"><Loading what="road network" /></div>}
      {error && <div className="map-overlay"><ErrorBox message={error} onRetry={() => setAttempt((a) => a + 1)} /></div>}
    </div>
  );
}
