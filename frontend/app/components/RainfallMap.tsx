"use client";

import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import Map, { Layer, Source } from "react-map-gl/maplibre";
import type { MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

import { MapMessageOverlay } from "@/app/components/rainfall-map/MapMessageOverlay";
import { RiskToolbar } from "@/app/components/rainfall-map/RiskToolbar";
import { StationDetailCard } from "@/app/components/rainfall-map/StationDetailCard";
import {
  ACTIVE_SOURCE_ID,
  ACTIVE_STATION_ZOOM,
  CAMERA_TRANSITION_DURATION,
  JAPAN_BOUNDS,
  MAP_STYLE,
  RISK_FILL_LAYER_ID,
  RISK_SOURCE_ID,
  activeRiskFillLayer,
  activeRiskOutlineBackdropLayer,
  activeRiskOutlineLayer,
  getRiskPalette,
  riskFillLayer,
  type RiskFilterLevel,
} from "@/app/components/rainfall-map/config";
import { useStationProbability } from "@/app/hooks/useStationProbability";
import { useStationRiskOverview } from "@/app/hooks/useStationRiskOverview";
import { stationsToGeoJSON } from "@/app/lib/geo";
import type { StationRiskOverviewItem } from "@/app/types/risk";

function getSelectedStation(
  stations: StationRiskOverviewItem[],
  selectedStationId: string | null,
): StationRiskOverviewItem | null {
  if (!selectedStationId) return null;
  return (
    stations.find((station) => station.site_code === selectedStationId) ?? null
  );
}

export default function RainfallMap() {
  const { stations, baseTime, updatedAt, isStale, loading, error } =
    useStationRiskOverview();
  const [selectedStationId, setSelectedStationId] = useState<string | null>(
    null,
  );
  const [activeRiskFilters, setActiveRiskFilters] = useState<
    Set<RiskFilterLevel>
  >(() => new Set());
  const [isMapReady, setIsMapReady] = useState(false);
  const mapRef = useRef<MapRef | null>(null);
  const hasFocusedStationRef = useRef(false);

  const visibleStations = useMemo(() => {
    if (activeRiskFilters.size === 0) return stations;

    return stations.filter(
      (station) =>
        station.risk_level !== "unknown" &&
        activeRiskFilters.has(station.risk_level),
    );
  }, [activeRiskFilters, stations]);

  const selectedStation = useMemo(
    () => getSelectedStation(visibleStations, selectedStationId),
    [selectedStationId, visibleStations],
  );
  const {
    detail,
    loading: detailLoading,
    error: detailError,
  } = useStationProbability(selectedStation?.site_code ?? null, baseTime);
  const selectedRiskPalette = getRiskPalette(selectedStation?.risk_level);

  const geojson = useMemo(
    () => stationsToGeoJSON(visibleStations),
    [visibleStations],
  );
  const selectedStationGeojson = useMemo(() => {
    return selectedStation ? stationsToGeoJSON([selectedStation]) : null;
  }, [selectedStation]);

  const showOverlay = !loading && !error && visibleStations.length === 0;

  function toggleRiskFilter(level: RiskFilterLevel) {
    setActiveRiskFilters((currentFilters) => {
      const nextFilters = new Set(currentFilters);

      if (nextFilters.has(level)) {
        nextFilters.delete(level);
      } else {
        nextFilters.add(level);
      }

      return nextFilters;
    });
  }

  useEffect(() => {
    if (!selectedStation) {
      hasFocusedStationRef.current = false;
    }
  }, [selectedStation]);

  useEffect(() => {
    if (!selectedStation || !mapRef.current || !isMapReady) return;

    mapRef.current.easeTo({
      center: [selectedStation.lon, selectedStation.lat],
      zoom: ACTIVE_STATION_ZOOM,
      duration: hasFocusedStationRef.current ? CAMERA_TRANSITION_DURATION : 0,
    });

    hasFocusedStationRef.current = true;
  }, [isMapReady, selectedStation]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    return () => {
      if (map) {
        map.getCanvas().style.cursor = "";
      }
    };
  }, []);

  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden bg-slate-200 px-4 py-8">
      <RiskToolbar
        activeRiskFilters={activeRiskFilters}
        stationCount={stations.length}
        updatedAt={updatedAt}
        isStale={isStale}
        onToggleRiskFilter={toggleRiskFilter}
      />

      <div className="relative h-[min(82vh,860px)] w-[92vw] overflow-hidden rounded-[2.15rem] border-10 border-white shadow-[0_40px_100px_rgba(15,23,42,0.24)] md:w-[60vw]">
        <Map
          ref={mapRef}
          onLoad={() => setIsMapReady(true)}
          onClick={(event) => {
            const feature = event.features?.find(
              (item) => item.layer.id === RISK_FILL_LAYER_ID,
            );
            const siteCode = feature?.properties?.site_code;

            if (typeof siteCode !== "string") return;
            startTransition(() => setSelectedStationId(siteCode));
          }}
          onMouseMove={(event) => {
            const map = mapRef.current?.getMap();
            if (!map) return;

            const isHovering = event.features?.some(
              (feature) => feature.layer.id === RISK_FILL_LAYER_ID,
            );
            map.getCanvas().style.cursor = isHovering ? "pointer" : "";
          }}
          interactiveLayerIds={[RISK_FILL_LAYER_ID]}
          initialViewState={{
            bounds: JAPAN_BOUNDS,
            fitBoundsOptions: {
              padding: {
                top: 100,
                right: 24,
                bottom: 24,
                left: 24,
              },
            },
          }}
          maxBounds={JAPAN_BOUNDS}
          minZoom={4.2}
          dragRotate={false}
          touchPitch={false}
          boxZoom={false}
          style={{ width: "100%", height: "100%" }}
          mapStyle={MAP_STYLE}
        >
          {stations.length > 0 && (
            <Source id={RISK_SOURCE_ID} type="geojson" data={geojson}>
              <Layer {...riskFillLayer} />
            </Source>
          )}

          {selectedStationGeojson && (
            <Source
              id={ACTIVE_SOURCE_ID}
              type="geojson"
              data={selectedStationGeojson}
            >
              <Layer
                {...activeRiskFillLayer}
                paint={{
                  ...activeRiskFillLayer.paint,
                  "fill-outline-color": selectedRiskPalette.stroke,
                }}
              />
              <Layer {...activeRiskOutlineBackdropLayer} />
              <Layer
                {...activeRiskOutlineLayer}
                paint={{
                  ...activeRiskOutlineLayer.paint,
                  "line-color": selectedRiskPalette.stroke,
                }}
              />
            </Source>
          )}
        </Map>

        <div className="pointer-events-none absolute inset-x-4 top-4 z-10 flex flex-col gap-3 md:flex-row md:items-start md:justify-end">
          {selectedStation && (
            <StationDetailCard
              selectedStation={selectedStation}
              detail={detail}
              detailLoading={detailLoading}
              detailError={detailError}
              onClose={() => setSelectedStationId(null)}
            />
          )}
        </div>
        {loading && <MapMessageOverlay message="Loading risk overview..." />}

        {error && <MapMessageOverlay message={error} tone="error" />}

        {showOverlay && (
          <MapMessageOverlay message="No risk overview data available currently" />
        )}
      </div>
    </div>
  );
}
