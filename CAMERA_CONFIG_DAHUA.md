# Dahua DH-IPC-HFW7442H-Z4FR FTP Configuration Guide

## Quick Reference

- **Model:** DH-IPC-HFW7442H-Z4FR (4MP turret, 2.7–13.5mm zoom, IR)
- **Default Credentials:** admin / admin
- **Default IP:** Check DHCP or use Dahua IP Scanner tool
- **Access URL:** `http://<camera-ip>`

---

## Step 1: Find Camera IP

### Option A: Router DHCP List
1. Log into your router (usually `192.168.1.1`)
2. Go to **DHCP Clients** or **Connected Devices**
3. Look for device named "Dahua" or "IPC-HFW7442H"
4. Note the IP address (e.g., `192.168.1.50`)

### Option B: ARP Scan
```bash
# Linux
arp-scan -l | grep -i dahua

# or
nmap -sn 192.168.1.0/24 | grep -i dahua

# or with curl
curl -s http://192.168.1.1/api/devices | jq '.[] | select(.name | contains("Dahua"))'
```

### Option C: Dahua Discovery Tool (Windows/Mac)
- Download from Dahua website: **IP Scanner Tool**
- Scan your LAN, find device, double-click to open web UI

---

## Step 2: Access Camera Web UI

1. Open browser: `http://<camera-ip>`
2. **WARNING:** If prompted about SSL certificate, click **Proceed** (self-signed is normal)
3. Login: **admin** / **admin**
4. **Immediately change password** (right panel → Change Password)

---

## Step 3: Configure FTP Upload

### Path: Settings → Network → Advanced → FTP

| Field | Value | Notes |
|-------|-------|-------|
| **Enable FTP** | ✓ Check | Required |
| **Server Address** | `192.168.1.100` (your machine IP) | Use hostname or IP reachable from camera |
| **Port** | `21` | Standard FTP port |
| **Username** | `cam001` | Created via `useradd cam001` |
| **Password** | `password123` | Must match system user password |
| **Remote Directory** | `incoming` | Path on FTP server (relative to user root `/data/ftp/cam001/`) |
| **Passive Mode** | ✓ Check | **CRITICAL** for 4G/unstable networks |
| **Max Upload Attempts** | `3` | Retry on connection fail |

### Test Connection
Click **Test** button
- ✅ **Success:** "Connection successful"
- ❌ **Fail:** Check network connectivity, firewall, FTP running

**If test fails, check:**
```bash
# On your machine
systemctl status vsftpd
# Should show "active (running)"

# Check FTP user exists
cat /etc/passwd | grep cam001

# Verify permissions
ls -la /data/ftp/cam001/
# Should be writable by cam001

# Test FTP manually
ftp -n << EOF
open 192.168.1.100
user cam001 password123
ls
quit
EOF
```

---

## Step 4: Configure Motion-Triggered Upload

### Path: Settings → Event → Motion Detection

1. **Enable Motion Detection** ✓
2. Adjust sensitivity slider (try 50–70% for parking lot)
3. Draw motion regions (optional, for ROI on camera side)

### Path: Settings → Event → Behavior Analysis (optional)
- **Vehicle Detection:** Enable (if available in firmware)
- **Upload on vehicle trigger:** ✓ Check

### FTP Upload Behavior
- When motion/vehicle detected: camera uploads 1 snapshot immediately
- Filename: `YYYY-MM-DD_HH-MM-SS.jpg` or similar (Dahua standard)

---

## Step 5: Configure Heartbeat (2-Minute Interval)

### Option A: Scheduled Upload (Preferred)

**Path: Settings → Network → Advanced → FTP → Scheduled Upload**

- **Enable Scheduled Upload** ✓
- **Interval:** `120` seconds (2 minutes)
- **FTP Upload Path:** `incoming`

### Option B: Snapshot Schedule (Alternative)

**Path: Settings → Network → Advanced → RTSP → Snapshot**

- **Enable Snapshot Server** ✓
- **Interval:** `120` seconds

Then configure CamPark worker to pull snapshots via RTSP GET request (fallback mechanism).

### Verify Heartbeat
After enabling, wait 2-3 minutes and check:
```bash
ls -latr /data/ftp/cam001/incoming/ | tail -5
# Should show new files every ~120 seconds
```

---

## Step 6: Adjust PDT (Pan/Tilt/Zoom) Settings

### ⚠️ CRITICAL: PT MUST BE LOCKED

**Path: Settings → Maintenance → Calibration**

1. Manually set desired **Pan** angle (left ← → right)
2. Manually set desired **Tilt** angle (down ↓ ↑ up)
3. Set **Zoom** to desired level (2.7x to 13.5x)
4. **Disable auto-track, auto-patrol, preset tours**

### Why?
- If camera auto-pans/tilts during vehicle detection, your ROI polygon becomes invalid
- Fixed frame ensures consistent zone overlap calculations

Check **Advanced Settings:**
- [ ] Auto-track: **Disabled**
- [ ] Patrol: **Disabled**
- [ ] PTZ presets/tours: **Disabled**
- [ ] Return to home on idle: **Disabled**

---

## Step 7: Verify File Uploads

From your machine, monitor incoming files:
```bash
watch -n 2 'ls -la /data/ftp/cam001/incoming/ | tail -10'
```

**Expected output (after motion or 2 min heartbeat):**
```
-rw-r--r-- cam001 cam001  85432 Feb 05 10:12:15 2026-02-05_10-12-15.jpg
-rw-r--r-- cam001 cam001  87654 Feb 05 10:14:15 2026-02-05_10-14-15.jpg
-rw-r--r-- cam001 cam001  89012 Feb 05 10:16:15 2026-02-05_10-16-15.jpg
```

**If no files appear:**
1. Check FTP test button result (should say "successful")
2. Verify remote directory name matches camera setting
3. Try uploading manually from camera: **Settings → Network → Test FTP**
4. **Last resort:** Enable DEBUG mode in camera settings, check system logs

---

## Step 8: Verify JPEG Quality

Ensure uploaded images are valid:
```bash
file /data/ftp/cam001/incoming/*.jpg
# Should all show "JPEG image data"

# Check image dimensions
identify /data/ftp/cam001/incoming/*.jpg | head -5
# Should show resolution (e.g., 4MP = 2688x1520)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| FTP test fails | Check firewall, ensure port 21 open, verify vsftpd running |
| No files appear | Enable motion detection, trigger manually, or wait for heartbeat |
| Files appear but corrupt | Check camera FTP setup, increase upload timeout |
| Camera locks up during upload | Enable FTP passive mode (critical!) |
| Network intermittent | Enable FTP retry (3 attempts), increase timeout to 30s |

---

## Your Camera FTP Config (Copy This for Reference)

```
Server Address: 192.168.1.100  (your local machine IP)
Port: 21
Username: cam001
Password: password123
Remote Directory: incoming
Passive Mode: ✓ ENABLED
Encode Type: JPEG (usually auto)
Upload Type: Incident + Scheduled (if available)
Scheduled Interval: 120 seconds
Motion Upload: ✓ ENABLED
Vehicle Upload: ✓ ENABLED (if available)
```

---

## Next: Run FTP Gate Test

Once configured, run:
```bash
bash /workspaces/CamPark/tests/ftp_test.sh
```

This validates your FTP setup before POC starts.
