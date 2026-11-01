import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef, useState } from "react";
import { fmt } from "./ui";

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

export interface LineSeries { name: string; values: number[]; slot: 1 | 2 }

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/** Hourly lines on one axis, with a legend, an axis tooltip and a table view. */
export function HourlyChart({ hours, series, label }: { hours: string[]; series: LineSeries[]; label: string }) {
  const el = useRef<HTMLDivElement>(null);
  const [table, setTable] = useState(false);

  useEffect(() => {
    if (!el.current || table) return;
    const chart = echarts.init(el.current);
    const muted = css("--text-secondary");
    chart.setOption({
      animation: false,
      textStyle: { fontFamily: "inherit" },
      grid: { left: 56, right: 16, top: series.length > 1 ? 32 : 12, bottom: 28 },
      tooltip: { trigger: "axis", valueFormatter: (v: number) => fmt(v) },
      legend: series.length > 1 ? { top: 0, left: 0, textStyle: { color: muted }, icon: "roundRect", itemWidth: 12, itemHeight: 3 } : undefined,
      xAxis: { type: "category", data: hours, boundaryGap: false, axisLabel: { color: muted, hideOverlap: true }, axisLine: { lineStyle: { color: css("--grid") } }, axisTick: { show: false } },
      yAxis: { type: "value", min: 0, minInterval: 1, axisLabel: { color: muted, formatter: (v: number) => fmt(v) }, splitLine: { lineStyle: { color: css("--grid") } } },
      series: series.map((s) => ({
        name: s.name, type: "line", data: s.values, showSymbol: hours.length < 3, symbolSize: 8,
        lineStyle: { width: 2, color: css(`--series-${s.slot}`) }, itemStyle: { color: css(`--series-${s.slot}`) },
      })),
    });
    const resize = new ResizeObserver(() => chart.resize());
    resize.observe(el.current);
    return () => { resize.disconnect(); chart.dispose(); };
  }, [hours, series, table]);

  return (
    <figure className="chart" aria-label={label}>
      <button className="link-button chart-toggle" onClick={() => setTable(!table)}>{table ? "Show chart" : "Show table"}</button>
      {table ? (
        <div key="table" className="table-scroll">
          <table>
            <thead><tr><th>Hour starting</th>{series.map((s) => <th key={s.name}>{s.name}</th>)}</tr></thead>
            <tbody>{hours.map((h, i) => <tr key={h}><td>{h}</td>{series.map((s) => <td key={s.name}>{fmt(s.values[i])}</td>)}</tr>)}</tbody>
          </table>
        </div>
      ) : <div key="canvas" ref={el} className="chart-canvas" role="img" aria-label={label} />}
    </figure>
  );
}
