import ProbabilityChart from "@/app/components/ProbabilityChart";
import { getRiskPalette } from "@/app/components/rainfall-map/config";
import type { StationProbabilityResponse } from "@/app/types/predict";
import type { StationRiskOverviewItem } from "@/app/types/risk";

interface StationDetailCardProps {
  selectedStation: StationRiskOverviewItem;
  detail: StationProbabilityResponse | null;
  detailLoading: boolean;
  detailError: string | null;
  onClose: () => void;
}

export function StationDetailCard({
  selectedStation,
  detail,
  detailLoading,
  detailError,
  onClose,
}: StationDetailCardProps) {
  const { fill, stroke } = getRiskPalette(selectedStation.risk_level);
  const areaName = selectedStation.station_name || selectedStation.site_code;
  const latestProbabilityValue = detail?.results.at(-1)?.prob_peak;
  const latestProbabilityText =
    typeof latestProbabilityValue === "number"
      ? `${(latestProbabilityValue * 100).toFixed(1)}%`
      : null;

  return (
    <div className="pointer-events-auto w-full md:max-w-[24rem]">
      <div className="rounded-[1.75rem] border border-white/85 bg-white/92 p-4 shadow-[0_24px_60px_rgba(15,23,42,0.16)] backdrop-blur">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="ml-3 flex items-end gap-2">
            <span className="text-2xl font-semibold text-zinc-500">{areaName}</span>
            <span className="text-2xl font-semibold text-zinc-500">-</span>
            {latestProbabilityText && (
              <span className="text-2xl font-semibold" style={{ color: stroke }}>
                {latestProbabilityText}
              </span>
            )}
          </div>
          <button
            type="button"
            aria-label="Deselect station"
            onClick={onClose}
            className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-white text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 active:bg-slate-800 active:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M6 6L18 18M18 6L6 18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        <div className="mt-1">
          {detailLoading && (
            <div className="flex h-44 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-sm text-slate-500">
              Loading probability curve...
            </div>
          )}

          {!detailLoading && detailError && (
            <div className="flex h-44 items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 px-4 text-center text-sm text-rose-700">
              {detailError}
            </div>
          )}

          {!detailLoading && !detailError && detail && (
            <ProbabilityChart results={detail.results} lineColor={fill} />
          )}
        </div>
      </div>
    </div>
  );
}
