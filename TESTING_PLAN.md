# CamPark POC Testing Plan & Gate Check

**Goal:** Prove camera FTP upload works locally, then execute 2-day POC  
**Owner:** You  
**Timeline:** Phase 1 (gate), Phase 2 (core), Phase 3 (admin), Phase 4 (hardening)

---

## ⛔ GATE CHECK: Camera FTP Upload (DO THIS FIRST)

### Why This Matters
Your FTP-first standard means: **if the camera cannot upload SNAPSHOTs via FTP, CamPark cannot ingest images.** This is non-negotiable.

### Target Camera
- **Model:** Dahua DH-IPC-HFW7442H-Z4FR
- **Connection:** POE LAN with router
- **Required capability:** Upload JPEG snapshots to FTP server

---

## Phase 1: Local FTP Server Setup (30 min)

### Objective
Set up a minimal FTP server on your local machine to test camera upload.

### Requirements
- Linux VM / dev container with Docker
- IP address reachable from camera network
- Writable FTP directory `./data/ftp/`

### Setup Steps

#### 1. Start FTP Server (Docker)
```bash
mkdir -p data/ftp/cam001/incoming
cp .env.example .env
# For VPS: set FTP_PUBLICHOST in .env to your public IP/hostname
docker-compose up -d ftp
```

#### 2. Test FTP Locally (from your machine)
```bash
# Test upload
ftp -n << EOF
open localhost
user cam001 password123
cd incoming
put test.jpg
quit
EOF

# Verify file arrived
ls -la data/ftp/cam001/incoming/
```

**Success Criteria:** `test.jpg` appears in `./data/ftp/cam001/incoming/`

---

## Phase 1b: Camera FTP Configuration (30 min – 1 hour)

### Objective
Configure Dahua DH-IPC-HFW7442H-Z4FR to upload snapshots to your FTP server.

### Access Camera Admin Panel
1. **IP discovery:** Ping camera IP on LAN (default usually Dahua broadcast), or check router DHCP
   ```bash
   nmap -sn 192.168.1.0/24 | grep -i dahua
   # or check your router's connected devices
   ```

2. **Login:** `http://<camera-ip>` → default user `admin` / `admin`  
   ⚠️ **Change password immediately after testing.**

### Configure Event-Based Upload (Motion/Vehicle)
**Path in admin UI:**  
`Settings` → `Network` → `Advanced` → `FTP`

- **FTP Server Address:** Your local machine IP (e.g., `192.168.1.100`)
- **Port:** `21`
- **Username:** `cam001`
- **Password:** `password123`
- **Remote directory:** `incoming` (or `/incoming/`)
- **Test connection:** ✅ Should pass

### Configure Event Triggers (Motion Detection)
**Path in admin UI:**  
`Settings` → `Event` → `Motion Detection` → `Enable`

- Enable motion-triggered snapshot upload
- Set to upload 1 snapshot per motion event

### Configure Heartbeat Interval (Optional but Recommended)
**Path in admin UI:**  
`Settings` → `Network` → `Advanced` → `FTP` → `Scheduled Upload` or `Heartbeat`

- Enable interval-based snapshot every 120 seconds
- Alternative: if not available in Dahua UI, CamPark's server-side rules will handle offline detection

### Verify Upload
Once enabled, wait 2–3 minutes for heartbeat or trigger motion:
```bash
watch -n 1 "ls -la data/ftp/cam001/incoming/ | tail -5"
```

**Success Criteria:**
- ✅ At least 1 file in `./data/ftp/cam001/incoming/` within 3 minutes
- ✅ File size > 10KB (real JPEG, not placeholder)
- ✅ Filename pattern matches Dahua (usually `YYYY-MM-DD_HH-MM-SS.jpg` or similar)

---

## Phase 1c: File Integrity Check (10 min)

Once files arrive, verify they are valid JPEGs:
```bash
file data/ftp/cam001/incoming/*.jpg

# Check all files are readable
for f in data/ftp/cam001/incoming/*.jpg; do
  identify "$f" 2>/dev/null && echo "✅ $f" || echo "❌ $f CORRUPT"
done
```

**If files are corrupt:** Camera FTP config is incomplete or broken. **DO NOT PROCEED** (this is your hard gate).

---

## ✅ Gate Validation Checklist

Confirm all before moving to POC:

- [ ] FTP server running locally (`docker ps | grep campark-ftp`)
- [ ] FTP user `cam001` can authenticate
- [ ] Test file uploaded successfully
- [ ] Camera IP reachable from local machine
- [ ] Camera admin panel accessible
- [ ] FTP settings saved in camera
- [ ] At least 1 valid JPEG snapshot in `./data/ftp/cam001/incoming/` from camera
- [ ] File size > 10KB (real image, not stub)
- [ ] Consecutive files arriving every ~120s (if heartbeat enabled)

**If ANY fail:** ❌ STOP. Fix camera FTP config. Do not proceed to POC.

---

## Phase 2: Local POC Setup (1–2 hours for full setup)

### Objective
Bring up minimal CamPark services locally to test full pipeline: FTP ingest → YOLO → zone state → JSON API.

### What You Need Locally
```
/workspaces/CamPark/
├── docker-compose.yml           # POC services definition
├── services/
│   ├── api/                     # Flask/FastAPI server
│   ├── worker/                  # YOLO inference worker
│   └── config/
│       ├── init.sql             # DB schema
│       └── init.sql             # DB schema
├── data/
│   ├── ftp/                     # Incoming uploads
│   ├── images/                  # Processed snapshots
│   ├── db/                      # Postgres volume
│   └── backups/                 # Daily snapshots
└── tests/
    └── ftp_test.sh              # Gate test script
```

