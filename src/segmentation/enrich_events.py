import os
import json
from pathlib import Path

def load_translation_map(project_root):
    map_path = project_root / "src" / "segmentation" / "translation_map.json"
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"apps_and_windows": {}, "urls": {}, "ui_labels": {}}

def enrich_and_reconstruct(events, translation_map):
    enriched = []
    
    current_text = []
    last_target = None
    
    def finalize_text_input(timestamp, context):
        if current_text:
            text_str = "".join(current_text)
            enriched.append({
                "schema_version": "1.0.0",
                "event_id": f"reconstructed_{timestamp}",
                "timestamp_ms": timestamp,
                "layer": "L2",
                "event_type": "reconstructed_text_input",
                "context": context,
                "payload": {
                    "text": text_str,
                    "target_field": last_target
                }
            })
            current_text.clear()
            
    for event in events:
        event_type = event.get('event_type')
        payload = event.get('payload') or {}
        context = event.get('context') or {}
        timestamp = event.get('timestamp_ms', 0)
        
        # Enrichment
        enriched_info = {}
        
        # App/Window
        active_app = context.get('active_app')
        if active_app:
            if isinstance(active_app, dict):
                title = active_app.get('window_title') or active_app.get('app_name')
                if title in translation_map.get('apps_and_windows', {}):
                    enriched_info['app_category'] = translation_map['apps_and_windows'][title]
            elif isinstance(active_app, str):
                if active_app in translation_map.get('apps_and_windows', {}):
                    enriched_info['app_category'] = translation_map['apps_and_windows'][active_app]
                    
        # URL
        active_browser = context.get('active_browser_tab')
        if active_browser and isinstance(active_browser, dict):
            url = active_browser.get('url')
            if url in translation_map.get('urls', {}):
                enriched_info['domain'] = translation_map['urls'][url]
                
        # UI Labels
        if event_type in ('browser_click', 'browser_form_input'):
            element = payload.get('element') or {}
            attributes = element.get('attributes') or {} if isinstance(element, dict) else {}
            if isinstance(attributes, dict):
                for k, v in attributes.items():
                    if v in translation_map.get('ui_labels', {}):
                        enriched_info['inferred_intent'] = translation_map['ui_labels'][v]
                        break
        
        if enriched_info:
            event['enriched_context'] = enriched_info
        
        # Text input reconstruction
        if event_type in ('app_switch', 'browser_click', 'mouse_click', 'browser_navigation'):
            finalize_text_input(timestamp, context)
            
        if event_type == 'keystroke':
            char = payload.get('character')
            key = payload.get('key')
            
            if key == 'Enter':
                finalize_text_input(timestamp, context)
            elif key == 'Backspace':
                if current_text:
                    current_text.pop()
            elif char and len(char) == 1:
                current_text.append(char)
                last_target = payload.get('target_field')
        
        enriched.append(event)
        
    finalize_text_input(events[-1].get('timestamp_ms', 0) if events else 0, {})
    
    return enriched

def process_datasets():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    base_dir = project_root / "dataset_a"
    out_dir = project_root / "enriched_dataset_a"
    
    if not base_dir.exists():
        print(f"Error: {base_dir} not found.")
        return
        
    translation_map = load_translation_map(project_root)
    
    sessions_data = {}
    event_files = list(base_dir.rglob("events.jsonl"))
    
    for path in event_files:
        if path.parent.name.startswith("chunk_"):
            session_id = path.parent.parent.name
        else:
            session_id = path.parent.name
            
        if session_id not in sessions_data:
            sessions_data[session_id] = []
            
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    event = json.loads(line)
                    sessions_data[session_id].append(event)
                except:
                    continue

    out_dir.mkdir(parents=True, exist_ok=True)
    
    for session_id, events in sessions_data.items():
        events.sort(key=lambda x: x.get('timestamp_ms', 0))
        enriched_events = enrich_and_reconstruct(events, translation_map)
        
        session_out_dir = out_dir / session_id
        session_out_dir.mkdir(parents=True, exist_ok=True)
        
        out_file = session_out_dir / "enriched_events.jsonl"
        with open(out_file, 'w', encoding='utf-8') as f:
            for e in enriched_events:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')
                
    print(f"Enriched {len(sessions_data)} sessions and saved to {out_dir}")

if __name__ == '__main__':
    process_datasets()
