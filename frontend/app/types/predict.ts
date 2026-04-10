export interface PeakProbabilityItem {
  peak_time: string;
  prob_peak: number;
}

export interface StationProbabilityResponse {
  station_id: string;
  station_name: string;
  base_time: string;
  results: PeakProbabilityItem[];
  max_prob: number;
  max_prob_time: string;
}
