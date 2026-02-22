# CamPark — Security & Readiness Audit Report

**Date:** 2026-02-22  
**Scope:** Full codebase audit — API, Worker, DB schema, YOLO pipeline, Zone Editor, Docker deployment  
**Status:** Fixes applied. Remaining improvements listed below.

---

## 1. VULNERABILITIES FOUND & FIXED

### 1.1 [CRITICAL] Open Redirect on Login
**File:** `services/api/main.py` — `/login` POST handler  
**Was:** `next_url = request.args.get("next", "/admin/scada")` → redirected to any URL  
**Risk:** Attacker could craft `https://yoursite/login?next=https://evil.com` — after login, user is sent to attacker-controlled page.  
**Fix applied:** Added `_safe_next_url()` that rejects any URL with a scheme, netloc, or `//` prefix. Only relative `/admin/*` paths are accepted.

### 1.2 [CRITICAL] Path Traversal via `send_file()`
**File:** `services/api/main.py` — `/api/v1/evidence/<id>` and `/api/v1/cameras/<id>/snapshot-latest`  
**Was:** `abs_path = os.path.join(IMAGE_ROOT, snapshot.file_path)` — if `file_path` contained `../../etc/passwd`, it would serve arbitrary files from the container.  
**Risk:** Arbitrary file read from the API container filesystem.  
**Fix applied:** Added `_safe_image_path()` that normalizes, resolves symlinks, and validates the final path stays within `IMAGE_ROOT` using `os.path.commonpath()`.

### 1.3 [HIGH] FTP Password Exposed in API Response
**File:** `services/api/main.py` — `/admin/cameras-detail.json`  
**Was:** `"ftp_password": cam.ftp_password_hash` — returned plaintext FTP password in JSON.  
**Risk:** Any admin-session holder could exfiltrate all camera FTP credentials via browser devtools.  
**Fix applied:** Replaced with `"ftp_password_set": bool(cam.ftp_password_hash)` — boolean only, no credential leak.

### 1.4 [HIGH] Zone Editor Data Loss — INNER JOIN Dropped Zones
**File:** `services/api/main.py` — `/admin/zones.json`  
**Was:** `session.query(Zone, ZoneState, Camera).join(ZoneState, ...)` — INNER JOIN silently dropped zones that had no ZoneState row yet (race condition on fresh zones).  
**Risk:** Dashboard and YOLO worker would silently miss newly-created zones until first occupancy event.  
**Fix applied:** Changed to `.outerjoin(ZoneState, ...)` with `None`-safe access on `zs` fields.

### 1.5 [HIGH] Zone Editor Couldn't Reload — Wrong Endpoint
**File:** `services/api/templates/zone_editor.html`  
**Was:** Editor loaded zones from `/admin/zones.json` which filters out `__campark_meta__` sentinels, breaking round-trip reload of lane shapes.  
**Fix applied:** Editor now fetches from `/admin/zones/editor-raw.json` (new endpoint) which returns ALL rows including meta sentinels.

### 1.6 [MEDIUM] `zones.name` Column Too Small for Meta Blobs
**Files:** `services/config/init.sql`, `services/api/app/db.py`, `services/worker/db.py`  
**Was:** `name VARCHAR(255)` — `__campark_meta__` JSON blobs can easily exceed 255 chars.  
**Fix applied:** Schema uses `TEXT`, both ORM models use `mapped_column(Text, ...)`.  
**Migration file:** `update/migrate_001_zones_name_text.sql` — run on existing DBs: `ALTER TABLE zones ALTER COLUMN name TYPE TEXT;`

### 1.7 [MEDIUM] Parent Lane Could Be Dragged After Split
**File:** `services/api/templates/zone_editor.html`  
**Was:** `hitTest()` returned `'move'` for split lanes, allowing accidental whole-lane drag.  
**Fix applied:** `hitTest()` now suppresses `'move'` for lanes where `cols > 0 && rows > 0`. Only corner + divider handles are active. Corner hit radius increased from 14px → 18px for usability.

---

## 2. VULNERABILITIES STILL PRESENT (Require Action)

