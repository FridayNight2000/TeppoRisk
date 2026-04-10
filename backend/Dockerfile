FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY model_assets/ model_assets/
COPY station_metadata_v2.xlsx .

ENV APP_NAME="Real Time Risk API" \
    DEBUG=false \
    API_V1_PREFIX=/v1 \
    CORS_ORIGINS='["*"]' \
    MODEL_CKPT_PATH=/app/model_assets/best_model.pth \
    SCALER_DYN_PATH=/app/model_assets/scaler_dyn.gz \
    SCALER_STAT_PATH=/app/model_assets/scaler_stat.gz \
    STATION_METADATA_PATH=/app/station_metadata_v2.xlsx

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
