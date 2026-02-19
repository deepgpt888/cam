import hashlib
import json
import logging
import os
import shutil
import time
import traceback
from datetime import datetime
from PIL import Image, UnidentifiedImageError

from db import Detection, Snapshot, Zone, ZoneEvent, ZoneState
from infer.zonecls.zone_classifier import ZoneClassifier
from yolo_processor import YoloProcessor

log = logging.getLogger(__name__)

VALID_CLASSES = {"car", "truck", "motorcycle", "bicycle"}


class InferencePipeline:
    def __init__(
        self,
        image_root: str,
        yolo_enabled: bool,
        yolo_model: str,
        yolo_confidence: float,
        overlap_threshold: float,
    ):
        self.image_root = image_root
        self.yolo_enabled = yolo_enabled
        self.zone_classifier = ZoneClassifier.from_env()
        self.pending_states = {}
        self.yolo_processor = None
        if self.yolo_enabled:
            self.yolo_processor = YoloProcessor(
                model_path=yolo_model,
                confidence=yolo_confidence,
                overlap_threshold=overlap_threshold,
            )

    def process_snapshot(self, session, camera, file_path):
        if not _file_is_stable(file_path):
            return

        file_hash = _sha256_file(file_path)
        if file_hash is None:
            return
        existing = session.query(Snapshot).filter(Snapshot.file_hash == file_hash).first()
        if existing:
            _quarantine(file_path)
            return

        now = datetime.utcnow()
        try:
            image = Image.open(file_path)
            image.verify()
            image = Image.open(file_path).convert("RGB")
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            log.warning("Corrupt image %s – moving to quarantine: %s", file_path, exc)
            _quarantine(file_path)
            return
        width, height = image.size

        date_folder = now.strftime("%Y%m%d")
        dest_dir = os.path.join(self.image_root, camera.camera_id, date_folder)
        _ensure_dir(dest_dir)

        dest_path = os.path.join(dest_dir, os.path.basename(file_path))
        shutil.move(file_path, dest_path)

        relative_path = os.path.relpath(dest_path, self.image_root)

        snapshot = Snapshot(
            camera_id=camera.id,
            file_path=relative_path,
            file_hash=file_hash,
            width=width,
            height=height,
            received_at=now,
            created_at=now,
        )
        session.add(snapshot)

        camera.last_seen_at = now
        camera.last_snapshot_at = now
        camera.status = "ONLINE"

        session.flush()

        zones = session.query(Zone).filter(Zone.camera_id == camera.id).all()
        occupied_any = False
        for zone in zones:
            zone_polygon = json.loads(zone.polygon_json)
            prediction = self.zone_classifier.predict_zone_occupied(image, zone_polygon)
            occupied = prediction.occupied
            occupied_any = occupied_any or occupied

            occupied_units = 1 if occupied else 0
            capacity = zone.capacity_units or 1
            state = _zone_state_label(occupied_units, capacity)

            zone_state = session.query(ZoneState).filter(ZoneState.zone_id == zone.id).first()
            if not zone_state:
                zone_state = ZoneState(
                    zone_id=zone.id,
                    occupied_units=occupied_units,
                    available_units=max(capacity - occupied_units, 0),
                    state=state,
                    last_change_at=now,
                    updated_at=now,
                )
                session.add(zone_state)
                continue

            if zone_state.occupied_units != occupied_units:
                pending = self.pending_states.get(zone.id)
                if pending and pending["units"] == occupied_units:
                    pending["count"] += 1
                else:
                    self.pending_states[zone.id] = {"units": occupied_units, "count": 1}

                if self.pending_states[zone.id]["count"] < 2:
                    continue

                self.pending_states.pop(zone.id, None)

                event = ZoneEvent(
                    zone_id=zone.id,
                    snapshot_id=snapshot.id,
                    old_state=zone_state.state,
                    new_state=state,
                    old_units=zone_state.occupied_units,
                    new_units=occupied_units,
                    event_type="OCCUPANCY_CHANGE",
                    triggered_at=now,
                    created_at=now,
                )
                zone_state.occupied_units = occupied_units
                zone_state.available_units = max(capacity - occupied_units, 0)
                zone_state.state = state
                zone_state.last_change_at = now
                zone_state.updated_at = now
                session.add(event)
            else:
                self.pending_states.pop(zone.id, None)

        if self.yolo_enabled and self.yolo_processor and occupied_any:
            detections = self.yolo_processor.detect(dest_path)
            filtered = [d for d in detections if d["class"] in VALID_CLASSES]
            for det in filtered:
                det_row = Detection(
                    snapshot_id=snapshot.id,
                    class_name=det["class"],
                    confidence=det["confidence"],
                    bbox_json=self.yolo_processor.to_bbox_json(det, width, height),
                    created_at=now,
                )
                session.add(det_row)

        snapshot.processed_at = datetime.utcnow()


def _sha256_file(path):
    try:
        hasher = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (FileNotFoundError, PermissionError) as exc:
        log.warning("Cannot hash %s: %s", path, exc)
        return None


def _file_is_stable(path):
    try:
        size1 = os.path.getsize(path)
        time.sleep(0.2)
        size2 = os.path.getsize(path)
        return size1 == size2 and size1 > 0
    except (FileNotFoundError, PermissionError):
        return False


def _quarantine(file_path):
    """Move bad files out of incoming so the worker doesn't retry them forever."""
    quarantine_dir = os.path.join(os.path.dirname(file_path), ".quarantine")
    os.makedirs(quarantine_dir, exist_ok=True)
    dest = os.path.join(quarantine_dir, os.path.basename(file_path))
    try:
        shutil.move(file_path, dest)
        log.info("Quarantined %s -> %s", file_path, dest)
    except OSError as exc:
        log.warning("Failed to quarantine %s: %s", file_path, exc)


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _zone_state_label(occupied, capacity):
    if occupied <= 0:
        return "FREE"
    if occupied >= capacity:
        return "FULL"
    return "PARTIAL"
