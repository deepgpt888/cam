import hashlib
import json
import logging
import os
import shutil
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image, UnidentifiedImageError

from db import Detection, Snapshot, SystemSetting, Zone, ZoneEvent, ZoneState
from infer.zonecls.zone_classifier import ZoneClassifier
from yolo_processor import YoloProcessor

log = logging.getLogger(__name__)

VALID_CLASSES = {"car", "truck", "motorcycle", "bicycle"}

# Env-var defaults (used before first DB refresh and as fallback)
_DEFAULT_OPERATING_START    = int(os.getenv("OPERATING_HOURS_START", "0"))
_DEFAULT_OPERATING_END      = int(os.getenv("OPERATING_HOURS_END",   "24"))
_DEFAULT_SCENE_DIFF_THRESHOLD = float(os.getenv("SCENE_DIFF_THRESHOLD", "6.0"))

# Timezone for operating-hours check — must match the camera's local timezone.
# Defaults to Asia/Kuala_Lumpur (UTC+8). Override with CAMERA_TZ env var.
_CAMERA_TZ = ZoneInfo(os.getenv("CAMERA_TZ", "Asia/Kuala_Lumpur"))

# Thumbnail size used for perceptual diff (smaller = faster, 32 is plenty)
_THUMB = (32, 32)


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
        # Per-camera perceptual fingerprints: camera_id -> np.ndarray (32x32 uint8)
        self._last_thumb: Dict[int, np.ndarray] = {}

        # Runtime settings — seeded from env, refreshed from DB each worker cycle
        self.operating_start    = _DEFAULT_OPERATING_START
        self.operating_end      = _DEFAULT_OPERATING_END
        self.scene_diff_threshold = _DEFAULT_SCENE_DIFF_THRESHOLD

    # ------------------------------------------------------------------
    # Settings refresh (called once per worker cycle from main.py)
    # ------------------------------------------------------------------

    def refresh_settings(self, session) -> None:
        """Re-read operating hours and scene diff threshold from system_settings table."""
        try:
            rows = session.query(SystemSetting).filter(
                SystemSetting.key.in_([
                    "operating_hours_start",
                    "operating_hours_end",
                    "scene_diff_threshold",
                ])
            ).all()
            settings = {r.key: r.value for r in rows}
            self.operating_start      = int(settings.get("operating_hours_start",   str(_DEFAULT_OPERATING_START)))
            self.operating_end        = int(settings.get("operating_hours_end",     str(_DEFAULT_OPERATING_END)))
            self.scene_diff_threshold = float(settings.get("scene_diff_threshold",  str(_DEFAULT_SCENE_DIFF_THRESHOLD)))
        except Exception as exc:  # DB unavailable — keep previous values
            log.warning("refresh_settings failed, keeping previous values: %s", exc)

    # ------------------------------------------------------------------
    # Perceptual diff helpers
    # ------------------------------------------------------------------

    def _thumb_of(self, image: Image.Image) -> np.ndarray:
        """Downsample image to a small grayscale thumbnail for fast comparison."""
        return np.array(image.resize(_THUMB, Image.BILINEAR).convert("L"), dtype=np.float32)

    def _scene_changed(self, camera_id: int, thumb: np.ndarray) -> Tuple[bool, float]:
        """Return (changed, mean_pixel_delta). Updates stored thumbnail on change."""
        if self.scene_diff_threshold <= 0:
            return True, 255.0  # disabled — always process
        prev = self._last_thumb.get(camera_id)
        if prev is None:
            # First image ever for this camera — always process
            self._last_thumb[camera_id] = thumb
            return True, 255.0
        diff = float(np.mean(np.abs(thumb - prev)))
        if diff >= self.scene_diff_threshold:
            self._last_thumb[camera_id] = thumb
            return True, diff
        return False, diff

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

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

        # ---- Operating hours gate ----
        # Use camera's local timezone (CAMERA_TZ env var, default Asia/Kuala_Lumpur)
        local_hour = datetime.now(tz=_CAMERA_TZ).hour
        in_hours = self.operating_start <= local_hour < self.operating_end
        if not in_hours:
            # Outside operating window — record heartbeat, skip inference
            camera.last_seen_at = now
            camera.status = "ONLINE"
            _discard(file_path)  # remove file, nothing to store
            log.debug("[%s] Outside operating hours (%02d:00 — window %02d–%02d) — heartbeat only",
                      camera.camera_id, local_hour, self.operating_start, self.operating_end)
            return

        try:
            image = Image.open(file_path)
            image.verify()
            image = Image.open(file_path).convert("RGB")
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            log.warning("Corrupt image %s – moving to quarantine: %s", file_path, exc)
            _quarantine(file_path)
            return
        width, height = image.size

        # ---- Perceptual diff — smart skip ----
        thumb = self._thumb_of(image)
        changed, delta = self._scene_changed(camera.id, thumb)
        if not changed:
            # Scene is static — update heartbeat only, discard image
            camera.last_seen_at = now
            camera.status = "ONLINE"
            _discard(file_path)
            log.debug("[%s] Scene unchanged (diff=%.2f < %.2f) — heartbeat only",
                      camera.camera_id, delta, self.scene_diff_threshold)
            return

        log.info("[%s] Scene changed (diff=%.2f) — running inference",
                 camera.camera_id, delta)

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

        # ---- Run YOLO detection (if enabled) ----
        all_detections = []
        vehicle_detections = []
        if self.yolo_enabled and self.yolo_processor:
            all_detections = self.yolo_processor.detect(dest_path)
            vehicle_detections = [d for d in all_detections if d["class"] in VALID_CLASSES]
            log.info("[%s] YOLO detected %d vehicles (%d total objects)",
                     camera.camera_id, len(vehicle_detections), len(all_detections))

        # ---- Zone occupancy ----
        zones = session.query(Zone).filter(Zone.camera_id == camera.id).all()
        for zone in zones:
            # __campark_meta__ zones are real parking spaces whose name field
            # carries lane-editor metadata.  Process them normally for occupancy.
            zone_polygon = json.loads(zone.polygon_json)

            if self.yolo_enabled and self.yolo_processor:
                # YOLO-based zone occupancy: count vehicles overlapping this zone
                zone_polygon_px = [
                    [pt[0] / 100.0 * width, pt[1] / 100.0 * height]
                    for pt in zone_polygon
                ]
                zone_vehicles = self.yolo_processor.filter_detections_for_zone(
                    vehicle_detections, zone_polygon_px,
                )
                occupied_units = len(zone_vehicles)
                log.info("[%s] Zone %s: %d vehicle(s) detected (capacity=%d)",
                         camera.camera_id, zone.zone_id, occupied_units, zone.capacity_units or 1)
            else:
                # Fallback: ZoneClassifier (placeholder or ONNX)
                prediction = self.zone_classifier.predict_zone_occupied(image, zone_polygon)
                occupied_units = 1 if prediction.occupied else 0

            capacity = zone.capacity_units or 1
            occupied_units = min(occupied_units, capacity)  # cap at capacity
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

        # ---- Store YOLO detections as evidence ----
        for det in vehicle_detections:
            det_row = Detection(
                snapshot_id=snapshot.id,
                class_name=det["class"],
                confidence=det["confidence"],
                bbox_json=self.yolo_processor.to_bbox_json(det, width, height),
                created_at=now,
            )
            session.add(det_row)

        snapshot.processed_at = datetime.utcnow()


def _discard(file_path):
    """Remove a file quietly (used for out-of-hours / unchanged frames)."""
    try:
        os.remove(file_path)
    except OSError:
        pass


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
