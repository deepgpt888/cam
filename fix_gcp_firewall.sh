#!/usr/bin/env bash
# ==============================================================
# fix_gcp_firewall.sh — Open FTP ports in GCP firewall
# Run this once from any machine that has gcloud authenticated
# and permission to edit firewall rules for the project.
#
# Ports opened:
#   21         — FTP control connection
#   30000-30049 — FTP passive data connections
# ==============================================================
set -euo pipefail

PROJECT=$(gcloud config get-value project 2>/dev/null)
echo "Project: $PROJECT"

# ── FTP control port (21) ──────────────────────────────────────
if gcloud compute firewall-rules describe allow-ftp-control --project="$PROJECT" &>/dev/null; then
  echo "Rule 'allow-ftp-control' already exists — skipping."
else
  gcloud compute firewall-rules create allow-ftp-control \
    --project="$PROJECT" \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:21 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=campark-server \
    --description="Allow FTP control connections from cameras"
  echo "Created rule: allow-ftp-control (port 21)"
fi

# ── FTP passive data ports (30000-30049) ──────────────────────
if gcloud compute firewall-rules describe allow-ftp-passive --project="$PROJECT" &>/dev/null; then
  echo "Rule 'allow-ftp-passive' already exists — skipping."
else
  gcloud compute firewall-rules create allow-ftp-passive \
    --project="$PROJECT" \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:30000-30049 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=campark-server \
    --description="Allow FTP passive data connections from cameras"
  echo "Created rule: allow-ftp-passive (ports 30000-30049)"
fi

echo ""
echo "================================================================"
echo "FTP firewall rules applied."
echo "Also make sure your GCP VM instance has the network tag: campark-server"
echo ""
echo "To add the tag to your VM, run:"
echo "  gcloud compute instances add-tags YOUR_VM_NAME --tags=campark-server --zone=YOUR_ZONE"
echo ""
echo "Or apply to ALL instances (no tag restriction):"
echo "  gcloud compute firewall-rules update allow-ftp-control --source-ranges=0.0.0.0/0"
echo "  (remove --target-tags flag from the create commands above)"
echo "================================================================"
