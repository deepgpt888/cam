import ftplib
import time
import socket
import os
import sys

def get_all_ips():
    ips = []
    try:
        # Get host name
        hostname = socket.gethostname()
        # Get all addresses for hostname
        _, _, addresses = socket.gethostbyname_ex(hostname)
        for ip in addresses:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    
    # Also try connecting to external to find primary route (most reliable for LAN)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip not in ips:
            ips.insert(0, primary_ip)
    except:
        pass
        
    return list(dict.fromkeys(ips)) # Dedup

def monitor_ftp():
    host = "localhost"
    port = 21
    user = "cam001"
    passwd = "password123"
    target_dir = "incoming"

    print("="*60)
    print("      🎥 REAL CAMERA CONNECTION MONITOR 🎥")
    print("="*60)
    
    ips = get_all_ips()
    print(f"\n👉 STEP 1: Configure your Camera FTP Settings:")
    print(f"   - Server Address: {ips[0] if ips else 'YOUR_LAN_IP'} (Try this first)")
    if len(ips) > 1:
        print(f"     Alternatives: {', '.join(ips[1:])}")
    print(f"   - Port: 21")
    print(f"   - Username: {user}")
    print(f"   - Password: {passwd}")
    print(f"   - Remote Directory: {target_dir}")
    print(f"   - Passive Mode: YES")
    
    print("\n👉 STEP 2: Firewall Check")
    print("   Ensure Windows Firewall allows port 21 and 30000-30009.")
    print("   PowerShell Admin Command to open ports:")
    print('   New-NetFirewallRule -DisplayName "CamPark FTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 21,30000-30009')

    print("\n👉 STEP 3: Monitor Starting...")
    print("-" * 60)

    known_files = set()
    
    # Initial scan
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port)
        ftp.login(user, passwd)
        
        # Ensure target directory exists
        try:
            ftp.cwd(target_dir)
        except ftplib.error_perm:
            ftp.mkd(target_dir)
            ftp.cwd(target_dir)

        files = []
        ftp.retrlines("LIST", files.append)
        known_files = set(files)
        print(f"[{time.strftime('%H:%M:%S')}] Currently {len(known_files)} files in directory.")
        ftp.quit()
        
    except Exception as e:
        print(f"Error connecting to local FTP: {e}")
        return

    # Loop
    print(f"[{time.strftime('%H:%M:%S')}] Waiting for camera uploads...")
    try:
        while True:
            time.sleep(5)
            try:
                ftp = ftplib.FTP()
                ftp.connect(host, port)
                ftp.login(user, passwd)
                ftp.cwd(target_dir)
                
                current_files = []
                ftp.retrlines("LIST", current_files.append)
                current_set = set(current_files)
                
                new_files = current_set - known_files
                
                if new_files:
                    print(f"\n✅ [{time.strftime('%H:%M:%S')}] NEW FILE RECEIVED!")
                    for f in new_files:
                        print(f"   📄 {f}")
                    known_files = current_set
                else:
                    # Heartbeat dot
                    sys.stdout.write(".")
                    sys.stdout.flush()
                
                ftp.quit()
                
            except Exception as e:
                print(f"\n⚠️ Monitor Error: {e}")
                time.sleep(5) 

    except KeyboardInterrupt:
        print("\nStopping monitor.")

if __name__ == "__main__":
    monitor_ftp()
