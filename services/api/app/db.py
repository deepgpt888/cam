import os
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, scoped_session, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://campark:changeme_poc@postgres:5432/campark",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False)
)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    camera_id: Mapped[str] = mapped_column(String(50))
    name: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    brand: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    model: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    ingest_protocol: Mapped[str] = mapped_column(String(30), default="ftp")
    ftp_username: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    ftp_password_hash: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    connection_config: Mapped[Optional[str]] = mapped_column(Text, default=None)
    lapi_device_code: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    lapi_secret: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    lapi_ws_port: Mapped[Optional[int]] = mapped_column(default=None)
    last_snapshot_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    status: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"))
    zone_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[Optional[str]] = mapped_column(Text, default=None)
    polygon_json: Mapped[str] = mapped_column(Text)
    capacity_units: Mapped[Optional[int]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class ZoneState(Base):
    __tablename__ = "zone_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"))
    occupied_units: Mapped[Optional[int]] = mapped_column(default=None)
    available_units: Mapped[Optional[int]] = mapped_column(default=None)
    state: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    last_change_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"))
    file_path: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    width: Mapped[Optional[int]] = mapped_column(default=None)
    height: Mapped[Optional[int]] = mapped_column(default=None)
    received_at: Mapped[datetime] = mapped_column()
    processed_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    class_name: Mapped[Optional[str]] = mapped_column("class", String(50), default=None)
    confidence: Mapped[Optional[float]] = mapped_column(default=None)
    bbox_json: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class ZoneEvent(Base):
    __tablename__ = "zone_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"))
    snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("snapshots.id"), default=None)
    old_state: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    new_state: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    old_units: Mapped[Optional[int]] = mapped_column(default=None)
    new_units: Mapped[Optional[int]] = mapped_column(default=None)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class CameraHealthEvent(Base):
    __tablename__ = "camera_health_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"))
    health_status: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class APIClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    api_key_hash: Mapped[str] = mapped_column(String(255))
    site_ids: Mapped[Optional[str]] = mapped_column(Text, default=None)
    scope: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    rate_limit_per_minute: Mapped[Optional[int]] = mapped_column(default=None)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class TokenLedger(Base):
    __tablename__ = "token_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_clients.id"), default=None)
    endpoint: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    method: Mapped[Optional[str]] = mapped_column(String(10), default=None)
    status_code: Mapped[Optional[int]] = mapped_column(default=None)
    response_time_ms: Mapped[Optional[int]] = mapped_column(default=None)
    tokens_used: Mapped[Optional[int]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)
