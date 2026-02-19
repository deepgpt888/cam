# CamPark GCP Pilot Plan (25 Cameras) + Upgrade Path

## Goal
Run a 25-camera pilot on Google Cloud (90-day trial) that is production-credible and can scale to 700 cameras with minimal rework.

## Recommended Pilot Setup (Best Fit)
This keeps ops simple while being upgrade-ready.

### 1) Compute
- **Compute Engine VM (Ubuntu 22.04 LTS, e2-standard-4)**
- Run the existing `docker-compose.yml` stack:
  - `ftp` (pure-ftpd)
  - `api` (Flask)
  - `worker` (ZoneCls + optional YOLO evidence)
  - `postgres` (can be local for pilot) or Cloud SQL
  - `redis` optional

Why: FTP needs inbound ports and a stable public IP. A VM is the simplest and most reliable way to handle FTP ingest.

### 2) Network
- Reserve **static external IP** for the VM
- Firewall rules:
  - TCP 21 (FTP)
  - Passive FTP port range (e.g., 30000-30049)
  - TCP 8000 (API/admin UI, can be protected behind a reverse proxy)
- Optional: restrict FTP source IPs to camera network ranges

### 3) Storage
- Use **VM persistent disk** for `data/ftp` and `data/images`
- Add **Cloud Storage bucket** for evidence archiving and model storage
  - Daily or weekly sync from `/data/images` to GCS
  - Keep only recent evidence locally to control disk usage

### 4) Database
- Pilot option A (fastest): **Postgres container** with persistent disk
- Pilot option B (preferred): **Cloud SQL for PostgreSQL**
  - More durable and closer to production
  - Minimal app changes (use `DATABASE_URL`)

### 5) Observability
- Install **Google Cloud Ops Agent** on VM
- Ship logs to **Cloud Logging**
- Set basic alerts (CPU > 80%, disk > 80%, no snapshots in 15 min)

### 6) Security
- Use API keys for external dashboard
- Set admin credentials via `.env`
- Consider nginx reverse proxy + TLS if public access is needed

## Pilot Sizing (25 Cameras)
- Snapshot interval: 120s heartbeat + motion-triggered
- Estimated ingress: 25 cameras * (0.5 to 2) images/min avg
- CPU: e2-standard-4 is sufficient for ZoneCls CPU inference
- Disk: start with 100-200GB; enforce retention

## Configuration Baseline (Pilot)
- `ZONECLS_MODE=placeholder` until a v1 model is trained
- `ZONECLS_THRESHOLD=0.55` (calibrate later)
- `YOLO_ENABLED=false` (enable only for evidence after stable)
- Snapshot retention: keep only on state change

## Future Upgrade Path (700 Cameras)
This is the plan to scale without rewrites.

### 1) Split Services
- **FTP Ingest**: keep on dedicated VM(s) with static IPs
- **Worker**: move to **GKE** or **Cloud Run Jobs**
- **API/Admin**: move to **Cloud Run** behind HTTPS load balancer

### 2) Use a Queue
- Introduce **Pub/Sub** for snapshot processing
- Worker pulls from Pub/Sub, enabling horizontal scaling

### 3) Storage Strategy
- Move snapshots to **Cloud Storage** with lifecycle rules
- Keep only hot evidence and last snapshots on local disk

### 4) Database
- **Cloud SQL** with read replica for reporting
- Add indexes on `snapshots.received_at`, `zone_events.triggered_at`

### 5) Model Ops
- Store ONNX models in **GCS** or **GitHub Releases**
- Add model version table for rollback
- Support hot-reload on worker restart

### 6) Multi-Site Scaling
- Partition by **site_id** and **camera_id**
- Separate worker queues by region or site to avoid backlogs

### 7) Cost Controls
- Reduce uploads by enforcing event-only evidence
- Compress evidence snapshots if needed
- Use CPU-only inference (ZoneCls) for base workload

## Summary (Best Recommendation)
- **Pilot**: single GCE VM + static IP + docker-compose, Cloud SQL if budget allows, GCS for model artifacts and optional archive.
- **Scale**: split FTP, API, Worker; add Pub/Sub; move API/Worker to managed services; keep FTP on dedicated VMs.

This keeps the 25-camera pilot stable and lays a clean path to 700+ without re-architecting later.
