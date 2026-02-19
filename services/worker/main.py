import logging
import os
import time
from pathlib import Path

from db import Camera, SessionLocal
from infer.pipeline import InferencePipeline

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("worker")

FTP_INGEST_PATH = os.getenv("FTP_INGEST_PATH", "/data/ftp")
IMAGE_ROOT = os.getenv("IMAGE_ROOT", "/data/images")
YOLO_CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", "0.80"))
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
OVERLAP_THRESHOLD = float(os.getenv("OVERLAP_THRESHOLD", "0.30"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))
YOLO_ENABLED = os.getenv("YOLO_ENABLED", "false").lower() == "true"


def run_worker():
    pipeline = InferencePipeline(
        image_root=IMAGE_ROOT,
        yolo_enabled=YOLO_ENABLED,
        yolo_model=YOLO_MODEL,
        yolo_confidence=YOLO_CONFIDENCE,
        overlap_threshold=OVERLAP_THRESHOLD,
    )

    print("CamPark worker started")
    log.info(
        "Zone classifier mode=%s  YOLO evidence=%s  poll=%.1fs",
        os.getenv("ZONECLS_MODE", "placeholder"),
        YOLO_ENABLED,
        POLL_INTERVAL,
    )

    while True:
        session = SessionLocal()
        try:
            cameras = session.query(Camera).all()
            for camera in cameras:
                # Determine the incoming directory based on protocol
                # FTP cameras use ftp_username, others use camera_id (lowercase)
                if camera.ingest_protocol == "ftp" and camera.ftp_username:
                    ingest_id = camera.ftp_username
                else:
                    ingest_id = camera.ftp_username or camera.camera_id.lower()
                incoming_dir = Path(FTP_INGEST_PATH) / ingest_id / "incoming"
                if not incoming_dir.exists():
                    continue
                # Use recursive glob to handle Dahua/Hikvision deep folder structures
                # Skip .quarantine directories to avoid re-processing corrupt files
                jpg_files = [
                    f for f in incoming_dir.rglob("*.jpg")
                    if ".quarantine" not in f.parts
                ]
                if jpg_files:
                    log.info("Found %d JPG files for camera %s in %s", len(jpg_files), camera.camera_id, incoming_dir)
                for file_path in jpg_files:
                    pipeline.process_snapshot(session, camera, str(file_path))
            session.commit()
        except Exception as exc:
            session.rollback()
            log.exception("Worker error: %s", exc)
        finally:
            session.close()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_worker()
