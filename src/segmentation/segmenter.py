import sys
import json
from pathlib import Path
import urllib.parse
from datetime import datetime, timezone

def extract_intent(event):
    enriched = event.get('enriched_context', {})
    
    intent = enriched.get('inferred_intent')
    domain = enriched.get('domain')
    
    if intent and intent not in ['general', 'approve', 'apply', 'save', 'search', 'reject', 'confirm']:
        return intent
        
    # Novel Dataset B / Unmapped handling
    context = event.get('context') or {}
    browser = context.get('active_browser_tab') or {}
    app = context.get('active_app')
    
    # Try to derive from URL
    if isinstance(browser, dict) and browser.get('url'):
        url = browser.get('url', '')
        try:
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.netloc.replace('www.', '')
            path = parsed.path.strip('/').split('/')[0] if parsed.path != '/' else ''
            derived = f"proc_{netloc}_{path}".strip('_')
            # Don't create generic new tab paths
            if 'newtab' not in derived and derived != 'proc_':
                return derived
        except:
            pass
            
    # Try to derive from active app
    if isinstance(app, dict) and app.get('app_name'):
        name = app.get('app_name').replace(' ', '_').lower()
        if name not in ['chrome', 'edge', 'firefox', 'explorer', 'explorer.exe']:
            return f"proc_{name}"
            
    if isinstance(app, str):
        name = app.replace(' ', '_').lower()
        if name not in ['chrome', 'edge', 'firefox', 'explorer', 'explorer.exe']:
            return f"proc_{name}"
            
    # If all fails, return domain if it exists and isn't general
    if domain and domain != 'general':
        return f"domain_{domain}"
        
    return "noise"

def segment_events(events, idle_threshold_ms=120000, noise_threshold_ms=60000):
    raw_intents = [extract_intent(event) for event in events]
    
    def is_explicit(idx):
        if idx < 0 or idx >= len(raw_intents): return False
        intent = raw_intents[idx]
        return intent and not intent.startswith('proc_') and not intent.startswith('domain_') and intent not in ['noise', 'general']
        
    filled_intents = list(raw_intents)
    
    # 1. Split into continuous blocks by idle time > 120s
    blocks = []
    start_idx = 0
    for i, event in enumerate(events):
        ts = event.get('timestamp_ms', 0)
        if i > 0 and ts - events[i-1].get('timestamp_ms', 0) > idle_threshold_ms:
            blocks.append((start_idx, i-1))
            start_idx = i
    if events:
        blocks.append((start_idx, len(events)-1))
        
    # 2. Back/Forward fill explicit intents within each block
    for b_start, b_end in blocks:
        explicit_indices = [i for i in range(b_start, b_end+1) if is_explicit(i)]
        
        if explicit_indices:
            intents_in_block = set(raw_intents[i] for i in explicit_indices)
            if len(intents_in_block) == 1:
                the_intent = intents_in_block.pop()
                for i in range(b_start, b_end+1):
                    filled_intents[i] = the_intent
            else:
                for i in range(b_start, b_end+1):
                    if not is_explicit(i):
                        nearest_idx = min(explicit_indices, key=lambda idx: abs(events[i].get('timestamp_ms', 0) - events[idx].get('timestamp_ms', 0)))
                        filled_intents[i] = raw_intents[nearest_idx]

    # 3. Generate segments
    segments = []
    current_intent = None
    seg_start_ts = None
    last_iso = None
    
    noise_start_ts = None
    
    for i, event in enumerate(events):
        ts = event.get('timestamp_ms', 0)
        iso_ts = event.get('timestamp_iso')
        if not iso_ts:
            dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
            iso_ts = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
        intent = filled_intents[i]
        
        # Break on idle threshold
        if i > 0 and ts - events[i-1].get('timestamp_ms', 0) > idle_threshold_ms:
            if current_intent is not None:
                segments.append({"start": seg_start_ts, "end": last_iso, "label": current_intent})
                current_intent = None
                noise_start_ts = None
                
        if intent == "noise" or intent == "general":
            if current_intent is not None:
                if noise_start_ts is None:
                    noise_start_ts = ts
                elif ts - noise_start_ts > noise_threshold_ms:
                    segments.append({"start": seg_start_ts, "end": last_iso, "label": current_intent})
                    current_intent = None
                    noise_start_ts = None
        else:
            noise_start_ts = None
            if current_intent is None:
                current_intent = intent
                seg_start_ts = iso_ts
                last_iso = iso_ts
            elif current_intent != intent:
                segments.append({"start": seg_start_ts, "end": last_iso, "label": current_intent})
                current_intent = intent
                seg_start_ts = iso_ts
                last_iso = iso_ts
            else:
                last_iso = iso_ts
                
    if current_intent is not None and last_iso is not None:
        segments.append({"start": seg_start_ts, "end": last_iso, "label": current_intent})
        
    return segments

def run_segmenter(input_dir, output_file):
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: {input_dir} not found.")
        sys.exit(1)
        
    all_segments = []
    
    event_files = list(input_path.rglob("enriched_events.jsonl"))
    
    for file_path in event_files:
        if file_path.parent.name.startswith("chunk_"):
            session_id = file_path.parent.parent.name
        else:
            session_id = file_path.parent.name
        
        events = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
                    
        events.sort(key=lambda x: x.get('timestamp_ms', 0))
        
        segments = segment_events(events)
        
        for seg in segments:
            if seg["start"] == seg["end"]:
                dt = datetime.fromisoformat(seg["end"].replace('Z', '+00:00'))
                dt_new = datetime.fromtimestamp(dt.timestamp() + 0.001, tz=timezone.utc)
                seg["end"] = dt_new.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                
            all_segments.append({
                "session_id": session_id,
                "start": seg["start"],
                "end": seg["end"],
                "label": seg["label"]
            })
            
    with open(output_file, 'w', encoding='utf-8') as f:
        for seg in all_segments:
            f.write(json.dumps(seg) + '\n')
            
    print(f"Wrote {len(all_segments)} segments to {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python segmenter.py <input_enriched_dir> <output_jsonl>")
        sys.exit(1)
    run_segmenter(sys.argv[1], sys.argv[2])
