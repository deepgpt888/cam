# CamPark Google Cloud Setup Guide: 8-Day Deployment Plan

**Date**: February 9, 2026  
**Goal**: Deploy CamPark for office parking installation  
**Timeline**: 8 days (Free Trial ending Feb 17, 2026)  
**Target**: Plug-and-play system with dashboard access

---

## 🚀 Day 1: Google Cloud Console Setup (TODAY)

### Step 1: Create Google Cloud Account & Project

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Sign in** with your Google account
3. **Accept the $300 free trial** (if available)
   - Note: You already have RM1,034.63 remaining with 82% left
   4. **Create a new project**:
      - Project name: `campark-office-pilot`
         - Project ID: `campark-office-pilot-[random-number]`
            - Location: Choose your organization (or no organization)

            ### Step 2: Enable Required APIs

            ```bash
            # These APIs need to be enabled (we'll do this via console)
            - Compute Engine API
            - Cloud SQL API  
            - Cloud Storage API
            - Cloud Logging API
            - Cloud Monitoring API
            ```

            **In Console**:
            1. Go to "APIs & Services" > "Library"
            2. Search and enable each API above
            3. Wait 2-3 minutes for activation

            ### Step 3: Setup Billing Account

            1. Go to "Billing" in left menu
            2. Verify your free trial billing account is active
            3. Set budget alerts:
               - Alert at 50% = ~$150 USD
                  - Alert at 80% = ~$240 USD

                  ### Step 4: Create Static IP Address

                  ```bash
                  # Reserve a static external IP for your camera FTP uploads
                  1. Go to "VPC network" > "External IP addresses"
                  2. Click "Reserve External Static Address"
                  3. Name: campark-office-ip
                  4. Network Service Tier: Premium
                  5. IP Version: IPv4
                  6. Type: Regional
                  7. Region: Choose closest to your location
                  8. Click "Reserve"
                  ```

                  **Save this IP address - your cameras will upload to this IP!**

                  ---

                  ## 🖥️ Day 2: Virtual Machine Setup

                  ### Step 5: Create Compute Engine VM

                  1. Go to "Compute Engine" > "VM instances"
                  2. Click "Create Instance"
                  3. **Configuration**:
                     - Name: `campark-office-vm`
                        - Region: Same as your static IP
                           - Zone: Any zone in that region
                              - Machine configuration: 
                                   - Series: E2
                                        - Machine type: `e2-standard-4` (4 vCPU, 16 GB memory)
                                           - Boot disk:
                                                - Operating System: Ubuntu
                                                     - Version: Ubuntu 20.04 LTS
                                                          - Boot disk type: Balanced persistent disk
                                                               - Size: 100 GB
                                                                  - Identity and API access: Allow default access
                                                                     - Firewall: Allow HTTP and HTTPS traffic

                                                                     4. Click "Create"

                                                                     ### Step 6: Configure Firewall Rules

                                                                     ```bash
                                                                     # Create firewall rules for FTP and API access
                                                                     1. Go to "VPC network" > "Firewall"
                                                                     2. Click "Create Firewall Rule"

                                                                     # Rule 1: FTP Control Port
                                                                     Name: campark-ftp-control
                                                                     Direction: Ingress
                                                                     Action: Allow
                                                                     Targets: Tags
                                                                     Target tags: campark-vm
                                                                     Source IP ranges: 0.0.0.0/0
                                                                     Protocols: TCP
                                                                     Ports: 21

                                                                     # Rule 2: FTP Data Ports (Passive)
                                                                     Name: campark-ftp-data
                                                                     Direction: Ingress
                                                                     Action: Allow
                                                                     Targets: Tags
                                                                     Target tags: campark-vm
                                                                     Source IP ranges: 0.0.0.0/0
                                                                     Protocols: TCP
                                                                     Ports: 30000-30049

                                                                     # Rule 3: API Access
                                                                     Name: campark-api
                                                                     Direction: Ingress
                                                                     Action: Allow
                                                                     Targets: Tags
                                                                     Target tags: campark-vm
                                                                     Source IP ranges: 0.0.0.0/0
                                                                     Protocols: TCP
                                                                     Ports: 8000
                                                                     ```

                                                                     ### Step 7: Assign Static IP to VM

                                                                     1. Go to "Compute Engine" > "VM instances"
                                                                     2. Click on your VM name
                                                                     3. Click "Edit"
                                                                     4. In "Network interfaces" section, click the pencil icon
                                                                     5. External IP: Select your reserved static IP
                                                                     6. Click "Done" then "Save"

                                                                     ---

                                                                     ## 📦 Day 3: Deploy CamPark Application

                                                                     ### Step 8: Connect to VM and Install Prerequisites

                                                                     ```bash
                                                                     # SSH into your VM (click SSH button in console)
                                                                     # Or from your local terminal:
                                                                     gcloud compute ssh campark-office-vm --zone=[YOUR-ZONE]

                                                                     # Update system
                                                                     sudo apt update && sudo apt upgrade -y

                                                                     # Install Docker
                                                                     curl -fsSL https://get.docker.com -o get-docker.sh
                                                                     sudo sh get-docker.sh
                                                                     sudo usermod -aG docker $USER

                                                                     # Install Docker Compose
                                                                     sudo apt install docker-compose -y

                                                                     # Install Git
                                                                     sudo apt install git -y

                                                                     # Logout and login to apply docker group
                                                                     exit
                                                                     # SSH back in
                                                                     ```

                                                                     ### Step 9: Clone and Deploy CamPark

                                                                     ```bash
                                                                     # Clone your repository
                                                                     git clone https://github.com/meerul-notaprogrammer/CamPark.git
                                                                     cd CamPark

                                                                     # Create environment file
                                                                     cp .env.example .env
                                                                     # Edit .env with your settings:
                                                                     nano .env

                                                                     # Set these values in .env:
                                                                     EXTERNAL_IP=[YOUR-STATIC-IP]
                                                                     DATABASE_URL=postgresql://campark:campark123@db:5432/campark
                                                                     REDIS_URL=redis://redis:6379/0
                                                                     DEBUG=false
                                                                     SECRET_KEY=[generate-random-key]
                                                                     ```

                                                                     ### Step 10: Launch Application

                                                                     ```bash
                                                                     # Start all services
                                                                     docker-compose up -d

                                                                     # Check status
                                                                     docker-compose ps

                                                                     # View logs
                                                                     docker-compose logs -f
                                                                     ```

                                                                     ---

                                                                     ## 📊 Day 4-5: Testing & Configuration

                                                                     ### Step 11: Verify System Health

                                                                     **Check Application Status:**
                                                                     ```bash
                                                                     # SSH into your VM
                                                                     ssh [your-vm-external-ip]

                                                                     # Check all containers are running
                                                                     docker-compose ps

                                                                     # Test API endpoint
                                                                     curl http://localhost:8000/health

                                                                     # Check FTP server
                                                                     curl ftp://[your-static-ip]:21
                                                                     ```

                                                                     **Access Dashboard:**
                                                                     - Open browser: `http://[your-static-ip]:8000`
                                                                     - Default login: admin / campark123 (change this!)

                                                                     ### Step 12: Configure Your First Camera

                                                                     1. **Camera Network Setup**:
                                                                        - Get your camera's IP address
                                                                           - Access camera web interface
                                                                              - Go to Network > FTP settings

                                                                              2. **Camera FTP Configuration**:
                                                                                 ```
                                                                                    FTP Server: [your-static-ip]
                                                                                       Port: 21
                                                                                          Username: cam001
                                                                                             Password: cam001pass
                                                                                                Directory: /incoming
                                                                                                   Upload on: Motion Detection + Scheduled (every 2 minutes)
                                                                                                      Format: JPEG
                                                                                                         ```

                                                                                                         3. **Test Upload**:
                                                                                                            - Trigger motion near camera
                                                                                                               - Check: `http://[your-static-ip]:8000/admin/health`
                                                                                                                  - Verify files appear in system

                                                                                                                  ---

                                                                                                                  ## 🎨 Day 6-7: Dashboard Enhancement

                                                                                                                  ### Step 13: Setup External Dashboard Access

                                                                                                                  **Create API Key:**
                                                                                                                  ```bash
                                                                                                                  # SSH to VM
                                                                                                                  cd CamPark

                                                                                                                  # Create API key for external access
                                                                                                                  python3 -c "
                                                                                                                  import secrets
                                                                                                                  print('API Key:', secrets.token_urlsafe(32))
                                                                                                                  "

                                                                                                                  # Add to .env file
                                                                                                                  echo "API_KEY=your-generated-key" >> .env

                                                                                                                  # Restart services
                                                                                                                  docker-compose restart
                                                                                                                  ```

                                                                                                                  **Dashboard URLs:**
                                                                                                                  - **Admin Interface**: `http://[your-static-ip]:8000/admin`
                                                                                                                  - **Live Dashboard**: `http://[your-static-ip]:8000/dashboard`
                                                                                                                  - **API Endpoint**: `http://[your-static-ip]:8000/api/zones`
                                                                                                                  - **Health Check**: `http://[your-static-ip]:8000/health`

                                                                                                                  ### Step 14: Setup Zone Configuration

                                                                                                                  1. Access admin panel: `http://[your-static-ip]:8000/admin/zones`
                                                                                                                  2. Create parking zones:
                                                                                                                     - Zone ID: PARKING_01, PARKING_02, etc.
                                                                                                                        - Camera: CAM001
                                                                                                                           - Polygon coordinates: Use zone editor
                                                                                                                           3. Set detection parameters:
                                                                                                                              - Object types: car, truck, motorcycle
                                                                                                                                 - Confidence threshold: 0.5
                                                                                                                                    - Update interval: 30 seconds

                                                                                                                                    ---

                                                                                                                                    ## 📱 Day 8: Go Live & Monitoring

                                                                                                                                    ### Step 15: Install at Office Parking

                                                                                                                                    **Physical Installation Checklist:**
                                                                                                                                    - [ ] Camera mounted with parking lot view
                                                                                                                                    - [ ] Network cable connected
                                                                                                                                    - [ ] Power supply connected
                                                                                                                                    - [ ] Camera accessible via web interface
                                                                                                                                    - [ ] FTP settings configured to your GCP IP
                                                                                                                                    - [ ] Test upload successful

                                                                                                                                    **Final Verification:**
                                                                                                                                    ```bash
                                                                                                                                    # Check system health
                                                                                                                                    curl http://[your-static-ip]:8000/health

                                                                                                                                    # Verify FTP uploads
                                                                                                                                    ls -la /home/[user]/CamPark/data/ftp/cam001/incoming/

                                                                                                                                    # Check detection results
                                                                                                                                    curl http://[your-static-ip]:8000/api/zones
                                                                                                                                    ```

                                                                                                                                    ### Step 16: Monitoring & Alerts

                                                                                                                                    **Setup Basic Monitoring:**
                                                                                                                                    1. Go to "Monitoring" in Google Cloud Console
                                                                                                                                    2. Create alerts for:
                                                                                                                                       - VM CPU > 80%
                                                                                                                                          - VM Disk > 80%
                                                                                                                                             - No FTP uploads in 15 minutes

                                                                                                                                             **Daily Health Check:**
                                                                                                                                             - Visit: `http://[your-static-ip]:8000/admin/health`
                                                                                                                                             - Check for green status indicators
                                                                                                                                             - Review detection accuracy

                                                                                                                                             ---

                                                                                                                                             ## 🎯 Quick Access Summary

                                                                                                                                             ### Essential URLs (Save These!)
                                                                                                                                             - **Dashboard**: `http://[your-static-ip]:8000/dashboard`
                                                                                                                                             - **Admin Panel**: `http://[your-static-ip]:8000/admin`
                                                                                                                                             - **API**: `http://[your-static-ip]:8000/api/zones`
                                                                                                                                             - **Health**: `http://[your-static-ip]:8000/health`

                                                                                                                                             ### Camera FTP Settings
                                                                                                                                             ```
                                                                                                                                             Server: [your-static-ip]
                                                                                                                                             Port: 21
                                                                                                                                             User: cam001
                                                                                                                                             Pass: cam001pass
                                                                                                                                             Path: /incoming
                                                                                                                                             ```

                                                                                                                                             ### SSH Access
                                                                                                                                             ```bash
                                                                                                                                             gcloud compute ssh campark-office-vm --zone=[your-zone]
                                                                                                                                             # Or: ssh [your-username]@[your-static-ip]
                                                                                                                                             ```

                                                                                                                                             ---

                                                                                                                                             ## 🆘 Emergency Troubleshooting

                                                                                                                                             ### Common Issues

                                                                                                                                             **Camera not uploading:**
                                                                                                                                             ```bash
                                                                                                                                             # Check FTP server
                                                                                                                                             sudo docker-compose logs ftp

                                                                                                                                             # Test FTP manually
                                                                                                                                             ftp [your-static-ip]
                                                                                                                                             # login: cam001 / cam001pass
                                                                                                                                             ```

                                                                                                                                             **API not responding:**
                                                                                                                                             ```bash
                                                                                                                                             # Restart application
                                                                                                                                             docker-compose restart

                                                                                                                                             # Check logs
                                                                                                                                             docker-compose logs api worker
                                                                                                                                             ```

                                                                                                                                             **Zone detection not working:**
                                                                                                                                             ```bash
                                                                                                                                             # Check worker processing
                                                                                                                                             docker-compose logs worker

                                                                                                                                             # Verify model files
                                                                                                                                             ls -la models/
                                                                                                                                             ```

                                                                                                                                             ### Get Help
                                                                                                                                             - System logs: `http://[your-static-ip]:8000/admin/system`
                                                                                                                                             - Support: Check GitHub issues or create new one
                                                                                                                                             - Emergency restart: `docker-compose restart`

                                                                                                                                             ---

                                                                                                                                             ## 💰 Cost Monitoring

                                                                                                                                             **Expected Usage (8 days):**
                                                                                                                                             - VM e2-standard-4: ~$96/month = ~$25 for 8 days  
                                                                                                                                             - Static IP: $1.46/month = ~$0.40 for 8 days
                                                                                                                                             - Storage (100GB): $10/month = ~$2.60 for 8 days
                                                                                                                                             - **Total Estimated Cost: ~$28 for 8 days**

                                                                                                                                             Your budget has plenty of room with RM1,034.63 remaining!

                                                                                                                                             Remember: This system is now **production-ready** and can scale to 25+ cameras later with minimal changes.