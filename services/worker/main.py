import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from db import Camera, SessionLocal
from infer.pipeline import InferencePipeline

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("worker")

FTP_INGEST_PATH   = os.getenv("FTP_INGEST_PATH",   "/data/ftp")
IMAGE_ROOT        = os.getenv("IMAGE_ROOT",         "/data/images")
YOLO_CONFIDENCE   = float(os.getenv("YOLO_CONFIDENCE",   "0.80"))
YOLO_MODEL        = os.getenv("YOLO_MODEL",          "yolov8n.pt")
OVERLAP_THRESHOLD = float(os.getenv("OVERLAP_THRESHOLD", "0.30"))
POLL_INTERVAL     = float(os.getenv("POLL_INTERVAL",     "1.0"))
YOLO_ENABLED      = os.getenv("YOLO_ENABLED", "false").lower() == "true"

# How many cameras to process in parallel.
# Rule of thumb: 2× CPU cores.  Override with WORKER_THREADS env var.
WORKER_THREADS = int(os.getenv("WORKER_THREADS", str(min(os.cpu_count() or 2, 16))))


def _incoming_dir(camera: Camera) -> Path:
    if camera.ingest_protocol == "ftp" and camera.ftp_username:
        ingest_id = camera.ftp_username
    else:
        ingest_id = camera.ftp_username or camera.camera_id.lower()
    return Path(FTP_INGEST_PATH) / ingest_id / "incoming"


def _process_camera(pipeline: InferencePipeline, camera: Camera) -> int:
    """Process all pending images for one camera. Returns number of files handled."""
    incoming = _incoming_dir(camera)
    if not incoming.exists():
        return 0

    jpg_files: List[Path] = [
        f for f in incoming.rglob("*.jpg")
        if ".quarantine" not in f.parts
    ]
    if not jpg_files:
        return 0

    session = SessionLocal()
    try:
        # Re-query the camera inside this thread's own session
        from db import Camera as CameraModel
        cam = session.query(CameraModel).filter(CameraModel.id == camera.id).first()
        if cam is None:
            return 0
        for file_path in jpg_files:
            pipeline.process_snapshot(session, cam, str(file_path))
        session.commit()
        return len(jpg_files)
    except Exception as exc:
        session.rollback()
        log.exception("[%s] camera processing error: %s", camera.camera_id, exc)
        return 0
    finally:
        session.close()


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
        "Zone classifier mode=%s  YOLO=%s  threads=%d  poll=%.1fs  hours=%s-%s",
        os.getenv("ZONECLS_MODE", "placeholder"),
        YOLO_ENABLED,
        WORKER_THREADS,
        POLL_INTERVAL,
        os.getenv("OPERATING_HOURS_START", "6"),
        os.getenv("OPERATING_HOURS_END",   "18"),
    )

    executor = ThreadPoolExecutor(max_workers=WORKER_THREADS)

    while True:
        # Fetch camera list once per cycle in a short-lived session
        list_session = SessionLocal()
        try:
            cameras = list_session.query(Camera).all()
        finally:
            list_session.close()

        if cameras:
            futures = {
                executor.submit(_process_camera, pipeline, cam): cam.camera_id
                for cam in cameras
            }
            total_files = 0
            for future in as_completed(futures):
                cam_id = futures[future]
                try:
                    n = future.result()
                    total_files += n
                    if n:
                        log.debug("[%s] processed %d file(s)", cam_id, n)
                except Exception as exc:
                    log.exception("[%s] future error: %s", cam_id, exc)

            if total_files:
                log.info("Cycle complete: %d camera(s), %d file(s) processed",
                         len(cameras), total_files)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_worker()
