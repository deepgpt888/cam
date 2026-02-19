# CamPark POC: Master Checklist

Use this checklist to track progress through the 4-phase POC.

---

## Phase 1: Gate Check (3–4 hours)

**Goal:** Prove camera can upload JPEG snapshots via FTP

### Pre-Flight (30 min)
- [ ] Docker installed (`docker --version`)
- [ ] Docker Compose installed (`docker-compose --version`)
- [ ] Python 3 installed (`python3 --version`)
- [ ] FTP client available (`which ftp`)
- [ ] Network access to camera (ping test)
- [ ] Project cloned to `/workspaces/CamPark`

### FTP Server Setup (Docker, 10 min)
- [ ] FTP folders created: `mkdir -p data/ftp/cam001/incoming`
- [ ] FTP container started: `docker-compose up -d ftp`
- [ ] Public host set in `.env` (`FTP_PUBLICHOST`)
- [ ] Passive ports set in `.env` (`FTP_PASSIVE_PORTS`)

### FTP Test (30 min)
- [ ] FTP test script exists: `/workspaces/CamPark/tests/ftp_test.sh`
- [ ] FTP test runs successfully: `bash tests/ftp_test.sh`
- [ ] Test creates minimal JPEG
- [ ] FTP upload succeeds
- [ ] File found in `./data/ftp/cam001/incoming/`
- [ ] File is valid JPEG (verified with `file` command)

### Camera Configuration (1–1.5 hours)
- [ ] Camera IP found (network scan or DHCP list)
- [ ] Camera web UI accessible: `http://<camera-ip>`
- [ ] Logged into camera admin panel (admin/admin)
- [ ] Camera password changed (for safety)
- [ ] FTP settings configured:
  - [ ] Server: Your machine IP (e.g., 192.168.1.100)
  - [ ] Port: 21
  - [ ] Username: cam001
  - [ ] Password: password123
  - [ ] Remote directory: incoming
  - [ ] Passive mode: ENABLED ✓
- [ ] FTP test button clicked → "Connection successful"
- [ ] Motion detection enabled
- [ ] Heartbeat interval set to 120 seconds

### Gate Validation (15 min)
- [ ] First heartbeat received (wait ~2 min)
- [ ] Files visible: `ls -la ./data/ftp/cam001/incoming/`
- [ ] File count ≥ 3 (at least 3 heartbeat snapshots)
- [ ] File size > 10KB (real JPEG, not corrupted)
- [ ] File validation: `file ./data/ftp/cam001/incoming/*.jpg` → JPEG image data
- [ ] Files arriving regularly (every ~120 seconds)

### Proof for Boss
- [ ] Screenshot of `./data/ftp/cam001/incoming/` with multiple files
- [ ] Terminal output showing file sizes and timestamps
- [ ] Timestamp showing files arriving at 120-second intervals

---

## Phase 2: Database & Infrastructure (Day 1, 1 hour)

### PostgreSQL Setup
- [ ] `docker-compose.yml` exists with postgres service
- [ ] `services/config/init.sql` exists with schema
- [ ] Docker network created (or auto-created by compose)
- [ ] `docker-compose up -d postgres` starts successfully
- [ ] Database ready: `docker ps | grep postgres | grep healthy`
- [ ] Schema loaded: `docker exec campark-db psql -U campark -d campark -c "SELECT COUNT(*) FROM cameras;"`
- [ ] Test data exists (cam001 should be in database)

---

## Phase 2: API Service (Day 1, 2–3 hours)

### Directory Structure
- [ ] `services/api/` directory created
- [ ] `services/api/main.py` created
- [ ] `services/api/requirements.txt` created
- [ ] `services/api/Dockerfile` created
- [ ] `services/api/app/__init__.py` created
- [ ] `services/api/app/db.py` created (SQLAlchemy models)

### SQLAlchemy Models (db.py)
- [ ] `Project` model defined
- [ ] `Site` model defined
- [ ] `Camera` model defined
- [ ] `Zone` model defined
- [ ] `ZoneState` model defined
- [ ] `Snapshot` model defined
- [ ] `Detection` model defined
- [ ] `ZoneEvent` model defined
- [ ] Database initialization in Flask app

