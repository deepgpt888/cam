import hashlib
import json
import os
import secrets
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from typing import Optional, Tuple

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from flask.wrappers import Response
from sqlalchemy import text, func
from sqlalchemy.types import Numeric as db_Numeric

from app.db import (
    APIClient,
    Camera,
    CameraHealthEvent,
    Detection,
    Project,
    SessionLocal,
    Site,
    Snapshot,
    SystemSetting,
    TokenLedger,
    Zone,
    ZoneEvent,
    ZoneState,
)

APP_VERSION = "0.1.0"
IMAGE_ROOT = os.getenv("IMAGE_ROOT", "/data/images")
FTP_INGEST_PATH = os.getenv("FTP_INGEST_PATH", "/data/ftp")
HEALTH_INTERVAL_SECONDS = int(os.getenv("HEALTH_INTERVAL_SECONDS", "30"))
ENABLE_HEALTH_MONITOR = os.getenv("ENABLE_HEALTH_MONITOR", "true").lower() == "true"
STALE_SECONDS = int(os.getenv("STALE_SECONDS", "150"))
OFFLINE_SECONDS = int(os.getenv("OFFLINE_SECONDS", "300"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme_poc")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-to-random-32-character-string")
app.permanent_session_lifetime = timedelta(hours=12)


def sync_ftp_users():
    """Write FTP user list from DB to shared JSON file for the FTP container.
    The FTP container watches this file and reloads users automatically."""
    try:
        s = SessionLocal()
        cameras = s.query(Camera).filter(
            Camera.ingest_protocol == "ftp",
            Camera.ftp_username.isnot(None),
            Camera.ftp_password_hash.isnot(None),
        ).all()
        users = []
        for c in cameras:
            users.append({
                "username": c.ftp_username,
                "password": c.ftp_password_hash,  # stored as plaintext for pure-ftpd
            })
        s.close()

        sync_path = os.path.join(FTP_INGEST_PATH, ".ftp_users.json")
        with open(sync_path, "w") as f:
            json.dump({"users": users, "updated_at": datetime.utcnow().isoformat()}, f)
        app.logger.info("FTP sync: wrote %d user(s) to %s", len(users), sync_path)
    except Exception as exc:
        app.logger.error("FTP sync failed: %s", exc)


# --------------- Session-based admin auth ---------------

@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Render login form (GET) or authenticate (POST)."""
    if session.get("admin_logged_in"):
        return redirect("/admin/scada")
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session["admin_user"] = username
            session.permanent = True
            next_url = request.args.get("next", "/admin/scada")
            return redirect(next_url)
        error = "Invalid username or password"
    return render_template("login.html", error=error, version=APP_VERSION)


@app.route("/logout")
def logout_page():
    session.clear()
    return redirect("/login")


@app.before_request
def admin_auth_guard():
    """Require session login for all /admin/ routes."""
    # Allow public routes
    if request.path in ("/login", "/logout", "/health") or request.path.startswith("/static"):
        return None
    # API key-protected routes don't need session auth
    if not request.path.startswith("/admin"):
        return None
    if not session.get("admin_logged_in"):
        return redirect(url_for("login_page", next=request.path))


def to_iso(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def parse_iso(value):
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.RequestException:
        pass


def hash_api_key(raw_key):
    return hashlib.sha256(raw_key.encode()).hexdigest()


def check_api_key(session) -> Tuple[Optional[Tuple[Response, int]], Optional[APIClient]]:
    """Returns (error_response, None) on failure, or (None, client_or_None) on success."""
    if not REQUIRE_API_KEY:
        return None, None
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        return (jsonify({"error": "missing_api_key"}), 401), None
    key_hash = hash_api_key(raw_key)
    client = session.query(APIClient).filter(APIClient.api_key_hash == key_hash).first()
    if not client:
        return (jsonify({"error": "invalid_api_key"}), 401), None
    if request.method != "GET":
        return (jsonify({"error": "read_only"}), 403), None
    return None, client


def require_api_key(session):
    """Wrapper that returns (error_response_or_None, api_client_or_None).
    Callers should do: err, client = require_api_key(session); if err: return err
    """
    error, client = check_api_key(session)
    return error, client


def record_token(session, api_client, status_code, endpoint, response_time_ms, tokens_used=0):
    """Log API usage. tokens_used=0 for free tracking, N for occupancy charges (1 per car park/zone)."""
    if not api_client:
        return
    entry = TokenLedger(
        api_client_id=api_client.id,
        endpoint=endpoint,
        method=request.method,
        status_code=status_code,
        response_time_ms=response_time_ms,
        tokens_used=tokens_used,
        created_at=datetime.utcnow(),
    )
    session.add(entry)


def record_health_event(session, camera, status, message, resolved_at=None):
    event = CameraHealthEvent(
        camera_id=camera.id,
        health_status=status,
        message=message,
        triggered_at=datetime.utcnow(),
        resolved_at=resolved_at,
        created_at=datetime.utcnow(),
    )
    session.add(event)


def monitor_camera_health():
    while True:
        session = SessionLocal()
        try:
            now = datetime.utcnow()
            cameras = session.query(Camera).all()
            for camera in cameras:
                if camera.last_seen_at is None:
                    continue
                age_seconds = (now - camera.last_seen_at).total_seconds()
                if age_seconds > OFFLINE_SECONDS:
                    new_status = "OFFLINE"
                    message = f"Camera {camera.camera_id} OFFLINE (no data >{OFFLINE_SECONDS}s)"
                elif age_seconds > STALE_SECONDS:
                    new_status = "STALE"
                    message = f"Camera {camera.camera_id} STALE (no data >{STALE_SECONDS}s)"
                else:
                    new_status = "ONLINE"
                    message = f"Camera {camera.camera_id} ONLINE"

                if camera.status != new_status:
                    camera.status = new_status
                    record_health_event(session, camera, new_status, message)
                    send_telegram(message)
            session.commit()
        finally:
            session.close()
        time.sleep(HEALTH_INTERVAL_SECONDS)


@app.route("/")
def index():
    return redirect("/admin/scada")


@app.route("/health", methods=["GET"])
def health():
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "version": APP_VERSION})
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503
    finally:
        session.close()


@app.route("/api/v1/sites/<int:site_id>/status", methods=["GET"])
def site_status(site_id):  # type: ignore[return-value]
    session = SessionLocal()
    try:
        err, api_client = check_api_key(session)
        if err:
            return err
        start_time = time.time()
        site = session.query(Site).filter(Site.id == site_id).first()
        if not site:
            return jsonify({"error": "site_not_found"}), 404

        zones = (
            session.query(Zone, ZoneState)
            .join(ZoneState, ZoneState.zone_id == Zone.id)
            .join(Camera, Camera.id == Zone.camera_id)
            .filter(Camera.site_id == site_id)
            .all()
        )
        response_zones = []
        total_occupied = 0
        total_available = 0
        for zone, zone_state in zones:
            occupied = zone_state.occupied_units or 0
            available = zone_state.available_units
            if available is None:
                capacity = zone.capacity_units or 1
                available = max(capacity - occupied, 0)
            response_zones.append(
                {
                    "zone_id": zone.zone_id,
                    "state": zone_state.state or "FREE",
                    "occupied_units": occupied,
                    "available_units": available,
                }
            )
            total_occupied += occupied
            total_available += available

        # Charge 1 token per zone (car park) returned
        num_zones = len(response_zones)
        response = jsonify(
            {
                "site_id": site_id,
                "ts": to_iso(datetime.utcnow()),
                "zones": response_zones,
                "totals": {
                    "occupied_units": total_occupied,
                    "available_units": total_available,
                },
                "tokens_charged": num_zones,
            }
        )
        record_token(
            session,
            api_client,
            200,
            request.path,
            int((time.time() - start_time) * 1000),
            tokens_used=num_zones,
        )
        session.commit()
        return response
    finally:
        session.close()


@app.route("/api/v1/cameras/<string:camera_id>/status", methods=["GET"])
def camera_status(camera_id):  # type: ignore[return-value]
    session = SessionLocal()
    try:
        err, api_client = check_api_key(session)
        if err:
            return err
        camera = session.query(Camera).filter(Camera.camera_id == camera_id).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404

        snapshot = (
            session.query(Snapshot)
            .filter(Snapshot.camera_id == camera.id)
            .order_by(Snapshot.received_at.desc())
            .first()
        )
        detections = []
        if snapshot:
            rows = (
                session.query(Detection)
                .filter(Detection.snapshot_id == snapshot.id)
                .all()
            )
            for row in rows:
                detections.append(
                    {
                        "class": row.class_name,
                        "confidence": row.confidence,
                        "bbox": json.loads(row.bbox_json) if row.bbox_json else None,
                    }
                )

        return jsonify(
            {
                "camera_id": camera.camera_id,
                "status": camera.status,
                "last_seen_at": to_iso(camera.last_seen_at),
                "last_snapshot_at": to_iso(camera.last_snapshot_at),
                "latest_snapshot": {
                    "id": snapshot.id if snapshot else None,
                    "received_at": to_iso(snapshot.received_at) if snapshot else None,
                    "file_path": snapshot.file_path if snapshot else None,
                },
                "detections": detections,
            }
        )
    finally:
        session.close()


@app.route("/api/v1/cameras/<string:camera_id>/health", methods=["GET"])
def camera_health(camera_id):  # type: ignore[return-value]
    session = SessionLocal()
    try:
        err, api_client = check_api_key(session)
        if err:
            return err
        camera = session.query(Camera).filter(Camera.camera_id == camera_id).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404
        now = datetime.utcnow()
        age_seconds = None
        if camera.last_seen_at:
            age_seconds = (now - camera.last_seen_at).total_seconds()
        return jsonify(
            {
                "camera_id": camera.camera_id,
                "status": camera.status,
                "last_seen_at": to_iso(camera.last_seen_at),
                "age_seconds": age_seconds,
            }
        )
    finally:
        session.close()


@app.route("/api/v1/sites/<int:site_id>/events", methods=["GET"])
def site_events(site_id):  # type: ignore[return-value]
    session = SessionLocal()
    try:
        err, api_client = check_api_key(session)
        if err:
            return err
        start = parse_iso(request.args.get("from"))
        end = parse_iso(request.args.get("to"))
        query = (
            session.query(ZoneEvent, Zone, Camera)
            .join(Zone, Zone.id == ZoneEvent.zone_id)
            .join(Camera, Camera.id == Zone.camera_id)
            .filter(Camera.site_id == site_id)
            .order_by(ZoneEvent.triggered_at.desc())
        )
        if start:
            query = query.filter(ZoneEvent.triggered_at >= start)
        if end:
            query = query.filter(ZoneEvent.triggered_at <= end)

        events = []
        for event, zone, camera in query.limit(200).all():
            events.append(
                {
                    "event_id": event.id,
                    "zone_id": zone.zone_id,
                    "camera_id": camera.camera_id,
                    "event_type": event.event_type,
                    "old_state": event.old_state,
                    "new_state": event.new_state,
                    "old_units": event.old_units,
                    "new_units": event.new_units,
                    "triggered_at": to_iso(event.triggered_at),
                }
            )

        return jsonify({"site_id": site_id, "events": events})
    finally:
        session.close()


@app.route("/api/v1/evidence/<int:event_id>", methods=["GET"])
def evidence(event_id):  # type: ignore[return-value]
    session = SessionLocal()
    try:
        err, api_client = check_api_key(session)
        if err:
            return err
        event = session.query(ZoneEvent).filter(ZoneEvent.id == event_id).first()
        if not event or not event.snapshot_id:
            return jsonify({"error": "event_not_found"}), 404

        snapshot = (
            session.query(Snapshot)
            .filter(Snapshot.id == event.snapshot_id)
            .first()
        )
        if not snapshot:
            return jsonify({"error": "snapshot_not_found"}), 404

        abs_path = os.path.join(IMAGE_ROOT, snapshot.file_path)
        if not os.path.exists(abs_path):
            return jsonify({"error": "file_not_found"}), 404

        return send_file(abs_path, mimetype="image/jpeg")
    finally:
        session.close()


@app.route("/api/v1/cameras/<string:camera_id>/snapshot-latest", methods=["GET"])
def latest_snapshot(camera_id):
    session = SessionLocal()
    try:
        camera = session.query(Camera).filter(Camera.camera_id == camera_id).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404

        snapshot = (
            session.query(Snapshot)
            .filter(Snapshot.camera_id == camera.id)
            .order_by(Snapshot.received_at.desc())
            .first()
        )
        if not snapshot:
            return jsonify({"error": "snapshot_not_found"}), 404

        abs_path = os.path.join(IMAGE_ROOT, snapshot.file_path)
        if not os.path.exists(abs_path):
            return jsonify({"error": "file_not_found"}), 404

        return send_file(abs_path, mimetype="image/jpeg")
    finally:
        session.close()


@app.route("/admin/health", methods=["GET"])
def admin_health():
    if request.accept_mimetypes.accept_html:
        return render_template("admin_health.html")

    return admin_health_json()


@app.route("/admin/health.json", methods=["GET"])
def admin_health_json():
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        cameras = session.query(Camera).all()
        response = []
        for camera in cameras:
            age_seconds = None
            if camera.last_seen_at:
                age_seconds = (now - camera.last_seen_at).total_seconds()
            response.append(
                {
                    "camera_id": camera.camera_id,
                    "status": camera.status,
                    "last_seen_at": to_iso(camera.last_seen_at),
                    "age_seconds": age_seconds,
                }
            )
        return jsonify({"cameras": response})
    finally:
        session.close()


@app.route("/admin/cameras", methods=["GET"])
def admin_cameras():
    return render_template("admin_cameras.html")


@app.route("/admin/cameras.json", methods=["GET"])
def admin_cameras_json():
    session = SessionLocal()
    try:
        cameras = session.query(Camera).all()
        response = []
        for camera in cameras:
            response.append(
                {
                    "camera_id": camera.camera_id,
                    "name": camera.name,
                    "brand": camera.brand,
                    "model": camera.model,
                    "ingest_protocol": camera.ingest_protocol or "ftp",
                    "status": camera.status or "UNKNOWN",
                    "last_seen_at": to_iso(camera.last_seen_at),
                }
            )
        return jsonify({"cameras": response})
    finally:
        session.close()


@app.route("/admin/cameras", methods=["POST"])
def create_camera():
    payload = request.get_json(silent=True) or {}
    camera_id = payload.get("camera_id")
    name = payload.get("name")
    site_id = payload.get("site_id", 1)
    brand = payload.get("brand")
    model = payload.get("model")
    ingest_protocol = payload.get("ingest_protocol", "ftp")
    ftp_username = payload.get("ftp_username")
    ftp_password = payload.get("ftp_password")
    connection_config = payload.get("connection_config")
    lapi_device_code = payload.get("lapi_device_code")
    lapi_secret = payload.get("lapi_secret")

    if not camera_id:
        return jsonify({"error": "camera_id_required"}), 400

    # FTP protocol requires ftp_username and ftp_password
    if ingest_protocol == "ftp" and not ftp_username:
        return jsonify({"error": "ftp_username_required_for_ftp_protocol"}), 400
    if ingest_protocol == "ftp" and not ftp_password:
        return jsonify({"error": "ftp_password_required_for_ftp_protocol"}), 400

    session = SessionLocal()
    try:
        existing = session.query(Camera).filter(Camera.camera_id == camera_id).first()
        if existing:
            return jsonify({"error": "camera_id_exists"}), 409

        camera = Camera(
            site_id=site_id,
            camera_id=camera_id,
            name=name,
            brand=brand,
            model=model,
            ingest_protocol=ingest_protocol,
            ftp_username=ftp_username,
            ftp_password_hash=ftp_password,  # stored plaintext for pure-ftpd virtual users
            connection_config=connection_config,
            lapi_device_code=lapi_device_code,
            lapi_secret=lapi_secret,
            status="UNKNOWN",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(camera)
        session.commit()

        # Create the incoming directory for the worker to poll
        ingest_id = ftp_username or camera_id.lower()
        ftp_path = os.path.join(os.getenv("FTP_INGEST_PATH", "/data/ftp"), ingest_id, "incoming")
        os.makedirs(ftp_path, exist_ok=True)

        # Sync FTP users file so FTP container picks up the new camera
        if ingest_protocol == "ftp":
            sync_ftp_users()

        result = {
            "camera_id": camera.camera_id,
            "ingest_protocol": camera.ingest_protocol,
            "ingest_path": ftp_path,
        }
        if ftp_username:
            result["ftp_username"] = ftp_username
        if lapi_device_code:
            result["lapi_device_code"] = lapi_device_code
            result["lapi_ws_port"] = os.getenv("LAPI_WS_PORT", "8765")

        return jsonify(result)
    finally:
        session.close()


@app.route("/admin/cameras/<string:camera_id>", methods=["DELETE"])
def delete_camera(camera_id):
    session = SessionLocal()
    try:
        camera = session.query(Camera).filter(Camera.camera_id == camera_id).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404

        # Delete related records (cascade)
        snapshots = session.query(Snapshot).filter(Snapshot.camera_id == camera.id).all()
        snap_ids = [s.id for s in snapshots]
        if snap_ids:
            session.query(Detection).filter(Detection.snapshot_id.in_(snap_ids)).delete(synchronize_session=False)
        session.query(Snapshot).filter(Snapshot.camera_id == camera.id).delete(synchronize_session=False)

        zones = session.query(Zone).filter(Zone.camera_id == camera.id).all()
        zone_ids = [z.id for z in zones]
        if zone_ids:
            session.query(ZoneState).filter(ZoneState.zone_id.in_(zone_ids)).delete(synchronize_session=False)
            session.query(ZoneEvent).filter(ZoneEvent.zone_id.in_(zone_ids)).delete(synchronize_session=False)
        session.query(Zone).filter(Zone.camera_id == camera.id).delete(synchronize_session=False)

        session.query(CameraHealthEvent).filter(CameraHealthEvent.camera_id == camera.id).delete(synchronize_session=False)
        was_ftp = camera.ingest_protocol == "ftp"
        session.delete(camera)
        session.commit()

        # Re-sync FTP users so deleted camera is removed
        if was_ftp:
            sync_ftp_users()

        return jsonify({"status": "deleted", "camera_id": camera_id})
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()


@app.route("/admin/ftp-sync", methods=["POST"])
def manual_ftp_sync():
    """Manually trigger FTP user sync from DB → FTP container."""
    sync_ftp_users()
    return jsonify({"status": "synced"})


@app.route("/admin/zones/<string:camera_id>/editor", methods=["GET"])
def zone_editor(camera_id):
    return render_template("zone_editor.html", camera_id=camera_id)


@app.route("/admin/zones", methods=["POST"])
def save_zone():
    payload = request.get_json(silent=True) or {}
    camera_id = payload.get("camera_id")
    zone_id = payload.get("zone_id")
    polygon_json = payload.get("polygon_json")
    name = payload.get("name")
    capacity_units = payload.get("capacity_units", 1)

    if not camera_id or not zone_id or not polygon_json:
        return jsonify({"error": "camera_id_zone_id_polygon_required"}), 400

    session = SessionLocal()
    try:
        camera = session.query(Camera).filter(Camera.camera_id == camera_id).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404

        zone = (
            session.query(Zone)
            .filter(Zone.camera_id == camera.id, Zone.zone_id == zone_id)
            .first()
        )
        if zone:
            zone.polygon_json = polygon_json
            zone.name = name
            zone.capacity_units = capacity_units
            zone.updated_at = datetime.utcnow()
        else:
            zone = Zone(
                camera_id=camera.id,
                zone_id=zone_id,
                name=name,
                polygon_json=polygon_json,
                capacity_units=capacity_units,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(zone)
            session.flush()
            state = ZoneState(
                zone_id=zone.id,
                occupied_units=0,
                available_units=capacity_units,
                state="FREE",
                last_change_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(state)

        session.commit()
        return jsonify({"status": "ok"})
    finally:
        session.close()


@app.route("/admin/zones/bulk", methods=["POST"])
def save_zones_bulk():
    """Bulk-save zones for a camera (auto-grid or manual batch)."""
    payload = request.get_json(silent=True) or {}
    camera_id = payload.get("camera_id")
    zones_data = payload.get("zones", [])
    clear_existing = payload.get("clear_existing", False)

    if not camera_id or not zones_data:
        return jsonify({"error": "camera_id and zones[] required"}), 400

    session = SessionLocal()
    try:
        camera = session.query(Camera).filter(Camera.camera_id == camera_id).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404

        # Optionally clear existing zones first
        if clear_existing:
            old_zones = session.query(Zone).filter(Zone.camera_id == camera.id).all()
            old_ids = [z.id for z in old_zones]
            if old_ids:
                session.query(ZoneState).filter(ZoneState.zone_id.in_(old_ids)).delete(synchronize_session=False)
                session.query(ZoneEvent).filter(ZoneEvent.zone_id.in_(old_ids)).delete(synchronize_session=False)
            session.query(Zone).filter(Zone.camera_id == camera.id).delete(synchronize_session=False)

        saved = 0
        for zd in zones_data:
            zone_id = zd.get("zone_id")
            polygon_json = zd.get("polygon_json")
            if not zone_id or not polygon_json:
                continue

            existing = (
                session.query(Zone)
                .filter(Zone.camera_id == camera.id, Zone.zone_id == zone_id)
                .first()
            )
            if existing:
                existing.polygon_json = polygon_json
                existing.name = zd.get("name", existing.name)
                existing.capacity_units = zd.get("capacity_units", existing.capacity_units)
                existing.updated_at = datetime.utcnow()
            else:
                zone = Zone(
                    camera_id=camera.id,
                    zone_id=zone_id,
                    name=zd.get("name", zone_id),
                    polygon_json=polygon_json,
                    capacity_units=zd.get("capacity_units", 1),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(zone)
                session.flush()
                state = ZoneState(
                    zone_id=zone.id,
                    occupied_units=0,
                    available_units=zd.get("capacity_units", 1),
                    state="FREE",
                    last_change_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(state)
            saved += 1

        session.commit()
        return jsonify({"status": "ok", "saved": saved})
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()


@app.route("/admin/zones/delete", methods=["POST"])
def delete_zone():
    """Delete a single zone by camera_id + zone_id."""
    payload = request.get_json(silent=True) or {}
    camera_id_str = payload.get("camera_id")
    zone_id = payload.get("zone_id")

    if not camera_id_str or not zone_id:
        return jsonify({"error": "camera_id and zone_id required"}), 400

    session = SessionLocal()
    try:
        camera = session.query(Camera).filter(Camera.camera_id == camera_id_str).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404

        zone = (
            session.query(Zone)
            .filter(Zone.camera_id == camera.id, Zone.zone_id == zone_id)
            .first()
        )
        if not zone:
            return jsonify({"error": "zone_not_found"}), 404

        session.query(ZoneState).filter(ZoneState.zone_id == zone.id).delete(synchronize_session=False)
        session.query(ZoneEvent).filter(ZoneEvent.zone_id == zone.id).delete(synchronize_session=False)
        session.delete(zone)
        session.commit()
        return jsonify({"status": "deleted", "zone_id": zone_id})
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()


@app.route("/admin/zones/delete-all", methods=["POST"])
def delete_all_zones():
    """Delete all zones for a camera."""
    payload = request.get_json(silent=True) or {}
    camera_id_str = payload.get("camera_id")

    if not camera_id_str:
        return jsonify({"error": "camera_id required"}), 400

    session = SessionLocal()
    try:
        camera = session.query(Camera).filter(Camera.camera_id == camera_id_str).first()
        if not camera:
            return jsonify({"error": "camera_not_found"}), 404

        old_zones = session.query(Zone).filter(Zone.camera_id == camera.id).all()
        old_ids = [z.id for z in old_zones]
        if old_ids:
            session.query(ZoneState).filter(ZoneState.zone_id.in_(old_ids)).delete(synchronize_session=False)
            session.query(ZoneEvent).filter(ZoneEvent.zone_id.in_(old_ids)).delete(synchronize_session=False)
        count = session.query(Zone).filter(Zone.camera_id == camera.id).delete(synchronize_session=False)
        session.commit()
        return jsonify({"status": "deleted", "count": count})
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()


@app.route("/admin/api-keys/generate", methods=["POST"])
def generate_api_key():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "dashboard")
    site_ids = payload.get("site_ids")
    rate_limit = payload.get("rate_limit_per_minute", 60)

    raw_key = secrets.token_urlsafe(32)
    key_hash = hash_api_key(raw_key)

    session = SessionLocal()
    try:
        client = APIClient(
            name=name,
            api_key_hash=key_hash,
            site_ids=json.dumps(site_ids) if site_ids is not None else None,
            scope="read:status,read:events",
            rate_limit_per_minute=rate_limit,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(client)
        session.commit()
        return jsonify({"api_key": raw_key, "warning": "save_this_key"})
    finally:
        session.close()


# ============================================
# DASHBOARD ROUTES
# ============================================

@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    return render_template("dashboard.html")


@app.route("/admin/scada", methods=["GET"])
def admin_scada():
    return render_template("admin_scada.html")


@app.route("/admin/dashboard.json", methods=["GET"])
def admin_dashboard_json():
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(hours=24)

        # Totals
        projects = session.query(Project).count()
        sites = session.query(Site).count()
        cameras = session.query(Camera).all()
        zones = session.query(Zone).all()
        zone_states = session.query(ZoneState).all()

        cam_online = sum(1 for c in cameras if c.status == "ONLINE")
        cam_stale = sum(1 for c in cameras if c.status == "STALE")
        cam_offline = sum(1 for c in cameras if c.status in ("OFFLINE", "UNKNOWN", None))

        zones_free = sum(1 for zs in zone_states if zs.state == "FREE")
        zones_full = sum(1 for zs in zone_states if zs.state == "FULL")

        events_1h = session.query(ZoneEvent).filter(ZoneEvent.triggered_at >= one_hour_ago).count()
        events_24h = session.query(ZoneEvent).filter(ZoneEvent.triggered_at >= one_day_ago).count()

        # System metrics
        snapshots_1h = session.query(Snapshot).filter(Snapshot.received_at >= one_hour_ago).count()
        snapshots_total = session.query(Snapshot).count()
        pending_queue = session.query(Snapshot).filter(Snapshot.processed_at.is_(None)).count()

        tokens_today = session.query(TokenLedger).filter(
            TokenLedger.created_at >= now.replace(hour=0, minute=0, second=0)
        ).count()

        # Disk usage
        try:
            disk = shutil.disk_usage("/")
            disk_total_gb = round(disk.total / (1024**3), 1)
            disk_used_gb = round(disk.used / (1024**3), 1)
            disk_free_gb = round(disk.free / (1024**3), 1)
            disk_used_str = f"{disk_used_gb} GB / {disk_total_gb} GB"
            disk_free_str = f"{disk_free_gb} GB"
        except Exception:
            disk_used_str = "N/A"
            disk_free_str = "N/A"

        # Snapshot disk usage (images folder)
        try:
            result = subprocess.run(
                ["du", "-sb", IMAGE_ROOT],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                snap_bytes = int(result.stdout.split()[0])
                if snap_bytes >= 1024**3:
                    snap_disk_str = f"{round(snap_bytes / (1024**3), 2)} GB"
                else:
                    snap_disk_str = f"{round(snap_bytes / (1024**2), 1)} MB"
            else:
                snap_disk_str = "0 MB"
        except Exception:
            snap_disk_str = "N/A"

        # Camera details
        camera_list = []
        for cam in cameras[:10]:
            snaps = session.query(Snapshot).filter(
                Snapshot.camera_id == cam.id,
                Snapshot.received_at >= one_hour_ago
            ).count()
            camera_list.append({
                "camera_id": cam.camera_id,
                "name": cam.name,
                "status": cam.status or "UNKNOWN",
                "last_seen_at": to_iso(cam.last_seen_at),
                "snapshots_1h": snaps,
            })

        # Recent events
        recent_events = session.query(ZoneEvent, Zone).join(Zone, ZoneEvent.zone_id == Zone.id).order_by(
            ZoneEvent.triggered_at.desc()
        ).limit(10).all()

        events_list = []
        for evt, z in recent_events:
            events_list.append({
                "zone_id": z.zone_id,
                "old_state": evt.old_state,
                "new_state": evt.new_state,
                "triggered_at": to_iso(evt.triggered_at),
            })

        return jsonify({
            "totals": {
                "projects": projects,
                "sites": sites,
                "cameras": len(cameras),
                "cameras_online": cam_online,
                "cameras_stale": cam_stale,
                "cameras_offline": cam_offline,
                "zones": len(zones),
                "zones_free": zones_free,
                "zones_full": zones_full,
                "events_1h": events_1h,
                "events_24h": events_24h,
                "snapshots_total": snapshots_total,
            },
            "system": {
                "ftp_rate_hour": snapshots_1h,
                "queue_pending": pending_queue,
                "queue_delay_sec": 0,
                "disk_used": disk_used_str,
                "disk_free": disk_free_str,
                "snap_disk": snap_disk_str,
                "tokens_today": tokens_today,
            },
            "cameras": camera_list,
            "recent_events": events_list,
        })
    finally:
        session.close()


@app.route("/admin/dashboard-detections.json", methods=["GET"])
def admin_dashboard_detections_json():
    """Detection stats for the dashboard chart: hourly buckets with count, avg/min/max confidence."""
    session = SessionLocal()
    try:
        hours = int(request.args.get("hours", 24))
        hours = min(hours, 168)  # cap at 7 days
        now = datetime.utcnow()
        since = now - timedelta(hours=hours)

        # Join detections with snapshots to get time info
        rows = (
            session.query(
                func.date_trunc("hour", Snapshot.received_at).label("bucket"),
                Detection.class_name,
                func.count(Detection.id).label("count"),
                func.round(func.avg(Detection.confidence).cast(db_Numeric), 3).label("avg_conf"),
                func.round(func.min(Detection.confidence).cast(db_Numeric), 3).label("min_conf"),
                func.round(func.max(Detection.confidence).cast(db_Numeric), 3).label("max_conf"),
            )
            .join(Snapshot, Detection.snapshot_id == Snapshot.id)
            .filter(Snapshot.received_at >= since)
            .group_by("bucket", Detection.class_name)
            .order_by(text("bucket"))
            .all()
        )

        buckets = {}
        for row in rows:
            ts = row.bucket.isoformat() + "Z" if row.bucket else None
            if ts not in buckets:
                buckets[ts] = {"time": ts, "classes": {}}
            buckets[ts]["classes"][row.class_name or "unknown"] = {
                "count": row.count,
                "avg_conf": float(row.avg_conf) if row.avg_conf else 0,
                "min_conf": float(row.min_conf) if row.min_conf else 0,
                "max_conf": float(row.max_conf) if row.max_conf else 0,
            }

        # Also get overall totals
        totals = (
            session.query(
                Detection.class_name,
                func.count(Detection.id).label("count"),
                func.round(func.avg(Detection.confidence).cast(db_Numeric), 3).label("avg_conf"),
                func.round(func.min(Detection.confidence).cast(db_Numeric), 3).label("min_conf"),
                func.round(func.max(Detection.confidence).cast(db_Numeric), 3).label("max_conf"),
            )
            .join(Snapshot, Detection.snapshot_id == Snapshot.id)
            .filter(Snapshot.received_at >= since)
            .group_by(Detection.class_name)
            .all()
        )

        total_map = {}
        for t in totals:
            total_map[t.class_name or "unknown"] = {
                "count": t.count,
                "avg_conf": float(t.avg_conf) if t.avg_conf else 0,
                "min_conf": float(t.min_conf) if t.min_conf else 0,
                "max_conf": float(t.max_conf) if t.max_conf else 0,
            }

        # Snapshots per hour for throughput line
        snap_rows = (
            session.query(
                func.date_trunc("hour", Snapshot.received_at).label("bucket"),
                func.count(Snapshot.id).label("count"),
            )
            .filter(Snapshot.received_at >= since)
            .group_by("bucket")
            .order_by(text("bucket"))
            .all()
        )
        snap_buckets = [{"time": r.bucket.isoformat() + "Z", "count": r.count} for r in snap_rows]

        return jsonify({
            "hours": hours,
            "detection_buckets": list(buckets.values()),
            "totals_by_class": total_map,
            "snapshot_throughput": snap_buckets,
        })
    finally:
        session.close()


@app.route("/admin/cameras-detail.json", methods=["GET"])
def admin_cameras_detail_json():
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        cameras = session.query(Camera).all()
        result = []
        for cam in cameras:
            zone_count = session.query(Zone).filter(Zone.camera_id == cam.id).count()
            snaps_1h = session.query(Snapshot).filter(
                Snapshot.camera_id == cam.id,
                Snapshot.received_at >= one_hour_ago
            ).count()
            latest_snap = session.query(Snapshot).filter(
                Snapshot.camera_id == cam.id
            ).order_by(Snapshot.received_at.desc()).first()

            result.append({
                "camera_id": cam.camera_id,
                "name": cam.name,
                "brand": cam.brand,
                "model": cam.model,
                "ingest_protocol": cam.ingest_protocol or "ftp",
                "status": cam.status or "UNKNOWN",
                "ftp_username": cam.ftp_username,
                "last_seen_at": to_iso(cam.last_seen_at),
                "last_inference": to_iso(latest_snap.processed_at) if latest_snap else None,
                "snapshots_1h": snaps_1h,
                "zone_count": zone_count,
                "has_snapshot": latest_snap is not None,
            })
        return jsonify({"cameras": result})
    finally:
        session.close()


@app.route("/admin/zones", methods=["GET"])
def admin_zones():
    return render_template("admin_zones.html")


@app.route("/admin/zones.json", methods=["GET"])
def admin_zones_json():
    session = SessionLocal()
    try:
        camera_filter = request.args.get("camera_id")
        state_filter = request.args.get("state")

        query = session.query(Zone, ZoneState, Camera).join(
            ZoneState, ZoneState.zone_id == Zone.id
        ).join(Camera, Camera.id == Zone.camera_id)

        if camera_filter:
            query = query.filter(Camera.camera_id == camera_filter)
        if state_filter:
            query = query.filter(ZoneState.state == state_filter)

        rows = query.all()

        zones = []
        total_occupied = 0
        total_capacity = 0
        count_free = 0
        count_partial = 0
        count_full = 0

        for z, zs, cam in rows:
            capacity = z.capacity_units or 1
            occupied = zs.occupied_units or 0
            total_occupied += occupied
            total_capacity += capacity

            if zs.state == "FREE":
                count_free += 1
            elif zs.state == "PARTIAL":
                count_partial += 1
            elif zs.state == "FULL":
                count_full += 1

            zones.append({
                "zone_id": z.zone_id,
                "name": z.name,
                "camera_id": cam.camera_id,
                "polygon_json": z.polygon_json,
                "state": zs.state or "FREE",
                "occupied": occupied,
                "capacity": capacity,
                "last_change": to_iso(zs.last_change_at),
            })

        return jsonify({
            "zones": zones,
            "summary": {
                "free": count_free,
                "partial": count_partial,
                "full": count_full,
                "total_occupied": total_occupied,
                "total_capacity": total_capacity,
            },
        })
    finally:
        session.close()


@app.route("/admin/events", methods=["GET"])
def admin_events():
    return render_template("admin_events.html")


@app.route("/admin/events.json", methods=["GET"])
def admin_events_json():
    session = SessionLocal()
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        camera_filter = request.args.get("camera_id")
        zone_filter = request.args.get("zone_id")
        event_type = request.args.get("event_type")
        date_filter = request.args.get("date")

        query = session.query(ZoneEvent, Zone, Camera).join(
            Zone, ZoneEvent.zone_id == Zone.id
        ).join(Camera, Camera.id == Zone.camera_id)

        if camera_filter:
            query = query.filter(Camera.camera_id == camera_filter)
        if zone_filter:
            query = query.filter(Zone.zone_id == zone_filter)
        if event_type:
            query = query.filter(ZoneEvent.event_type == event_type)
        if date_filter:
            try:
                dt = datetime.strptime(date_filter, "%Y-%m-%d")
                query = query.filter(
                    ZoneEvent.triggered_at >= dt,
                    ZoneEvent.triggered_at < dt + timedelta(days=1)
                )
            except ValueError:
                pass

        total = query.count()
        rows = query.order_by(ZoneEvent.triggered_at.desc()).offset((page - 1) * limit).limit(limit).all()

        events = []
        for evt, z, cam in rows:
            events.append({
                "id": evt.id,
                "camera_id": cam.camera_id,
                "zone_id": z.zone_id,
                "event_type": evt.event_type or "OCCUPANCY_CHANGE",
                "old_state": evt.old_state,
                "new_state": evt.new_state,
                "old_units": evt.old_units,
                "new_units": evt.new_units,
                "triggered_at": to_iso(evt.triggered_at),
                "has_snapshot": evt.snapshot_id is not None,
            })

        return jsonify({"events": events, "total": total, "page": page, "limit": limit})
    finally:
        session.close()


@app.route("/admin/tokens", methods=["GET"])
def admin_tokens():
    return render_template("admin_tokens.html")


@app.route("/admin/tokens/summary.json", methods=["GET"])
def admin_tokens_summary():
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        from sqlalchemy import func

        # Tokens charged (sum of tokens_used, i.e. 1 per car park)
        tokens_today = session.query(func.coalesce(func.sum(TokenLedger.tokens_used), 0)).filter(
            TokenLedger.created_at >= today_start
        ).scalar()
        tokens_yesterday = session.query(func.coalesce(func.sum(TokenLedger.tokens_used), 0)).filter(
            TokenLedger.created_at >= yesterday_start,
            TokenLedger.created_at < today_start
        ).scalar()
        tokens_week = session.query(func.coalesce(func.sum(TokenLedger.tokens_used), 0)).filter(
            TokenLedger.created_at >= week_start
        ).scalar()
        tokens_month = session.query(func.coalesce(func.sum(TokenLedger.tokens_used), 0)).filter(
            TokenLedger.created_at >= month_start
        ).scalar()

        # API calls (count of rows regardless of tokens)
        calls_today = session.query(TokenLedger).filter(TokenLedger.created_at >= today_start).count()
        calls_week = session.query(TokenLedger).filter(TokenLedger.created_at >= week_start).count()
        calls_month = session.query(TokenLedger).filter(TokenLedger.created_at >= month_start).count()

        active_clients = session.query(TokenLedger.api_client_id).filter(
            TokenLedger.created_at >= today_start
        ).distinct().count()

        return jsonify({
            "tokens_today": int(tokens_today),
            "tokens_yesterday": int(tokens_yesterday),
            "tokens_week": int(tokens_week),
            "tokens_month": int(tokens_month),
            "calls_today": calls_today,
            "calls_week": calls_week,
            "calls_month": calls_month,
            "active_clients": active_clients,
        })
    finally:
        session.close()


@app.route("/admin/tokens/by-client.json", methods=["GET"])
def admin_tokens_by_client():
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        from sqlalchemy import func

        clients = session.query(APIClient).all()
        result = []
        for c in clients:
            # Tokens charged (sum)
            tokens_today = session.query(func.coalesce(func.sum(TokenLedger.tokens_used), 0)).filter(
                TokenLedger.api_client_id == c.id,
                TokenLedger.created_at >= today_start
            ).scalar()
            tokens_week = session.query(func.coalesce(func.sum(TokenLedger.tokens_used), 0)).filter(
                TokenLedger.api_client_id == c.id,
                TokenLedger.created_at >= week_start
            ).scalar()
            tokens_month = session.query(func.coalesce(func.sum(TokenLedger.tokens_used), 0)).filter(
                TokenLedger.api_client_id == c.id,
                TokenLedger.created_at >= month_start
            ).scalar()
            # API calls (count)
            calls_today = session.query(TokenLedger).filter(
                TokenLedger.api_client_id == c.id,
                TokenLedger.created_at >= today_start
            ).count()
            calls_week = session.query(TokenLedger).filter(
                TokenLedger.api_client_id == c.id,
                TokenLedger.created_at >= week_start
            ).count()

            result.append({
                "id": c.id,
                "name": c.name,
                "tokens_today": int(tokens_today),
                "tokens_week": int(tokens_week),
                "tokens_month": int(tokens_month),
                "calls_today": calls_today,
                "calls_week": calls_week,
                "rate_limit": c.rate_limit_per_minute or 60,
                "rate_usage_pct": 0,
                "last_used": to_iso(c.last_used_at),
            })

        return jsonify({"clients": result})
    finally:
        session.close()


@app.route("/admin/tokens/ledger.json", methods=["GET"])
def admin_tokens_ledger():
    session = SessionLocal()
    try:
        limit = int(request.args.get("limit", 50))
        client_id = request.args.get("client_id")
        endpoint = request.args.get("endpoint")
        date_filter = request.args.get("date")

        query = session.query(TokenLedger, APIClient).outerjoin(
            APIClient, APIClient.id == TokenLedger.api_client_id
        )

        if client_id:
            query = query.filter(TokenLedger.api_client_id == int(client_id))
        if endpoint:
            query = query.filter(TokenLedger.endpoint.like(f"%{endpoint}%"))
        if date_filter:
            try:
                dt = datetime.strptime(date_filter, "%Y-%m-%d")
                query = query.filter(
                    TokenLedger.created_at >= dt,
                    TokenLedger.created_at < dt + timedelta(days=1)
                )
            except ValueError:
                pass

        rows = query.order_by(TokenLedger.created_at.desc()).limit(limit).all()

        entries = []
        for t, c in rows:
            entries.append({
                "id": t.id,
                "client_name": c.name if c else None,
                "endpoint": t.endpoint,
                "method": t.method,
                "status_code": t.status_code,
                "response_time_ms": t.response_time_ms,
                "tokens_used": t.tokens_used,
                "created_at": to_iso(t.created_at),
            })

        return jsonify({"entries": entries})
    finally:
        session.close()


@app.route("/admin/integrations", methods=["GET"])
def admin_integrations():
    return render_template("admin_integrations.html")


@app.route("/admin/api-keys.json", methods=["GET"])
def admin_api_keys_json():
    session = SessionLocal()
    try:
        clients = session.query(APIClient).all()
        result = []
        for c in clients:
            result.append({
                "id": c.id,
                "name": c.name,
                "site_ids": c.site_ids,
                "rate_limit": c.rate_limit_per_minute or 60,
                "last_used_at": to_iso(c.last_used_at),
                "created_at": to_iso(c.created_at),
            })
        return jsonify({"keys": result})
    finally:
        session.close()


@app.route("/admin/api-keys/<int:key_id>", methods=["DELETE"])
def admin_delete_api_key(key_id):
    session = SessionLocal()
    try:
        client = session.query(APIClient).filter(APIClient.id == key_id).first()
        if client:
            session.delete(client)
            session.commit()
        return jsonify({"status": "ok"})
    finally:
        session.close()


@app.route("/admin/system", methods=["GET"])
def admin_system():
    return render_template("admin_system.html")


@app.route("/admin/system/services.json", methods=["GET"])
def admin_system_services():
    session = SessionLocal()
    services = []
    try:
        # Check DB
        session.execute(text("SELECT 1"))
        services.append({"name": "PostgreSQL Database", "status": "up", "details": "Connected"})

        # API is running (we are here)
        services.append({"name": "API Server (Flask)", "status": "up", "details": f"v{APP_VERSION}"})

        # Worker status (check recent snapshots processed)
        recent = session.query(Snapshot).filter(
            Snapshot.processed_at >= datetime.utcnow() - timedelta(minutes=10)
        ).count()
        if recent > 0:
            services.append({"name": "Zone Classifier Worker", "status": "up", "details": f"{recent} processed (10m)"})
        else:
            services.append({"name": "Zone Classifier Worker", "status": "degraded", "details": "No recent processing"})

        # FTP (check recent snapshots received)
        received = session.query(Snapshot).filter(
            Snapshot.received_at >= datetime.utcnow() - timedelta(minutes=10)
        ).count()
        if received > 0:
            services.append({"name": "FTP Ingest", "status": "up", "details": f"{received} received (10m)"})
        else:
            services.append({"name": "FTP Ingest", "status": "degraded", "details": "No recent uploads"})
    except Exception:
        services.append({"name": "PostgreSQL Database", "status": "down", "details": "Connection failed"})
    finally:
        session.close()

    return jsonify({"services": services})


@app.route("/admin/system/resources.json", methods=["GET"])
def admin_system_resources():
    session = SessionLocal()
    try:
        # Database stats
        db_rows = session.query(Snapshot).count()
        img_count = db_rows

        # Images on disk
        img_path = os.path.join(IMAGE_ROOT)
        img_size = "N/A"
        try:
            total_size = 0
            for root, dirs, files in os.walk(img_path):
                for f in files:
                    total_size += os.path.getsize(os.path.join(root, f))
            img_size = f"{total_size / (1024*1024):.1f} MB"
        except Exception:
            pass

        # Queue
        pending = session.query(Snapshot).filter(Snapshot.processed_at.is_(None)).count()

        return jsonify({
            "disk": {"percent": 25, "used": "N/A", "total": "N/A"},
            "database": {"size": "N/A", "rows": db_rows},
            "images": {"count": img_count, "size": img_size},
            "queue": {"pending": pending, "rate": 0},
        })
    finally:
        session.close()


@app.route("/admin/system/config.json", methods=["GET"])
def admin_system_config():
    return jsonify({
        "config": {
            "Zone Classifier Mode": os.getenv("ZONECLS_MODE", "placeholder"),
            "YOLO Evidence Enabled": os.getenv("YOLO_ENABLED", "false"),
            "YOLO Model": os.getenv("YOLO_MODEL", "yolov8n.pt"),
            "YOLO Confidence": os.getenv("YOLO_CONFIDENCE", "0.80"),
            "Overlap Threshold": os.getenv("OVERLAP_THRESHOLD", "0.30"),
            "Poll Interval": os.getenv("POLL_INTERVAL", "1.0") + "s",
            "Image Root": IMAGE_ROOT,
            "Require API Key": os.getenv("REQUIRE_API_KEY", "false"),
        },
        "alerts": {
            "telegram_enabled": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
            "telegram_token_suffix": TELEGRAM_BOT_TOKEN[-6:] if TELEGRAM_BOT_TOKEN else None,
            "telegram_chat_id": TELEGRAM_CHAT_ID,
            "stale_seconds": STALE_SECONDS,
            "offline_seconds": OFFLINE_SECONDS,
            "health_interval": HEALTH_INTERVAL_SECONDS,
        },
    })


@app.route("/admin/system/settings.json", methods=["GET"])
def admin_system_settings_get():
    """Return current runtime settings stored in the DB (falls back to env defaults)."""
    session = SessionLocal()
    try:
        rows = session.query(SystemSetting).all()
        db_vals = {r.key: r.value for r in rows}
    finally:
        session.close()

    defaults = {
        "operating_hours_start": os.getenv("OPERATING_HOURS_START", "6"),
        "operating_hours_end":   os.getenv("OPERATING_HOURS_END", "18"),
        "scene_diff_threshold":  os.getenv("SCENE_DIFF_THRESHOLD", "6.0"),
    }
    return jsonify({**defaults, **db_vals})


@app.route("/admin/system/settings", methods=["POST"])
def admin_system_settings_save():
    """Upsert one or more runtime settings.  Body: {key: value, ...}"""
    data = request.get_json(force=True) or {}
    allowed_keys = {"operating_hours_start", "operating_hours_end", "scene_diff_threshold"}
    session = SessionLocal()
    try:
        for key, value in data.items():
            if key not in allowed_keys:
                continue
            row = session.query(SystemSetting).filter(SystemSetting.key == key).first()
            if row:
                row.value = str(value)
                row.updated_at = datetime.utcnow()
            else:
                session.add(SystemSetting(key=key, value=str(value), updated_at=datetime.utcnow()))
        session.commit()
        return jsonify({"ok": True})
    except Exception as exc:
        session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        session.close()


@app.route("/admin/system/health-events.json", methods=["GET"])
def admin_system_health_events():
    session = SessionLocal()
    try:
        events = session.query(CameraHealthEvent, Camera).join(
            Camera, CameraHealthEvent.camera_id == Camera.id
        ).order_by(CameraHealthEvent.triggered_at.desc()).limit(20).all()

        result = []
        for evt, cam in events:
            result.append({
                "camera_id": cam.camera_id,
                "health_status": evt.health_status,
                "message": evt.message,
                "triggered_at": to_iso(evt.triggered_at),
            })

        return jsonify({"events": result})
    finally:
        session.close()


if ENABLE_HEALTH_MONITOR:
    monitor_thread = threading.Thread(target=monitor_camera_health, daemon=True)
    monitor_thread.start()

# Sync FTP users on startup
sync_ftp_users()

