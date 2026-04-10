import type { Feature, FeatureCollection, Polygon } from "geojson";

import type { StationRiskOverviewItem } from "@/app/types/risk";

const STATION_SQUARE_SIZE_DEGREES = 0.05;

export function stationToPolygon(
  lat: number,
  lon: number,
  size = STATION_SQUARE_SIZE_DEGREES
): Polygon {
  const half = size / 2;
  return {
    type: "Polygon",
    coordinates: [
      [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
      ],
    ],
  };
}

export function stationsToGeoJSON(
  stations: StationRiskOverviewItem[]
): FeatureCollection<Polygon> {
  const features: Feature<Polygon>[] = stations.map((s) => ({
    type: "Feature",
    geometry: stationToPolygon(s.lat, s.lon),
    properties: {
      site_code: s.site_code,
      station_name: s.station_name,
      current_prob: s.current_prob,
      risk_level: s.risk_level,
    },
  }));

  return { type: "FeatureCollection", features };
}
