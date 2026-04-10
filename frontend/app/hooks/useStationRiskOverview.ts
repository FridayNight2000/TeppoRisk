import { useEffect, useState } from "react";

import type {
  CurrentProbabilitiesResponse,
  StationRiskOverviewItem,
} from "@/app/types/risk";

interface UseStationRiskOverviewResult {
  baseTime: string | null;
  updatedAt: string | null;
  isStale: boolean;
  stations: StationRiskOverviewItem[];
  loading: boolean;
  error: string | null;
}

export function useStationRiskOverview(): UseStationRiskOverviewResult {
  const [baseTime, setBaseTime] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);
  const [stations, setStations] = useState<StationRiskOverviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchOverview() {
      try {
        const response = await fetch("/api/v1/predict/current-probabilities", {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data: CurrentProbabilitiesResponse = await response.json();
        setBaseTime(data.base_time);
        setUpdatedAt(data.updated_at);
        setIsStale(data.is_stale);
        setStations(data.stations);
        setError(null);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to fetch risk overview");
      } finally {
        setLoading(false);
      }
    }

    fetchOverview();
    return () => controller.abort();
  }, []);

  return { baseTime, updatedAt, isStale, stations, loading, error };
}
