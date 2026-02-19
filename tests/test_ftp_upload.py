import ftplib
import os
import sys
import time

def test_ftp_upload():
    host = "localhost"
    port = 21
    user = "cam001"
    passwd = "password123"
    upload_file = "test_snapshot.jpg"
    
    # Check if test file exists
    if not os.path.exists(upload_file):
        # Try to find it relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        possible_path = os.path.join(parent_dir, upload_file)
        if os.path.exists(possible_path):
            upload_file = possible_path
        else:
            print(f"ERROR: Cannot find {upload_file}")
            sys.exit(1)

    print(f"Connecting to FTP {host}:{port}...")
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port)
        print(f"Connected to {host}:{port}")
        
        ftp.login(user, passwd)
        print(f"Logged in as {user}")
        
        remote_cwd = ftp.pwd()
        print(f"Current Remote Directory: {remote_cwd}")
        
        # Check explicit path on server
        if remote_cwd == "/":
            # This is root of chroot jail
            pass
        else:
             print(f"Note: Current dir is {remote_cwd}, expected '/' or similar for chroot user.")

        target_name = f"test_upload_{int(time.time())}.jpg"
        print(f"Uploading {upload_file} as {target_name}...")
        
        with open(upload_file, "rb") as f:
            ftp.storbinary(f"STOR {target_name}", f)
        
        print("Upload complete.")
        
        print("Listing files on server:")
        files = []
        ftp.retrlines("LIST", files.append)
        for f in files:
            print(f" - {f}")

        found = any(target_name in f for f in files)
        
        if found:
            print("SUCCESS: File verified on server.")
        else:
            print("FAILURE: File NOT found on server list.")
            sys.exit(1)
            
        ftp.quit()
        
    except Exception as e:
        print(f"FTP Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_ftp_upload()
