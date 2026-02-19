# CamPark POC: 2-Day Execution Roadmap

**Goal:** Build a proof-of-concept to show your boss:
1. Camera can upload snapshots via FTP ✅
2. Server can process them with YOLO ✅
3. Zone occupancy updates automatically ✅
4. Admin can add cameras without code ✅
5. System alerts when camera goes offline ✅

**Timeline:** Day 0 (gate) + Day 1 (inference) + Day 2 (admin + alerts)

---

## Day 0: Gate Check (3–4 hours)

### Objective
Prove the Dahua camera can upload JPEG snapshots to your FTP server. This is **blocking** — if it fails, stop and fix the camera config.

### Checklist

- [ ] **Phase 0a: Local FTP Setup (30 min)**
  - [ ] Install vsftpd: `sudo apt install vsftpd`
  - [ ] Create FTP user: `sudo useradd -m -s /bin/false cam001`
  - [ ] Set password: `echo "cam001:password123" | sudo chpasswd`
  - [ ] Create FTP root: `sudo mkdir -p /data/ftp/cam001/incoming`
  - [ ] Set permissions: `sudo chown -R cam001:cam001 /data/ftp/cam001`
  - [ ] Edit `/etc/vsftpd.conf` (append local_enable=YES, write_enable=YES, etc.)
  - [ ] Restart: `sudo systemctl restart vsftpd`
  - [ ] Test locally: `ftp localhost` → upload test.jpg → verify in `/data/ftp/cam001/incoming/`

- [ ] **Phase 0b: Camera Network Access (15 min)**
  - [ ] Find camera IP: `nmap -sn 192.168.1.0/24 | grep -i dahua`
  - [ ] Test ping: `ping <camera-ip>` (should respond)
  - [ ] Open browser: `http://<camera-ip>`
  - [ ] Login: admin / admin
  - [ ] Change password (for safety)

- [ ] **Phase 0c: Camera FTP Configuration (30 min)**
  - [ ] Navigate: Settings → Network → Advanced → FTP
  - [ ] **FTP Server Address:** Your machine IP (e.g., 192.168.1.100)
  - [ ] **Port:** 21
  - [ ] **Username:** cam001
  - [ ] **Password:** password123
  - [ ] **Remote Directory:** incoming
  - [ ] **Passive Mode:** ✓ ENABLE
  - [ ] Click **Test** → should say "Connection successful"

- [ ] **Phase 0d: Enable Motion & Heartbeat (15 min)**
  - [ ] Navigate: Settings → Event → Motion Detection → Enable
  - [ ] Navigate: Settings → Network → Advanced → FTP → Scheduled Upload
  - [ ] **Interval:** 120 seconds
  - [ ] Enable

- [ ] **Phase 0e: Verify Files Arrive (15 min, patience required)**
  - [ ] Wait 2–3 minutes
  - [ ] Check: `ls -la /data/ftp/cam001/incoming/`
  - [ ] Should see at least 1 file (heartbeat snapshot)
  - [ ] Verify: `file /data/ftp/cam001/incoming/*.jpg` → should say "JPEG image data"
  - [ ] Verify size: > 10KB (real image, not stub)

### Success Criteria (Gate)
- ✅ FTP user `cam001` created and password set
- ✅ vsftpd running and listening on port 21
- ✅ FTP test from camera admin panel says "successful"
- ✅ At least 3 JPEG files in `/data/ftp/cam001/incoming/`
- ✅ Files arrive every ~120 seconds (heartbeat working)
- ✅ File size > 10KB (valid images, not corrupted)

### If Gate Fails
❌ **DO NOT PROCEED** — camera cannot upload.

**Troubleshooting:**
- FTP test fails: Check firewall, verify port 21 open, verify vsftpd running
- Files don't appear: Check camera FTP settings (passive mode critical!), test network connectivity
- Files corrupt: Check camera FTP encode settings, verify JPEG support

