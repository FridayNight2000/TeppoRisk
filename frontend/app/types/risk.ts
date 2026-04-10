export type RiskLevel =
  | "low"
  | "medium"
  | "high"
  | "critical"
  | "unknown";

export interface StationRiskOverviewItem {
  site_code: string;
  station_name: string;
  lat: number;
  lon: number;
  current_prob: number | null;
  risk_level: RiskLevel;
}

export interface CurrentProbabilitiesResponse {
  updated_at: string;
  base_time: string;
  is_stale: boolean;
  stations: StationRiskOverviewItem[];
}
