import json
import glob
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

elements_found = set()
urls_found = set()
notes_values = []
events_sequence = []

for dataset_dir in ['enriched_dataset_b', 'enriched_dataset_a']:
    if not os.path.exists(dataset_dir):
        continue
    for sess in os.listdir(dataset_dir):
        p = os.path.join(dataset_dir, sess, 'enriched_events.jsonl')
        if not os.path.exists(p):
            continue
        with open(p, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                ev = json.loads(line)
                ctx = ev.get('context') or {}
                abt = ctx.get('active_browser_tab') or {}
                url = abt.get('url') or ''
                app = ctx.get('active_app') or {}
                window_title = app.get('window_title') or ''
                
                if 'payroll-items' in url or '5132' in url or '5133' in url or '給与' in window_title or 'payroll' in str(ev).lower():
                    if url:
                        urls_found.add(url)
                    
                    payload = ev.get('payload') or {}
                    el = payload.get('element') or {}
                    sel = el.get('css_selector') or el.get('id')
                    tag = el.get('tag')
                    cls = (el.get('attributes') or {}).get('class')
                    if sel or tag:
                        elements_found.add(f"{tag} | {sel} | class={cls}")
                    
                    val = payload.get('value') or payload.get('text') or payload.get('input_text')
                    if val and ('pi-note' in str(ev) or 'note' in str(ev).lower()):
                        notes_values.append(val)
                        
                    uia_target = ((ev.get('extensions') or {}).get('uia_v2') or {}).get('target') or {}
                    if uia_target.get('automation_id'):
                        elements_found.add(f"UIA: {uia_target.get('automation_id')} | class={uia_target.get('class_name')} | ctrl={uia_target.get('control_type')}")

print(f"=== URLs Visited ({len(urls_found)}) ===")
for u in sorted(urls_found):
    print(f"  - {u}")

print(f"\n=== DOM & UIA Elements Discovered ({len(elements_found)}) ===")
for e in sorted(elements_found):
    print(f"  - {e}")

print(f"\n=== Sample Input Values / Remarks Populated ({len(notes_values)}) ===")
for v in notes_values[:20]:
    print(f"  - {v}")
