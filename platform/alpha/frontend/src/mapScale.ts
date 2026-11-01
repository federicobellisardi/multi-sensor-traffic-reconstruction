/** Square-root scales: link flows are strongly skewed, a linear scale would leave most roads pale. */
export function flowNorm(flow: number[]): { norm: number[]; max: number } {
  const max = Math.max(0, ...flow);
  return { max, norm: flow.map((v) => (max > 0 ? Math.sqrt(v / max) : 0)) };
}

/** Signed, symmetric around zero, on the same scale for both signs. */
export function diffNorm(a: number[], b: number[]): { norm: number[]; max: number } {
  const d = b.map((v, i) => v - a[i]);
  const max = Math.max(0, ...d.map(Math.abs));
  return { max, norm: d.map((v) => (max > 0 ? Math.sign(v) * Math.sqrt(Math.abs(v) / max) : 0)) };
}
