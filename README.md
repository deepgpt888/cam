# CamPark — Snapshot-Only Parking Occupancy Platform

**Goal:** Detect vehicle parking occupancy using CCTV snapshots + YOLO, with real-time alerts and operator-friendly admin UI.

**Status:** Phase 3 complete (admin UI + alerts + API keys). Phase 4 hardening pending.

---

## ⚡ Quick Links (Start Here)

| Document | Purpose | Read If... |
|----------|---------|-----------|
| [QUICK_START.md](QUICK_START.md) | 10-min overview for developers | You're new to the project |
| [TESTING_PLAN.md](TESTING_PLAN.md) | Full test phases + gate check | You need to validate camera FTP upload |
| [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md) | Camera setup guide (DH-IPC-HFW7442H-Z4FR) | You're configuring the Dahua camera |
| [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md) | Build roadmap + code snippets | You're executing the 2-day POC |
| [REQUIREMENTS.md](REQUIREMENTS.md) | All dependencies + pre-flight checklist | You need to verify your environment |

---

## 🎯 What This System Does

```
Dahua CCTV Camera (FTP)
  ├─ Uploads snapshots every 120s (heartbeat)
  └─ Uploads on motion/vehicle trigger
           ↓
    CamPark Server
  ├─ pure-ftpd (FTP ingest, Docker)
  ├─ YOLO worker (vehicle detection)
  ├─ PostgreSQL (state + events)
  ├─ Flask API (JSON + admin UI)
  └─ Telegram alerts (offline notifications)
           ↓
External Dashboard
  └─ Reads zone occupancy via HTTPS JSON
```

---

## 🔑 Key Features (POC)

✅ **Event-Based + Heartbeat Snapshots**
- Camera uploads on motion trigger (primary)
- Camera uploads every 2 minutes (heartbeat, secondary)
- Prevents battery drain (no 30-second interval loops)

✅ **Real-Time Vehicle Detection**
- YOLO CPU inference (no GPU needed)
- Detects: car, truck, motorcycle, bicycle
- Confidence threshold: 0.80 (tunable)

✅ **ROI + Zone Management**
- Define parking zone polygon via web UI (click/drag)
- Only count vehicles inside zone (ignore street traffic)
- Multi-zone per camera supported

✅ **Offline Detection (Immediate)**
- STALE alert: no snapshot for 150 seconds
- OFFLINE escalation: no snapshot for 300 seconds
- Auto-resolve when camera resumes

✅ **Admin-Friendly Operations**
- Add camera without code changes (UI button)
- Draw zones on live snapshot (web canvas)
- Real-time health page (ONLINE/STALE/OFFLINE)
- Telegram alerts for critical events

✅ **External Dashboard Integration**
- Read-only HTTPS JSON API
- API key auth (no shared passwords)
- Rate limiting + usage logging
- Immutable audit trail

✅ **Single-Server Deployment**
- Docker Compose (all services in one file)
- PostgreSQL + Redis volumes
- < 5 hours downtime for safe upgrades
- Target 99% uptime

---

## 📋 The Hard Gate (Before You Code)

**Your chosen camera MUST upload JPEG snapshots via FTP.** If it can't, the system cannot ingest images—there's no workaround.

### Gate Test (30 min)
```bash
cd /workspaces/CamPark
docker-compose up -d ftp
bash tests/ftp_test.sh
```

This validates:
- FTP server running locally (Docker)
- Camera can authenticate
- Files arrive in `./data/ftp/cam001/incoming/`
- Files are valid JPEGs (> 10KB)

**If gate test passes:** You're cleared to build POC  
**If gate test fails:** Fix camera config first (see [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md))

---

## 🚀 Roadmap (4 Phases)

### Phase 1: Gate (FTP Upload)
1. Start FTP server (Docker `campark-ftp`)
2. Configure camera to upload via FTP
3. Verify snapshots arrive in `./data/ftp/cam001/incoming/`

### Phase 2: Core Pipeline (FTP → YOLO → API)
1. Bring up PostgreSQL
2. Run API + worker services
3. Validate: snapshot → detection → zone update → JSON API

### Phase 3: Admin + Alerts (Complete)
1. Camera health monitoring (ONLINE/STALE/OFFLINE)
2. Telegram alerts
3. Admin UI (camera list, zone editor, health page)
4. External API key + read-only enforcement

### Phase 4: Deployment Hardening (Next)
1. VPS firewall + passive FTP ports
2. TLS + reverse proxy
3. Backups + retention
4. Logging + monitoring

