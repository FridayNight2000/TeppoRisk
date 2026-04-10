"use client";

import { useId } from "react";

import type { PeakProbabilityItem } from "@/app/types/predict";

const CHART_WIDTH = 320;
const CHART_HEIGHT = 168;
const CHART_PADDING_X = 38;
const CHART_PADDING_Y = 18;

interface ProbabilityChartProps {
  results: PeakProbabilityItem[];
  lineColor?: string;
}

function formatHourLabel(value: string): string {
  return new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function buildLinePath(results: PeakProbabilityItem[]): string {
  const innerWidth = CHART_WIDTH - CHART_PADDING_X * 2;
  const innerHeight = CHART_HEIGHT - CHART_PADDING_Y * 2;

  return results
    .map((entry, index) => {
      const x =
        CHART_PADDING_X +
        (results.length === 1
          ? 0
          : (index / (results.length - 1)) * innerWidth);
      const y =
        CHART_PADDING_Y +
        (1 - Math.min(Math.max(entry.prob_peak, 0), 1)) * innerHeight;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
}

function buildAreaPath(results: PeakProbabilityItem[]): string {
  const innerWidth = CHART_WIDTH - CHART_PADDING_X * 2;
  const innerHeight = CHART_HEIGHT - CHART_PADDING_Y * 2;
  const baselineY = CHART_PADDING_Y + innerHeight;
  const line = results
    .map((entry, index) => {
      const x =
        CHART_PADDING_X +
        (results.length === 1
          ? 0
          : (index / (results.length - 1)) * innerWidth);
      const y =
        CHART_PADDING_Y +
        (1 - Math.min(Math.max(entry.prob_peak, 0), 1)) * innerHeight;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  return `${line} L ${CHART_PADDING_X + innerWidth} ${baselineY} L ${CHART_PADDING_X} ${baselineY} Z`;
}

export default function ProbabilityChart({
  results,
  lineColor = "#f97316",
}: ProbabilityChartProps) {
  const gradientId = `${useId().replace(/:/g, "")}-probability-area`;

  if (results.length === 0) {
    return (
      <div className="flex h-44 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-sm text-slate-500">
        No probability curve data available
      </div>
    );
  }

  const path = buildLinePath(results);
  const areaPath = buildAreaPath(results);
  const firstLabel = formatHourLabel(results[0].peak_time);
  const lastLabel = formatHourLabel(
    results.at(-1)?.peak_time ?? results[0].peak_time,
  );

  return (
    <div className="rounded-[1.75rem] border border-slate-200/80 bg-white/95 p-4 shadow-[0_18px_46px_rgba(15,23,42,0.10)] backdrop-blur">
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        className="-mx-2 h-44 w-[calc(100%+1rem)] overflow-visible"
        role="img"
        aria-label="Station probability trend"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity="0.28" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {[0, 0.25, 0.5, 0.75, 1].map((value) => {
          const y =
            CHART_PADDING_Y +
            (1 - value) * (CHART_HEIGHT - CHART_PADDING_Y * 2);
          return (
            <g key={value}>
              <line
                x1={CHART_PADDING_X}
                x2={CHART_WIDTH - CHART_PADDING_X}
                y1={y}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="4 6"
              />
              <text x={6} y={y + 4} fontSize="11" fill="#64748b">
                {value.toFixed(2)}
              </text>
            </g>
          );
        })}

        <path d={areaPath} fill={`url(#${gradientId})`} />
        <path
          d={path}
          fill="none"
          stroke={lineColor}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {results.map((entry, index) => {
          const x =
            CHART_PADDING_X +
            (results.length === 1
              ? 0
              : (index / (results.length - 1)) *
                (CHART_WIDTH - CHART_PADDING_X * 2));
          const y =
            CHART_PADDING_Y +
            (1 - Math.min(Math.max(entry.prob_peak, 0), 1)) *
              (CHART_HEIGHT - CHART_PADDING_Y * 2);
          return (
            <circle
              key={`${entry.peak_time}-${index}`}
              cx={x}
              cy={y}
              r={index === results.length - 1 ? 4.5 : 3}
              fill={lineColor}
              stroke="#fff7ed"
              strokeWidth="2"
            />
          );
        })}
      </svg>

      <div className="mt-0 flex items-center justify-between text-xs text-slate-500 px-5">
        <span>{firstLabel}</span>
        <span>{lastLabel}</span>
      </div>
    </div>
  );
}
