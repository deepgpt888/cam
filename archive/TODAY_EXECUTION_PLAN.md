# 🎯 CamPark POC - TODAY'S EXECUTION PLAN
**Date:** 2026-02-05  
**Time:** 15:32 (7+ hours remaining)  
**Goal:** Show boss a working POC by end of day

---

## ⚡ QUICK STATUS CHECK

### What's Already Built ✅
- ✅ Database schema (init.sql)
- ✅ Docker Compose (FTP, Postgres, API, Worker)
- ✅ API service (Flask with all endpoints)
- ✅ YOLO Worker (FTP monitoring + inference)
- ✅ Health monitoring + Telegram alerts
- ✅ Admin UI templates (cameras, zones, health)
- ✅ API key generation

### What We Need to Execute 🚀
1. **Setup local environment** (30 min)
2. **Build & start services** (30 min)
3. **Test FTP upload** (15 min)
4. **Verify YOLO processing** (15 min)
5. **Test admin UI** (30 min)
6. **Create demo script** (30 min)
7. **Run end-to-end test** (1 hour)

**Total:** ~3.5 hours + buffer = **5 hours max**

---

## 📋 EXECUTION STEPS

### Step 1: Environment Setup (30 min)

#### 1.1 Create .env file
```bash
cd c:\document\CamPark
cp .env.example .env
```

#### 1.2 Create data directories
```bash
mkdir -p data/ftp/cam001/incoming
mkdir -p data/images
mkdir -p data/db
mkdir -p models
```

#### 1.3 Download YOLO model (if needed)
```bash
# The worker will auto-download yolov8n.pt on first run
# Or manually: wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolov8n.pt
```

---

### Step 2: Build & Start Services (30 min)

#### 2.1 Build all services
```bash
docker-compose build
```

#### 2.2 Start infrastructure
```bash
docker-compose up -d postgres redis ftp
```

#### 2.3 Wait for Postgres to be ready
```bash
# Wait 30 seconds
docker logs campark-db | grep "database system is ready"
```

#### 2.4 Start application services
```bash
docker-compose up -d api worker
```

#### 2.5 Verify all services running
```bash
docker ps
# Should see: campark-ftp, campark-db, campark-redis, campark-api, campark-worker
```

---

### Step 3: Test FTP Upload (15 min)

#### 3.1 Create test image
```bash
# Create a simple test JPEG (or use a real photo)
# We'll use Python to create one
```

#### 3.2 Upload via FTP
```bash
# Test FTP connection
ftp localhost
# user: cam001
# password: password123
# cd incoming
# put test.jpg
# quit
```

#### 3.3 Verify file arrived
```bash
ls -la data/ftp/cam001/incoming/
```

---

### Step 4: Verify YOLO Processing (15 min)

#### 4.1 Check worker logs
```bash
docker logs -f campark-worker
# Should see: "Processing snapshot..." and "Detections: X vehicles"
```

#### 4.2 Check database
```bash
docker exec -it campark-db psql -U campark -d campark -c "SELECT * FROM snapshots ORDER BY received_at DESC LIMIT 5;"
docker exec -it campark-db psql -U campark -d campark -c "SELECT * FROM detections ORDER BY created_at DESC LIMIT 5;"
```

#### 4.3 Test API endpoint
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/sites/1/status | jq
```

---

### Step 5: Test Admin UI (30 min)

#### 5.1 Open browser to admin pages
- http://localhost:8000/admin/cameras
- http://localhost:8000/admin/health
- http://localhost:8000/admin/zones/CAM001/editor

#### 5.2 Test camera list
- Should show CAM001 with status

#### 5.3 Test zone editor
- Open zone editor
- Draw a polygon
- Save zone
- Verify in database

#### 5.4 Test API key generation
```bash
curl -X POST http://localhost:8000/admin/api-keys/generate \
  -H "Content-Type: application/json" \
  -d '{"name": "Dashboard", "site_ids": [1]}'
```

---

### Step 6: Camera Integration (OPTIONAL - if you have Dahua camera)

#### 6.1 Find camera IP
```bash
# Check router DHCP or use nmap
nmap -sn 192.168.1.0/24
```

#### 6.2 Configure camera FTP
- Login to camera web UI
- Settings → Network → FTP
- Server: YOUR_PC_IP
- Port: 21
- Username: cam001
- Password: password123
- Remote directory: incoming
- Test connection

#### 6.3 Enable motion detection
- Settings → Event → Motion Detection
- Enable snapshot upload on motion

#### 6.4 Enable heartbeat (120s interval)
- Settings → Network → FTP → Scheduled Upload
- Interval: 120 seconds

---

### Step 7: Create Demo Script (30 min)

Create a demo script that shows:
1. ✅ FTP server receiving snapshots
2. ✅ YOLO detecting vehicles
3. ✅ Zone occupancy updating
4. ✅ API returning JSON
5. ✅ Admin UI showing cameras
6. ✅ Health monitoring working
7. ✅ Telegram alerts (if configured)

---

### Step 8: End-to-End Test (1 hour)

#### Test Scenario 1: Normal Operation
1. Upload snapshot with vehicle
2. Wait 5 seconds
3. Check API: `curl http://localhost:8000/api/v1/sites/1/status | jq`
4. Verify zone shows occupied_units > 0

