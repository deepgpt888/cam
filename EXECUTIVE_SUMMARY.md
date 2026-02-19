# CamPark POC: Executive Summary for Your Boss

**Date:** February 5, 2026  
**Prepared for:** Project sponsor / decision maker  
**Status:** POC-ready, 2-day execution plan approved  

---

## The Ask

Build **CamPark**: a parking occupancy detection system that uses CCTV snapshots + vehicle AI to provide real-time zone occupancy updates.

**Timeline:** 2 days (Day 0 gate + Day 1-2 build)  
**Team:** 1–2 developers  
**Hardware:** Single server (Docker), one CCTV camera  
**Cost:** ~$0 (existing infrastructure) + dev time  

---

## What You Get (POC MVP)

### Why It Works (Indonesia/Malaysia proven pattern)
1. **Event-based snapshots** (motion/vehicle triggers) + **2-minute heartbeat** → Camera tells us immediately when something changes, but doesn't drain battery
2. **CPU-only inference** (YOLO) → Works on 5-year-old servers, no expensive GPU hardware
3. **ROI + zone overlap logic** → Ignores street traffic, only counts parking area vehicles
4. **Offline detection in 2.5 minutes** → Team knows when camera dies, not 3 hours later

### Core Functionality
✅ **Snapshot Ingest** — Camera uploads JPEG via FTP (every 120s + on motion)  
✅ **Vehicle Detection** — YOLO detects cars/trucks (confidence ≥ 0.80)  
✅ **Zone Occupancy** — Counts vehicles per parking zone in real-time  
✅ **Offline Alerts** — Telegram notification if camera silent > 150s (STALE) / 300s (OFFLINE)  
✅ **Admin UI** — Add cameras without code changes, draw zones via click/drag  
✅ **External API** — Dashboard pulls zone JSON with read-only API key  
✅ **Single-Server Ops** — Docker Compose, safe upgrades (< 5 hours downtime), 99% uptime target  

---

## Hard Gate (Non-Negotiable)

Your chosen camera **MUST** upload JPEG snapshots to FTP server.

**If it can't:** The system cannot ingest images. Zero workaround.

**We test this first (Day 0, 3–4 hours).**
- If gate passes: Cleared for 2-day POC build
- If gate fails: Fix camera, then restart POC

---

## 2-Day Timeline

### Day 0: Gate Check (3–4 hours)
**Owner:** You  
**Activity:** Setup local FTP server, configure camera, verify files arrive

**Proof for you:**
```
/data/ftp/cam001/incoming/
├── 2026-02-05_10:12:15.jpg (85 KB)
├── 2026-02-05_10:14:15.jpg (87 KB)
├── 2026-02-05_10:16:15.jpg (89 KB)
```

✅ **Gate result:** "Camera works. We're cleared to build."

---

### Day 1: Core Inference (6–8 hours)
**Owner:** Dev team  
**What Gets Built:**
- PostgreSQL database (zone state + events)
- Flask API (JSON endpoints + health monitoring)
- YOLO worker (vehicle detection in background)
- Docker Compose (all services bundled)

**Proof for you (live demo):**
```bash
$ curl http://localhost:8000/api/v1/sites/1/status
{
  "site_id": 1,
  "ts": "2026-02-05T10:30:00Z",
  "zones": [
    {
      "zone_id": "A01",
      "state": "PARTIAL",
      "occupied_units": 1,
      "available_units": 0
    }
  ]
}
```

✅ **Demo talking points:** "Camera uploads → Server processes with YOLO → Zone occupancy updates in JSON"

---

### Day 2: Operations + Alerts (8–10 hours)
**Owner:** Dev team  
**What Gets Built:**
- Camera **health monitoring** (ONLINE/STALE/OFFLINE detection in 150–300s)
- **Telegram alerts** (offline notification to your phone)
- **Admin web UI** (add camera, draw zones, see health status)
- **External API keys** (dashboard gets read-only access)

**Proof for you (live demo):**

1. **Admin panel** — Add new camera without touching code
   ```
   Browser: http://localhost:8000/admin/cameras
   Click: "+ Add Camera"
   Fill: name="Test Cam 2", ftp_user="cam002"
   System: Auto-generates FTP user + password
   ```

2. **Zone editor** — Draw parking zone visually
   ```
   Browser: http://localhost:8000/admin/zones/1/editor
   See: Live camera snapshot
   Do: Click/drag to draw polygon around parking spaces
   Click: "Save"
   Result: Zone saved to DB, inference starts using it
   ```

