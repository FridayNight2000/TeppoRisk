import type {
  FillLayerSpecification,
  LineLayerSpecification,
  StyleSpecification,
} from "maplibre-gl";

import type { RiskLevel } from "@/app/types/risk";

export type RiskFilterLevel = Exclude<RiskLevel, "unknown">;

export interface RiskFilterItem {
  label: string;
  level: RiskFilterLevel;
  color: string;
}

export interface RiskPalette {
  fill: string;
  stroke: string;
}

export const ACTIVE_STATION_ZOOM = 8.2;
export const CAMERA_TRANSITION_DURATION = 700;
export const RISK_SOURCE_ID = "station-risk";
export const RISK_FILL_LAYER_ID = "station-risk-fill";
export const ACTIVE_SOURCE_ID = "active-station";
export const JAPAN_BOUNDS = [
  [129, 30],
  [146.5, 46.5],
] as [[number, number], [number, number]];

export const MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    openmaptiles: {
      type: "vector",
      url: "https://tiles.openfreemap.org/planet",
    },
  },
  layers: [
    {
      id: "background",
      type: "background",
      paint: {
        "background-color": "#f8fafc",
      },
    },
    {
      id: "water",
      type: "fill",
      source: "openmaptiles",
      "source-layer": "water",
      filter: ["!=", ["get", "brunnel"], "tunnel"],
      paint: {
        "fill-color": "#dbeafe",
        "fill-outline-color": "#93c5fd",
      },
    },
    {
      id: "landcover",
      type: "fill",
      source: "openmaptiles",
      "source-layer": "landcover",
      paint: {
        "fill-color": "#f8faf2",
        "fill-opacity": 0.55,
      },
    },
    {
      id: "admin-boundary-local",
      type: "line",
      source: "openmaptiles",
      "source-layer": "boundary",
      filter: [
        "all",
        [">=", ["get", "admin_level"], 3],
        ["<=", ["get", "admin_level"], 6],
        ["!=", ["get", "maritime"], 1],
        ["!=", ["get", "disputed"], 1],
        ["!", ["has", "claimed_by"]],
      ],
      paint: {
        "line-color": "#cbd5e1",
        "line-dasharray": [2, 2],
        "line-width": [
          "interpolate",
          ["linear"],
          ["zoom"],
          4,
          0.5,
          7,
          1,
          11,
          1.6,
        ],
      },
    },
    {
      id: "admin-boundary-country",
      type: "line",
      source: "openmaptiles",
      "source-layer": "boundary",
      filter: [
        "all",
        ["==", ["get", "admin_level"], 2],
        ["!=", ["get", "maritime"], 1],
        ["!=", ["get", "disputed"], 1],
        ["!", ["has", "claimed_by"]],
      ],
      paint: {
        "line-color": "#64748b",
        "line-width": [
          "interpolate",
          ["linear"],
          ["zoom"],
          3,
          0.8,
          5,
          1.2,
          12,
          2.4,
        ],
      },
    },
  ],
};

export const riskFillLayer: FillLayerSpecification = {
  id: RISK_FILL_LAYER_ID,
  type: "fill",
  source: RISK_SOURCE_ID,
  paint: {
    "fill-color": [
      "match",
      ["get", "risk_level"],
      "low",
      "#7dd3fc",
      "medium",
      "#fde047",
      "high",
      "#fb923c",
      "critical",
      "#ef4444",
      "#94a3b8",
    ],
    "fill-outline-color": [
      "match",
      ["get", "risk_level"],
      "low",
      "#0369a1",
      "medium",
      "#ca8a04",
      "high",
      "#c2410c",
      "critical",
      "#b91c1c",
      "#64748b",
    ],
    "fill-opacity": [
      "case",
      ["==", ["get", "risk_level"], "unknown"],
      0.34,
      0.62,
    ],
  },
};

export const activeRiskFillLayer: FillLayerSpecification = {
  id: "active-station-fill",
  type: "fill",
  source: ACTIVE_SOURCE_ID,
  paint: {
    "fill-color": "#fff7ed",
    "fill-opacity": 0.14,
    "fill-outline-color": "#f97316",
  },
};

export const activeRiskOutlineBackdropLayer: LineLayerSpecification = {
  id: "active-station-outline-backdrop",
  type: "line",
  source: ACTIVE_SOURCE_ID,
  paint: {
    "line-color": "#ffffff",
    "line-width": 6,
    "line-opacity": 0.96,
  },
};

export const activeRiskOutlineLayer: LineLayerSpecification = {
  id: "active-station-outline",
  type: "line",
  source: ACTIVE_SOURCE_ID,
  paint: {
    "line-color": "#f97316",
    "line-width": 3,
    "line-opacity": 1,
  },
};

export const FILTER_PILL_ITEMS: RiskFilterItem[] = [
  { label: "Low", level: "low", color: "#7dd3fc" },
  { label: "Medium", level: "medium", color: "#fde047" },
  { label: "High", level: "high", color: "#fb923c" },
  { label: "Critical", level: "critical", color: "#ef4444" },
];

const RISK_LEVEL_COLORS: Record<RiskLevel, RiskPalette> = {
  low: { fill: "#7dd3fc", stroke: "#0369a1" },
  medium: { fill: "#fde047", stroke: "#a16207" },
  high: { fill: "#fb923c", stroke: "#c2410c" },
  critical: { fill: "#ef4444", stroke: "#b91c1c" },
  unknown: { fill: "#94a3b8", stroke: "#475569" },
};

export function getFilterPillClasses(isActive: boolean): string {
  if (isActive) {
    return "inline-flex cursor-pointer items-center gap-2 rounded-full bg-slate-600 px-3 py-1.5 text-xs font-semibold text-white shadow-none backdrop-blur transition-colors hover:bg-slate-700 active:bg-slate-900";
  }

  return "inline-flex cursor-pointer items-center gap-2 rounded-full bg-white/90 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-[0_16px_34px_rgba(15,23,42,0.13)] backdrop-blur transition-colors hover:bg-zinc-300 active:bg-slate-800 active:text-white";
}

export function formatTimeLabel(value: string | null): string {
  if (!value) return "--";

  return new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function getRiskPalette(level: RiskLevel | null | undefined): RiskPalette {
  if (!level) {
    return RISK_LEVEL_COLORS.unknown;
  }

  return RISK_LEVEL_COLORS[level];
}
