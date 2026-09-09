import os
import json
import glob
from pathlib import Path

def ingest_and_extract():
    # Resolve paths relative to this script's location so it works regardless of CWD
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    base_dir = project_root / "dataset_a"
    
    if not base_dir.exists():
        print(f"Error: {base_dir} not found.")
        return

    # To store events per session
    sessions_data = {}
    
    # To store unique text elements
    unique_apps = set()
    unique_urls = set()
    unique_ui_labels = set()

    # Find all events.jsonl files using pathlib for cross-platform compatibility
    event_files = list(base_dir.rglob("events.jsonl"))
    
    for path in event_files:
        # Expected path structure: dataset_a/ses_<id>/chunk_<id>/events.jsonl
        # Or dataset_a/ses_<id>/events.jsonl
        if path.parent.name.startswith("chunk_"):
            session_id = path.parent.parent.name
        else:
            session_id = path.parent.name
        
        if session_id not in sessions_data:
            sessions_data[session_id] = []
            
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    sessions_data[session_id].append(event)
                    
                    # Extraction logic
                    context = event.get('context') or {}
                    payload = event.get('payload') or {}
                    event_type = event.get('event_type')
                    
                    # 1. Window titles and application names
                    active_app = context.get('active_app')
                    if active_app:
                        if isinstance(active_app, dict):
                            for k in ('app_name', 'window_title', 'process_name'):
                                val = active_app.get(k)
                                if val and isinstance(val, str):
                                    unique_apps.add(val)
                        elif isinstance(active_app, str):
                            unique_apps.add(active_app)

                    # Also check open_apps and visible_windows
                    for app in (context.get('open_apps') or []):
                        if isinstance(app, dict):
                            for k in ('app_name', 'window_title', 'process_name'):
                                val = app.get(k)
                                if val and isinstance(val, str):
                                    unique_apps.add(val)
                        elif isinstance(app, str):
                            unique_apps.add(app)

                    for win in (context.get('visible_windows') or []):
                        if isinstance(win, dict):
                            title = win.get('window_title') or win.get('title')
                            if title and isinstance(title, str):
                                unique_apps.add(title)

                    # Also check payload app switches and window titles
                    for k in ('new_app', 'previous_app', 'window_title', 'title', 'dialog_title'):
                        val = payload.get(k)
                        if val and isinstance(val, str):
                            unique_apps.add(val)

                    # 2. Browser URLs and titles
                    active_browser = context.get('active_browser_tab')
                    if active_browser and isinstance(active_browser, dict):
                        url = active_browser.get('url')
                        title = active_browser.get('title')
                        if url and isinstance(url, str): unique_urls.add(url)
                        if title and isinstance(title, str): unique_urls.add(title)
                        
                    # 3. UI element attributes and labels
                    if event_type in ('browser_click', 'browser_form_input'):
                        element = payload.get('element') or {}
                        attributes = element.get('attributes') or {} if isinstance(element, dict) else {}
                        if isinstance(attributes, dict):
                            for key, value in attributes.items():
                                if value and isinstance(value, str):
                                    unique_ui_labels.add(value)

                    # Target field attributes in keystroke events
                    target_field = payload.get('target_field') or {}
                    if isinstance(target_field, dict):
                        for k, v in target_field.items():
                            if v and isinstance(v, str):
                                unique_ui_labels.add(v)

                    # 4. Extracted text from screen (OCR text in context)
                    extracted_text = context.get('extracted_text')
                    if extracted_text and isinstance(extracted_text, str):
                        unique_ui_labels.add(extracted_text.strip())

                except json.JSONDecodeError:
                    print(f"Error parsing JSON in {path}")
                    continue

    # Sort events per session chronologically
    for session_id in sessions_data:
        sessions_data[session_id].sort(key=lambda x: x.get('timestamp_ms', 0))
        
    print(f"Ingested {len(sessions_data)} sessions.")
    
    # Save extracted elements
    extracted_data = {
        "window_and_app_names": sorted(list(unique_apps)),
        "browser_urls_and_titles": sorted(list(unique_urls)),
        "ui_element_attributes": sorted(list(unique_ui_labels))
    }
    
    output_file = project_root / "extracted_ui_elements.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        
    print(f"Extracted UI elements saved to {output_file}")
    print(f" - Unique Apps/Windows: {len(unique_apps)}")
    print(f" - Unique URLs/Titles: {len(unique_urls)}")
    print(f" - Unique UI Labels: {len(unique_ui_labels)}")

if __name__ == "__main__":
    ingest_and_extract()
