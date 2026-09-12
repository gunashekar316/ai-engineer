import os
import sys
import json
import math
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def parse_iso(ts):
    if not ts: return 0.0
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
    except Exception as e:
        return 0.0

def load_data(project_root):
    segments_file = project_root / "segments.jsonl"
    enriched_dir = project_root / "enriched_dataset_b"
    
    if not segments_file.exists():
        print(f"Error: {segments_file} does not exist.")
        sys.exit(1)
        
    if not enriched_dir.exists():
        print(f"Error: {enriched_dir} does not exist.")
        sys.exit(1)
        
    with open(segments_file, 'r', encoding='utf-8') as f:
        segments = [json.loads(line) for line in f if line.strip()]
        
    # Group segments by session_id
    segments_by_session = defaultdict(list)
    for seg in segments:
        s_ts = parse_iso(seg['start']) * 1000.0
        e_ts = parse_iso(seg['end']) * 1000.0
        segments_by_session[seg['session_id']].append({
            'session_id': seg['session_id'],
            'start_iso': seg['start'],
            'end_iso': seg['end'],
            'start_ms': s_ts,
            'end_ms': e_ts,
            'duration_sec': max(0.0, (e_ts - s_ts) / 1000.0),
            'label': seg['label']
        })
        
    # Load enriched events per session
    events_by_session = {}
    for session_path in enriched_dir.iterdir():
        if session_path.is_dir():
            ev_file = session_path / "enriched_events.jsonl"
            if ev_file.exists():
                session_events = []
                with open(ev_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            session_events.append(json.loads(line))
                session_events.sort(key=lambda x: x.get('timestamp_ms', 0))
                events_by_session[session_path.name] = session_events
                
    return segments, segments_by_session, events_by_session

def analyze_operations(segments, segments_by_session, events_by_session):
    total_tracked_duration = sum(s['duration_sec'] for seg_list in segments_by_session.values() for s in seg_list)
    
    process_runs = defaultdict(list)
    
    for session_id, seg_list in segments_by_session.items():
        session_events = events_by_session.get(session_id, [])
        machine_id = session_id.split('-')[-1] if '-' in session_id else session_id
        
        for seg in seg_list:
            s_ms = seg['start_ms']
            e_ms = seg['end_ms']
            label = seg['label']
            
            # Events in this segment
            seg_events = [e for e in session_events if s_ms <= e.get('timestamp_ms', 0) <= e_ms]
            
            app_switches = 0
            keystrokes = 0
            clicks = 0
            clipboard_ops = 0
            reconstructed_chars = 0
            browser_errors = 0
            
            apps_used = set()
            urls_visited = set()
            window_titles_used = set()
            screen_transitions = []
            
            for e in seg_events:
                etype = e.get('event_type', '')
                payload = e.get('payload') or {}
                ctx = e.get('context') or {}
                
                if etype in ('app_switch', 'window_title_change'):
                    app_switches += 1
                if etype in ('keystroke', 'reconstructed_text_input'):
                    keystrokes += 1
                    if etype == 'reconstructed_text_input':
                        reconstructed_chars += len(payload.get('text', ''))
                if 'click' in etype:
                    clicks += 1
                if etype == 'shortcut':
                    combo = str(payload.get('combo', '')).lower()
                    if 'c' in combo or 'v' in combo:
                        clipboard_ops += 1
                if etype == 'browser_error':
                    browser_errors += 1
                    
                # App & screen tracking
                app_info = ctx.get('active_app') or {}
                app_name = app_info.get('app_name', '') if isinstance(app_info, dict) else str(app_info)
                w_title = app_info.get('window_title', '') if isinstance(app_info, dict) else ''
                tab_info = ctx.get('active_browser_tab') or {}
                url = tab_info.get('url', '') if isinstance(tab_info, dict) else ''
                
                if app_name: apps_used.add(app_name)
                if w_title: window_titles_used.add(w_title)
                if url: urls_visited.add(url)
                
                # Screen transition signature: URL path or window title
                screen_id = ""
                if url:
                    if '#' in url:
                        screen_id = '#' + url.split('#')[-1]
                    else:
                        screen_id = url.replace('http://127.0.0.1:5132', '').replace('http://127.0.0.1:5133', '').replace('http://127.0.0.1:5134', '')
                elif w_title:
                    screen_id = w_title.split('-')[0].strip()
                elif app_name:
                    screen_id = app_name
                    
                if screen_id and (not screen_transitions or screen_transitions[-1] != screen_id):
                    screen_transitions.append(screen_id)
                    
            path_sig = " -> ".join(screen_transitions[:5]) if screen_transitions else "Single-Screen"
            
            process_runs[label].append({
                'session_id': session_id,
                'machine_id': machine_id,
                'duration_sec': seg['duration_sec'],
                'event_count': len(seg_events),
                'app_switches': app_switches,
                'keystrokes': keystrokes,
                'clicks': clicks,
                'clipboard_ops': clipboard_ops,
                'reconstructed_chars': reconstructed_chars,
                'browser_errors': browser_errors,
                'apps_used': list(apps_used),
                'urls_visited': list(urls_visited),
                'path_sig': path_sig
            })
            
    # Aggregate metrics per process label
    process_metrics = {}
    
    for label, runs in process_runs.items():
        count = len(runs)
        durations = [r['duration_sec'] for r in runs]
        tot_dur = sum(durations)
        avg_dur = tot_dur / count if count else 0.0
        
        # Variance / Std dev
        variance = sum((d - avg_dur) ** 2 for d in durations) / count if count > 1 else 0.0
        std_dur = math.sqrt(variance)
        
        time_share = (tot_dur / total_tracked_duration * 100.0) if total_tracked_duration else 0.0
        
        sessions = set(r['session_id'] for r in runs)
        machines = set(r['machine_id'] for r in runs)
        
        avg_events = sum(r['event_count'] for r in runs) / count
        avg_switches = sum(r['app_switches'] for r in runs) / count
        avg_keys = sum(r['keystrokes'] for r in runs) / count
        avg_clicks = sum(r['clicks'] for r in runs) / count
        avg_clipboard = sum(r['clipboard_ops'] for r in runs) / count
        avg_chars = sum(r['reconstructed_chars'] for r in runs) / count
        tot_errors = sum(r['browser_errors'] for r in runs)
        
        # Paths & branches
        path_counts = Counter(r['path_sig'] for r in runs)
        top_paths = path_counts.most_common(3)
        dominant_path_ratio = (top_paths[0][1] / count) if top_paths else 0.0
        distinct_variants = len(path_counts)
        
        process_metrics[label] = {
            'frequency': count,
            'cumulative_duration_sec': round(tot_dur, 1),
            'avg_duration_sec': round(avg_dur, 1),
            'std_duration_sec': round(std_dur, 1),
            'time_share_pct': round(time_share, 2),
            'session_count': len(sessions),
            'machine_count': len(machines),
            'avg_events_per_run': round(avg_events, 1),
            'avg_app_switches': round(avg_switches, 1),
            'avg_keystrokes': round(avg_keys, 1),
            'avg_clicks': round(avg_clicks, 1),
            'avg_clipboard_ops': round(avg_clipboard, 1),
            'avg_input_chars': round(avg_chars, 1),
            'total_errors': tot_errors,
            'distinct_variants': distinct_variants,
            'dominant_path_ratio': round(dominant_path_ratio, 3),
            'top_paths': [{'path': p, 'count': c, 'ratio': round(c/count, 2)} for p, c in top_paths]
        }
        
    return total_tracked_duration, process_metrics

def compute_roi_and_ranking(process_metrics):
    max_time_share = max(m['time_share_pct'] for m in process_metrics.values()) or 1.0
    max_freq = max(m['frequency'] for m in process_metrics.values()) or 1.0
    
    scored_processes = []
    
    for label, m in process_metrics.items():
        # 1. Impact Score (0 - 100)
        # 60% based on total labor time consumed, 40% based on execution frequency
        norm_time = (m['time_share_pct'] / max_time_share) * 100.0
        norm_freq = (m['frequency'] / max_freq) * 100.0
        impact_score = (0.60 * norm_time) + (0.40 * norm_freq)
        
        # 2. Feasibility Score (0 - 100)
        # Component A: Path Predictability & Low Branching (40 pts)
        path_predictability = m['dominant_path_ratio'] * 40.0
        
        # Component B: Low Application/Window Switching Friction (30 pts)
        switches = m['avg_app_switches']
        if switches <= 1.0:
            app_score = 30.0
        elif switches <= 3.0:
            app_score = 25.0
        elif switches <= 6.0:
            app_score = 18.0
        elif switches <= 10.0:
            app_score = 10.0
        else:
            app_score = 5.0
            
        # Component C: Input Determinism & Low Exception Rate (30 pts)
        error_penalty = min(15.0, m['total_errors'] * 3.0)
        input_determinism = 30.0 - error_penalty
        
        feasibility_score = path_predictability + app_score + input_determinism
        
        # 3. Composite Priority Score (0 - 100)
        # Balanced 55% Impact, 45% Feasibility
        composite_score = (0.55 * impact_score) + (0.45 * feasibility_score)
        
        scored_processes.append({
            'label': label,
            'frequency': m['frequency'],
            'cumulative_duration_sec': m['cumulative_duration_sec'],
            'avg_duration_sec': m['avg_duration_sec'],
            'time_share_pct': m['time_share_pct'],
            'session_count': m['session_count'],
            'machine_count': m['machine_count'],
            'avg_events': m['avg_events_per_run'],
            'avg_switches': m['avg_app_switches'],
            'avg_keys': m['avg_keystrokes'],
            'avg_clicks': m['avg_clicks'],
            'dominant_path_ratio': m['dominant_path_ratio'],
            'impact_score': round(impact_score, 1),
            'feasibility_score': round(feasibility_score, 1),
            'composite_score': round(composite_score, 1),
            'raw_metrics': m
        })
        
    # Sort descending by composite score
    scored_processes.sort(key=lambda x: -x['composite_score'])
    
    for idx, item in enumerate(scored_processes, 1):
        item['priority_rank'] = idx
        
    return scored_processes

def generate_markdown_report(total_duration, scored_processes):
    lines = []
    lines.append("# Dataset B Operational Analysis & Automation Prioritization Matrix")
    lines.append(f"\n**Total Tracked Operational Duration:** {total_duration:,.1f} seconds ({total_duration/3600:.2f} hours) across 15 production sessions.")
    lines.append(f"**Discovered Business Processes:** {len(scored_processes)} distinct workflows.\n")
    
    lines.append("## 1. Process Operations & Friction Metrics Summary")
    lines.append("| Rank | Process Label | Freq | Total Time (s) | Time Share (%) | Avg Dur (s) | Machines | Avg Evts | Avg Sw | Avg Keys | Avg Clicks |")
    lines.append("|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    
    for p in scored_processes:
        lines.append(f"| {p['priority_rank']} | `{p['label']}` | {p['frequency']} | {p['cumulative_duration_sec']:,.1f} | {p['time_share_pct']}% | {p['avg_duration_sec']} | {p['machine_count']} | {p['avg_events']} | {p['avg_switches']} | {p['avg_keys']} | {p['avg_clicks']} |")
        
    lines.append("\n## 2. Automation Ranking & ROI Matrix")
    lines.append("| Rank | Process Label | Impact Score (55%) | Feasibility Score (45%) | Priority Score | Primary Automation Barrier / Enabler | Recommendation |")
    lines.append("|:---:|:---|:---:|:---:|:---:|:---|:---|")
    
    for p in scored_processes:
        m = p['raw_metrics']
        enabler = ""
        rec = ""
        if p['priority_rank'] == 1:
            enabler = "High volume, clean browser form UI, standardized keystroke entries"
            rec = "**Prototype Target (#1)**"
        elif p['priority_rank'] <= 3:
            enabler = "High operational time share, repetitive tabular reconciliation"
            rec = "Phase 3 Secondary Candidate"
        elif p['feasibility_score'] < 60:
            enabler = "High branching entropy or cross-application spread"
            rec = "Standardize Procedure First"
        else:
            enabler = "Moderate volume, deterministic entry fields"
            rec = "Phase 4 Pipeline"
            
        lines.append(f"| {p['priority_rank']} | `{p['label']}` | {p['impact_score']} | {p['feasibility_score']} | **{p['composite_score']}** | {enabler} | {rec} |")
        
    lines.append("\n## 3. Workflow Pattern & Path Variance Analysis")
    lines.append("| Process Label | Distinct Variants | Dominant Path Ratio (%) | Dominant Execution Path |")
    lines.append("|:---|:---:|:---:|:---|")
    for p in scored_processes:
        m = p['raw_metrics']
        dom_path = m['top_paths'][0]['path'] if m['top_paths'] else "N/A"
        lines.append(f"| `{p['label']}` | {m['distinct_variants']} | {m['dominant_path_ratio']*100:.1f}% | `{dom_path}` |")
        
    return "\n".join(lines)

def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    segments, segments_by_session, events_by_session = load_data(project_root)
    
    total_duration, process_metrics = analyze_operations(segments, segments_by_session, events_by_session)
    scored_processes = compute_roi_and_ranking(process_metrics)
    
    # Save output json
    output_json_path = project_root / "src" / "analysis" / "process_metrics.json"
    output_payload = {
        'total_duration_sec': round(total_duration, 1),
        'total_segments_count': len(segments),
        'ranked_processes': scored_processes,
        'detailed_metrics': process_metrics
    }
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully computed operational metrics for {len(scored_processes)} processes.")
    print(f"Metrics saved to: {output_json_path}\n")
    
    # Print formatted markdown table
    md_report = generate_markdown_report(total_duration, scored_processes)
    print(md_report)

if __name__ == '__main__':
    main()
