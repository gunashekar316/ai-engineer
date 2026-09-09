import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gdown
from gdown.download_folder import _get_session, _parse_embedded_folder_view, _GoogleDriveFile
from gdown.download import download

def get_session():
    sess, _ = _get_session(
        proxy=None,
        use_cookies=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        cookies_file=None
    )
    return sess

def crawl_session(session_id, session_name, session_dir, sess, skip_screenshots=True):
    session_dir.mkdir(parents=True, exist_ok=True)
    def recurse(current_id, current_local_dir):
        current_local_dir.mkdir(parents=True, exist_ok=True)
        try:
            folder_name, children = _parse_embedded_folder_view(sess=sess, folder_id=current_id, verify=True)
        except Exception as e:
            print(f"Error fetching folder {current_id} ({folder_name if 'folder_name' in locals() else ''}): {e}")
            return
            
        for child_id, child_name, child_type in children:
            if child_type == _GoogleDriveFile.TYPE_FOLDER:
                if skip_screenshots and child_name.lower() == 'screenshots':
                    continue
                recurse(child_id, current_local_dir / child_name)
            else:
                if child_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                dest_file = current_local_dir / child_name
                if dest_file.exists() and dest_file.stat().st_size > 0:
                    continue
                try:
                    download(id=child_id, output=str(dest_file), quiet=True)
                    print(f"Downloaded: {dest_file.relative_to(session_dir.parent.parent)} ({dest_file.stat().st_size} bytes)")
                except Exception as err:
                    print(f"Failed to download {child_name}: {err}")

    recurse(session_id, session_dir)

def crawl_and_download_parallel(root_folder_id, target_dir, max_workers=8):
    root_sess = get_session()
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Scanning root folder: {root_folder_id}...")
    folder_name, root_children = _parse_embedded_folder_view(sess=root_sess, folder_id=root_folder_id, verify=True)
    print(f"Found {len(root_children)} top-level items in {folder_name}")
    root_sess.close()

    tasks = []
    for child_id, child_name, child_type in root_children:
        if child_type == _GoogleDriveFile.TYPE_FOLDER:
            tasks.append((child_id, child_name, target_path / child_name))
        else:
            if not child_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                dest = target_path / child_name
                if not (dest.exists() and dest.stat().st_size > 0):
                    download(id=child_id, output=str(dest), quiet=True)
                    print(f"Downloaded root file: {child_name}")

    def worker(task):
        cid, cname, cdir = task
        s = get_session()
        try:
            crawl_session(cid, cname, cdir, s)
        finally:
            s.close()
        return cname

    print(f"Starting parallel download with {max_workers} threads across {len(tasks)} folders...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, t): t[1] for t in tasks}
        completed = 0
        for f in as_completed(futures):
            cname = futures[f]
            try:
                f.result()
                completed += 1
                print(f"[{completed}/{len(tasks)}] Finished folder: {cname}")
            except Exception as e:
                print(f"Error on {cname}: {e}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    print("--- DOWNLOADING DATASET A ---")
    crawl_and_download_parallel("1gCW_uGRl-BeYNBxmX4DkMivdsV9HO0yY", project_root / "dataset_a", max_workers=8)
    print("--- DOWNLOADING DATASET B ---")
    crawl_and_download_parallel("1Zqb96i7jsLIU5V06wvvNko1MRwiI9pHF", project_root / "dataset_b", max_workers=8)
    print("ALL DOWNLOADS COMPLETE!")
