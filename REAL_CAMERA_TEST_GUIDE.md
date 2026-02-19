# Real Camera Connection Test Guide

## ✅ Pre-Test Verification Complete

### System Status
- **FTP Server**: ✅ Running (Docker container `campark-ftp`)
- **Firewall**: ✅ Configured (Ports 21, 30000-30009 open)
- **Test Upload**: ✅ Successful (Python script verified)

### Your Network Configuration
Based on `ipconfig`, you have multiple network interfaces:

| Interface | IP Address | Use Case |
|-----------|------------|----------|
| **Primary LAN** | `192.168.1.111` | **Use this for camera** |
| VirtualBox | `192.168.56.1` | Virtual machines |
| VPN/Tailscale | `100.93.106.110` | Remote access |
| WSL | `172.26.128.1` | Windows Subsystem for Linux |

---

## 📋 Camera Configuration Steps

### Step 1: Find Your Camera's IP Address

**Option A: Check Router**
1. Access your router admin panel (usually `http://192.168.1.1`)
2. Look for DHCP clients or connected devices
3. Find device named "Dahua" or similar
4. Note the IP address (e.g., `192.168.1.50`)

**Option B: Use Network Scanner**
```powershell
# Install if needed
choco install nmap

# Scan your network
nmap -sn 192.168.1.0/24
```

**Option C: Download Dahua ConfigTool**
- Visit: https://dahuawiki.com/Software/Tools
- Download "ConfigTool" or "IP Scanner"
- Scan your LAN to find the camera

---

### Step 2: Access Camera Web Interface

1. Open browser: `http://<camera-ip>`
2. Login with default credentials:
   - Username: `admin`
   - Password: `admin` (or check camera label)
3. **Change password immediately** for security

---

### Step 3: Configure FTP Settings

Navigate to: **Settings → Network → FTP**

| Setting | Value | Notes |
|---------|-------|-------|
| **Enable FTP** | ✅ Checked | Required |
| **Server Address** | `192.168.1.111` | **Your PC's LAN IP** |
| **Port** | `21` | Standard FTP port |
| **Username** | `cam001` | FTP user account |
| **Password** | `password123` | FTP password |
| **Remote Directory** | `incoming` | Upload folder |
| **Passive Mode** | ✅ **ENABLED** | Critical for NAT/firewall |
| **Anonymous** | ❌ Disabled | Use authentication |

---

### Step 4: Test FTP Connection

1. In camera web UI, click **"Test"** button next to FTP settings
2. Expected result: **"Connection Successful"** or similar message

**If test fails:**
- Verify camera can ping `192.168.1.111`
- Check Windows Firewall is allowing connections
- Ensure FTP server is running: `docker ps | findstr campark-ftp`

---

### Step 5: Configure Motion Detection Upload

Navigate to: **Settings → Event → Motion Detection**

1. **Enable Motion Detection**: ✅ Checked
2. **Sensitivity**: 50-70% (adjust based on environment)
3. **Upload to FTP on Motion**: ✅ Checked
4. **Snapshot Interval**: Immediate (on detection)

---

### Step 6: Configure Heartbeat (Optional but Recommended)

Navigate to: **Settings → Network → FTP → Scheduled Upload**

1. **Enable Scheduled Upload**: ✅ Checked
2. **Interval**: `120` seconds (2 minutes)
3. **Upload Path**: `incoming`

This ensures regular snapshots even without motion.

---

## 🧪 Testing the Connection

### Test 1: Manual Upload Test

After configuring FTP settings:
1. Click the **"Test"** button in camera FTP settings
2. Monitor for upload:

```powershell
# Run the monitor script
python tests/monitor_real_connection.py
```

You should see: `✅ NEW FILE RECEIVED!`

---

### Test 2: Motion Detection Test

1. Enable motion detection in camera settings
2. Wave your hand in front of the camera
3. Wait 5-10 seconds
4. Check the monitor script for new uploads

---

### Test 3: Verify Files on Disk

Check if files are actually being saved:

```powershell
# List files in FTP directory
docker exec campark-ftp ls -la /home/cam001/incoming/

# Or check from Windows (if volume is mounted)
dir data\ftp\cam001\incoming\
```

---

## 🔍 Troubleshooting

### Problem: Camera "Test" Button Fails

