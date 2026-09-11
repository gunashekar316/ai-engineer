import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Explicit mapping from English label to Ground Truth process code
LABEL_TO_CODE = {
    "resident_tax": "A",
    "salary_maintenance": "B",
    "childcare_leave": "C",
    "social_insurance": "D",
    "onboarding_allowance": "E",
    "invoice_approval": "F",
    "expense_claim": "G",
    "bank_reconciliation": "H",
    "budget_variance": "I",
    "payment_processing": "J",
    "order_processing": "K",
    "inventory_adjustment": "L",
    "supplier_contact": "M",
    "shipment_tracking": "N",
    "return_processing": "O"
}

def parse_iso(ts):
    # Handle potentially varying precision and timezones cleanly
    if not ts: return 0
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
    except Exception as e:
        print(f"Error parsing timestamp {ts}: {e}")
        return 0

def compute_overlap(start1, end1, start2, end2):
    latest_start = max(start1, start2)
    earliest_end = min(end1, end2)
    delta = earliest_end - latest_start
    return max(0, delta)

def evaluate(dataset_dir, predicted_segments_file):
    dataset_path = Path(dataset_dir)
    pred_path = Path(predicted_segments_file)
    
    # Load ground truth
    gt_data = {}
    
    for gt_file in dataset_path.rglob("gt_manifest.json"):
        if gt_file.parent.name.startswith("chunk_"):
            session_id = gt_file.parent.parent.name
        else:
            session_id = gt_file.parent.name
        if session_id not in gt_data:
            gt_data[session_id] = {}
        with open(gt_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            
        for process in manifest.get('processes', []):
            code = process.get('code')
            if not code: continue
            
            if code not in gt_data[session_id]:
                gt_data[session_id][code] = []
                
            for execution in process.get('executions', []):
                start_val = execution.get('start_ts')
                end_val = execution.get('end_ts')
                if not start_val or not end_val:
                    continue
                start = parse_iso(start_val)
                end = parse_iso(end_val)
                gt_data[session_id][code].append((start, end))
                
    # Load predicted segments
    pred_data = {}
    with open(pred_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            seg = json.loads(line)
            session_id = seg['session_id']
            label = seg['label']
            start = parse_iso(seg['start'])
            end = parse_iso(seg['end'])
            
            code = LABEL_TO_CODE.get(label)
            if not code:
                continue # Ignore noise or general processes not in ground truth
                
            if session_id not in pred_data:
                pred_data[session_id] = {}
            if code not in pred_data[session_id]:
                pred_data[session_id][code] = []
                
            pred_data[session_id][code].append((start, end))
            
    # Compute metrics per process code
    metrics = {code: {'intersection': 0, 'pred_duration': 0, 'gt_duration': 0} for code in LABEL_TO_CODE.values()}
    
    # Process GT durations
    for session_id, codes in gt_data.items():
        for code, intervals in codes.items():
            for s, e in intervals:
                if code in metrics:
                    metrics[code]['gt_duration'] += (e - s)
                    
    # Process Pred durations and intersections
    for session_id, codes in pred_data.items():
        for code, pred_intervals in codes.items():
            for ps, pe in pred_intervals:
                if code in metrics:
                    metrics[code]['pred_duration'] += (pe - ps)
                    
                # Find overlaps with GT
                gt_intervals = gt_data.get(session_id, {}).get(code, [])
                for gs, ge in gt_intervals:
                    overlap = compute_overlap(ps, pe, gs, ge)
                    if overlap > 0 and code in metrics:
                        metrics[code]['intersection'] += overlap
                        
    # Print results
    print("=== Segmentation Evaluation Summary ===")
    print(f"{'Code':<5} | {'Label':<25} | {'Intersection':<12} | {'Pred_Dur':<12} | {'GT_Dur':<12} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 110)
    
    total_intersection = 0
    total_pred = 0
    total_gt = 0
    
    for label, code in LABEL_TO_CODE.items():
        intersection = metrics[code]['intersection']
        pred_dur = metrics[code]['pred_duration']
        gt_dur = metrics[code]['gt_duration']
        
        total_intersection += intersection
        total_pred += pred_dur
        total_gt += gt_dur
        
        precision = (intersection / pred_dur) if pred_dur > 0 else 0
        recall = (intersection / gt_dur) if gt_dur > 0 else 0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"{code:<5} | {label:<25} | {intersection:12.1f} | {pred_dur:12.1f} | {gt_dur:12.1f} | {precision:10.4f} | {recall:10.4f} | {f1:10.4f}")
        
    print("-" * 110)
    global_p = (total_intersection / total_pred) if total_pred > 0 else 0
    global_r = (total_intersection / total_gt) if total_gt > 0 else 0
    global_f1 = (2 * global_p * global_r) / (global_p + global_r) if (global_p + global_r) > 0 else 0
    
    print(f"{'ALL':<5} | {'Global Macro':<25} | {total_intersection:12.1f} | {total_pred:12.1f} | {total_gt:12.1f} | {global_p:10.4f} | {global_r:10.4f} | {global_f1:10.4f}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python evaluate.py <dataset_a_dir> <predicted_segments_jsonl>")
        sys.exit(1)
    evaluate(sys.argv[1], sys.argv[2])