### Flask Routes (routes.py)
- [ ] `/health` GET endpoint (service health)
- [ ] `/api/v1/sites/<site_id>/status` GET endpoint
- [ ] `/api/v1/cameras/<camera_id>/status` GET endpoint
- [ ] `/admin/cameras` GET endpoint (list cameras)
- [ ] Response format includes: `zones`, `occupied_units`, `available_units`

### Dockerfile
- [ ] `FROM python:3.9`
- [ ] `COPY requirements.txt .`
- [ ] `RUN pip install -r requirements.txt`
- [ ] `COPY app/ app/`
- [ ] `CMD ["gunicorn", "-b", "0.0.0.0:8000", "main:app"]`

### Environment & Secrets
- [ ] `DATABASE_URL` env var set
- [ ] `LOG_LEVEL` env var set
- [ ] Flask debug mode disabled (production mode)

### Docker Container
- [ ] API service builds: `docker-compose build api`
- [ ] API service starts: `docker-compose up -d api`
- [ ] Container healthy: `docker ps | grep campark-api | grep Up`
- [ ] Health endpoint responds: `curl http://localhost:8000/health`

---

## Phase 2: YOLO Worker (Day 1, 2–3 hours)

### Directory Structure
- [ ] `services/worker/` directory created
- [ ] `services/worker/main.py` created
- [ ] `services/worker/requirements.txt` created
- [ ] `services/worker/Dockerfile` created
- [ ] `services/worker/yolo_processor.py` created

### FTP Watcher (main.py)
- [ ] Monitors `/data/ftp/cam001/incoming/`
- [ ] Detects new `.jpg` files
- [ ] Checks for duplicates (using set or DB)
- [ ] Enqueues file for processing (DB table: `queue`)
- [ ] Handles errors gracefully (logs failures)
- [ ] Runs in infinite loop with 1-second sleep

### YOLO Inference (yolo_processor.py)
- [ ] Loads `yolov8n.pt` model
- [ ] Loads image from file path
- [ ] Runs inference with confidence threshold (0.80)
- [ ] Extracts detections: class, confidence, bounding box
- [ ] Normalizes bbox to 0–100% (image coordinates)
- [ ] Saves detections to DB table: `detections`
- [ ] Updates `snapshots.processed_at` timestamp

### Zone State Update
- [ ] Queries all zones for this camera
- [ ] For each detection:
  - [ ] Check overlap with zone polygon
  - [ ] Count if overlap ≥ 30%
- [ ] Apply debounce rule: need 2 consecutive frames to commit state change
- [ ] Update `zone_states.occupied_units`
- [ ] Create `zone_events` record if state changed
- [ ] Set `zone_events.snapshot_id` to evidence

### Dockerfile
- [ ] `FROM python:3.9`
- [ ] Includes torch+cpu (or pip install)
- [ ] `RUN pip install -r requirements.txt`
- [ ] Mounts `/data/ftp` and `/data/images`
- [ ] `CMD ["python", "main.py"]`

### Docker Container
- [ ] Worker service builds: `docker-compose build worker`
- [ ] Worker service starts: `docker-compose up -d worker`
- [ ] Container running: `docker ps | grep campark-worker | grep Up`
- [ ] Logs show detection processing: `docker logs campark-worker | grep vehicle`

---

## Phase 2: Integration Test (Day 1, 30 min)

### Manual Snapshot Upload
- [ ] Create test JPEG (or use real photo with cars)
- [ ] Upload to FTP: `cp test.jpg /data/ftp/cam001/incoming/test_20260205_103000.jpg`
- [ ] Wait 5 seconds for worker to process
- [ ] Check queue table: `docker exec campark-db psql -U campark -d campark -c "SELECT * FROM queue;"`
- [ ] Check detections: `docker exec campark-db psql -U campark -d campark -c "SELECT * FROM detections ORDER BY created_at DESC LIMIT 5;"`

### API Response Validation
- [ ] Call API: `curl http://localhost:8000/api/v1/sites/1/status | jq`
- [ ] Response includes: `site_id`, `ts`, `zones`, `totals`
- [ ] Zone entry includes: `zone_id`, `state`, `occupied_units`, `available_units`
- [ ] Occupancy reflects YOLO detections
- [ ] Response is valid JSON

