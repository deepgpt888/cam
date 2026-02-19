# CamPark POC: What's Needed (Dependencies & Requirements)

**Date:** February 5, 2026  
**Goal:** Identify all dependencies, tools, and requirements for 4-phase POC  
**Status:** Pre-flight checklist

---

## Part A: Local Machine Requirements

### Hardware
- [ ] Linux VM or dev container (recommended: Ubuntu 20.04+)
- [ ] 4GB RAM minimum (8GB recommended for YOLO + Docker)
- [ ] 10GB free disk space (for DB, images, YOLO model)
- [ ] Network: direct LAN access to camera (no NAT/VPN barriers)

### Network
- [ ] Camera reachable from local machine (ping test)
- [ ] FTP server can bind to port 21 (check firewall)
- [ ] Passive FTP ports 30000–30100 open (for camera upload)
- [ ] No antivirus blocking FTP (common issue)

---

## Part B: System Dependencies

### Installed Tools (Phase 1 — FTP Setup)

```bash
# Check what's available
which ftp python3 docker docker-compose

# Install if missing
sudo apt update
sudo apt install -y \
  postgresql-client \   # psql CLI (optional)
  curl \                # API testing
  git \                 # Version control
  python3 \             # Scripting
  imagemagick \         # Image validation (identify command)
  file                  # File type detection
```

### FTP User (Docker)
The FTP user is defined in docker-compose (`cam001` / `password123`).

```bash
mkdir -p data/ftp/cam001/incoming
```

### Docker & Docker Compose
```bash
# Verify installed
docker --version      # Should be 20.10+
docker-compose --version  # Should be 1.29+

# If missing, install Docker Desktop or from Docker docs
# For Ubuntu: https://docs.docker.com/engine/install/ubuntu/
```

---

## Part C: Code & Configuration Files (Must Exist)

### Workspace Structure
```
/workspaces/CamPark/
├── README.md                           ✓ Exists
├── TESTING_PLAN.md                     ✓ Will create
├── CAMERA_CONFIG_DAHUA.md              ✓ Will create
├── docker-compose.yml                  ✓ Will create
├── services/
│   ├── api/
│   │   ├── Dockerfile                  ⚠️ Needs creation
│   │   ├── main.py                     ⚠️ Needs creation
│   │   ├── requirements.txt            ⚠️ Needs creation
│   │   └── app/
│   │       └── db.py                   ⚠️ Needs creation
│   ├── worker/
│   │   ├── Dockerfile                  ⚠️ Needs creation
│   │   ├── main.py                     ⚠️ Needs creation
│   │   └── requirements.txt            ⚠️ Needs creation
│   └── config/
│       └── init.sql                    ✓ Will create
├── data/
│   ├── ftp/                            ⚠️ Needs mkdir
│   ├── images/                         ⚠️ Needs mkdir
│   ├── db/                             ⚠️ Docker volume
│   └── backups/                        ⚠️ Needs mkdir
├── models/                             ⚠️ For YOLO weights (download at runtime or pre-seed)
└── tests/
    └── ftp_test.sh                     ✓ Will create
```

### Status Legend
- ✓ = Already exists or will be created
- ⚠️ = Must be created before POC

---

## Part D: API Service Dependencies

### Python packages (services/api/requirements.txt)
```txt
Flask==2.3.2
psycopg2-binary==2.9.6
SQLAlchemy==2.0.19
pydantic==2.0.2
python-dotenv==1.0.0
gunicorn==21.0.0
```

### API Endpoints Required (Day 1-2)

| Endpoint | Method | Purpose | Day |
|---------|--------|---------|-----|
| `/api/v1/sites/{site_id}/status` | GET | Zone occupancy JSON | 1 |
| `/api/v1/cameras/{camera_id}/health` | GET | Camera ONLINE/STALE/OFFLINE | 2 |
| `/api/v1/cameras/{camera_id}/status` | GET | Last snapshot, detections | 1 |
| `/api/v1/sites/{site_id}/events` | GET | Zone change events (paginated) | 2 |
| `/api/v1/evidence/{event_id}` | GET | Evidence snapshot for event | 2 |
| `/admin/cameras` | GET/POST | Add/list cameras (web UI) | 2 |
| `/admin/zones/{camera_id}/editor` | GET/POST | Zone drawing UI (canvas) | 2 |
| `/admin/health` | GET | System health (DB, workers, disk) | 2 |
| `/admin/api-keys/generate` | POST | Issue external API key | 2 |

---

## Part E: Worker Service Dependencies

