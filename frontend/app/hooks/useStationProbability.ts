import { useEffect, useState } from "react";

import type { StationProbabilityResponse } from "@/app/types/predict";

interface UseStationProbabilityResult {
  detail: StationProbabilityResponse | null;
  loading: boolean;
  error: string | null;
}

export function useStationProbability(
  stationId: string | null,
  baseTime: string | null,
): UseStationProbabilityResult {
  const [detail, setDetail] = useState<StationProbabilityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!stationId) {
      setDetail(null);
      setLoading(false);
      setError(null);
      return;
    }

    const controller = new AbortController();
    const requestedStationId = stationId;

    async function fetchStationProbability() {
      setDetail(null);
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          station_id: requestedStationId,
        });
        if (baseTime) {
          params.set("base_time", baseTime);
        }

        const response = await fetch(
          `/api/v1/predict/station-probability?${params}`,
          {
            signal: controller.signal,
          },
        );
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data: StationProbabilityResponse = await response.json();
        if (controller.signal.aborted) return;
        setDetail(data);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setDetail(null);
        setError(
          err instanceof Error ? err.message : "Failed to fetch station detail",
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchStationProbability();
    return () => controller.abort();
  }, [baseTime, stationId]);

  return { detail, loading, error };
}
