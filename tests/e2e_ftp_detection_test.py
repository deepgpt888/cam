#!/usr/bin/env python3
"""
CamPark End-to-End FTP + Detection Test
========================================
Uploads a test image via FTP (simulating a Dahua camera),
then monitors the worker and checks detection results in the DB.

Usage:
    python tests/e2e_ftp_detection_test.py [--image path/to/image.jpg] [--camera cam001]
"""

import argparse
import ftplib
import os
import sys
import time
import psycopg2
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
FTP_HOST     = "localhost"
FTP_PORT     = 21
DB_URL       = os.getenv("DATABASE_URL",
               "postgresql://campark:changeme_poc@localhost:5432/campark")
API_BASE     = "http://localhost:8000"

CAMERAS = {
    "cam001": "password123",
    "cam002": "SecureP@ss2",
    "cam003": "SecureP@ss3",
}

DEFAULT_IMAGE = Path(__file__).parent / "car_parking_test.jpg"
FALLBACK_IMAGE = Path(__file__).parent.parent / "test_snapshot.jpg"

# ──────────────────────────────────────────────────────────────────────────────

def hr(char="-", width=60): print(char * width)

def colour(text, code): return f"\033[{code}m{text}\033[0m"
OK   = lambda t: colour(t, "32")   # green
FAIL = lambda t: colour(t, "31")   # red
INFO = lambda t: colour(t, "36")   # cyan
WARN = lambda t: colour(t, "33")   # yellow


def pick_image(override: str | None) -> Path:
    if override:
        p = Path(override)
        if not p.exists():
            print(FAIL(f"Image not found: {p}"))
            sys.exit(1)
        return p
    if DEFAULT_IMAGE.exists():
        return DEFAULT_IMAGE
    if FALLBACK_IMAGE.exists():
        return FALLBACK_IMAGE
    print(FAIL("No test image found. Run from repo root or pass --image."))
    sys.exit(1)