### 2.1 [CRITICAL] Hardcoded Default Secrets in Production `.env`
**File:** `.env`  
```
POSTGRES_PASSWORD=changeme_poc
ADMIN_PASSWORD=changeme_poc
SECRET_KEY=change-this-to-random-32-character-string
API_KEY=your-secure-api-key-here
```
**Risk:** Bots scan for default credentials continuously. Anyone who finds port 8000 or 443 can log in as admin.  
**Action required:**
```bash
# Generate strong values:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Set each in .env, then restart: docker compose up -d --build
```

### 2.2 [HIGH] FTP Passwords Stored as Plaintext
**File:** `cameras.ftp_password_hash` column — name says "hash" but stores **plaintext** passwords.  
**Context:** Required by pure-ftpd's virtual user system which needs plaintext.  
**Risk:** DB breach exposes all FTP credentials.  
**Mitigation options:**
- Encrypt with a symmetric key (AES-256) stored in env var, decrypt only when writing `.ftp_users.json`
- Or accept the risk with strong DB access controls and encrypted backups

### 2.3 [HIGH] No CSRF Protection on Admin POST Routes
**File:** `services/api/main.py` — all `/admin/*` POST endpoints  
**Risk:** Attacker can craft a page that submits `POST /admin/cameras` or `POST /admin/zones/delete-all` using the admin's session cookie.  
**Fix:** Add `flask-wtf` CSRFProtect or a manual CSRF token pattern:
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

### 2.4 [HIGH] No Rate Limiting on Login
**File:** `services/api/main.py` — `POST /login`  
**Risk:** Unlimited brute-force attempts on admin credentials.  
**Fix:** Add `flask-limiter`:
```python
from flask_limiter import Limiter
limiter = Limiter(app, default_limits=["5/minute"])
@limiter.limit("5/minute")
@app.route("/login", methods=["POST"])
```

### 2.5 [MEDIUM] Health Monitor Thread Has No Error Recovery
**File:** `services/api/main.py` — `monitor_camera_health()`  
**Risk:** Unhandled exception in the loop kills the thread silently; health monitoring stops forever.  
**Fix:** Wrap the inner loop body in `try/except` with logging (it already has try/finally for session close, but an uncaught exception in commit could kill the thread).

### 2.6 [MEDIUM] No Session Timeout / Rotation
**Session lifetime:** 12 hours, no rotation on auth.  
**Risk:** Stolen session cookie is valid for 12 hours.  
**Fix:** Regenerate session ID on login, reduce lifetime in production, add IP binding.

### 2.7 [LOW] Telegram Token Suffix Exposed in `/admin/system/config.json`
```python
"telegram_token_suffix": TELEGRAM_BOT_TOKEN[-6:]
```
**Risk:** Low, but unnecessary information disclosure. Replace with `"telegram_configured": True/False`.

### 2.8 [LOW] No Content Security Policy Headers
**Risk:** XSS attacks via injected scripts.  
**Fix:** Add CSP headers in Caddy or Flask:
```python
@app.after_request
def security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' 'unsafe-inline'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
```

---

## 3. DATABASE HEALTH CHECK

| Check | Status | Notes |
|-------|--------|-------|
| `zones.name` column type | ✅ `TEXT` | init.sql + both ORM models aligned |
| `system_settings` seeded | ✅ | operating_hours_start/end, scene_diff_threshold |
| Indexes present | ✅ | All important query paths indexed |
| ORM model parity (api ↔ worker) | ✅ | Both `db.py` files are now in sync |
| Foreign key cascades | ✅ | `ON DELETE CASCADE` on all child tables |
| Migration needed on live DB | ⚠️ | Run `migrate_001_zones_name_text.sql` if DB was created before this update |

---

## 4. YOLO WORKER READINESS

| Check | Status | Notes |
|-------|--------|-------|
| YOLO_ENABLED | ✅ `true` in docker-compose.yml | Worker will run inference |
| YOLO_MODEL | ✅ `yolov8n.pt` | Auto-downloads on first run, ~6MB |
| YOLO_CONFIDENCE | ✅ `0.50` | Reasonable for parking POC |
| OVERLAP_THRESHOLD | ✅ `0.30` | 30% bbox-zone overlap required |
| Valid classes | ✅ car, truck, motorcycle, bicycle | Hardcoded in pipeline.py |
| Perceptual diff gate | ✅ threshold=6.0 | Skips static frames to save CPU |
| Operating hours gate | ✅ Reads from DB each cycle | No restart needed for changes |
| Meta zone filter | ✅ `__campark_meta__` zones skipped | Won't count parent outlines |
| 2-frame debounce | ✅ `pending_states` dict | Prevents flapping on single-frame noise |
| File stability check | ✅ 200ms delay + size compare | Prevents reading partial FTP uploads |
| SHA-256 dedup | ✅ | Same image won't be processed twice |
| Quarantine for corrupt files | ✅ | Bad images moved to `.quarantine/` |
| `ultralytics` version | ⚠️ `8.0.110` | Consider updating — current stable is 8.3.x, has performance fixes |
| `Pillow` version | ⚠️ `10.0.0` | Update to 10.4+ for security patches |
| `onnxruntime` version | ⚠️ `1.17.3` | Update to 1.19+ if using ONNX zone classifier |

