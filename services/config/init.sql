-- CamPark POC Database Schema
-- Minimal schema for days 1-2 POC

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sites (one project can have multiple sites)
CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- Cameras (one site can have multiple cameras)
CREATE TABLE IF NOT EXISTS cameras (
    id SERIAL PRIMARY KEY,
    site_id INT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    camera_id VARCHAR(50) NOT NULL,  -- external ID (e.g., "CAM001")
    name VARCHAR(255),
    brand VARCHAR(100),               -- e.g., "dahua", "uniarch", "hikvision", "generic"
    model VARCHAR(255),               -- e.g., "IPC-HFW7442H-Z4FR"
    ingest_protocol VARCHAR(30) NOT NULL DEFAULT 'ftp',  -- ftp | lapi_ws | rtsp | onvif | http_snap
    ftp_username VARCHAR(100) UNIQUE, -- only required for ftp protocol
    ftp_password_hash VARCHAR(255),   -- store hashed or encrypted
    -- Connection config (JSON) for non-FTP protocols
    -- e.g., {"ip":"x.x.x.x","port":82,"secret":"...","device_code":"..."}
    connection_config TEXT,
    -- LAPI WebSocket fields
    lapi_device_code VARCHAR(255),    -- device serial, used to match WS registration
    lapi_secret VARCHAR(255),         -- shared secret for HMAC-SHA256 auth
    lapi_ws_port INT DEFAULT 8765,    -- WebSocket listen port for this camera
    last_snapshot_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'UNKNOWN',  -- ONLINE, STALE, OFFLINE
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(site_id, camera_id)
);

-- Zones (one camera can have multiple zones / ROIs)
CREATE TABLE IF NOT EXISTS zones (
    id SERIAL PRIMARY KEY,
    camera_id INT NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    zone_id VARCHAR(100) NOT NULL,  -- external ID (e.g., "A01", "A02")
    name VARCHAR(255),
    polygon_json TEXT NOT NULL,  -- JSON: [[x1,y1], [x2,y2], ...] normalized to 0-100%
    capacity_units INT DEFAULT 1,  -- how many parking spaces in this zone
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(camera_id, zone_id)
);