# ── Step 1: FTP upload ─────────────────────────────────────────────────────
def ftp_upload(camera: str, password: str, image_path: Path) -> str:
    """Upload image via FTP. Returns the remote filename."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_name = f"cam_snap_{ts}.jpg"

    print(f"\n  Host    : {FTP_HOST}:{FTP_PORT}")
    print(f"  User    : {camera}")
    print(f"  File    : {image_path.name} → {remote_name}")

    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
    ftp.login(camera, password)

    # pure-ftpd chroots user, so we're already in their home dir
    # The worker looks at /{ftp_base}/{username}/incoming/
    # From inside the chroot the path is just /incoming
    try:
        ftp.cwd("incoming")
    except ftplib.error_perm:
        # try creating it
        ftp.mkd("incoming")
        ftp.cwd("incoming")

    with open(image_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_name}", f)

    # Verify it's there
    listing = ftp.nlst()
    ftp.quit()

    if remote_name not in listing:
        raise RuntimeError(f"File not found in listing after upload: {listing}")

    return remote_name


# ── Step 2: Wait for worker to pick it up ─────────────────────────────────
def wait_for_processing(camera_id: str, remote_name: str,
                        timeout: int = 30) -> bool:
    """Poll the DB until the snapshot is recorded."""
    import re

    # Normalise camera_id to what the worker uses as camera_id in DB (uppercase)
    db_camera_id = camera_id.upper()

    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    deadline = time.time() + timeout
    stem = Path(remote_name).stem  # e.g. cam_snap_20260219_123456

    print(f"\n  Waiting up to {timeout}s for worker to process {remote_name}...")
    dots = 0
    while time.time() < deadline:
        cur.execute("""
            SELECT s.id, s.file_path, s.received_at, s.processed_at
            FROM snapshots s
            JOIN cameras c ON c.id = s.camera_id
            WHERE c.camera_id = %s
              AND s.file_path LIKE %s
            ORDER BY s.received_at DESC
            LIMIT 1
        """, (db_camera_id, f"%{stem}%"))

        row = cur.fetchone()
        if row:
            conn.close()
            return row

        time.sleep(1)
        dots += 1
        print(f"  {'.' * dots}", end="\r")

    conn.close()
    return None


# ── Step 3: Print detection summary ───────────────────────────────────────
def print_results(row, camera_id: str):
    snap_id, file_path, received_at, processed_at = row
    hr("=")
    print(OK("  DETECTION RESULTS"))
    hr("=")
    print(f"  Snapshot ID    : {snap_id}")
    print(f"  Camera         : {camera_id.upper()}")
    print(f"  File           : {file_path}")
    print(f"  Received at    : {received_at}")
    print(f"  Processed at   : {processed_at or WARN('(pending)')}")

    # Fetch detections from the detections table
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()
    cur.execute("""
        SELECT class, confidence, bbox_json
        FROM detections
        WHERE snapshot_id = %s
        ORDER BY confidence DESC
    """, (snap_id,))
    detections = cur.fetchall()
    conn.close()

    vehicle_classes = {"car", "truck", "bus", "motorcycle", "bicycle"}
    vehicle_count = sum(1 for d in detections if d[0] in vehicle_classes)

    print(f"  Vehicle count  : {INFO(str(vehicle_count))}")
    print(f"  Total objects  : {len(detections)}")

    if detections:
        hr()
        print(f"  YOLO detections ({len(detections)}):")
        for cls, conf, bbox in detections[:10]:
            marker = "🚗" if cls in vehicle_classes else "  "
            print(f"    {marker} {cls:<14}  conf={conf:.0%}  bbox={bbox}")
    else:
        print(WARN("  No detections found (YOLO may still be processing)"))
    hr("=")


# ── Step 4: Check zone states ─────────────────────────────────────────────
def check_zones(camera_id: str):
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()
    cur.execute("""
        SELECT z.name, zs.occupied_units, zs.available_units, zs.state, zs.updated_at
        FROM zone_states zs
        JOIN zones z ON z.id = zs.zone_id
        JOIN cameras c ON c.id = z.camera_id
        WHERE c.camera_id = %s
        ORDER BY z.name
    """, (camera_id.upper(),))
    rows = cur.fetchall()
    conn.close()

    if rows:
        print(f"\n  Zone states for {camera_id.upper()}:")
        for name, occ, avail, state, upd in rows:
            is_free = state.upper() in ("FREE", "AVAILABLE", "EMPTY")
            state_col = OK(state) if is_free else WARN(state)
            print(f"    {name:<20}  occupied={occ}  available={avail}  state={state_col}  updated={upd}")
    else:
        print(WARN(f"\n  No zones configured for {camera_id.upper()} yet."))
        print(f"  → Set up zones at: {API_BASE}/admin/zones")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="CamPark E2E FTP Detection Test")
    parser.add_argument("--image",   default=None, help="Path to test image (JPG)")
    parser.add_argument("--camera",  default="cam001", choices=list(CAMERAS))
    parser.add_argument("--timeout", default=30, type=int,
                        help="Seconds to wait for worker (default 30)")
    args = parser.parse_args()

    password = CAMERAS[args.camera]
    image    = pick_image(args.image)

    hr("=")
    print(INFO("  CamPark E2E Test  —  FTP Upload → YOLO Detection → DB Check"))
    hr("=")
    print(f"  Image  : {image}")
    print(f"  Camera : {args.camera}")

    # 1. Upload via FTP
    hr()
    print(INFO("  [1/3]  FTP Upload"))
    hr()
    try:
        remote_name = ftp_upload(args.camera, password, image)
        print(OK(f"  ✓ Uploaded as {remote_name}"))
    except Exception as e:
        print(FAIL(f"  ✗ FTP upload failed: {e}"))
        sys.exit(1)

    # 2. Wait for worker
    hr()
    print(INFO("  [2/3]  Waiting for worker to process image"))
    hr()
    row = wait_for_processing(args.camera, remote_name, timeout=args.timeout)

    if not row:
        print(FAIL(f"\n  ✗ Worker did not process '{remote_name}' within {args.timeout}s"))
        print()
        print("  Possible causes:")
        print("  • Worker crashed — check logs: docker logs campark-worker --tail 50")
        print("  • YOLO model downloading for first time (can take 1-2 min)")
        print("  • File in quarantine (check /data/ftp/cam001/incoming/.quarantine/)")
        sys.exit(1)

    # 3. Print results
    hr()
    print(INFO("  [3/3]  Detection Results"))
    print_results(row, args.camera)

    # 4. Zone states
    check_zones(args.camera)

    print()
    print(OK("  ✓ E2E test passed!"))
    print(f"  Dashboard: {API_BASE}/")
    print(f"  Events:    {API_BASE}/admin/events")
    print()


if __name__ == "__main__":
    main()