### Python packages (services/worker/requirements.txt)
```txt
torch==2.0.1+cpu
torchvision==0.15.2+cpu
ultralytics==8.0.110
psycopg2-binary==2.9.6
SQLAlchemy==2.0.19
python-dotenv==1.0.0
Pillow==10.0.0
numpy==1.24.3
redis==5.0.0
```

### YOLO Model
```bash
# Download at runtime or pre-seed
# Option A: ultralytics auto-downloads on first run
#   (models/cache/yolov8n.pt ~ 6.3 MB)
#
# Option B: Pre-download before POC
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
mv yolov8n.pt /workspaces/CamPark/models/yolov8n.pt

# Verify
ls -lh /workspaces/CamPark/models/yolov8n.pt
# Should be ~6-7 MB
```

### Worker Tasks (Queue)
```
Queue backend: PostgreSQL table (queue) or Redis
Queue table structure:
{
  id: int,
  snapshot_id: int,
  status: varchar (pending, processing, done, failed),
  created_at: timestamp,
  started_at: timestamp,
  completed_at: timestamp
}
```

---

## Part F: Database Requirements

### PostgreSQL
- Version: 13+ (15 recommended)
- Method: Docker container (postgres:15-alpine in docker-compose)
- Database name: `campark`
- User: `campark`
- Password: `changeme_poc` (for POC only!)
- Port: 5432

### Initial Migration
```sql
-- Run in init.sql (auto-executed by Docker)
-- Tables: projects, sites, cameras, zones, zone_states, snapshots, detections, zone_events, etc.
-- Indices: camera_last_seen, zone_id, snapshot_received_at, etc.
```

### Data Retention
- Keep snapshots for POC until 2-day test complete (no deletion needed yet)
- Archive strategy planned for pilot (after POC)

---

## Part G: FTP Server Requirements

### pure-ftpd (Docker) Configuration
FTP server runs as a container in docker-compose.

```bash
# .env
FTP_PUBLICHOST=<public-ip-or-hostname>
FTP_PASSIVE_PORTS=30000:30009

# Start FTP service
docker-compose up -d ftp
```

### Firewall (if applicable)
```bash
# Allow inbound FTP
sudo ufw allow 21/tcp
sudo ufw allow 30000:30100/tcp

# or check iptables
sudo iptables -L | grep 21
```

---

## Part H: File System & Volumes

### Directory Structure
```bash
mkdir -p data/ftp/cam001/incoming         # Camera uploads here
mkdir -p data/images/processed data/images/events
mkdir -p data/db                          # Postgres volume
mkdir -p data/backups                     # Daily snapshots
mkdir -p /workspaces/CamPark/models       # YOLO model weights

# Permissions
chmod 755 data/ftp/cam001/incoming
chmod 755 data/images
chmod 755 data/backups
```

### Disk Space
- `/data/images/`: ~1–5 MB/day (1 zone, 4-5 snapshots/min = ~500 images/day @ 10-20 KB each)
- `/data/db/`: ~10–50 MB/day (metadata only, no image blobs)
- `/data/backups/`: < 100 MB (nightly snapshots)
- **Total for POC (2 days):** ~20 MB sufficient

---

## Part I: Monitoring & Observability (Optional for POC)

### Log Aggregation
- Docker logs only (no centralized system needed for POC)
- Check logs: `docker logs -f campark-api`

### Alerting
- [ ] Telegram bot token (for offline alerts) — get from @BotFather on Telegram
- [ ] Telegram chat ID of your phone (for test alerts)

### Health Checks
```bash
# Manual health tests
curl http://localhost:8000/health                  # API running
curl http://localhost:8000/api/v1/db/status      # DB connected
docker exec campark-db pg_isready -U campark     # DB healthy
docker ps | grep campark-ftp                      # FTP running
```

---

## Part J: External Dependencies (Camera Side)

### Camera
- [ ] Dahua DH-IPC-HFW7442H-Z4FR (or equivalent with FTP upload support)
- [ ] Network connectivity (POE LAN or 4G with stable IP)
- [ ] FTP credentials configured (username, password, server IP/port, passive mode)
- [ ] Motion detection enabled
- [ ] Heartbeat interval set to 120 seconds
- [ ] **PT locked** (no auto-pan/tilt/patrol)

### External Dashboard (Future, Not for POC)
- [ ] API client credentials (to be generated in Day 2 admin UI)
- [ ] HTTPS endpoint to consume `/api/v1/sites/{id}/status`
- [ ] Webhook ingest endpoint (optional for push alerts)

---

## Part K: Security & Secrets (POC-Only Defaults)

### ⚠️ Change These Before Pilot

