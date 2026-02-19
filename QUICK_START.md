# CamPark POC: Quick Start Guide for Developers

**Objective:** Get up to speed in 10 minutes. Know what to build and in what order.

**Audience:** You (the developer) + anyone joining the team

---

## 📋 What You're Building

A **parking occupancy system** that:
1. Receives JPEG snapshots from CCTV camera via FTP (every 2 min + on motion)
2. Runs YOLO object detection (vehicle counting)
3. Updates zone occupancy in real-time
4. Sends alerts when camera goes offline
5. Exposes JSON API for external dashboard

**Success = POC in 4 phases** (Gate → Core → Admin → Hardening)

---

## 🎯 The Hard Gate (Phase 1)

You have a **Dahua DH-IPC-HFW7442H-Z4FR** camera that **must** upload snapshots via FTP.

**If this fails, the entire system cannot ingest images.** No workaround.

### Gate Test (3–4 hours)

1. Setup local FTP server
2. Configure camera to upload via FTP
3. Verify files arrive in `./data/ftp/cam001/incoming/`

**If it works:** You're cleared for POC  
**If it fails:** Fix camera first (don't proceed)

See: [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md) + [TESTING_PLAN.md](TESTING_PLAN.md)

---

## 📁 Project Structure

```
/workspaces/CamPark/
├── docker-compose.yml              # All services defined here
├── services/
│   ├── api/                        # Flask API server
│   │   ├── main.py                 # Entry point
│   │   ├── requirements.txt        # Dependencies
│   │   ├── Dockerfile
│   │   └── app/
│   │       └── db.py               # SQLAlchemy models
│   ├── worker/                     # YOLO inference worker
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── yolo_processor.py       # Detection logic
│   └── config/
│       ├── init.sql                # DB schema
│       └── init.sql                # DB schema
├── data/
│   ├── ftp/                        # Camera uploads here
│   ├── images/                     # Processed snapshots
│   ├── db/                         # Postgres volume
│   └── backups/
├── models/                         # YOLO weights
├── tests/
│   └── ftp_test.sh                 # Gate test script
├── docs/
│   ├── TESTING_PLAN.md             # Full testing plan
│   ├── CAMERA_CONFIG_DAHUA.md      # Camera setup
│   ├── REQUIREMENTS.md             # Dependencies
│   ├── DAY_BY_DAY_PLAN.md          # Build roadmap
│   └── API_REFERENCE.md            # (TBD) Endpoint specs
└── README.md
```

---

## 🔧 Tech Stack

**Backend:**
- Python 3.9+
- Flask (web framework)
- PostgreSQL (database)
- SQLAlchemy (ORM)
- Ultralytics YOLO (inference)
- Redis (optional queue)

**Infrastructure:**
- Docker + Docker Compose
- pure-ftpd (FTP server, Docker)
- Telegram (alerts)

**Frontend (POC):**
- Simple HTML + JavaScript
- Fabric.js (canvas drawing for zones)

---

## 🚀 Getting Started

### Prerequisites
```bash
# Install
sudo apt update
sudo apt install -y python3 docker.io docker-compose ftp

# Verify
docker --version
docker-compose --version
python3 --version
```

### FTP Setup (5 min)
```bash
mkdir -p data/ftp/cam001/incoming
docker-compose up -d ftp
```

### Test Gate (30 min)
```bash
cd /workspaces/CamPark
docker-compose up -d ftp
bash tests/ftp_test.sh
```

If this passes: You're cleared for build.

### Run POC (docker-compose)
```bash
# Start all services
docker-compose up -d

# Wait for DB to be healthy
sleep 10

# Check services
docker ps

# View logs
docker logs campark-api
docker logs campark-worker
docker logs campark-db
```

---

## 📅 Build Schedule

### Phase 1: Gate Check (3–4 hours)
- [ ] FTP server running (Docker)
- [ ] Camera uploading snapshots
- [ ] Verify files in `./data/ftp/cam001/incoming/`

**Approval:** Show boss proof of files arriving

---

### Phase 2: Core Inference Pipeline (6–8 hours)

Build the inference loop:

**1. PostgreSQL (30 min)**
```bash
docker-compose up -d postgres
# Tables auto-created from init.sql
```

**2. API Service (2–3 hours)**
- Flask app with SQLAlchemy models
- Routes: `GET /api/v1/sites/1/status` → JSON zone occupancy
- Database: cameras, zones, zone_states, snapshots, detections
- Task: Respond with current zone state

**3. YOLO Worker (2–3 hours)**
- Monitor `/data/ftp/cam001/incoming/` (container path, host is `./data/ftp/...`) for new files
- Run YOLO inference on each snapshot
- Save detections to DB
- Update zone state (debounce on 2 frames)

**4. Integration Test (30 min)**
```bash
# Upload snapshot
cp my_photo.jpg data/ftp/cam001/incoming/test.jpg

# Verify API response
curl http://localhost:8000/api/v1/sites/1/status | jq

# Should show zone with occupancy
```

**Approval:** API returns zone state, YOLO detects vehicles

---

### Phase 3: Admin + Alerts (8–10 hours)

Add operational features:

**1. Camera Health Monitoring (2 hours)**
- Background task checks `camera.last_seen_at`
- STALE: no snapshot for 150s → alert
- OFFLINE: no snapshot for 300s → escalate alert
- ONLINE: back online → resolve alert

**2. Telegram Alerts (1.5 hours)**
- Get Telegram bot token from @BotFather
- Send alert messages on STALE/OFFLINE
- Log events to DB

**3. Admin UI (3–4 hours)**
- Camera list page (with status: ONLINE/STALE/OFFLINE)
- Zone editor (draw polygon on snapshot, save to DB)
- Health page (real-time camera status)
- API key generator (read-only external access)

**4. External API Key Auth (1.5 hours)**
- Generate API keys for external dashboard
- Enforce read-only (GET only)
- Rate limiting (polite quota)

**Integration Test (1 hour)**
- Add camera via UI
- Draw zone via editor
- Stop camera → verify STALE alert at 150s
- Resume camera → verify ONLINE alert
- External dashboard fetches data with API key

**Approval:** Boss can see admin UI, receives alerts, external dashboard connects

---

### Phase 4: Deployment Hardening (Next)
- [ ] Set `PUBLICHOST` to VPS public IP/hostname
- [ ] Open port 21 + passive range on firewall
- [ ] Add TLS + reverse proxy (nginx/caddy)
- [ ] Backups + retention for `data/db` and `data/images`
- [ ] Enable monitoring + log rotation

---

## 📊 APIs to Implement (Priority Order)

### Day 1 (Core)
```
GET /api/v1/sites/{site_id}/status
  → Zone occupancy JSON ({"zones": [{"zone_id": "A01", "occupied": 1}]})

GET /api/v1/cameras/{camera_id}/status
  → Last snapshot + detections
```

### Day 2 (Operational)
```
GET /admin/cameras
  → List cameras with status

POST /admin/cameras
  → Add new camera (auto-gen FTP user)

GET /admin/health
  → System health (cameras ONLINE/STALE/OFFLINE)

POST /admin/api-keys/generate
  → Create read-only external key

GET /api/v1/sites/{site_id}/events?from=&to=
  → Zone change events (with pagination)

GET /api/v1/evidence/{event_id}
  → Snapshot evidence for event (costs API tokens)
```

See: [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md) for full specs

---

## 🧪 Testing Checklist

### Unit Tests (Minimum for POC)
- [ ] YOLO confidence threshold (0.80+)
- [ ] ROI crop (detection inside polygon)
- [ ] Zone overlap (30% threshold)
- [ ] Debounce (2-frame rule)
- [ ] Offline timer (150s stale, 300s offline)

### Integration Tests
- [ ] File upload → YOLO → zone state in API response
- [ ] Offline alert triggers reliably
- [ ] External API key enforces read-only
- [ ] Zone editor saves polygon correctly

### Manual Tests
- [ ] Camera uploads continuously
- [ ] Motion triggers snapshot → zone updates < 10s
- [ ] Stop camera → STALE alert at ~150s
- [ ] Restart camera → alert resolves

---

## 🐳 Docker Commands (Essential)

```bash
# Start all services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker logs campark-api
docker logs campark-worker
docker logs campark-db

# Restart a service
docker-compose restart api

# Remove volumes (database reset)
docker-compose down -v

# Rebuild images
docker-compose build

# SSH into database
docker exec -it campark-db psql -U campark -d campark

# Check service health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## 🚨 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Camera won't upload | FTP not running | `docker ps | grep campark-ftp` |
| No YOLO detections | Model not downloaded | Auto-downloads on first run |
| API timeout | DB not healthy | `docker logs campark-db` |
| Zone state stuck | Debounce waiting | Need 2 consecutive frames |
| Offline alert late | Timer not resetting | Ensure `last_seen_at` updates on every snapshot |

---

## 📝 Key Files to Edit

**You will create/edit these:**

```bash
services/api/main.py                  # Flask app
services/api/app/db.py                # Models + ORM
services/api/app/routes.py            # Endpoints
services/api/app/models.py            # Pydantic schemas

services/worker/main.py               # Worker entry
services/worker/yolo_processor.py     # YOLO logic

services/api/requirements.txt          # Dependencies
services/worker/requirements.txt       # Dependencies

services/api/templates/admin_*.html    # Admin UI
services/api/templates/zone_editor.html # Zone drawing

docker-compose.yml                     # (lightly modify)
```

**You will NOT edit:**
- `services/config/init.sql` (schema auto-created)
- `TESTING_PLAN.md`, `CAMERA_CONFIG_DAHUA.md`, etc. (reference docs)

---

## 💡 Quick Tips

### YOLO
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # Auto-downloads
results = model(image_path, conf=0.80)

for box in results[0].boxes:
    class_id = int(box.cls)
    confidence = float(box.conf)
    x1, y1, x2, y2 = box.xyxy[0]
```

### Database Query
```python
from app.db import Camera, Zone, ZoneState

cameras = Camera.query.all()
camera = Camera.query.get(1)

zone_state = ZoneState.query.filter_by(zone_id=1).first()
zone_state.occupied_units = 5
db.session.commit()
```

### FTP File Monitoring
```python
from pathlib import Path
import time

ftp_path = Path('/data/ftp/cam001/incoming')
processed = set()

while True:
    files = list(ftp_path.glob('*.jpg'))
    new_files = [f for f in files if f.name not in processed]
    
    for file in new_files:
        process_snapshot(file)
        processed.add(file.name)
    
    time.sleep(1)  # Check every second
```

### Telegram Alert
```python
import requests
import os

token = os.environ['TELEGRAM_BOT_TOKEN']
chat_id = os.environ['TELEGRAM_CHAT_ID']

requests.post(
    f'https://api.telegram.org/bot{token}/sendMessage',
    json={'chat_id': chat_id, 'text': '🚨 Camera offline!'}
)
```

---

## 📚 Reference Docs

- [TESTING_PLAN.md](TESTING_PLAN.md) — Full test phases + success criteria
- [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md) — Camera FTP setup guide
- [REQUIREMENTS.md](REQUIREMENTS.md) — All dependencies + checklist
- [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md) — Detailed build roadmap + code snippets
- [System Architecture](#) — Helicopter view of how pieces fit

---

## 🎯 Success Criteria (Show Your Boss)

**End of Day 0 (Gate):**
```
✅ Files in ./data/ftp/cam001/incoming/
✅ File size > 10KB (real images)
✅ Files arrive every ~120 seconds
```

**End of Day 1 (Inference):**
```
✅ API returns JSON: {"zones": [...]}
✅ Zone state updates on YOLO detections
✅ All services running in Docker
```

**End of Day 2 (Operations):**
```
✅ Admin can add camera (no code change)
✅ Admin can draw zones (click/drag on UI)
✅ Telegram alerts on offline camera
✅ External dashboard fetches JSON with API key
✅ System enforces read-only access
```

---

## 🔐 Environment Variables

Create `.env` in project root before `docker-compose up`:

```bash
# Database
DATABASE_URL=postgresql://campark:changeme_poc@postgres:5432/campark

# FTP
FTP_INGEST_PATH=/data/ftp
FTP_WATCH_USER=cam001

# YOLO
YOLO_CONFIDENCE=0.80
YOLO_MODEL=yolov8n.pt

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme_poc

# Telegram
TELEGRAM_BOT_TOKEN=<get from @BotFather>
TELEGRAM_CHAT_ID=<get from /getUpdates>

# Logging
LOG_LEVEL=INFO
```

---

## ⏰ Time Estimates

| Task | Estimate | Difficulty |
|------|----------|------------|
| Gate (FTP setup) | 3–4 hours | 🟢 Easy |
| API + DB | 2–3 hours | 🟡 Medium |
| YOLO worker | 2–3 hours | 🟡 Medium |
| Integration test | 30 min | 🟢 Easy |
| Health monitoring | 2 hours | 🟡 Medium |
| Telegram alerts | 1.5 hours | 🟢 Easy |
| Admin UI | 3–4 hours | 🟡 Medium |
| External API key | 1.5 hours | 🟡 Medium |
| **Total POC** | **17–22 hours** | - |

---

## 🎓 Learning Resources

If you're new to any tech stack:

- **Flask:** https://flask.palletsprojects.com/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **YOLO:** https://github.com/ultralytics/ultralytics
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Docker:** https://docs.docker.com/

---

## 🆘 Need Help?

1. **Camera not uploading:** See [CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md)
2. **YOLO not detecting:** Check confidence threshold, image quality
3. **API errors:** Check `docker logs campark-api`
4. **DB issues:** Verify `docker ps`, check PostgreSQL is healthy
5. **Offline alerts not triggering:** Verify background task running, check timestamps

---

**Ready to start?**

1. Do the gate check: `bash tests/ftp_test.sh`
2. Follow Day 1 in [DAY_BY_DAY_PLAN.md](DAY_BY_DAY_PLAN.md)
3. Build the inference pipeline
4. Follow Day 2 for admin + alerts
5. Show your boss the proof

**Good luck! This is achievable in 2 days.** 🚀