### Proof for Boss (Take Screenshot)
```bash
ls -la /data/ftp/cam001/incoming/ | tail -5
# Output shows:
# 2026-02-05_10:12:15.jpg  (85 KB)
# 2026-02-05_10:14:15.jpg  (87 KB)
# 2026-02-05_10:16:15.jpg  (89 KB)

file /data/ftp/cam001/incoming/*.jpg
# Output shows:
# JPEG image data, 4208 x 3120, baseline
```

**Show this to your boss:** "Camera is uploading snapshots successfully. We're now ready for Day 1."

---

## Day 1: FTP → YOLO → Zone State (6–8 hours)

### Objective
Build the core inference pipeline: camera uploads → YOLO detects vehicles → zone occupancy updates → JSON API returns current state.

### Starting Point (Beginning of Day 1)
- ✅ Camera uploading snapshots to FTP
- ✅ Directory structure in place
- ✅ Docker & PostgreSQL ready

### Build Tasks

#### Task 1.1: Bring Up Database (30 min)

```bash
cd /workspaces/CamPark

# Create Docker network and volumes
docker network create campark
docker volume create postgres_data

# Start PostgreSQL only
docker-compose up -d postgres

# Verify
docker ps | grep postgres
docker logs campark-db | head -20

# Wait for healthy status
docker ps | grep "postgres" | grep "healthy"
```

**Checkpoint:** `docker exec campark-db psql -U campark -d campark -c "SELECT COUNT(*) FROM cameras;"` returns 1 (test camera created)

#### Task 1.2: Build API Service (2–3 hours)

Create `services/api/` directory structure:

```
services/api/
├── Dockerfile
├── main.py
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── db.py           # SQLAlchemy models
│   ├── models.py       # Pydantic schemas
│   └── routes.py       # Flask endpoints
└── .env                # DB connection string
```

**Key endpoints to implement:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sites/{site_id}/status` | GET | Current zone occupancy (JSON) |
| `/api/v1/cameras/{camera_id}/status` | GET | Last snapshot + detections |
| `/health` | GET | Service health check |

**Sample `/api/v1/sites/1/status` response:**
```json
{
  "site_id": 1,
  "ts": "2026-02-05T10:30:00Z",
  "zones": [
    {
      "zone_id": "ZONE_A01",
      "state": "FREE",
      "occupied_units": 0,
      "available_units": 1
    }
  ],
  "totals": {
    "occupied_units": 0,
    "available_units": 1
  }
}
```

**Minimal `main.py`:**
```python
from flask import Flask, jsonify
from app.db import init_db
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

