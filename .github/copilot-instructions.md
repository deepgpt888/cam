# CamPark — AI Coding Agent Instructions

## What This System Is
Snapshot-only parking occupancy platform. Cameras upload JPEG snapshots via FTP → worker runs YOLO + zone classifier → Flask API serves occupancy JSON + admin UI. **No video streams.** FTP is the hard prerequisite: no FTP upload = no ingestion.

## Architecture & Data Flow
```
Camera (FTP upload every ~120s or on motion)
  └─> pure-ftpd container → /data/ftp/{ftp_username}/incoming/*.jpg
        └─> worker (polls every 1s per camera, ThreadPoolExecutor)
              ├─ perceptual diff (32×32 thumb) — skip if scene unchanged
              ├─ YOLO inference (car/truck/motorcycle/bicycle, conf≥0.50)
              ├─ ZoneCls (ONNX classifier or placeholder)
              └─> PostgreSQL (snapshots, detections, zone_states, zone_events)
                    └─> Flask API (:8000) → Caddy (TLS) → external dashboards
```

**Key services** (all in `docker-compose.yml`):
- `ftp` — pure-ftpd, multi-user via `/data/ftp/.ftp_users.json` (written by API on camera add/delete)
- `worker` — `services/worker/` — polls filesystem, no Redis queue needed (`REDIS_USE_DB_FALLBACK=true`)
- `api` — `services/api/main.py` (Flask, 1658 lines) — admin UI + JSON API + health monitor thread
- `ingestion` — **commented out by default**; only needed for LAPI WebSocket / RTSP cameras

## DB Schema Conventions
- Schema lives in `services/config/init.sql` — **never use SQLAlchemy `create_all()`**; tables are pre-created by Docker init.
- ORM models are duplicated in `services/api/app/db.py` and `services/worker/db.py` — keep both in sync when adding columns.
- Zone polygons stored as JSON strings `[[x,y],...]` normalized to **0–100%** of image dimensions.
- `ftp_password_hash` is a misnomer — it stores **plaintext** password for pure-ftpd virtual users.

## Adding a Camera
Done via `POST /admin/cameras` (no code changes needed). The API:
1. Inserts `cameras` row, creates `/data/ftp/{ftp_username}/incoming/` directory
2. Calls `sync_ftp_users()` → writes `/data/ftp/.ftp_users.json` for the FTP container to hot-reload

## Worker Inference Pipeline (`services/worker/infer/pipeline.py`)
1. **Stability check** — wait until file size is stable (prevents partial-write reads)
2. **SHA-256 dedup** — skip if `file_hash` already in `snapshots` table
3. **Operating hours gate** — outside `operating_hours_start`–`operating_hours_end`: heartbeat only, discard file
4. **Perceptual diff** — 32×32 grayscale thumb, mean pixel delta vs previous. Skip if `< scene_diff_threshold` (default 6.0). Set to `≤0` to disable.
5. **YOLO** (if `YOLO_ENABLED=true`) — valid classes: `car`, `truck`, `motorcycle`, `bicycle`
6. **ZoneCls** — mode set by `ZONECLS_MODE`: `placeholder` (dev), `onnx` (prod, model at `/models/zonecls.onnx`)
7. Settings (`operating_hours_start/end`, `scene_diff_threshold`) are re-read from `system_settings` table **each worker cycle** — no restart needed.

## API Auth Patterns
- **Admin UI** (`/admin/*`) — session cookie (`ADMIN_USERNAME`/`ADMIN_PASSWORD` env vars, default `admin`/`changeme_poc`)
- **External JSON API** (`/api/v1/*`) — `X-API-Key` header; keys stored as SHA-256 hash in `api_clients` table. Disabled by default (`REQUIRE_API_KEY=false`). Read-only; 1 token charged per zone per `/status` call.
- `check_api_key()` returns `(error_tuple_or_None, client_or_None)` — always call at the top of API routes.

## Dev Workflows
```bash
# Start all services (GCP VM)
docker compose up -d

# Initial deployment on new GCP VM
./deploy.sh YOUR_STATIC_IP

# Deploy code changes from local → server (templates baked into image — MUST rebuild)
ssh campark-server "cd ~/CamPark && git pull origin main && docker compose up -d --build --no-deps api"

# Validate FTP ingest end-to-end (must pass before building)
docker compose up -d ftp
bash tests/ftp_test.sh

# View worker logs
docker compose logs -f worker

# Force-sync FTP users after DB change
curl -X POST http://localhost:8000/admin/ftp-sync
```

## ML: Zone Classifier Training
```bash
# Generate labeled crops from DB snapshots
python ml/zonecls/dataset_gen.py --camera-id cam001 --sampling-mode state_change ...

# Train (outputs .pt checkpoint)
python ml/zonecls/train.py --config ml/zonecls/configs/v1.yaml

# Export to ONNX → copy to ./models/zonecls.onnx
python ml/zonecls/export_onnx.py --checkpoint model_best.pt --output /models/zonecls.onnx
# Then set ZONECLS_MODE=onnx in docker-compose.yml / .env
```

## Camera Health States
`ONLINE` → `STALE` (>150s no snapshot) → `OFFLINE` (>300s). Transitions fire Telegram alert via `send_telegram()`. Thresholds: `STALE_SECONDS` / `OFFLINE_SECONDS` env vars.

## Key Files Quick Reference
| File | Purpose |
|------|---------|
| `services/api/main.py` | All Flask routes, health monitor, FTP sync |
| `services/worker/infer/pipeline.py` | Core inference loop |
| `services/worker/db.py` | Worker ORM models |
| `services/api/app/db.py` | API ORM models (keep in sync with worker's) |
| `services/config/init.sql` | Source of truth for DB schema |
| `docker-compose.yml` | All env var defaults documented inline |
| `.env.example` | Required env vars for GCP deployment |
