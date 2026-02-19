# ✅ FTP Server Ready for Camera Connection

**Status**: FIXED - Firewall updated to allow correct passive ports  
**Date**: 2026-02-05 17:06  
**Issue Resolved**: Passive port mismatch

---

## 🎯 What Was Fixed

### Problem Identified
- FTP server was using passive ports **21000-21010**
- Windows Firewall was only allowing ports **30000-30009**
- Camera's passive FTP connections were being blocked

### Solution Applied
✅ Updated Windows Firewall rule to allow ports **21, 21000-21010**

```powershell
# Firewall rule updated successfully
DisplayName: CamPark FTP
Status: Enabled
Direction: Inbound
Action: Allow
Ports: 21, 21000-21010 ✅
```

---

## 📋 Camera Configuration Instructions

### Step 1: Find Your Camera IP

**Option A: Check Router**
1. Open browser: `http://192.168.1.1` (or your router IP)
2. Login to router admin
3. Look for **DHCP Clients** or **Connected Devices**
4. Find device named "Dahua" or "IPC-HFW7442H"
5. Note the IP address (e.g., `192.168.1.50`)

**Option B: Use Network Scanner**
```powershell
# Scan your network for devices
arp -a | findstr "192.168.1"
```

**Option C: Download Dahua ConfigTool**
- Search for "Dahua ConfigTool" or "Dahua IP Scanner"
- Download from official Dahua website
- Run tool to discover camera on your network

---

### Step 2: Access Camera Web Interface

1. Open browser and navigate to: `http://<camera-ip>`
   - Example: `http://192.168.1.50`

2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin` (or check camera label/manual)

3. ⚠️ **IMPORTANT**: Change the default password immediately!

---

### Step 3: Configure FTP Settings

Navigate to: **Settings → Network → FTP** (or similar path)

Enter these exact values:

| Setting | Value | Critical? |
|---------|-------|-----------|
| **Enable FTP** | ✅ Checked | YES |
| **Server Address** | `192.168.1.111` | YES |
| **Port** | `21` | YES |
| **Username** | `cam001` | YES |
| **Password** | `password123` | YES |
| **Remote Directory** | `incoming` | YES |
| **Passive Mode** | ✅ **ENABLED** | **CRITICAL** |
| **Anonymous Login** | ❌ Disabled | YES |

⚠️ **CRITICAL**: Make sure **Passive Mode** is ENABLED! Without this, the connection will fail.

---

### Step 4: Test FTP Connection

1. In the camera web UI, find the **"Test"** button (usually next to FTP settings)
2. Click **"Test"**
3. Wait 5-10 seconds

**Expected Result**: 
- ✅ "Connection Successful" or "Test Passed"
- ✅ "Upload Successful"

**If test fails**, see troubleshooting section below.

---

### Step 5: Configure Motion Detection Upload

Navigate to: **Settings → Event → Motion Detection**

1. **Enable Motion Detection**: ✅ Checked
2. **Sensitivity**: Set to `50-70%` (adjust based on your environment)
3. **Upload to FTP on Motion**: ✅ Checked
4. **Snapshot Type**: JPEG
5. **Upload Interval**: Immediate (or minimum delay)

---

### Step 6: Configure Heartbeat (Recommended)

Navigate to: **Settings → Network → FTP → Scheduled Upload** (or similar)

1. **Enable Scheduled Upload**: ✅ Checked
2. **Interval**: `120` seconds (2 minutes)
3. **Upload Path**: `incoming`

This ensures regular snapshots even when there's no motion, helping you verify the connection is working.

---

## 🧪 Verify Connection is Working

### Monitor FTP Server Logs

Open PowerShell and run:

```powershell
# Watch FTP server logs in real-time
docker logs -f campark-ftp
```

**What to look for:**
- When camera connects, you should see:
```
Thu Feb  5 17:15:23 2026 [pid 123] CONNECT: Client "192.168.1.50"
Thu Feb  5 17:15:23 2026 [pid 122] [cam001] OK LOGIN: Client "192.168.1.50"
Thu Feb  5 17:15:24 2026 [pid 122] [cam001] OK UPLOAD: Client "192.168.1.50"
```

Replace `192.168.1.50` with your actual camera IP.

---

### Check Uploaded Files

```powershell
# List files uploaded by camera
docker exec campark-ftp ls -la /1000/incoming/