init_db(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/v1/sites/<int:site_id>/status', methods=['GET'])
def get_site_status(site_id):
    # Query DB for zone states
    # Return JSON
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
```

#### Task 1.3: Build YOLO Worker (2–3 hours)

Create `services/worker/` directory structure:

```
services/worker/
├── Dockerfile
├── main.py
├── requirements.txt
└── yolo_processor.py
```

**Key functionality:**

1. **Monitor FTP incoming directory:**
   ```python
   import os
   import time
   from pathlib import Path
   
   ftp_path = Path('/data/ftp/cam001/incoming')
   processed_files = set()
   
   while True:
       files = list(ftp_path.glob('*.jpg'))
       new_files = [f for f in files if f.name not in processed_files]
       
       for file in new_files:
           process_snapshot(file)
           processed_files.add(file.name)
       
       time.sleep(1)
   ```

2. **Run YOLO inference:**
   ```python
   from ultralytics import YOLO
   
   model = YOLO('yolov8n.pt')
   
   def process_snapshot(file_path):
       results = model(str(file_path), conf=0.80)
       
       for detection in results[0].boxes:
           class_name = results[0].names[int(detection.cls)]
           confidence = float(detection.conf)
           bbox = detection.xyxy[0]  # [x1, y1, x2, y2]
           
           # Save to DB
           save_detection_to_db(file_path, class_name, confidence, bbox)
   ```

3. **Update zone state:**
   ```python
   def update_zone_state(zone_id, detections):
       # For POC: hardcoded zone
       # Check if detections overlap zone polygon by >= 30%
       # Count occupied units
       # Update zone_state table
       pass
   ```

#### Task 1.4: Docker Compose (30 min)

Update `docker-compose.yml` to include postgres + api + worker:

```bash
docker-compose up -d

# Wait for services to be healthy
sleep 10

docker ps
docker logs campark-api
docker logs campark-worker
```

#### Task 1.5: Integration Test (30 min)

```bash
# 1. Upload a test snapshot to FTP manually
cp /path/to/test_car_photo.jpg /data/ftp/cam001/incoming/test_20260205_103000.jpg

# 2. Wait 5 seconds for worker to process
sleep 5

# 3. Check detections in DB
docker exec campark-db psql -U campark -d campark -c "SELECT * FROM detections ORDER BY created_at DESC LIMIT 1;"

# 4. Check API response
curl http://localhost:8000/api/v1/sites/1/status | jq

# Should show:
# {
#   "zones": [{"zone_id": "ZONE_A01", "state": "FREE", "occupied_units": 0}]
# }
```

### Proof for Boss (End of Day 1)

**Show this in terminal:**

```bash
# 1. Camera is uploading
ls -la /data/ftp/cam001/incoming/ | wc -l
# Output: "5" (5 files = active camera)

# 2. YOLO is processing
docker logs campark-worker | grep "vehicle detected" | tail -3
# Output: processing logs with detections

# 3. API is responding
curl http://localhost:8000/api/v1/sites/1/status
# Output: {"zones": [{"zone_id": "ZONE_A01", "state": "PARTIAL", ...}]}

# 4. Database has data
docker exec campark-db psql -U campark -d campark -c "SELECT COUNT(*) FROM detections;"
# Output: "42" (X detections processed)
```

**Talking Points for Boss:**
- ✅ "Camera uploads snapshots autonomously to our FTP server every 2 minutes"
- ✅ "Server processes them in real-time with YOLO (car/truck detection)"
- ✅ "Zone occupancy updates automatically"
- ✅ "JSON API returns current parking state"
- ✅ "All services running in Docker (ready for deployment)"

**Success Criteria:**
- ✅ API `/status` endpoint returns valid JSON
- ✅ Zone state updates reflect YOLO detections
- ✅ Both services (api + worker) running without errors
- ✅ Database contains detection records

---

## Day 2: Admin UI + Offline Alerting + External API (8–10 hours)

### Objective
Add user-facing features: zone editor (UI), health page (ONLINE/STALE/OFFLINE), offline alerts (Telegram), external API key auth.

### Starting Point
- ✅ Core inference pipeline working
- ✅ API returning zone status JSON
- ✅ YOLO processing snapshots

### Build Tasks

#### Task 2.1: Camera Health Monitoring (2 hours)

**Implement server-side heartbeat rules:**

```python
# In API service, add background task:
from threading import Thread
from datetime import datetime, timedelta

def monitor_camera_health():
    """
    Check every 30 seconds if cameras are offline.
    STALE: no snapshot in 150 seconds
    OFFLINE: no snapshot in 300 seconds
    """
    while True:
        cameras = Camera.query.all()
        
        for camera in cameras:
            now = datetime.utcnow()
            last_seen = camera.last_seen_at
            
            if last_seen is None:
                continue
            
            age_seconds = (now - last_seen).total_seconds()
            
            if age_seconds > 300:
                # OFFLINE
                if camera.status != 'OFFLINE':
                    trigger_alert(camera, 'OFFLINE', f'No snapshot for {age_seconds}s')
                    camera.status = 'OFFLINE'
            elif age_seconds > 150:
                # STALE
                if camera.status != 'STALE':
                    trigger_alert(camera, 'STALE', f'No snapshot for {age_seconds}s')
                    camera.status = 'STALE'
            else:
                # ONLINE
                if camera.status != 'ONLINE':
                    trigger_alert(camera, 'ONLINE', 'Camera back online')
                    camera.status = 'ONLINE'
            
            db.session.commit()
        
        time.sleep(30)

# Start in background
Thread(target=monitor_camera_health, daemon=True).start()
```

#### Task 2.2: Telegram Alerts (1.5 hours)

**Get Telegram token:**
1. Open Telegram → @BotFather
2. /newbot → follow prompts → get token
3. Send message to your bot → get chat_id from `/getUpdates`

**Implement alert sender:**
```python
import requests

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def trigger_alert(camera, status, message):
    text = f"🚨 Camera {camera.camera_id} {status}: {message}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text
    })
    
    # Log event to DB
    CameraHealthEvent.create(
        camera_id=camera.id,
        health_status=status,
        message=message
    )