---

## 5. ZONE EDITOR READINESS

| Check | Status | Notes |
|-------|--------|-------|
| Round-trip meta persistence | ✅ | Saves `__campark_meta__` in first child zone name |
| Editor loads from `editor-raw.json` | ✅ | Gets all zones including meta sentinels |
| Dashboard loads from `zones.json` | ✅ | Filters out meta sentinels |
| Corner warp handles | ✅ | 18px hit radius, white dots rendered |
| Parent move blocked after split | ✅ | hitTest suppresses 'move' for split lanes |
| Divider drag | ✅ | Shared edges, adjacent children adjust automatically |
| Convexity validation | ✅ | `G.isConvex()` called before accepting quad |

---

## 6. DOCKER / DEPLOYMENT CHECK

| Check | Status | Notes |
|-------|--------|-------|
| Caddy TLS | ✅ | Reverse proxy with auto-HTTPS |
| PostgreSQL health check | ✅ | `pg_isready` with dependency in compose |
| Redis | ⚠️ | Running but unused (`REDIS_USE_DB_FALLBACK=true`) — remove to save RAM |
| Ingestion service | ℹ️ | Commented out (correct for FTP-only cameras) |
| Container restart policy | ⚠️ | Only caddy has `restart: unless-stopped` — add to all services |
| Log rotation | ❌ | No Docker log rotation configured — disk fills over time |
| Backups | ❌ | No automated PostgreSQL backup configured |
| `.env` in git | ❌ | `.env` should be in `.gitignore` (contains secrets) |

---

## 7. PRIORITY ACTION LIST

| # | Priority | Task | Effort |
|---|----------|------|--------|
| 1 | 🔴 CRITICAL | Change all default passwords in `.env` and restart | 5 min |
| 2 | 🔴 CRITICAL | Add `.env` to `.gitignore` before pushing to any repo | 1 min |
| 3 | 🟠 HIGH | Add CSRF protection (`flask-wtf`) | 30 min |
| 4 | 🟠 HIGH | Add login rate limiting (`flask-limiter`) | 15 min |
| 5 | 🟠 HIGH | Run `migrate_001_zones_name_text.sql` on live DB | 1 min |
| 6 | 🟡 MEDIUM | Add `restart: unless-stopped` to all compose services | 2 min |
| 7 | 🟡 MEDIUM | Add Docker log rotation (`max-size: 10m, max-file: 3`) | 5 min |
| 8 | 🟡 MEDIUM | Wrap health monitor loop in inner try/except | 5 min |
| 9 | 🟡 MEDIUM | Add security headers (CSP, X-Frame-Options) | 10 min |
| 10 | 🟢 LOW | Update `ultralytics`, `Pillow`, `onnxruntime` versions | 10 min |
| 11 | 🟢 LOW | Set up automated PostgreSQL backups (pg_dump cron) | 20 min |
| 12 | 🟢 LOW | Remove unused Redis service | 2 min |

---

## 8. FILES CHANGED IN THIS UPDATE

| File | Change |
|------|--------|
| `services/api/main.py` | Added `_safe_next_url()`, `_safe_image_path()`, `editor-raw.json` endpoint, outerjoin fix, FTP password redaction |
| `services/api/app/db.py` | `Zone.name` → `Text` type |
| `services/worker/db.py` | `Zone.name` → `Text` type (sync with api) |
| `services/config/init.sql` | `zones.name` → `TEXT` |
| `services/api/templates/zone_editor.html` | `HIT_CORNER=18`, loads from `editor-raw.json`, move-after-split blocked |
| `update/migrate_001_zones_name_text.sql` | Run-once migration for existing databases |
| `AUDIT_REPORT.md` | This file |