3. **Offline alert** — Stop camera, watch Telegram
   ```
   Power off camera
   Wait 150 seconds
   Phone notification: "🚨 Camera CAM001 STALE (no data >150s)"
   Wait another 150 seconds
   Phone notification: "🚨 Camera CAM001 OFFLINE (no data >300s)"
   Power on camera
   Phone notification: "✅ Camera CAM001 ONLINE"
   ```

4. **External dashboard** — API key auth + read-only
   ```bash
   $ curl -X POST http://localhost:8000/admin/api-keys/generate \
     -d '{"name": "dashboard"}'
   → Returns: {"api_key": "sk_..."}
   
   $ curl -H "X-API-Key: sk_..." \
     http://localhost:8000/api/v1/sites/1/status
   → Returns: Valid JSON (zone occupancy)
   
   $ curl -X POST -H "X-API-Key: sk_..." ...
   → Returns: 403 Forbidden (read-only enforced)
   ```

✅ **Demo talking points:** "Team can add cameras instantly. Operations draws zones. Alerts notify immediately. Dashboard integrates via secure API."

---

## Risks & Mitigations

| Risk | Mitigation | Owner |
|------|-----------|-------|
| **Camera can't upload FTP** | Gate test (Day 0) catches immediately | You |
| **YOLO CPU too slow** | Test with actual snapshot before Day 1 | Dev team |
| **Zone drawing UX complex** | Use Fabric.js (proven, simple API) | Dev team |
| **Offline alerts unreliable** | Server-side timer (not camera clock) | Dev team |
| **Missing requirements** | Spec locked (this document) | Both |

---

## What Success Looks Like

### End of Day 0
You show your boss:
> "Our camera is uploading snapshots every 2 minutes to our server. Files are real JPEGs, > 10KB each. System is ready for build."

### End of Day 1
Dev team shows your boss:
> "We process each snapshot with YOLO (detects 4 vehicle classes). Zone occupancy updates in real-time. Our JSON API returns the current state. Everything runs in Docker."

**Proof:** Live API call returning zone occupancy JSON

### End of Day 2
Dev team shows your boss:
> "Operators can add cameras without writing code. They draw zones visually on the snapshot. System alerts us when cameras go offline (within 150 seconds). External dashboards get secure read-only API access."

**Proof:**
- Live admin UI (add camera, draw zone, see health)
- Telegram notifications (offline alert)
- API key + read-only enforcement

---

## Deployment (Single Server)

### Architecture
```
                    Dahua CCTV (FTP)
                           ↓
                   CamPark Server (VM)
                      ├─ vsftpd
                      ├─ PostgreSQL
                      ├─ Flask API
                      └─ YOLO Worker
                           ↓
            External Dashboard (read-only JSON)
```

### Server Requirements
- **Hardware:** 4GB RAM, 10GB disk, POE LAN to camera
- **OS:** Ubuntu 20.04+
- **Software:** Docker, Docker Compose, vsftpd
- **Network:** FTP ports open, HTTPS for external API

### Ops Model
- **Uptime target:** 99% (safe upgrades < 5 hours downtime)
- **Backups:** Nightly snapshots to secondary storage
- **Monitoring:** Prometheus + Grafana (optional for POC)
- **Alerting:** Telegram + email (escalation path)

---

## Cost Breakdown (POC)

| Item | Cost | Notes |
|------|------|-------|
| **Dev time (2 days)** | $500–2000 | 1–2 engineers @ $250/hr |
| **Server (POC)** | $0 | Reuse existing VM |
| **Camera (if new)** | $150–300 | Dahua 4MP with PTZ |
| **FTP server** | $0 | vsftpd (open source) |
| **Telegram bot** | $0 | Free @BotFather |
| **Database** | $0 | PostgreSQL (open source) |
| **YOLO inference** | $0 | Ultralytics (open source) |
| **TOTAL POC** | **$500–2300** | Dev + camera (if needed) |

### Pilot (Estimated)
- 4 cameras × 1 week integration = $2000–4000
- TLS + nginx + monitoring = $500–1000
- Backup + ops runbooks = $500–1000
- **Pilot: ~$5000–6000 total**

---

## Success Metrics

### Technical (Validation)
- ✅ Camera uploading FTP snapshots (gate)
- ✅ YOLO detecting vehicles (> 80% confidence)
- ✅ Zone occupancy JSON responsive < 200ms
- ✅ Offline alerts triggering within 150s (STALE) / 300s (OFFLINE)
- ✅ API key auth enforced (read-only)

### Operational (Value)
- ✅ Operators can add cameras without code
- ✅ Admin can draw zones via UI (5 min, no training)
- ✅ System alerts on offline (vs. manual checking)
- ✅ Dashboard integrates with existing tools (JSON API)