**Check 1: Network Connectivity**
```powershell
# Ping camera from PC
ping <camera-ip>

# Verify FTP port is accessible
Test-NetConnection -ComputerName 192.168.1.111 -Port 21
```

**Check 2: Firewall**
```powershell
# Verify firewall rule exists
Get-NetFirewallRule -DisplayName "CamPark FTP"

# Re-run setup if needed
.\tests\setup_firewall.ps1
```

**Check 3: FTP Server Status**
```powershell
# Check if container is running
docker ps | findstr campark-ftp

# Check FTP logs
docker logs --tail 50 campark-ftp
```

---

### Problem: Files Not Appearing

**Check 1: Directory Permissions**
```powershell
# Verify incoming directory exists
docker exec campark-ftp ls -la /home/cam001/
```

**Check 2: Camera Logs**
- Access camera web UI
- Go to **Maintenance → System Log**
- Look for FTP upload errors

**Check 3: Passive Mode**
- Ensure **Passive Mode** is enabled in camera FTP settings
- This is critical for NAT traversal

---

### Problem: Uploads Work but Files Are Corrupted

**Check 1: File Format**
```powershell
# Verify JPEG format
docker exec campark-ftp file /home/cam001/incoming/*.jpg
```

**Check 2: Camera Image Settings**
- Go to **Settings → Camera → Image**
- Ensure quality is set to "High" or "Best"
- Resolution should match camera specs (e.g., 4MP = 2688×1520)

---

## 📊 Expected Results

### Successful Configuration

When everything is working:

1. **FTP Test**: Shows "Connection Successful"
2. **Monitor Script**: Shows new files every 2 minutes (heartbeat)
3. **Motion Detection**: Uploads within 5-10 seconds of motion
4. **File Format**: Valid JPEG images
5. **FTP Logs**: Show successful uploads from camera IP

### Sample FTP Log (Success)
```
Thu Feb  5 09:15:23 2026 [pid 123] CONNECT: Client "192.168.1.50"
Thu Feb  5 09:15:23 2026 [pid 122] [cam001] OK LOGIN: Client "192.168.1.50"
Thu Feb  5 09:15:24 2026 [pid 122] [cam001] OK UPLOAD: /incoming/2026-02-05_09-15-23.jpg
```

---

## 🎯 Next Steps After Successful Test

Once camera is uploading successfully:

1. **Start Full POC Stack**
   ```powershell
   docker-compose up -d
   ```

2. **Verify All Services**
   ```powershell
   docker-compose ps
   ```

3. **Check API Health**
   ```powershell
   curl http://localhost:8000/health
   ```

4. **Access Admin UI**
   - Open browser: `http://localhost:8000`
   - Login: `admin` / `changeme_poc`

5. **Monitor Processing**
   ```powershell
   # Watch worker logs for YOLO processing
   docker logs -f campark-worker
   ```

---

## 📝 Configuration Summary

### Your FTP Server Details
```
Host: 192.168.1.111
Port: 21
Username: cam001
Password: password123
Remote Directory: incoming
Passive Mode: ENABLED
```

### Camera Should Upload To
```
ftp://cam001:password123@192.168.1.111:21/incoming/
```

### Files Will Be Stored At
```
Docker: /home/cam001/incoming/
Windows: C:\document\CamPark\data\ftp\cam001\incoming\
```

---

## 🚀 Quick Command Reference

```powershell
# Start monitoring for uploads
python tests/monitor_real_connection.py

# Check FTP server logs
docker logs --tail 50 campark-ftp

# List uploaded files
docker exec campark-ftp ls -la /home/cam001/incoming/

# Test FTP from Python
python tests/test_ftp_upload.py

# Restart FTP server if needed
docker restart campark-ftp

# Check firewall status
Get-NetFirewallRule -DisplayName "CamPark FTP"
```

---

## ✅ Pre-Flight Checklist

Before connecting camera:
- [ ] FTP server running (`docker ps`)
- [ ] Firewall configured (`Get-NetFirewallRule`)
- [ ] Test upload successful (`python tests/test_ftp_upload.py`)
- [ ] Monitor script works (`python tests/monitor_real_connection.py`)
- [ ] Know your PC's LAN IP (`192.168.1.111`)
- [ ] Know your camera's IP address
- [ ] Can access camera web UI

---

**You are now ready to connect your real Dahua camera!** 🎥
