# FTP Server Diagnosis Report
**Date**: 2026-02-05 17:02  
**Issue**: Dahua CCTV failed to connect to FTP server

---

## ✅ FTP Server Status: RUNNING

### Container Details
```
Container ID: 3ec2bb3c20d9
Image: delfer/alpine-ftp-server
Status: Up About an hour
Ports: 
  - 0.0.0.0:21->21/tcp
  - [::]:21->21/tcp
  - 0.0.0.0:21000-21010->21000-21010/tcp
  - [::]:21000-21010->21000-21010/tcp
```

### ⚠️ IMPORTANT FINDING: Port Mismatch!

**Expected Passive Ports**: 30000-30009 (from documentation)  
**Actual Passive Ports**: 21000-21010 (from running container)

This is likely why your Dahua camera cannot connect!

---

## Current Configuration

### FTP User Account
- **Username**: cam001
- **Password**: password123
- **UID/GID**: 1000/1000
- **Home Directory**: `/1000/` (inside container)
- **Upload Directory**: `/1000/incoming/`

### Network Configuration
- **Server IP**: 192.168.1.111 (Primary LAN)
- **FTP Port**: 21 ✅
- **Passive Ports**: 21000-21010 ⚠️ (Should be 30000-30009)

### Firewall Status
```
Rule Name: CamPark FTP
Status: Enabled
Direction: Inbound
Action: Allow
Ports: 21, 30000-30009
```

**⚠️ PROBLEM**: Firewall allows ports 30000-30009, but FTP server is using 21000-21010!

---

## Test Results

### ✅ FTP Server Logs (Recent Activity)
The server shows successful connections from Docker internal network (172.18.0.1):
```
Thu Feb  5 08:58:29 2026 [pid 769] CONNECT: Client "172.18.0.1"
Thu Feb  5 08:58:29 2026 [pid 768] [cam001] OK LOGIN: Client "172.18.0.1"
```

**Note**: No connections from external camera IP detected in logs.

### ✅ Test Files Present
Files successfully uploaded from test scripts:
```
/1000/incoming/test_upload_1770280532.jpg (65,700 bytes)
/1000/incoming/ directory exists
```

### ✅ Windows Firewall
Rule "CamPark FTP" is active and allowing inbound traffic.

---

## Root Cause Analysis

### Why Camera Connection Fails

1. **Passive Port Mismatch**:
   - Camera tries to use passive mode (required for NAT)
   - FTP server advertises ports 21000-21010
   - Windows Firewall only allows 30000-30009
   - Camera's passive connection gets blocked by firewall

2. **Container Configuration Issue**:
   - Running container uses `delfer/alpine-ftp-server` image
   - docker-compose.yml specifies `stilliard/pure-ftpd` image
   - Port mappings don't match between documentation and reality

---

## Solutions

### Option 1: Fix Firewall to Match Current Ports (Quick Fix)

Update Windows Firewall to allow the actual passive ports:

```powershell
# Remove old rule
Remove-NetFirewallRule -DisplayName "CamPark FTP"

# Add new rule with correct ports
New-NetFirewallRule -DisplayName "CamPark FTP" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 21,21000-21010 `
  -Profile Any
```

### Option 2: Rebuild Container with Correct Ports (Recommended)

1. Stop and remove current container:
```powershell
docker stop campark-ftp
docker rm campark-ftp
```

2. Rebuild using docker-compose (which has correct port mappings):
```powershell
docker-compose up -d ftp
```

3. Verify ports:
```powershell
docker ps | findstr campark-ftp
# Should show: 30000-30009:30000-30009
```

### Option 3: Manual Container Restart with Correct Ports

```powershell
docker stop campark-ftp
docker rm campark-ftp

docker run -d \
  --name campark-ftp \
  -p 21:21 \
  -p 30000-30009:30000-30009 \
  -e USERS="cam001|password123|1000|1000" \
  -e ADDRESS=192.168.1.111 \
  -e MIN_PORT=30000 \
  -e MAX_PORT=30009 \
  -v C:\document\CamPark\data\ftp:/ftp/cam001 \
  delfer/alpine-ftp-server
```

---

## Camera Configuration (After Fix)

Once ports are fixed, configure your Dahua camera with:

```
FTP Server: 192.168.1.111
Port: 21
Username: cam001
Password: password123
Remote Directory: incoming
Passive Mode: ENABLED ✅
```

**Passive Port Range**: Will be automatically negotiated (30000-30009 after fix)

---

## Verification Steps

After applying fix:

1. **Check Container Ports**:
```powershell
docker ps | findstr campark-ftp
# Should show: 30000-30009:30000-30009
```

2. **Check Firewall**:
```powershell
Get-NetFirewallRule -DisplayName "CamPark FTP" | 
  Get-NetFirewallPortFilter
# Should show: LocalPort: 21,30000-30009
```

3. **Test from Camera**:
   - Go to camera web UI
   - Settings → Network → FTP
   - Click "Test" button
   - Should see "Connection Successful"

4. **Monitor FTP Logs**:
```powershell
docker logs -f campark-ftp
# Should see connection from camera IP (e.g., 192.168.1.50)
```

---

## Expected Success Indicators

When working correctly, you should see:

1. **FTP Logs showing camera IP**:
```
Thu Feb  5 17:15:23 2026 [pid 123] CONNECT: Client "192.168.1.50"
Thu Feb  5 17:15:23 2026 [pid 122] [cam001] OK LOGIN: Client "192.168.1.50"
Thu Feb  5 17:15:24 2026 [pid 122] [cam001] OK UPLOAD: /incoming/snapshot.jpg
```

2. **Files appearing in directory**:
```powershell
docker exec campark-ftp ls -la /1000/incoming/
# Should show new .jpg files from camera
```

3. **Camera web UI shows "Test Successful"**

---

## Additional Diagnostics

### Check What Camera Sees

From camera's perspective, test if ports are accessible:

```powershell
# Test FTP control port (should work)
Test-NetConnection -ComputerName 192.168.1.111 -Port 21

# Test passive ports (currently blocked)
Test-NetConnection -ComputerName 192.168.1.111 -Port 30000
Test-NetConnection -ComputerName 192.168.1.111 -Port 21000
```

### Check FTP Server Configuration

```powershell
# View FTP server environment
docker exec campark-ftp env | findstr -i "port\|address\|pasv"

# Check if passive mode is enabled
docker exec campark-ftp cat /etc/pure-ftpd/pure-ftpd.conf 2>$null
# (May not exist for alpine-ftp-server)
```

---

## Recommended Action Plan

**IMMEDIATE**: Apply Option 1 (Quick Fix) to test if port mismatch is the issue:

```powershell
# 1. Update firewall
Remove-NetFirewallRule -DisplayName "CamPark FTP" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "CamPark FTP" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 21,21000-21010 `
  -Profile Any

# 2. Test from camera
# Go to camera web UI → FTP settings → Click "Test"

# 3. Monitor logs
docker logs -f campark-ftp
```

**LONG-TERM**: Apply Option 2 to align with docker-compose.yml configuration.

---

## Summary

- ✅ FTP server is running
- ✅ FTP user account exists
- ✅ Test uploads work from localhost
- ❌ **Passive port mismatch preventing camera connections**
- ❌ **Firewall blocking actual passive ports (21000-21010)**

**Fix**: Update firewall to allow ports 21000-21010, OR rebuild container to use ports 30000-30009.
