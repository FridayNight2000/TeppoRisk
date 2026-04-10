<div align="center">
  <h1>🌊 TeppoRisk</h1>
  <p><strong>Real-Time Flash Flood (鉄砲水 - Teppo-mizu) Risk Assessment & Visualization for Japan</strong></p>
</div>

## 📖 Overview

**TeppoRisk** is a modern, high-performance web platform designed specifically to monitor, assess, and visualize real-time flash flood risks across Japan. 

In regions with complex terrain and steep waterways, *Teppo-mizu* (sudden flash floods) can occur with devastating speed following heavy but localized rainfall. Traditional long-term weather forecasts often lack the spatial granularity and immediacy needed to provide warning in these rapid physical phenomena. TeppoRisk bridges this critical gap by offering immediate, localized insights and translating complex data into an intuitive interactive map.

## ✨ Core Features

- 🗺️ **Dynamic Risk Mapping**: Real-time visual representation of precipitation intensity and instant calculated flash-flood probability metrics directly on an interactive geographical map.
- ⚡ **Rapid Assessment Engine**: Powered by a robust data-driven backend model, the system rapidly analyzes incoming meteorological data, radar outputs, and localized geographical context to compute vulnerability on the fly.
- 📍 **Granular Station Tracking**: Incorporates highly detailed metadata from observation stations across Japan, enabling pinpoint accuracy and localized tracking rather than broad, unhelpful regional generalizations.

## 🧠 Methodology & Architecture

TeppoRisk is structured to offer maximum reliability, speed, and visual clarity:

1. **Frontend Experience**: An intuitive and responsive Next.js application that leverages WebGL mapping technologies for perfectly smooth, high-fidelity spatial interactions. 
2. **Inference API**: A high-speed FastAPI service that serves model assessments, processes station correlations (`station_metadata`), and connects our predictive algorithms directly to the frontend.

By interpreting fast-moving streams of meteorological metrics through localized real-world knowledge, **TeppoRisk** provides a vital, immediate tool for disaster awareness and visual data analysis.