---

## 📁 Repository Structure

```
CamPark/
├── README.md                    ← You are here
├── QUICK_START.md               ← Start here if new
├── TESTING_PLAN.md              ← Full test phases
├── CAMERA_CONFIG_DAHUA.md       ← Camera setup
├── DAY_BY_DAY_PLAN.md           ← Build roadmap
├── REQUIREMENTS.md              ← Dependencies
│
├── docker-compose.yml           ← All services (postgres, api, worker)
│
├── services/
│   ├── api/                     ← Flask server (admin UI + JSON API)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── app/
│   │       └── db.py            ← SQLAlchemy models
│   │
│   ├── worker/                  ← YOLO inference worker
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── yolo_processor.py    ← Vehicle detection logic
│   │
│   └── config/
│       └── init.sql             ← Database schema (auto-loaded)
│
├── data/                        ← Volumes
│   ├── ftp/                     ← Camera uploads here
│   ├── images/                  ← Processed snapshots + evidence
│   ├── db/                      ← PostgreSQL data
│   └── backups/                 ← Nightly snapshots
│
├── models/                      ← YOLO weights (auto-download)
└── tests/
    └── ftp_test.sh              ← Gate check script
```

---

## 🛠️ System Requirements

### Hardware
- Linux VM or dev container (Ubuntu 20.04+)
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space
- Network access to camera (POE LAN)

### Software
```bash
# Install once
sudo apt update
sudo apt install -y python3 docker.io docker-compose ftp

# Verify
docker --version      # 20.10+
docker-compose --version  # 1.29+
```

### Network
- Camera reachable from your machine (ping test)
- FTP ports 21 + 30000–30100 available
- Telegram bot token (from @BotFather on Telegram)

---

## 📚 Documentation Map

| Document | Covers |
|----------|--------|
| [QUICK_START.md](QUICK_START.md) | Tech stack, code tips, common issues |
| [TESTING_PLAN.md](TESTING_PLAN.md) | Gate check + phases 1–4 + success criteria |
| [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md) | Step-by-step camera FTP/motion setup |
| [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md) | Detailed tasks + code snippets + proofs for boss |
| [REQUIREMENTS.md](REQUIREMENTS.md) | All dependencies + checklist + architecture |

---

## 🎬 Getting Started Now

### 1. Verify Prerequisites (5 min)
```bash
which docker docker-compose python3 ftp
# All should print paths, not "not found"
```

### 2. Prepare FTP Folders + Start FTP (5 min)
```bash
mkdir -p data/ftp/cam001/incoming
docker-compose up -d ftp
```

### 3. Configure .env (2 min)
```bash
cp .env.example .env
# Edit .env for Telegram alerts or API key enforcement if needed
```

### 4. Run Gate Test (30 min, includes waiting)
```bash
cd /workspaces/CamPark
bash tests/ftp_test.sh
```

**If this passes**, you're ready for the 2-day build. See [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md).

**If this fails**, follow [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md) to fix camera FTP settings.

---

## 🚢 Infrastructure (Docker Compose)

All services run in Docker for easy deploy + upgrade:

```bash
# Start everything
docker-compose up -d

# Monitor logs
docker logs -f campark-api
docker logs -f campark-worker
docker logs -f campark-db

# Stop everything
docker-compose down
```

Services:
- **campark-ftp** — pure-ftpd FTP ingest (port 21 + passive ports)
- **postgres:15** — Database (zone state + events + configs)
- **campark-api** — Flask server (admin UI + JSON API)
- **campark-worker** — YOLO inference (background task)
- **redis:7** — Optional queue backend (falls back to DB)

---

## 📊 Data Model (Minimal)

```
Projects
  └─ Sites
      └─ Cameras (with FTP credentials)
          ├─ Zones (ROI polygons, capacity)
          │   └─ ZoneState (current occupancy)
          │       └─ ZoneEvents (state changes with evidence)
          │
          └─ Snapshots (files from FTP)
              ├─ Detections (YOLO results: class, conf, bbox)
              └─ CameraHealthEvents (ONLINE/STALE/OFFLINE)
```

Full schema in [services/config/init.sql](services/config/init.sql).

---

## 🔒 Security (POC Defaults)

⚠️ **These are POC defaults. Change before pilot:**