```

#### Task 2.3: Admin Camera Page (1.5 hours)

**Create simple HTML admin interface:**

```html
<!-- services/api/templates/admin_cameras.html -->
<html>
<head><title>CamPark Admin - Cameras</title></head>
<body>
<h1>Cameras</h1>

<button onclick="showAddCameraForm()">+ Add Camera</button>

<table>
  <thead>
    <tr><th>ID</th><th>Name</th><th>Status</th><th>Last Seen</th><th>Actions</th></tr>
  </thead>
  <tbody id="camera-list"></tbody>
</table>

<script>
async function fetchCameras() {
  const resp = await fetch('/admin/cameras');
  const cameras = await resp.json();
  const tbody = document.getElementById('camera-list');
  
  cameras.forEach(cam => {
    const row = `
      <tr>
        <td>${cam.camera_id}</td>
        <td>${cam.name}</td>
        <td><span class="status-${cam.status}">${cam.status}</span></td>
        <td>${cam.last_seen_at || 'Never'}</td>
        <td><button onclick="editCamera(${cam.id})">Edit</button></td>
      </tr>
    `;
    tbody.innerHTML += row;
  });
}

fetchCameras();
</script>
</body>
</html>
```

**Add Flask routes:**
```python
@app.route('/admin/cameras', methods=['GET'])
def list_cameras():
    cameras = Camera.query.all()
    return jsonify([
        {
            'id': c.id,
            'camera_id': c.camera_id,
            'name': c.name,
            'status': c.status,
            'last_seen_at': c.last_seen_at
        }
        for c in cameras
    ])

@app.route('/admin/cameras', methods=['POST'])
def add_camera():
    data = request.json
    camera = Camera.create(
        site_id=data['site_id'],
        camera_id=data['camera_id'],
        name=data['name'],
        ftp_username=data['ftp_username']
    )
    # Generate new FTP user if needed
    os.system(f"sudo useradd -m -s /bin/false {camera.ftp_username}")
    return jsonify(camera.to_dict()), 201
```

#### Task 2.4: Zone Editor UI (2–3 hours)

**Simple HTML canvas zone drawing:**

```html
<!-- services/api/templates/zone_editor.html -->
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
  <style>
    canvas { border: 1px solid #ccc; }
  </style>
</head>
<body>
<h1>Zone Editor - Camera CAM001</h1>

<canvas id="canvas" width="800" height="600"></canvas>

<button onclick="startDrawing()">Draw Zone</button>
<button onclick="saveZone()">Save Zone</button>
<button onclick="clearCanvas()">Clear</button>

<script>
const canvas = new fabric.Canvas('canvas');

// Load last snapshot as background
fetch('/api/v1/cameras/1/snapshot-latest')
  .then(r => r.blob())
  .then(blob => {
    const url = URL.createObjectURL(blob);
    fabric.Image.fromURL(url, (img) => {
      canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas));
    });
  });

let isDrawing = false;
let points = [];