# Or use this to watch for new files
docker exec campark-ftp watch -n 2 'ls -la /1000/incoming/ | tail -10'
```

**Expected output:**
```
-rw-r--r-- cam001 cam001  85432 Feb 05 17:15:15 snapshot_001.jpg
-rw-r--r-- cam001 cam001  87654 Feb 05 17:17:15 snapshot_002.jpg
-rw-r--r-- cam001 cam001  89012 Feb 05 17:19:15 snapshot_003.jpg
```

---

### Run Monitor Script

```powershell
# Start the monitoring script
python tests/monitor_real_connection.py
```

This will show real-time notifications when new files are uploaded.

---

## 🔧 Troubleshooting

### Camera Test Button Shows "Connection Failed"

**Check 1: Network Connectivity**
```powershell
# Ping camera from your PC
ping <camera-ip>

# Test FTP port
Test-NetConnection -ComputerName 192.168.1.111 -Port 21
```

**Check 2: FTP Server Running**
```powershell
docker ps | findstr campark-ftp
# Should show: Up X minutes
```

**Check 3: Firewall**
```powershell
Get-NetFirewallRule -DisplayName "CamPark FTP"
# Should show: Enabled = True
```

**Check 4: Passive Mode**
- Go back to camera FTP settings
- Make absolutely sure "Passive Mode" is checked
- Save settings and test again

---

### Camera Test Succeeds but No Files Appear

**Check 1: Motion Detection Enabled**
- Verify motion detection is turned on
- Try waving your hand in front of camera
- Check sensitivity isn't too low

**Check 2: Remote Directory Name**
- Make sure it's exactly: `incoming` (lowercase, no slashes)
- Not: `/incoming` or `Incoming` or `/incoming/`

**Check 3: Camera Logs**
- Access camera web UI
- Go to **Maintenance → System Log**
- Look for FTP-related errors

---

### Files Upload but Are Corrupted

**Check 1: Verify File Format**
```powershell
docker exec campark-ftp file /1000/incoming/*.jpg
# Should show: JPEG image data
```

**Check 2: Camera Image Quality**
- Go to **Settings → Camera → Image**
- Set quality to "High" or "Best"
- Ensure resolution matches camera specs

---

## 📊 Current System Status

### ✅ FTP Server
```
Container: campark-ftp
Status: Running
Image: delfer/alpine-ftp-server
Uptime: ~1 hour
```

### ✅ Network Configuration
```
Server IP: 192.168.1.111 (Primary LAN)
FTP Port: 21
Passive Ports: 21000-21010
```

### ✅ Firewall
```
Rule: CamPark FTP
Status: Enabled
Ports: 21, 21000-21010
Direction: Inbound
Action: Allow
```

### ✅ FTP User Account
```
Username: cam001
Password: password123
Home: /1000/
Upload Dir: /1000/incoming/
```

---

## 🎬 Quick Start Checklist

Before configuring camera:
- [x] FTP server running
- [x] Firewall configured
- [x] Passive ports open
- [x] Test upload successful
- [ ] Camera IP address identified
- [ ] Camera web UI accessible
- [ ] FTP settings configured in camera
- [ ] Test button clicked successfully
- [ ] Files appearing in `/1000/incoming/`

---

## 📞 Next Steps

1. **Find your camera's IP address** (see Step 1 above)
2. **Access camera web interface** (see Step 2 above)
3. **Configure FTP settings** (see Step 3 above)
4. **Click Test button** (see Step 4 above)
5. **Monitor logs** to verify connection:
   ```powershell
   docker logs -f campark-ftp
   ```

---

## 🚀 After Camera is Connected

Once you see files uploading successfully:

1. **Start the full CamPark stack**:
   ```powershell
   docker-compose up -d
   ```

2. **Access the admin UI**:
   - Open browser: `http://localhost:8000`
   - Login: `admin` / `changeme_poc`

3. **Monitor YOLO processing**:
   ```powershell
   docker logs -f campark-worker
   ```

---

## 📚 Related Documentation

- **FTP Diagnosis**: `FTP_DIAGNOSIS.md` (detailed technical analysis)
- **Test Summary**: `FTP_TEST_SUMMARY.md` (previous test results)
- **Camera Config Guide**: `CAMERA_CONFIG_DAHUA.md` (detailed Dahua setup)
- **Real Camera Test**: `REAL_CAMERA_TEST_GUIDE.md` (comprehensive testing guide)

---

**Your FTP server is now ready! Configure your camera and start testing.** 🎥✨