### Business (ROI)
- ✅ Proof camera + software works together
- ✅ Real parking data in 48 hours
- ✅ Team confidence for pilot deployment
- ✅ Clear path to multi-site rollout

---

## Timeline & Approval Gates

```
Day 0 (3–4h)        Day 1 (6–8h)          Day 2 (8–10h)
┌──────────────┐   ┌──────────────┬───┐   ┌──────────────┐
│  FTP Gate    │──▶│  Inference   │   │──▶│   Admin UI   │
│  Test        │   │  Pipeline    │   │   │   + Alerts   │
│  PASS/FAIL   │   │  (JSON API)  │   │   │   (Live ops) │
└──────────────┘   └──────────────┴───┘   └──────────────┘
       ▲                    ▲                      ▲
       │                    │                      │
    Go/No-Go          Demo for Boss        Final Sign-Off
```

### Go/No-Go Decision Points

**Day 0:** 
- ✅ Camera FTP upload working → **Proceed to Day 1**
- ❌ Camera FTP upload failing → **Stop. Fix camera. Restart.**

**Day 1:**
- ✅ YOLO + zone occupancy JSON working → **Proceed to Day 2**
- ❌ Major delays or tech issues → **Pivot: simplify features**

**Day 2:**
- ✅ Admin UI + alerts working → **POC Success. Plan pilot.**
- 🟡 Some features incomplete → **Alpha version. Plan beta.**

---

## Next Steps (After POC)

### Week 2–3: Pilot Prep
- [ ] Multi-camera, multi-site support (POC was single)
- [ ] TLS certificates + nginx reverse proxy
- [ ] Prometheus monitoring + alerting dashboard
- [ ] Database backups + disaster recovery test
- [ ] Rate limiting + API quotas (token bucket)

### Week 4: Pilot Rollout
- [ ] 4 sites, 1 camera each (20 zones total)
- [ ] Team training on admin UI
- [ ] Integration with parking dashboard (if exists)
- [ ] 30-day trial with stakeholders

### Month 2: Production
- [ ] Kubernetes deployment (if needed for scale)
- [ ] Centralized logging + audit trail
- [ ] Production secrets management (Vault)
- [ ] SLA 99.5% uptime commitment

---

## Questions to Ask Your Team

1. **Camera ready?** "Do we have the Dahua unit ready and powered on the network?"
2. **Dev capacity?** "Can 1–2 engineers commit 2 days for sprints, or split across weeks?"
3. **Telegram bot?** "Do you want phone alerts, or email only?"
4. **Dashboard integration?** "What format does your parking dashboard expect? (JSON example below)"
5. **Timeline pressure?** "Is this a hard deadline, or can we iterate?"

---

## Sample External Dashboard Integration

**Your dashboard PULLS from CamPark (not push):**

```bash
# Your dashboard app
GET /api/v1/sites/{site_id}/status
Authorization: Bearer sk_<api_key>

Response:
{
  "site_id": 1,
  "timestamp": "2026-02-05T10:30:00Z",
  "zones": [
    {
      "zone_id": "A01",
      "capacity": 1,
      "occupied": 1,
      "available": 0,
      "state": "FULL"
    },
    {
      "zone_id": "A02",
      "capacity": 1,
      "occupied": 0,
      "available": 1,
      "state": "FREE"
    }
  ],
  "summary": {
    "total_capacity": 2,
    "total_occupied": 1,
    "total_available": 1,
    "occupancy_rate": 0.50
  }
}
```

Your dashboard calls this every 30 seconds, updates UI.

---

## Checklist for Approval

Before greenlight:
- [ ] Boss approves 2-day POC timeline
- [ ] Dev team assigned (1–2 engineers)
- [ ] Camera hardware ready and powered on
- [ ] Server VM provisioned (4GB RAM, 10GB disk)
- [ ] Telegram token obtained (if alerts required)
- [ ] Success criteria documented (this doc)

---

## Final Pitch

> **"We can prove this works in 2 days.** 
> 
> Day 0: Camera uploads snapshots (gate test).  
> Day 1: System detects vehicles, updates zone occupancy in JSON.  
> Day 2: Operators get admin UI, alerts work, external dashboard integrates.  
> 
> Risk is low (open-source tech, proven pattern in India/Malaysia). Cost is dev time only. ROI: real parking data in 48 hours, clear path to pilot rollout.  
> 
> **Timeline:** 2 days (achievable).  
> **Hard gate:** Camera can upload FTP (we test this first).  
> **Success:** Boss sees live system doing job, team ready for next phase."

---

**Document prepared:** Feb 5, 2026  
**Status:** Ready for approval  
**Next step:** Execute Day 0 gate check  
**Contact:** [Your name] for questions