SHELL := /bin/bash

BACKEND_DIR := ../backend
BACKEND_PYTHON := $(BACKEND_DIR)/.venv/bin/python
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000
BACKEND_HEALTH_URL := http://$(BACKEND_HOST):$(BACKEND_PORT)/v1/health

.PHONY: dev dev-backend dev-frontend

dev:
	@if [ ! -x "$(BACKEND_PYTHON)" ]; then \
		echo "Missing backend python: $(BACKEND_PYTHON)"; \
		exit 1; \
	fi
	@set -euo pipefail; \
	if curl -fsS "$(BACKEND_HEALTH_URL)" >/dev/null 2>&1; then \
		echo "Using existing backend at $(BACKEND_HEALTH_URL)"; \
		pnpm exec next dev --port $(FRONTEND_PORT); \
	else \
		echo "Starting backend at $(BACKEND_HEALTH_URL)"; \
		cd "$(BACKEND_DIR)" && .venv/bin/python -m uvicorn app.main:app --host "$(BACKEND_HOST)" --port "$(BACKEND_PORT)" & \
		backend_pid=$$!; \
		cleanup() { \
			kill $$backend_pid 2>/dev/null || true; \
			wait $$backend_pid 2>/dev/null || true; \
		}; \
		trap cleanup EXIT INT TERM; \
		for attempt in $$(seq 1 30); do \
			if curl -fsS "$(BACKEND_HEALTH_URL)" >/dev/null 2>&1; then \
				break; \
			fi; \
			if ! kill -0 $$backend_pid 2>/dev/null; then \
				echo "Backend exited before becoming ready"; \
				exit 1; \
			fi; \
			sleep 1; \
		done; \
		curl -fsS "$(BACKEND_HEALTH_URL)" >/dev/null 2>&1 || { \
			echo "Backend did not become ready in time"; \
			exit 1; \
		}; \
		pnpm exec next dev --port $(FRONTEND_PORT); \
	fi

dev-backend:
	cd "$(BACKEND_DIR)" && .venv/bin/python -m uvicorn app.main:app --host "$(BACKEND_HOST)" --port "$(BACKEND_PORT)"

dev-frontend:
	pnpm exec next dev --port $(FRONTEND_PORT)