-- Zone States (current occupancy per zone)
CREATE TABLE IF NOT EXISTS zone_states (
    id SERIAL PRIMARY KEY,
    zone_id INT NOT NULL REFERENCES zones(id) ON DELETE CASCADE UNIQUE,
    occupied_units INT DEFAULT 0,
    available_units INT DEFAULT 0,
    state VARCHAR(50) DEFAULT 'FREE',  -- FREE, PARTIAL, FULL
    last_change_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Snapshots (file references)
CREATE TABLE IF NOT EXISTS snapshots (
    id SERIAL PRIMARY KEY,
    camera_id INT NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    file_path VARCHAR(255) NOT NULL,  -- relative path in /data/images/
    file_hash VARCHAR(64) UNIQUE,  -- SHA256 for deduplication
    width INT,  -- image dimensions
    height INT,
    received_at TIMESTAMP NOT NULL,  -- when FTP server received it
    processed_at TIMESTAMP,  -- when YOLO processed it
    created_at TIMESTAMP DEFAULT NOW()
);

-- YOLO Detections (raw inference results)
CREATE TABLE IF NOT EXISTS detections (
    id SERIAL PRIMARY KEY,
    snapshot_id INT NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    class VARCHAR(50),  -- car, truck, motorcycle, bicycle
    confidence FLOAT,  -- 0.0-1.0
    bbox_json TEXT,  -- JSON: {x, y, width, height} normalized to 0-100%
    created_at TIMESTAMP DEFAULT NOW()
);

-- Zone Events (state changes with evidence)
CREATE TABLE IF NOT EXISTS zone_events (
    id SERIAL PRIMARY KEY,
    zone_id INT NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    snapshot_id INT REFERENCES snapshots(id) ON DELETE SET NULL,
    old_state VARCHAR(50),  -- previous state (FREE, PARTIAL, FULL)
    new_state VARCHAR(50),  -- new state
    old_units INT,
    new_units INT,
    event_type VARCHAR(50),  -- OCCUPANCY_CHANGE, OFFLINE_ALERT, STALE_ALERT
    triggered_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Camera Health Events (offline/stale alerts)
CREATE TABLE IF NOT EXISTS camera_health_events (
    id SERIAL PRIMARY KEY,
    camera_id INT NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    health_status VARCHAR(20),  -- ONLINE, STALE, OFFLINE
    message TEXT,
    triggered_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- API Clients (external dashboard auth)
CREATE TABLE IF NOT EXISTS api_clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    api_key_hash VARCHAR(255) NOT NULL UNIQUE,
    site_ids TEXT,  -- JSON array [1, 2, 3] or null for all sites
    scope VARCHAR(255) DEFAULT 'read:status,read:events',  -- read-only enforced
    rate_limit_per_minute INT DEFAULT 60,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Token Ledger (immutable audit trail for API usage)
CREATE TABLE IF NOT EXISTS token_ledger (
    id SERIAL PRIMARY KEY,
    api_client_id INT REFERENCES api_clients(id) ON DELETE CASCADE,
    endpoint VARCHAR(255),  -- GET /api/v1/sites/{id}/status
    method VARCHAR(10),  -- GET, POST
    status_code INT,
    response_time_ms INT,
    tokens_used INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indices for common queries
CREATE INDEX idx_cameras_site_id ON cameras(site_id);
CREATE INDEX idx_cameras_last_seen ON cameras(last_seen_at);
CREATE INDEX idx_cameras_status ON cameras(status);
CREATE INDEX idx_zones_camera_id ON zones(camera_id);
CREATE INDEX idx_zone_states_zone_id ON zone_states(zone_id);
CREATE INDEX idx_snapshots_camera_id ON snapshots(camera_id);
CREATE INDEX idx_snapshots_received_at ON snapshots(received_at DESC);
CREATE INDEX idx_detections_snapshot_id ON detections(snapshot_id);
CREATE INDEX idx_zone_events_zone_id ON zone_events(zone_id);
CREATE INDEX idx_zone_events_triggered ON zone_events(triggered_at DESC);
CREATE INDEX idx_camera_health_camera_id ON camera_health_events(camera_id);
CREATE INDEX idx_camera_health_triggered ON camera_health_events(triggered_at DESC);

-- Insert default test data
INSERT INTO projects (name) VALUES ('POC_Project_01') ON CONFLICT DO NOTHING;

INSERT INTO sites (project_id, name, location)
SELECT id, 'POC_Site_01', 'Test Location'
FROM projects WHERE name = 'POC_Project_01'
ON CONFLICT DO NOTHING;

INSERT INTO cameras (site_id, camera_id, name, brand, model, ingest_protocol, ftp_username, ftp_password_hash)
SELECT id, 'CAM001', 'Dahua Parking Entrance', 'dahua', 'IPC-HFW7442H-Z4FR', 'ftp', 'cam001', '$2b$12$PLACEHOLDER_HASH'
FROM sites WHERE name = 'POC_Site_01'
ON CONFLICT DO NOTHING;

INSERT INTO cameras (site_id, camera_id, name, brand, model, ingest_protocol, lapi_device_code, lapi_secret)
SELECT id, 'CAM002', 'Uniarch Parking 4G', 'uniarch', 'UHO-P2G-M3F4D-AS', 'lapi_ws', 'UNIARCH_CAM002', '123456'
FROM sites WHERE name = 'POC_Site_01'
ON CONFLICT DO NOTHING;

INSERT INTO zones (camera_id, zone_id, name, polygon_json, capacity_units)
SELECT id, 'ZONE_A01', 'Parking Zone A', '[[0,0],[100,0],[100,100],[0,100]]', 1
FROM cameras WHERE camera_id = 'CAM001'
ON CONFLICT DO NOTHING;

INSERT INTO zone_states (zone_id, occupied_units, available_units, state)
SELECT id, 0, 1, 'FREE'
FROM zones WHERE zone_id = 'ZONE_A01'
ON CONFLICT DO NOTHING;
