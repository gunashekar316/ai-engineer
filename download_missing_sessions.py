import os
import sys
import time
from pathlib import Path
import requests
from gdown.download_folder import _get_session, _parse_embedded_folder_view, _GoogleDriveFile

def download_file_direct(file_id, dest_path, max_retries=5):
    for attempt in range(max_retries):
        try:
            sess = requests.Session()
            sess.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            url = f"https://drive.google.com/uc?id={file_id}&export=download"
            res = sess.get(url, stream=True, timeout=30)
            
            token = None
            for k, v in res.cookies.items():
                if k.startswith("download_warning"):
                    token = v
                    break
            if token:
                url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm={token}"
                res = sess.get(url, stream=True, timeout=30)
                
            if res.status_code == 200:
                dest_path = Path(dest_path)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                if dest_path.exists() and dest_path.stat().st_size > 0:
                    print(f"    [OK] Downloaded {dest_path.name} ({dest_path.stat().st_size} bytes)")
                    return True
            elif res.status_code == 429:
                wait_time = 2 ** (attempt + 1)
                print(f"    [429 Rate Limit] Backing off for {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    [HTTP {res.status_code}] Attempt {attempt+1}/{max_retries}")
                time.sleep(2)
        except Exception as e:
            print(f"    [Error] {e} on attempt {attempt+1}/{max_retries}")
            time.sleep(2)
    return False

def sync_dataset_a():
    project_root = Path(__file__).resolve().parent
    base_dir = project_root / "dataset_a"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    gdrive_sess, _ = _get_session(
        proxy=None,
        use_cookies=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        cookies_file=None
    )
    
    dataset_a_id = "1gCW_uGRl-BeYNBxmX4DkMivdsV9HO0yY"
    print(f"Fetching session list from Google Drive (folder ID: {dataset_a_id})...")
    folder_name, session_items = _parse_embedded_folder_view(sess=gdrive_sess, folder_id=dataset_a_id, verify=True)
    print(f"Found {len(session_items)} items in {folder_name}")
    
    session_folders = [item for item in session_items if item[2] == _GoogleDriveFile.TYPE_FOLDER and item[1].startswith("ses_")]
    print(f"Total session folders: {len(session_folders)}")
    
    for idx, (ses_id, ses_name, _) in enumerate(session_folders, 1):
        local_ses_dir = base_dir / ses_name
        local_ses_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already complete: has gt.jsonl and at least one events.jsonl
        has_gt = (local_ses_dir / "gt.jsonl").exists() and (local_ses_dir / "gt.jsonl").stat().st_size > 0
        has_events = bool(list(local_ses_dir.rglob("events.jsonl")))
        
        if has_gt and has_events:
            print(f"[{idx}/{len(session_folders)}] Session {ses_name} already complete. Skipping.")
            continue
            
        print(f"\n[{idx}/{len(session_folders)}] Processing missing session: {ses_name}")
        try:
            _, ses_children = _parse_embedded_folder_view(sess=gdrive_sess, folder_id=ses_id, verify=True)
        except Exception as e:
            print(f"  Error fetching session view: {e}")
            continue
            
        for item_id, item_name, item_type in ses_children:
            if item_type == _GoogleDriveFile.TYPE_FOLDER:
                if item_name.startswith("chunk_"):
                    local_chunk_dir = local_ses_dir / item_name
                    local_chunk_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        _, chunk_children = _parse_embedded_folder_view(sess=gdrive_sess, folder_id=item_id, verify=True)
                    except Exception as e:
                        print(f"    Error fetching chunk {item_name}: {e}")
                        continue
                        
                    for c_id, c_name, c_type in chunk_children:
                        if c_type != _GoogleDriveFile.TYPE_FOLDER and not c_name.lower().endswith((".jpg", ".jpeg", ".png")):
                            chunk_file = local_chunk_dir / c_name
                            if not (chunk_file.exists() and chunk_file.stat().st_size > 0):
                                print(f"  Downloading chunk file {item_name}/{c_name}...")
                                download_file_direct(c_id, chunk_file)
                                time.sleep(0.3)
            else:
                if not item_name.lower().endswith((".jpg", ".jpeg", ".png")):
                    ses_file = local_ses_dir / item_name
                    if not (ses_file.exists() and ses_file.stat().st_size > 0):
                        print(f"  Downloading session file {item_name}...")
                        download_file_direct(item_id, ses_file)
                        time.sleep(0.3)

    gdrive_sess.close()
    print("\nDataset A synchronization finished!")

if __name__ == "__main__":
    sync_dataset_a()
