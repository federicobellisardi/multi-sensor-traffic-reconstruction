import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, errorText } from "./api";
import { DataBadge, ErrorBox, StatusPill } from "./components/ui";
import { diffNorm, flowNorm } from "./mapScale";
import { formToParams, type FormState } from "./pages/ScenariosPage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const form: FormState = { name: "n", description: "", profile: "research_frozen", hours: "", trips: "1", day: "2020-02-15", variant: "V6_scaled", seed: "", factor: "1" };

describe("scenario form", () => {
  it("keeps a frozen research scenario free of overrides", () => {
    expect(formToParams(form)).toEqual({ seed: null, perturbations: [], day: "2020-02-15", variant: "V6_scaled", hours: null });
  });
  it("turns a factor into a demand perturbation", () => {
    expect(formToParams({ ...form, factor: "1.5", seed: "3" })).toMatchObject({ seed: 3, perturbations: [{ kind: "demand_scale", factor: 1.5 }] });
  });
  it("sends the demo fields", () => {
    expect(formToParams({ ...form, profile: "demo_synthetic", hours: "4", trips: "500" })).toMatchObject({ hours: 4, trips_per_day: 500 });
  });
});

describe("map scales", () => {
  it("normalises flows and survives an empty hour", () => {
    expect(flowNorm([0, 25, 100])).toEqual({ max: 100, norm: [0, 0.5, 1] });
    expect(flowNorm([0, 0]).norm).toEqual([0, 0]);
  });
  it("keeps the sign of differences on a symmetric scale", () => {
    expect(diffNorm([100, 100, 5], [0, 125, 5])).toEqual({ max: 100, norm: [-1, 0.5, 0] });
  });
});

describe("api errors", () => {
  it("formats validation errors", () => {
    expect(errorText([{ loc: ["body", "hours"], msg: "too large" }])).toBe("hours: too large");
  });
  it("reports the server detail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "queue full" }), { status: 429 })));
    await expect(api.runs()).rejects.toMatchObject({ status: 429, message: "queue full" });
  });
  it("reports an unreachable server", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("network"); }));
    await expect(api.runs()).rejects.toBeInstanceOf(ApiError);
  });
});

describe("components", () => {
  it("never conveys status by colour alone", () => {
    render(<StatusPill status="failed" />);
    expect(screen.getByTestId("status")).toHaveTextContent("Failed");
  });
  it("labels synthetic data", () => {
    render(<DataBadge run={{ data_class: "synthetic" }} />);
    expect(screen.getByText(/SYNTHETIC/)).toBeInTheDocument();
  });
  it("offers a retry", () => {
    const retry = vi.fn();
    render(<ErrorBox message="x" onRetry={retry} />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