| Secret | POC Value | Pilot Value |
|--------|-----------|------------|
| DB password | `changeme_poc` | 32-char random |
| Admin password | `changeme_poc` | 32-char random |
| FTP cam001 password | `password123` | 32-char random per camera |
| API key | None (generate in Day 2) | Random + HMAC-SHA256 |
| TLS certificate | Self-signed by nginx | Proper CA cert |

### Secure Storage (Pilot)
- Passwords: PostgreSQL with bcrypt hash
- API keys: SHA256 hash in DB
- Secrets: Docker secrets or `.env` file (don't commit)

---

## Part L: Testing Requirements

### Functional Tests (Manual, End-to-End)
```bash
# 1. FTP upload (Phase 0)
bash tests/ftp_test.sh

# 2. API response (Phase 1, Day 1)
curl http://localhost:8000/api/v1/sites/1/status | jq

# 3. Zone update on inference (Phase 1, Day 1)
# Upload snapshot, verify zone_state.occupied_units increments

# 4. Health checks (Phase 2, Day 2)
curl http://localhost:8000/api/v1/cameras/1/health | jq

# 5. Offline alert (Phase 2, Day 2)
# Stop camera, wait 150s, verify STALE alert
# Wait 300s, verify OFFLINE alert
```

### Load-Testing (Not Required for POC)
- Skip load testing for POC
- Plan for pilot: 5 FPS × 4 cameras = 20 images/sec throughput test

---

## Part M: Documentation Files (Create Before POC)

**Status: 100% of documentation will be created**

- [x] `TESTING_PLAN.md` — This document (phases + checklists)
- [x] `CAMERA_CONFIG_DAHUA.md` — Camera setup guide
- [x] `docker-compose.yml` — Service definitions
- [x] `services/config/init.sql` — DB schema
- [ ] `API_REFERENCE.md` — Endpoint specifications (create Day 1)
- [ ] `ADMIN_UI_GUIDE.md` — Zone editor walkthrough (create Day 2)
- [ ] `DEPLOYMENT_RUNBOOK.md` — How to deploy to production (create after POC)

---

## Part N: Quick Pre-Flight Checklist (Before Starting)

```bash
# Run all checks before Day 1
echo "1. Checking system..."
which ftp python3 docker docker-compose git

echo "2. Checking directories..."
ls -d data/ftp data/images data/backups 2>/dev/null || echo "⚠️  Create dirs"

echo "3. Checking FTP user..."
echo "4. Checking FTP container..."
docker ps | grep campark-ftp >/dev/null || echo "⚠️  Start: docker-compose up -d ftp"

echo "5. Checking Docker..."
docker ps 2>/dev/null || echo "⚠️  Start Docker daemon"

echo "6. Checking camera..."
ping -c 1 192.168.1.50 2>/dev/null && echo "✓ Camera reachable" || echo "⚠️  Camera IP not reachable"

echo "7. Checking workspace..."
ls /workspaces/CamPark/README.md && echo "✓ Workspace OK" || echo "⚠️  Workspace missing"

echo "8. Running FTP test..."
bash /workspaces/CamPark/tests/ftp_test.sh
```

---

## Summary: What Needs to Be Built vs. What Exists

### Already Exists
- ✅ Project structure
- ✅ Testing plan + checklist
- ✅ Camera config guide
- ✅ FTP test script
- ✅ Database schema
- ✅ API service (Flask)
- ✅ YOLO worker (FTP watcher + inference)
- ✅ Admin UI templates
- ✅ API key generation

### Must Be Created (Phase 4 Hardening)
- 🔨 TLS + reverse proxy
- 🔨 Backups + retention policy
- 🔨 Monitoring + alerting
- 🔨 Log rotation

### Must Be Configured
- ⚙️ pure-ftpd (Docker FTP server)
- ⚙️ PostgreSQL (Docker container)
- ⚙️ Docker networks + volumes

### Must Be Tested
- 🧪 Camera FTP upload (Phase 0 gate)
- 🧪 YOLO inference on camera snapshot (Day 1)
- 🧪 Zone state updates (Day 1)
- 🧪 Offline detection (Day 2)
- 🧪 API key enforcement (Day 2)

---

## Next Step

**Run this command to validate your base setup:**

```bash
cd /workspaces/CamPark
docker-compose up -d ftp
bash tests/ftp_test.sh
```

If all checks pass, you're gate-ready. Otherwise, fix the failures before proceeding to POC.

---

**Document Version:** POC v0.1  
**Last Updated:** Feb 5, 2026  
**Owner:** You  
**Status:** Pre-flight (Ready for Day 0 gate check)