### End-of-Day Proof
- [ ] API responding: ✅
- [ ] Database has detections: ✅
- [ ] Zone state updating: ✅
- [ ] Docker services healthy: ✅

---

## Phase 3: Camera Health Monitoring (Day 2, 2 hours)

### Background Task
- [ ] Background thread created in Flask app
- [ ] Task runs every 30 seconds
- [ ] Queries all cameras from DB
- [ ] Calculates `age_seconds = now - camera.last_seen_at`

### Health Status Rules
- [ ] age_seconds > 300 → status = OFFLINE
- [ ] age_seconds > 150 (< 300) → status = STALE
- [ ] age_seconds ≤ 150 → status = ONLINE

### Alert Triggering
- [ ] On status change, call `trigger_alert(camera, new_status, message)`
- [ ] Creates `CameraHealthEvent` record in DB
- [ ] Stores timestamp in `triggered_at`
- [ ] On ONLINE → `resolved_at` set to now

### last_seen_at Updates (Connectivity)
- [ ] Worker updates `snapshots.received_at` when FTP file detected
- [ ] API watcher sets `camera.last_seen_at = now` on new snapshot
- [ ] Verification: `docker exec campark-db psql -U campark -d campark -c "SELECT camera_id, last_seen_at FROM cameras;"`

### Health Endpoint
- [ ] `/admin/health` GET endpoint created
- [ ] Returns list of cameras with: `camera_id`, `status`, `last_seen_at`, `age_seconds`
- [ ] Refreshes on each call (no caching)

---

## Phase 3: Telegram Alerts (Day 2, 1.5 hours)

### Telegram Setup
- [ ] Telegram bot token obtained from @BotFather
- [ ] Token stored in env var: `TELEGRAM_BOT_TOKEN`
- [ ] Personal chat ID obtained from `/getUpdates`
- [ ] Chat ID stored in env var: `TELEGRAM_CHAT_ID`