#### Test Scenario 2: Camera Offline Detection
1. Stop uploading (simulate camera offline)
2. Wait 150 seconds
3. Check health: `curl http://localhost:8000/admin/health.json | jq`
4. Should show status: STALE
5. Wait 150 more seconds (total 300s)
6. Should show status: OFFLINE
7. If Telegram configured, should receive alert

#### Test Scenario 3: External API Access
1. Generate API key
2. Use key to access API:
```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/v1/sites/1/status | jq
```
3. Try to POST (should fail with 403):
```bash
curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:8000/admin/cameras
```

---

## 🎬 DEMO SCRIPT FOR BOSS

### Opening (1 min)
"I've built a proof-of-concept parking monitoring system called CamPark. It uses IP cameras with FTP upload, YOLO AI for vehicle detection, and provides a JSON API for dashboards."

### Demo 1: Live System (2 min)
```bash
# Show running services
docker ps

# Show API health
curl http://localhost:8000/health | jq

# Show current zone status
curl http://localhost:8000/api/v1/sites/1/status | jq
```

**Talk:** "All services are running in Docker. The API is healthy and returning real-time zone occupancy data."

### Demo 2: FTP Ingest (2 min)
```bash
# Show FTP directory
ls -la data/ftp/cam001/incoming/

# Upload test image
# (prepare this beforehand)

# Show worker processing
docker logs campark-worker | tail -20
```

**Talk:** "Camera uploads snapshots via FTP every 2 minutes. The worker detects new files, runs YOLO inference, and updates zone states."

### Demo 3: Admin UI (3 min)
- Open browser: http://localhost:8000/admin/cameras
- Show camera list with status
- Open zone editor: http://localhost:8000/admin/zones/CAM001/editor
- Draw a zone polygon
- Save zone

**Talk:** "Admins can add cameras without code changes. The zone editor lets you draw parking zones on live snapshots."

### Demo 4: Health Monitoring (2 min)
- Open: http://localhost:8000/admin/health
- Show camera status (ONLINE/STALE/OFFLINE)
- Explain: "System detects offline cameras in 2.5 minutes and sends Telegram alerts"

### Demo 5: External API (2 min)
```bash
# Generate API key
curl -X POST http://localhost:8000/admin/api-keys/generate \
  -H "Content-Type: application/json" \
  -d '{"name": "Dashboard"}'

# Use API key
curl -H "X-API-Key: GENERATED_KEY" \
  http://localhost:8000/api/v1/sites/1/status | jq

# Show read-only enforcement
curl -X POST -H "X-API-Key: GENERATED_KEY" \
  http://localhost:8000/admin/cameras
# Returns 403 Forbidden
```

**Talk:** "External dashboards get read-only API keys. They can fetch zone status but cannot modify data."

### Closing (1 min)
"This POC proves:
- ✅ Camera FTP upload works
- ✅ YOLO detects vehicles accurately
- ✅ Zone occupancy updates in real-time
- ✅ Admin can add cameras/zones without coding
- ✅ External dashboards can consume JSON API
- ✅ System detects offline cameras reliably

Ready for pilot deployment."

---

## 🚨 TROUBLESHOOTING

### Issue: Docker build fails
**Fix:** Check Docker is running, check internet connection for base images

### Issue: Postgres not ready
**Fix:** Wait 30 seconds, check logs: `docker logs campark-db`

### Issue: Worker crashes
**Fix:** Check YOLO model downloaded, check logs: `docker logs campark-worker`

### Issue: FTP connection refused
**Fix:** Check FTP container running: `docker ps | grep ftp`

### Issue: No detections
**Fix:** Check image has vehicles, lower confidence threshold in .env

### Issue: API returns 500
**Fix:** Check database connection, check logs: `docker logs campark-api`

---

## ✅ SUCCESS CRITERIA

By end of day, you should be able to:
- [ ] Show all Docker services running
- [ ] Upload snapshot via FTP
- [ ] See YOLO detections in database
- [ ] Get JSON response from API with zone occupancy
- [ ] Show admin UI (cameras, zones, health)
- [ ] Generate and use API key
- [ ] Demonstrate offline detection (optional)

---

## 📸 SCREENSHOTS TO PREPARE

1. `docker ps` showing all services
2. API response: `/api/v1/sites/1/status`
3. Admin cameras page
4. Zone editor with drawn polygon
5. Health monitoring page
6. Worker logs showing detections

---

## ⏰ TIMELINE

- **15:30 - 16:00** (30 min): Environment setup
- **16:00 - 16:30** (30 min): Build & start services
- **16:30 - 17:00** (30 min): Test FTP & YOLO
- **17:00 - 17:30** (30 min): Test Admin UI
- **17:30 - 18:00** (30 min): Create demo script
- **18:00 - 19:00** (1 hour): End-to-end testing
- **19:00 - 20:00** (1 hour): Buffer for issues
- **20:00+**: Ready for demo!

---

**LET'S GO! 🚀**
