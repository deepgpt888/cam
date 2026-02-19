# 🟢 CamPark POC Status Update

**Last Updated**: 2026-02-05 17:30 (Local Time)
**Current Phase**: Camera Integration & Data Ingestion
**Status**: UP AND RUNNING ✅

---

## 🚀 Latest Achievement: Real Camera Connected!
We have successfully connected the **Dahua DH-IPC-HFW7442H-Z4FR** camera to our local CamPark infrastructure.

### ✅ What is Working
1.  **FTP Server**: Running stably on Docker (Port 21).
2.  **Firewall**: Configured to allow Passive Mode (Ports 21000-21010).
3.  **File Ingestion**: 
    - Camera is successfully uploading JPEG snapshots to `C:\document\CamPark\data\ftp\incoming`.
    - Files are persisting correctly on the Windows host.
4.  **Motion Detection**: Validated that camera uploads files upon triggering events.

### ⚠️ Known Issues
- **Camera Test Button Error**: The "Test" button in the Dahua web UI returns **"FTP server test failure, list right loss"**.
    - **Impact**: None on actual functionality.
    - **Cause**: Camera-specific validation of directory listing permissions or format.
    - **Workaround**: Ignored. Actual file uploads are verified to be working correctly despite this error.

---

## 🛠 Infrastructure Changes
- **FTP Container**: Switched to use explicit volume mapping (`/1000`) to ensure Windows persistence.
- **Port Mapping**: Docker ports aligned with Windows Firewall.
- **Permissions**: Forced `chmod 777` on upload directories to ensure accessibility.

## 🔜 Next Steps
1.  **Start Worker Service**: Spin up the YOLO worker to consume these images.
2.  **Verify Processing**: Ensure images landing in `/incoming` are detected, processed, and results stored in Postgres.
3.  **Frontend**: View the processed data in the Dashboard.

---

**Technical Note for Codespaces/Devs**:
- The FTP server configuration in `docker-compose.yml` might need to be updated to reflect the manual `docker run` command we used if we want it to be reproducible. 
- Currently running manual container: `campark-ftp` with `delfer/alpine-ftp-server`.
