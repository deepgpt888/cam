#!/bin/bash

# CamPark Plug-and-Play Deployment Script
# Version: 1.0
# Date: February 9, 2026
# Usage: ./deploy.sh [STATIC_IP]

set -e

echo "🚀 CamPark Plug-and-Play Deployment Starting..."
echo "=================================================="

# Check if static IP provided
if [ -z "$1" ]; then
    echo "❌ Error: Please provide your Google Cloud static IP address"
    echo "Usage: ./deploy.sh YOUR_STATIC_IP"
    exit 1
fi

STATIC_IP=$1
echo "📍 Using Static IP: $STATIC_IP"

# Check if we're on Google Cloud VM
if [ ! -f /etc/google_hostname ]; then
    echo "⚠️  Warning: This doesn't appear to be a Google Cloud VM"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# System setup
echo "🔧 Setting up system prerequisites..."
sudo apt update -qq
sudo apt install -y docker.io docker-compose git curl

# Add user to docker group
if ! groups $USER | grep -q docker; then
    sudo usermod -aG docker $USER
    echo "✅ Added $USER to docker group"
    echo "⚠️  Please logout and login again, then re-run this script"
    exit 0
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Starting Docker..."
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Clone repository if not exists
if [ ! -d "CamPark" ]; then
    echo "📦 Cloning CamPark repository..."
    git clone https://github.com/meerul-notaprogrammer/CamPark.git
fi

cd CamPark

# Create .env from template
echo "⚙️  Creating environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    
    # Replace static IP in .env file
    sed -i "s/YOUR_STATIC_IP_HERE/$STATIC_IP/g" .env
    
    # Generate secure passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)
    API_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    SECRET_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    
    # Update passwords in .env
    sed -i "s/changeme_poc/$DB_PASSWORD/g" .env
    sed -i "s/ADMIN_PASSWORD=changeme_poc/ADMIN_PASSWORD=$ADMIN_PASSWORD/g" .env
    sed -i "s/API_KEY=your-secure-api-key-here/API_KEY=$API_KEY/g" .env
    sed -i "s/SECRET_KEY=change-this-to-random-32-character-string/SECRET_KEY=$SECRET_KEY/g" .env
    
    echo "✅ Environment file created with secure passwords"
    echo "📝 Admin Password: $ADMIN_PASSWORD"
    echo "🔑 API Key: $API_KEY"
    echo "💾 Saving credentials to credentials.txt"
    
    echo "=== CamPark Deployment Credentials ===" > credentials.txt
    echo "Dashboard URL: http://$STATIC_IP:8000" >> credentials.txt
    echo "Admin Username: admin" >> credentials.txt  
    echo "Admin Password: $ADMIN_PASSWORD" >> credentials.txt
    echo "API Key: $API_KEY" >> credentials.txt
    echo "Database Password: $DB_PASSWORD" >> credentials.txt
    echo "Created: $(date)" >> credentials.txt
    
else
    echo "✅ .env file already exists"
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/ftp/cam001/incoming
mkdir -p data/images
mkdir -p models

# Set proper permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/

# Pull latest Docker images
echo "🐳 Pulling Docker images..."
docker-compose pull

# Start services
echo "🚀 Starting CamPark services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 30

# Health check
echo "🔍 Checking service health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API service is healthy"
else
    echo "❌ API service health check failed"
    echo "📋 Check logs: docker-compose logs"
fi

# Final status
echo ""
echo "=========================================="
echo "🎉 CamPark Deployment Complete!"
echo "=========================================="
echo ""
echo "📊 Dashboard: http://$STATIC_IP:8000"
echo "🔧 Admin Panel: http://$STATIC_IP:8000/admin"  
echo "📡 API Endpoint: http://$STATIC_IP:8000/api/zones"
echo "❤️  Health Check: http://$STATIC_IP:8000/health"
echo ""
echo "🔐 Credentials saved in: credentials.txt"
echo ""
echo "Camera FTP Settings:"
echo "  Server: $STATIC_IP"
echo "  Port: 21"
echo "  Username: cam001"
echo "  Password: cam001pass"
echo "  Directory: /incoming"
echo ""
echo "🛠️  Management Commands:"
echo "  Status: docker-compose ps"
echo "  Logs: docker-compose logs -f"  
echo "  Restart: docker-compose restart"
echo "  Stop: docker-compose down"
echo ""
echo "📚 Documentation:"
echo "  Setup Guide: GCP_SETUP_GUIDE.md"
echo "  Camera Config: CAMERA_CONFIG_DAHUA.md"
echo "  Quick Start: QUICK_START.md"
echo ""
echo "🎯 Next Steps:"
echo "1. Configure your camera FTP settings (use IP: $STATIC_IP)"
echo "2. Test camera upload by triggering motion"
echo "3. Access dashboard to verify detection"
echo "4. Setup parking zones in admin panel"
echo ""
echo "✅ System is ready for production!"