### Services to Deploy (Day 1 POC Scope)

| Service | Purpose | POC Required? | Status |
|---------|---------|---------------|--------|
| `pure-ftpd` | FTP ingest | YES | Docker container |
| `postgres` | Zone state + events | YES | Docker container |
| `redis` | Queue (optional v1) | NO | Use list in DB |
| `api` | Admin + JSON + health | YES | Flask + gunicorn |
| `worker` | YOLO inference | YES | Python + torch |
| `nginx` | TLS termination | NO (POC) | Skip, use Flask directly |
| `prometheus + grafana` | Monitoring | NO | Skip for POC |

---

## Phase 3: Day 1 POC Execution (End-of-Day Targets)

### Target Outcomes (End of Day 1)
1. ✅ Camera snapshots arrive in `./data/ftp/cam001/incoming/`
2. ✅ API watcher detects new files
3. ✅ YOLO processes snapshots (CPU-only)
4. ✅ Zone state updates (hardcoded 1 zone for now)
5. ✅ `GET /api/v1/sites/SITE01/status` returns valid JSON with zone occupancy

### Implementation Checklist

- [ ] DB schema created (projects, cameras, zones, snapshots, zone_state)
- [ ] FTP watcher running (detects new files, hashes, enqueues)
- [ ] YOLO worker running (processes queue, stores detections)
- [ ] Zone engine applies ROI + debounce (2-frame rule)
- [ ] API `/status` endpoint returns JSON
- [ ] Manual test: upload snapshot, verify zone state in API response

---

## Phase 4: Day 2 POC Execution (End-of-Day Targets)

### Target Outcomes (End of Day 2)
1. ✅ Admin UI: create camera (auto-gen FTP user)
2. ✅ Zone editor: draw ROI + zones, save to DB
3. ✅ Health page: show ONLINE/STALE/OFFLINE per camera
4. ✅ Offline alerts: trigger at 150s (STALE), 300s (OFFLINE)
5. ✅ External API key: issue key, enforce read-only scope
6. ✅ Telegram alerts: send to your phone when offline

### Implementation Checklist

- [ ] Admin zone editor UI (canvas + polygon draw)
- [ ] Camera health page (list cameras + last_seen_at + status)
- [ ] Server-side offline rules (heartbeat 120s, stale 150s, offline 300s)
- [ ] Telegram bot integration (send alerts)
- [ ] API key generation + scope enforcement
- [ ] External dashboard APIs: /status, /cameras/{id}/health, /events
- [ ] Manual test: sign up for API key, pull events as external client

---

## Testing & Validation Checklists

### Unit Tests (Minimum for POC)

- [ ] FTP file detection (new files appear in queue)
- [ ] YOLO inference (vehicle detection scores > 0.80)
- [ ] ROI crop (detection inside polygon counted, outside ignored)
- [ ] Zone overlap (30% overlap gating works)
- [ ] Debounce (zone state stable after 2 frames)
- [ ] Offline rules (timer resets on snapshot)

### Integration Tests (Minimum for POC)

- [ ] End-to-end: upload snapshot → FTP → watcher → YOLO → zone → API response
- [ ] Health check: offline alert triggers reliably
- [ ] API: external key cannot modify data (read-only enforced)

### Manual Testing (Required Before Pilot)

- [ ] Insert motion in front of camera → snapshot uploads → zone updates in <10s
- [ ] Stop camera (unplug or power off) → STALE alert at ~150s, OFFLINE at ~300s
- [ ] Restart camera (power on) → alert resolves, zone state resumes

---

## What You'll Have at End of Day 2

**Proof Points for Boss:**
```
✅ Camera uploads JPEG snapshots via FTP (hardware works)
✅ Server ingests, processes, and detects vehicles (YOLO works)
✅ Admin can add camera without code changes (UI works)
✅ Zone occupancy updates in real time (core logic works)
✅ External dashboard gets read-only JSON API (integration ready)
✅ Offline alerts trigger reliably (safety mechanism works)
✅ Single-server deployment with docker-compose (ops ready)
```

**Production Checklist for Pilot (add after POC):**
- Monitoring + alerting (Prometheus + Telegram escalation)
- Upgrade protocol + version pinning
- Nightly backups + recovery test
- TLS certificates + nginx
- Rate limiting + API quotas
- Structured logging to disk

---

## Testing File (Run Before Each Build)

See `tests/ftp_test.sh` (auto-generated - verifies FTP connectivity)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Camera FTP upload fails | **GATE TEST** catches this immediately (Phase 0) |
| YOLO CPU too slow | Start with 640x480 snapshots; optimize later |
| DB migrations complex | Keep POC schema simple, no production data migration patterns needed |
| Zone editor UI too complex | Day 2 use canvas library (Fabric.js / Konva.js) with simple polygon save |
| Offline alerts flaky | Use server-side clock (not camera clock). Heartbeat at 120s, alert at 150s, escalate at 300s |

---

## Success = You Prove This to Your Boss

```
Camera: "Our Dahua uploads snapshots to FTP ✅"
Server: "CamPark processes them, detects vehicles ✅"
Admin: "I can add zones without writing code ✅"
API: "Dashboard consumes JSON, gets vehicle counts ✅"
Alerts: "System tells us when camera goes offline ✅"
Ops: "All services in docker-compose, < 5 min deploy ✅"
```

**Estimated timeline:** 2 days  
**Hard gate:** FTP upload works (Phase 0 validates)  
**Risk:** If camera can't upload via FTP, system cannot ingest images. **This is blocking.**