| Secret | POC Value | Before Pilot |
|--------|-----------|-------------|
| DB password | `changeme_poc` | 32-char random |
| Admin password | `changeme_poc` | 32-char random |
| FTP password | `password123` | 32-char random per camera |
| API key | Generated on Day 2 | SHA256 hashed |
| TLS certificate | Self-signed | Proper CA cert |

---

## 🎯 Success Criteria (Show Your Boss)

**End of Day 0:**
```
✅ Files in ./data/ftp/cam001/incoming/
✅ Files are valid JPEGs (> 10KB)
✅ Files arrive every 120 seconds
```

**End of Day 1:**
```
✅ API returns zone occupancy JSON
✅ Zone updates on YOLO detections
✅ All services healthy in docker-compose
```

**End of Day 2:**
```
✅ Admin can add camera (no code)
✅ Admin can draw zones (click/drag)
✅ Telegram alerts on offline
✅ External dashboard consumes JSON API
✅ System enforces read-only access
```

---

## 📞 Support

### Before You Start
- **Camera won't upload FTP?** → [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md)
- **Don't know the tech stack?** → [QUICK_START.md](QUICK_START.md#-tech-stack)
- **Need dependencies checklist?** → [REQUIREMENTS.md](REQUIREMENTS.md)

### During Development
- **Stuck on Day 1?** → [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md#day-1-ftp--yolo--zone-state-6--8-hours)
- **Docker issues?** → Check `docker logs <service>`
- **Database errors?** → `docker exec campark-db psql -U campark -d campark`

### Common Issues
| Problem | Fix |
|---------|-----|
| FTP test fails | `docker ps | grep campark-ftp` + read [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md) |
| YOLO too slow | Use 640x480 images, reduce confidence threshold |
| API won't start | Check DB healthy: `docker logs campark-db` |
| Offline alert late | Verify `last_seen_at` updates on every snapshot |

---

## 🎓 Next Steps (After POC)

Once POC succeeds, you'll have:
- ✅ Proven camera FTP integration
- ✅ Working YOLO inference pipeline
- ✅ Basic admin UI
- ✅ Offline alerting framework
- ✅ External API pattern

**Pilot enhancements** (not in POC):
- [ ] Multi-camera multi-site support (POC was single)
- [ ] TLS + nginx reverse proxy
- [ ] Prometheus + Grafana monitoring
- [ ] Nightly backups + recovery test
- [ ] Rate limiting + API quotas
- [ ] Production secrets management (vault/K8s)

---

## 📈 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Dahua CCTV Camera                        │
│  (FTP upload: 120s heartbeat + motion trigger)              │
└──────────────────────┬────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   CamPark Server (Single VM)                │
├─────────────────────────────────────────────────────────────┤
│ pure-ftpd                                                    │
│  ├─ FTP user: cam001                                       │
│  └─ Incoming: /data/ftp/cam001/incoming/                   │
├─────────────────────────────────────────────────────────────┤
│ Worker (YOLO Inference)                                     │
│  ├─ Monitor /data/ftp/cam001/incoming/                    │
│  ├─ Run YOLO (vehicle detection)                           │
│  ├─ Update zone_state (overlap + debounce)                │
│  └─ Save detections to PostgreSQL                          │
├─────────────────────────────────────────────────────────────┤
│ API Service (Flask)                                         │
│  ├─ /admin/* (UI pages: cameras, zones, health)           │
│  ├─ /api/v1/* (JSON: status, events, evidence)            │
│  └─ Background: camera health monitoring + alerts         │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL Database                                         │
│  └─ tables: projects, sites, cameras, zones, snapshots,    │
│             detections, zone_events, api_clients           │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├─────────────────┬──────────────────┐
               ▼                 ▼                  ▼
        External Dashboard   Telegram Bot    Operator Phone
        (read-only JSON)     (offline alert)  (alert notifications)
```

---

## 📄 License & Attribution

- YOLO detection model: Ultralytics YOLOv8 (Apache 2.0)
- pure-ftpd: FTP server (BSD-style)
- Flask: Web framework (BSD 3-Clause)
- PostgreSQL: Database (PostgreSQL License)

---

## 🙏 Credits

**System design validated in Malaysia for:**
- Event-based snapshots (motion/vehicle triggers)
- 2-minute heartbeat (battery safe)
- Immediate offline alerting (within 150 seconds)
- Single-server deployment (99% uptime target)
- Admin-friendly operations (no code changes to add camera)

**POC achievable in 2 days.** Hard gate: camera must upload via FTP.

---

**Ready to start?** → Read [QUICK_START.md](QUICK_START.md) or jump to [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md)