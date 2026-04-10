import {
  FILTER_PILL_ITEMS,
  formatTimeLabel,
  getFilterPillClasses,
  type RiskFilterLevel,
} from "@/app/components/rainfall-map/config";

interface RiskToolbarProps {
  activeRiskFilters: ReadonlySet<RiskFilterLevel>;
  stationCount: number;
  updatedAt: string | null;
  isStale: boolean;
  onToggleRiskFilter: (level: RiskFilterLevel) => void;
}

const floatingPillClasses =
  "inline-flex items-center gap-2 rounded-full border border-white/85 bg-white/90 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-[0_16px_34px_rgba(15,23,42,0.13)] backdrop-blur";

export function RiskToolbar({
  activeRiskFilters,
  stationCount,
  updatedAt,
  isStale,
  onToggleRiskFilter,
}: RiskToolbarProps) {
  return (
    <div className="mb-4 flex w-[92vw] flex-col gap-2 md:w-[60vw] md:flex-row md:items-center md:justify-center md:gap-x-108">
      <div className="flex flex-wrap items-center gap-2">
        {FILTER_PILL_ITEMS.map((item) => (
          <button
            key={item.level}
            type="button"
            aria-pressed={activeRiskFilters.has(item.level)}
            onClick={() => onToggleRiskFilter(item.level)}
            className={getFilterPillClasses(activeRiskFilters.has(item.level))}
          >
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            {item.label}
          </button>
        ))}
      </div>
      <div className="flex justify-end">
        <span className={floatingPillClasses}>
          <span className="font-medium text-slate-500">Areas</span> {stationCount} ·{" "}
          <span className="font-medium text-slate-500">Updated</span>{" "}
          {formatTimeLabel(updatedAt)}
          {isStale && (
            <>
              {" · "}
              <span className="font-medium text-amber-700">Stale cache</span>
            </>
          )}
        </span>
      </div>
    </div>
  );
}
