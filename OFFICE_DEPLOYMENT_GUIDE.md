# CamPark Office Installation: Quick Reference Guide

**Your 8-Day Deployment Plan** | **Ready for Tomorrow's Installation**

---

## 🏗️ Installation Summary

**What you have**: Complete parking monitoring system  
**What you need**: Google Cloud VM + Camera configuration  
**Time to deploy**: ~2 hours setup + 30 minutes camera config  
**Cost for 8 days**: ~$28 (well within your RM1,034 budget)

---

## 📋 TODAY'S Google Cloud Setup Checklist

### ✅ Step 1: Google Cloud Console Setup (15 minutes)

1. **Go to**: https://console.cloud.google.com/
2. **Create project**: `campark-office-pilot`
3. **Enable APIs**: Compute Engine, Cloud SQL, Cloud Storage
4. **Reserve Static IP**: 
   - Go to "VPC Network" > "External IP addresses"
   - Reserve regional static IP
   - **📝 SAVE THIS IP - YOU'LL NEED IT!**

### ✅ Step 2: Create Virtual Machine (10 minutes)

```bash
Machine Config:
- Name: campark-office-vm
- Type: e2-standard-4 (4 CPU, 16GB RAM)
- Disk: Ubuntu 20.04 LTS, 100GB
- Network: Assign your static IP
- Firewall: Allow HTTP/HTTPS
```

### ✅ Step 3: Configure Firewall (5 minutes)

Create these firewall rules:
- **FTP Control**: Port 21 (ingress)
- **FTP Data**: Ports 30000-30049 (ingress)  
- **API Access**: Port 8000 (ingress)

---

## 🚀 TOMORROW'S Deployment Commands

### ✅ Step 1: SSH to Your VM

```bash
# From Google Cloud Console, click "SSH" next to your VM
# Or from terminal:
gcloud compute ssh campark-office-vm --zone=[your-zone]
```

### ✅ Step 2: One-Command Deployment

```bash
# Clone and run deployment script
git clone https://github.com/meerul-notaprogrammer/CamPark.git
cd CamPark
./deploy.sh [YOUR-STATIC-IP]

# Example:
# ./deploy.sh 34.142.123.456
```

**That's it!** The script will:
- Install Docker & prerequisites
- Clone your code
- Generate secure passwords
- Configure FTP server  
- Start all services
- Show you the dashboard URLs

---

## 📊 Where to See Results

### 🎯 Main Dashboard
```
URL: http://[your-static-ip]:8000/dashboard
Purpose: Live parking occupancy view
Updates: Real-time (every 30 seconds)
```

### 🔧 Admin Panel
```
URL: http://[your-static-ip]:8000/admin
Login: admin / [generated-password]
Features: 
- Zone configuration
- Camera health monitoring  
- System settings
- Detection logs
```

### 📡 API Endpoint (for external apps)
```
URL: http://[your-static-ip]:8000/api/zones
Format: JSON
Authentication: API key required
Response: {"zones": [{"id": "PARKING_01", "occupied": true, "count": 3}]}
```

### ❤️ Health Monitor
```
URL: http://[your-static-ip]:8000/health
Purpose: System status, FTP uploads, detection performance
Use: Troubleshooting and monitoring
```

---

## 📷 Camera Configuration (On-Site Tomorrow)

### Physical Setup
1. **Mount camera** with clear parking lot view
2. **Connect network cable** to office network
3. **Connect power** (PoE or external adapter)
4. **Find camera IP** (check router DHCP table)

### FTP Configuration
```bash
# Access camera web interface at http://[camera-ip]
# Go to: Network > FTP Settings

Server Address: [your-static-ip]
Port: 21
Username: cam001  
Password: cam001pass
Remote Directory: /incoming

# Upload Settings:
Upload on Motion: Enabled
Scheduled Upload: Every 2 minutes  
Image Format: JPEG
Resolution: 1920x1080 (or highest available)
```

### Test Upload
1. **Wave hand** in front of camera (trigger motion)
2. **Check dashboard**: http://[your-static-ip]:8000/health
3. **Verify**: "Last Upload" timestamp updates
4. **Success indicator**: Green status lights

---

## 🎨 Dashboard Enhancement Plan (Days 6-7)

### Current Dashboard Features
- ✅ Live occupancy counts
- ✅ Camera health status  
- ✅ Recent detection images
- ✅ Zone configuration
- ✅ Real-time updates

### Planned Enhancements
- 📈 **Occupancy trends** (hourly/daily graphs)
- 📱 **Mobile responsive** design
- 🚨 **Alert notifications** (email/SMS when lot full)
- 📊 **Analytics dashboard** (peak hours, utilization %)
- 🎯 **Zone heatmaps** (most/least used spaces)
- 🔄 **Auto-refresh settings** (5s, 30s, 60s options)

### Custom Features You Can Add
```python
# API endpoints for custom integrations:
GET /api/zones/{zone_id}/history    # Historical data
GET /api/analytics/peak-hours       # Usage patterns  
GET /api/alerts/configuration       # Alert settings
POST /api/zones/{zone_id}/reserve   # Reservation system
```

---

## 🛠️ Daily Operations

### Morning Checklist (2 minutes)
```bash
# SSH to VM
ssh [username]@[your-static-ip]

# Check system status
cd CamPark && docker-compose ps

# View overnight activity  
curl http://localhost:8000/health
```

### Quick Commands
```bash
# Restart if needed
docker-compose restart

# View live logs
docker-compose logs -f worker

# Check FTP uploads
ls -la data/ftp/cam001/incoming/

# System health
curl http://localhost:8000/api/zones
```

### Troubleshooting
```bash
# Camera not uploading?
docker-compose logs ftp

# Detection not working?  
docker-compose logs worker

# Dashboard not loading?
docker-compose logs api
```

---

## 💰 Cost Monitoring (8 Days)

**Current Budget**: RM1,034.63 (82% remaining)  
**Estimated 8-day cost**: ~$28 USD (~RM120)  
**Remaining after deployment**: ~RM900+ 

**Daily monitoring**: https://console.cloud.google.com/billing

---

## 📞 Support & Documentation

### Quick Help
- **System status**: http://[your-ip]:8000/health
- **Error logs**: `docker-compose logs [service-name]`
- **Restart everything**: `docker-compose restart`

### Full Documentation
- **[GCP_SETUP_GUIDE.md](GCP_SETUP_GUIDE.md)**: Detailed Google Cloud setup
- **[CAMERA_CONFIG_DAHUA.md](CAMERA_CONFIG_DAHUA.md)**: Camera configuration guide  
- **[QUICK_START.md](QUICK_START.md)**: Developer overview
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**: Production deployment

### Emergency Contacts
- **System Issues**: Check GitHub Issues
- **Google Cloud Support**: Cloud Console support tab
- **Camera Issues**: Dahua support documentation

---

## 🎯 Success Metrics

**Day 1-2**: System deployed and accessible  
**Day 3**: Camera uploading images successfully  
**Day 4**: Parking detection working accurately
**Day 5**: Dashboard showing real-time data
**Day 6-7**: Enhanced features implemented
**Day 8**: Stable production system ready for scaling

**🏆 Goal**: Smooth office parking monitoring with potential for 25+ camera expansion!

---

*Generated on February 9, 2026 - Ready for your office deployment tomorrow! 🚀*