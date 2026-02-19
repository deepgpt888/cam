#!/bin/bash
# FTP Gate Test - Validates camera can upload to FTP server
# Run this BEFORE starting POC
# Usage: bash tests/ftp_test.sh

set -e

echo "=== CamPark FTP Gate Test ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FTP_USERNAME="cam001"
FTP_PASSWORD="password123"
FTP_PORT="21"
FTP_ROOT="$REPO_ROOT/data/ftp/cam001/incoming"
TEST_FILE="test_upload_$(date +%s).jpg"

# Helper functions
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}✗ $1 not found${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $1 available${NC}"
}

check_directory() {
    if [ ! -d "$1" ]; then
        echo -e "${RED}✗ Directory not found: $1${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Directory exists: $1${NC}"
}

check_ftp_container() {
    if docker ps --format "{{.Names}}" | grep -q "^campark-ftp$"; then
        echo -e "${GREEN}✓ campark-ftp container running${NC}"
        return 0
    fi
    echo -e "${RED}✗ campark-ftp container not running${NC}"
    echo "   Start: docker-compose up -d ftp"
    return 1
}

# Pre-flight checks
echo "Checking prerequisites..."
check_command curl || exit 1
check_command docker || exit 1
check_directory "$FTP_ROOT" || exit 1

echo ""
echo "Checking FTP server..."
check_ftp_container || exit 1

# Count current files
CURRENT_COUNT=$(ls -1 "$FTP_ROOT"/*.jpg 2>/dev/null | wc -l)
echo -e "${YELLOW}Current files in $FTP_ROOT: $CURRENT_COUNT${NC}"

# Create minimal test JPEG (1x1 white pixel)
echo ""
echo "Creating test JPEG..."
# Minimal JPEG header + minimal data
python3 -c "
import struct
# Start of Image
data = b'\\xff\\xd8'
# Quantization Table
data += b'\\xff\\xdb\\x00C\\x00\\x08\\x06\\x06\\x07\\x06\\x05\\x08\\x07\\x07\\x07\\t\\t\\x08\\n\\x0c\\x14\\r\\x0c\\x0b\\x0b\\x0c\\x19\\x12\\x13\\x0f\\x14\\x1d\\x1a\\x1f\\x1e\\x1d\\x1a\\x1c\\x1c $.\' \",#\\x1c\\x1c(7),01444\\x1f\\'9=82<.342'
# Start of Frame
data += b'\\xff\\xc0\\x00\\x0b\\x08\\x00\\x01\\x00\\x01\\x01\\x01\\x11\\x00'
# Huffman Table (DC)
data += b'\\xff\\xc4\\x00\\x1f\\x00\\x00\\x01\\x05\\x01\\x01\\x01\\x01\\x01\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\t\\n\\x0b'
# Huffman Table (AC)
data += b'\\xff\\xc4\\x00\\xb5\\x10\\x00\\x02\\x01\\x03\\x03\\x02\\x04\\x03\\x05\\x05\\x04\\x04\\x00\\x00\\x01}\\x01\\x02\\x03\\x00\\x04\\x11\\x05\\x12!1A\\x06\\x13Qa\\x07\"q\\x142\\x81\\x91\\xa1\\x08#B\\xb1\\xc1\\x15R\\xd1\\xf0$3br\\x82\\t\\n\\x16\\x17\\x18\\x19\\x1a%&\\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\\x83\\x84\\x85\\x86\\x87\\x88\\x89\\x8a\\x92\\x93\\x94\\x95\\x96\\x97\\x98\\x99\\x9a\\xa2\\xa3\\xa4\\xa5\\xa6\\xa7\\xa8\\xa9\\xaa\\xb2\\xb3\\xb4\\xb5\\xb6\\xb7\\xb8\\xb9\\xba\\xc2\\xc3\\xc4\\xc5\\xc6\\xc7\\xc8\\xc9\\xca\\xd2\\xd3\\xd4\\xd5\\xd6\\xd7\\xd8\\xd9\\xda\\xe1\\xe2\\xe3\\xe4\\xe5\\xe6\\xe7\\xe8\\xe9\\xea\\xf1\\xf2\\xf3\\xf4\\xf5\\xf6\\xf7\\xf8\\xf9\\xfa'
# Start of Scan
data += b'\\xff\\xda\\x00\\x08\\x01\\x01\\x00\\x00?\\x00\\xfb\\xd2'
# End of Image
data += b'\\xff\\xd9'
with open('$TEST_FILE', 'wb') as f:
    f.write(data)
"
if [ -f "$TEST_FILE" ]; then
    SIZE=$(stat -f%z "$TEST_FILE" 2>/dev/null || stat -c%s "$TEST_FILE")
    echo -e "${GREEN}✓ Test JPEG created ($SIZE bytes)${NC}"
else
    echo -e "${RED}✗ Failed to create test JPEG${NC}"
    exit 1
fi

# Test FTP upload
echo ""
echo "Uploading to FTP (user: $FTP_USERNAME)..."
if curl --silent --show-error --fail \
    -T "$TEST_FILE" \
    "ftp://$FTP_USERNAME:$FTP_PASSWORD@localhost:$FTP_PORT/incoming/$TEST_FILE"; then
    echo -e "${GREEN}✓ FTP upload succeeded${NC}"
else
    echo -e "${RED}✗ FTP upload failed${NC}"
    rm -f "$TEST_FILE"
    exit 1
fi

# Verify file in FTP root
echo ""
echo "Verifying file in $FTP_ROOT..."
sleep 1
if [ -f "$FTP_ROOT/$TEST_FILE" ]; then
    SIZE=$(stat -f%z "$FTP_ROOT/$TEST_FILE" 2>/dev/null || stat -c%s "$FTP_ROOT/$TEST_FILE")
    echo -e "${GREEN}✓ File found in FTP root ($SIZE bytes)${NC}"
    echo -e "${GREEN}   Path: $FTP_ROOT/$TEST_FILE${NC}"
else
    echo -e "${RED}✗ File NOT found in FTP root${NC}"
    echo "   Debug: ls -la $FTP_ROOT/"
    ls -la "$FTP_ROOT/"
    rm -f "$TEST_FILE"
    exit 1
fi

# Validate JPEG
echo ""
echo "Validating JPEG..."
if file "$FTP_ROOT/$TEST_FILE" | grep -q JPEG; then
    echo -e "${GREEN}✓ Valid JPEG format${NC}"
else
    echo -e "${RED}✗ File is not a valid JPEG${NC}"
    file "$FTP_ROOT/$TEST_FILE"
    rm -f "$TEST_FILE"
    exit 1
fi

# Clean up
rm -f "$TEST_FILE"
rm -f /tmp/ftp_log.txt

echo ""
echo "========================================"
echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
echo "========================================"
echo ""
echo "⚠️  Next Steps:"
echo "   1. Configure your Dahua camera FTP settings"
echo "   2. Enable motion detection + FTP upload"
echo "   3. Wait 3 minutes for first heartbeat snapshot"
echo "   4. Check: ls -la $FTP_ROOT/"
echo "   5. If files appear, you're ready for POC!"
echo ""