function startDrawing() {
  isDrawing = true;
  points = [];
  canvas.forEachObject(obj => canvas.remove(obj));
  canvas.on('mouse:down', (e) => {
    const pos = canvas.getPointer(e.e);
    points.push([pos.x / 800 * 100, pos.y / 600 * 100]); // normalize to 0-100
    
    const dot = new fabric.Circle({
      left: pos.x - 5,
      top: pos.y - 5,
      radius: 5,
      fill: 'red'
    });
    canvas.add(dot);
    
    if (points.length > 1) {
      const prev = points[points.length - 2];
      const line = new fabric.Line(
        [prev[0] * 8, prev[1] * 6, pos.x, pos.y],
        { stroke: 'blue', strokeWidth: 2 }
      );
      canvas.add(line);
    }
  });
}

function saveZone() {
  isDrawing = false;
  canvas.off('mouse:down');
  
  fetch('/admin/zones', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      camera_id: 1,
      zone_id: 'ZONE_A01',
      name: 'Parking Zone A',
      polygon_json: JSON.stringify(points),
      capacity_units: document.getElementById('capacity').value
    })
  }).then(() => alert('Zone saved!'));
}
</script>

Capacity: <input type="number" id="capacity" value="1">
</body>
</html>
```

#### Task 2.5: External API Key + Read-Only Enforcement (1.5 hours)

**Add API key generation:**

```python
import secrets
import hashlib

@app.route('/admin/api-keys/generate', methods=['POST'])
def generate_api_key():
    data = request.json
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    client = APIClient.create(
        name=data['name'],
        api_key_hash=key_hash,
        site_ids=json.dumps(data.get('site_ids', [])),
        scope='read:status,read:events'  # read-only
    )
    
    return jsonify({
        'api_key': raw_key,
        'warning': 'Save this key safely. You cannot view it again.'
    })

# Middleware to enforce read-only
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if not key:
            return {'error': 'Missing X-API-Key'}, 401
        
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        client = APIClient.query.filter_by(api_key_hash=key_hash).first()
        
        if not client:
            return {'error': 'Invalid X-API-Key'}, 401
        
        # Only allow GET requests (read-only)
        if request.method != 'GET':
            return {'error': 'Unauthorized: read-only key'}, 403
        
        g.api_client = client
        return f(*args, **kwargs)
    
    return decorated

@app.route('/api/v1/sites/<int:site_id>/status', methods=['GET'])
@require_api_key
def get_site_status(site_id):
    # ... existing code
```

#### Task 2.6: Health Page UI (1 hour)

```html
<!-- services/api/templates/health.html -->
<html>
<head><title>CamPark Health</title></head>
<body>
<h1>System Health</h1>

<h2>Cameras</h2>
<table>
  <thead><tr><th>Camera</th><th>Status</th><th>Last Seen</th><th>Age (s)</th></tr></thead>
  <tbody id="cameras"></tbody>
</table>

<script>
async function updateHealth() {
  const resp = await fetch('/admin/health');
  const data = await resp.json();
  
  const tbody = document.getElementById('cameras');
  tbody.innerHTML = data.cameras.map(c => `
    <tr>
      <td>${c.camera_id}</td>
      <td><span class="status-${c.status}">${c.status}</span></td>
      <td>${c.last_seen_at}</td>
      <td>${c.age_seconds}</td>
    </tr>
  `).join('');
}

updateHealth();
setInterval(updateHealth, 30000); // Refresh every 30s
</script>

</body>
</html>
```

### Integration Test (2 hours)

```bash
# 1. Verify camera health monitoring
curl http://localhost:8000/admin/health | jq '.cameras[0]'
# Should show status: "ONLINE"

# 2. Test offline detection (manual)
# Stop camera (unplug or turn off power)
# Wait 150 seconds
# Should receive Telegram alert: "Camera CAM001 STALE"
# Wait another 150 seconds
# Should receive another alert: "Camera CAM001 OFFLINE"

# 3. Test API key auth
API_KEY=$(curl -X POST http://localhost:8000/admin/api-keys/generate \
  -H "Content-Type: application/json" \
  -d '{"name": "dashboard"}' | jq -r '.api_key')

curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/sites/1/status | jq

# 4. Test read-only enforcement
curl -X POST -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/sites/1 \
  -d '{"occupied": 5}' 2>&1 | grep "read-only"
```

### Proof for Boss (End of Day 2)

**Live demo:**

1. **Add a new camera (no code):**
   - Open http://localhost:8000/admin/cameras
   - Click "+ Add Camera"
   - Enter name, FTP username
   - Click Save
   - Show: System auto-generates FTP user without touching terminal

2. **Edit zones visually:**
   - Open http://localhost:8000/admin/zones/1
   - Draw polygon on snapshot
   - Save
   - Show DB updated

3. **Watch offline alerts:**
   - Stop camera (turn off power)
   - Wait ~150 seconds
   - Show: Telegram alert "Camera CAM001 STALE"
   - Wait ~150 more seconds
   - Show: Telegram alert "Camera CAM001 OFFLINE"

4. **External dashboard integration:**
   - Generate API key: `curl -X POST http://localhost:8000/admin/api-keys/generate`
   - Show key generated
   - Use key to fetch data: `curl -H "X-API-Key: ..." http://localhost:8000/api/v1/sites/1/status`
   - Show JSON response
   - Emphasize: **External dashboard has read-only access** (cannot modify)

**Talking Points:**
- ✅ "No code changes needed to add new camera"
- ✅ "Zone editor lets operations teams draw ROI themselves"
- ✅ "System detects offline cameras in 2.5 minutes (150s stale)"
- ✅ "Telegram alerts notify team immediately"
- ✅ "External dashboard gets secure read-only JSON API"
- ✅ "Everything runs in Docker with 99% uptime target"

**Success Criteria:**
- ✅ Admin UI operational (cameras, zones, health pages)
- ✅ Offline alerts triggering reliably (STALE at 150s, OFFLINE at 300s)
- ✅ API key auth enforced (read-only)
- ✅ Zone editor saving to DB correctly
- ✅ All services healthy in docker-compose

---

## Summary: What You'll Show Your Boss

| Feature | Day 1 | Day 2 | Status |
|---------|-------|-------|--------|
| Camera uploads FTP | ✅ Gate | - | **Proven** |
| YOLO inference | ✅ Working | ✅ | **Live** |
| Zone occupancy API | ✅ JSON | ✅ | **Live** |
| Admin camera list | - | ✅ | **Live** |
| Zone editor UI | - | ✅ | **Live** |
| Health page | - | ✅ | **Live** |
| Offline detection | - | ✅ alerting | **Live** |
| External API key | - | ✅ read-only | **Live** |
| Telegram alerts | - | ✅ | **Live** |

---

## Deployment Readiness (After POC)

Once POC is done, you have:

- [ ] Docker Compose setup (single VM deploy)
- [ ] Database schema + migrations
- [ ] Core inference pipeline
- [ ] Admin + API services
- [ ] Offline alerting framework

**Next steps for pilot:**
1. Add multi-camera support (POC was single camera hardcoded)
2. Add multi-site support (POC was single site)
3. Setup TLS + nginx (POC: Flask direct)
4. Add monitoring + Prometheus
5. Setup nightly backups + recovery test
6. Rate limiting + API quotas
7. Production secrets management

---

## Timeline & Resource

| Phase | Duration | Owner | Status |
|-------|----------|-------|--------|
| Day 0 Gate | 3–4 hours | You | Pre-flight |
| Day 1 Build | 6–8 hours | You (or team) | Core logic |
| Day 2 Build | 8–10 hours | You (or team) | UX + features |
| **Total POC Time** | **17–22 hours** | - | **Achievable in 2 days** |

**Realistic timeline:** ~3 days if including breaks and debugging.

---

**Document Version:** POC v0.2  
**Last Updated:** Feb 5, 2026  
**Ready:** Yes, gate check first