### Alert Function
- [ ] `trigger_alert(camera, status, message)` implemented
- [ ] Sends POST to Telegram API endpoint
- [ ] Message format: "🚨 Camera {camera_id} {status}: {message}"
- [ ] Handles failures gracefully (logs errors, doesn't crash)

### Integration
- [ ] Called from `monitor_camera_health()` on status change
- [ ] Test: Stop camera → wait 150s → receive Telegram alert
- [ ] Verify: Alert says "STALE" and includes timestamp

### Logging
- [ ] Events logged to `camera_health_events` table
- [ ] Includes: camera_id, health_status, message, triggered_at, resolved_at

---

## Phase 3: Admin UI - Camera List (Day 2, 1.5 hours)

### HTML Template
- [ ] `services/api/templates/admin_cameras.html` created
- [ ] Page title: "CamPark Admin - Cameras"
- [ ] Table with columns: ID, Name, Status, Last Seen, Actions

### Flask Routes
- [ ] `GET /admin/cameras` → JSON list of cameras
- [ ] Response format: `[{id, camera_id, name, status, last_seen_at}]`
- [ ] `POST /admin/cameras` → Create new camera
  - [ ] Body: `{site_id, camera_id, name, ftp_username}`
  - [ ] Auto-generates random FTP password
  - [ ] Auto-creates FTP system user: `sudo useradd -m -s /bin/false {username}`
  - [ ] Returns camera ID and FTP credentials

### JavaScript/Canvas
- [ ] Fetch cameras on page load
- [ ] Populate table rows dynamically
- [ ] Color-code status: ONLINE=green, STALE=yellow, OFFLINE=red
- [ ] Add Camera button triggers form dialog

### Proof
- [ ] Open browser: `http://localhost:8000/admin/cameras`
- [ ] See existing camera (CAM001)
- [ ] Click "+ Add Camera"
- [ ] Fill: name="Test Camera 2", ftp_username="cam002"
- [ ] Click Save
- [ ] New camera appears in table
- [ ] Check `/data/ftp/cam002/` directory created

---

## Phase 3: Admin UI - Zone Editor (Day 2, 2–3 hours)

### HTML Template
- [ ] `services/api/templates/zone_editor.html` created
- [ ] Page displays live snapshot as background image
- [ ] Canvas overlay for drawing
- [ ] Controls: "Draw Zone", "Save Zone", "Clear"

### Canvas Library (Fabric.js)
- [ ] Include Fabric.js CDN
- [ ] Create fabric.Canvas on `<canvas id="canvas">`
- [ ] Handle mouse events for point click
- [ ] Draw red dots at click points
- [ ] Draw blue lines between consecutive points

### Zone Data Structure
- [ ] Points stored as normalized coordinates: `[[x%, y%], ...]`
- [ ] Min 3 points required (triangle) for valid polygon
- [ ] Close polygon by clicking first point again (or add "Finalize" button)

### Flask Endpoints
- [ ] `GET /admin/zones/<camera_id>/editor` → HTML template
- [ ] `GET /api/v1/cameras/<camera_id>/snapshot-latest` → JPEG bytes (for background)
- [ ] `POST /admin/zones` → Save zone
  - [ ] Body: `{camera_id, zone_id, name, polygon_json, capacity_units}`
  - [ ] Create/update row in `zones` table
  - [ ] Return HTTP 201 (created)

### Verification
- [ ] Open browser: `http://localhost:8000/admin/zones/1/editor`
- [ ] See latest snapshot
- [ ] Draw polygon (click 4 points to make rectangle)
- [ ] Click "Save Zone"
- [ ] Check DB: `SELECT * FROM zones WHERE camera_id = 1;`
- [ ] Polygon coordinates saved

---

## Phase 3: External API Key & Auth (Day 2, 1.5 hours)

### API Key Generation
- [ ] `POST /admin/api-keys/generate` endpoint created
- [ ] Input: `{name: "Dashboard", site_ids: [1, 2]}`
- [ ] Generates 32-byte random key (base64 or URL-safe)
- [ ] Hashes key with SHA256
- [ ] Stores hash in DB table: `api_clients`
- [ ] Returns raw key (once, not retrievable later)
- [ ] Returns warning: "Save this key safely"

### Database Table (api_clients)
- [ ] Columns: id, name, api_key_hash, site_ids (JSON), scope, rate_limit_per_minute, created_at
- [ ] Scope always "read:status,read:events" (read-only)
- [ ] No write permissions

### Auth Middleware
- [ ] Decorator: `@require_api_key`
- [ ] Checks header: `X-API-Key: <key>`
- [ ] Hashes key and looks up in DB
- [ ] If not found: return 401 Unauthorized
- [ ] If found: attach `g.api_client` to request object

### Read-Only Enforcement
- [ ] `@require_api_key` enforces `request.method == 'GET'`
- [ ] POST/PUT/DELETE requests return 403 Forbidden
- [ ] Test: `curl -X POST -H "X-API-Key: ..." http://localhost:8000/...` → 403

### Protected Endpoints
- [ ] `GET /api/v1/sites/<site_id>/status` → protected with `@require_api_key`
- [ ] `GET /api/v1/cameras/<camera_id>/health` → protected
- [ ] `GET /api/v1/sites/<site_id>/events` → protected

### Testing
- [ ] Generate key: `curl -X POST http://localhost:8000/admin/api-keys/generate ...`
- [ ] Copy returned key
- [ ] Use key: `curl -H "X-API-Key: <key>" http://localhost:8000/api/v1/sites/1/status`
- [ ] Verify valid JSON response
- [ ] Try write: `curl -X POST -H "X-API-Key: <key>" ...` → 403 Forbidden

---

## Phase 3: Integration Test (Day 2, 1 hour)

### Camera Health Monitoring
- [ ] Stop camera (turn off power or unplug)
- [ ] Wait 150 seconds
- [ ] Receive Telegram alert: "Camera CAM001 STALE"
- [ ] Check DB: `SELECT * FROM camera_health_events ORDER BY triggered_at DESC LIMIT 1;`
- [ ] Wait 150 more seconds (total 300s)
- [ ] Receive Telegram alert: "Camera CAM001 OFFLINE"
- [ ] Restart camera (power on)
- [ ] Wait < 150s for new heartbeat snapshot
- [ ] Receive Telegram alert: "Camera CAM001 ONLINE"
- [ ] Check `/admin/health` page → status changed to ONLINE

### Admin UI Workflows
- [ ] Open `/admin/cameras` → see camera list with status
- [ ] Open `/admin/zones/1/editor` → draw zone successfully
- [ ] Open `/admin/health` → see camera status updates in real-time

### External API
- [ ] Generate API key → receive key string
- [ ] Fetch `/api/v1/sites/1/status` with key → valid JSON
- [ ] Try POST with key → 403 Forbidden (enforcing read-only)
- [ ] Extract `zones[0].occupied_units` from response

---

## End-of-Day Tests

### Day 1 Success
- [ ] `/api/v1/sites/1/status` returns JSON with zones
- [ ] Zone `occupied_units` > 0 when vehicle detected
- [ ] YOLO processing logs visible: `docker logs campark-worker | grep detection`
- [ ] Database has ≥ 10 snapshot and detection records
- [ ] All containers healthy: `docker ps | grep Up`

### Day 2 Success
- [ ] Admin cameras page shows camera list (0 hardcoding)
- [ ] Zone editor allows drawing polygon (saves to DB)
- [ ] Health page shows camera status updates
- [ ] Telegram alerts sent on offline/online
- [ ] API key generated and works (read-only enforced)
- [ ] External client can fetch JSON with API key

---

## Proof Points for Boss

### Day 0
```
Screenshot of: ls -la /data/ftp/cam001/incoming/ | tail -5
Shows: Multiple JPEG files, each > 10KB, timestamps 120 seconds apart
Talk: "Camera uploads snapshots every 2 minutes autonomously"
```

### Day 1
```
Terminal: curl http://localhost:8000/api/v1/sites/1/status | jq
Shows: {"zones": [{"zone_id": "A01", "occupied_units": 1, ...}]}
Talk: "YOLO detects vehicles, zone occupancy updates in real-time"
```

### Day 2
```
Browser: http://localhost:8000/admin/cameras
Shows: Cameras listed with ONLINE/STALE/OFFLINE status (click to add new)

Browser: http://localhost:8000/admin/zones/1/editor
Shows: Draw zone on live snapshot (click/drag polygon)

Phone: Telegram alerts received (e.g., "Camera CAM001 OFFLINE")
Talk: "System detects offline camera in 2.5 minutes, sends alert"

Terminal: curl -H "X-API-Key: ..." http://localhost:8000/api/v1/sites/1/status
Shows: External dashboard can fetch JSON with secure read-only key
```

---

## Quick Reference Commands

```bash
# Start / stop services
docker-compose up -d
docker-compose down

# View logs
docker logs -f campark-api
docker logs -f campark-worker
docker logs -f campark-db

# Database access
docker exec -it campark-db psql -U campark -d campark

# Useful queries
SELECT * FROM cameras;
SELECT * FROM detections ORDER BY created_at DESC LIMIT 10;
SELECT * FROM zone_events ORDER BY triggered_at DESC LIMIT 10;
SELECT * FROM camera_health_events ORDER BY triggered_at DESC LIMIT 10;

# FTP test
bash tests/ftp_test.sh

# API test
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/sites/1/status | jq

# Check containers
docker ps
docker ps -a (show stopped)
```

---

## Troubleshooting Checklist

| Issue | Check | Fix |
|-------|-------|-----|
| Camera FTP upload fails | `systemctl status vsftpd` | Restart: `systemctl restart vsftpd` |
| No YOLO detections | `docker logs campark-worker` | Check image quality, confidence threshold |
| API crashes | `docker logs campark-api` | Check DB connection, syntax errors |
| DB not ready | `docker logs campark-db` | Wait 30s, check `docker ps postgres` |
| Zone editor not loading | Browser console errors | Check `/api/v1/cameras/1/snapshot-latest` |
| Telegram alert not sent | Check token + chat_id in env | Test: `curl -X POST https://api.telegram.org/bot.../sendMessage` |
| Offline alert doesn't trigger | Check `last_seen_at` updates | Verify snapshot enqueue + DB writes |

---

**Status:** Ready for execution  
**Gate:** FTP upload (Phase 0) must pass before proceeding  
**Timeline:** Days 0–2, achievable in parallel with team