import json
import sys
import re
from datetime import datetime

def validate_iso8601_utc(ts):
    if not ts.endswith('Z') and not ts.endswith('+00:00'):
        return False
    try:
        ts_clean = ts.replace('Z', '+00:00')
        datetime.fromisoformat(ts_clean)
        return True
    except ValueError:
        return False

def validate_schema(file_path):
    required_keys = {'session_id', 'start', 'end', 'label'}
    
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: Invalid JSON - {str(e)}")
                    continue
                    
                if not isinstance(obj, dict):
                    errors.append(f"Line {line_num}: Must be a JSON object.")
                    continue
                    
                keys = set(obj.keys())
                if keys != required_keys:
                    errors.append(f"Line {line_num}: Keys mismatch. Found {keys}, expected exactly {required_keys}")
                    
                start = obj.get('start')
                end = obj.get('end')
                
                if isinstance(start, str) and not validate_iso8601_utc(start):
                    errors.append(f"Line {line_num}: 'start' is not a valid ISO 8601 UTC timestamp ({start})")
                if isinstance(end, str) and not validate_iso8601_utc(end):
                    errors.append(f"Line {line_num}: 'end' is not a valid ISO 8601 UTC timestamp ({end})")
                    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
        
    if errors:
        print("Validation Failed:", file=sys.stderr)
        for err in errors[:50]: # Print up to 50 errors
            print(f"  {err}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more errors.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Validation Passed: '{file_path}' is strictly compliant.")
        sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python validate_schema.py <path_to_jsonl>")
        sys.exit(1)
    validate_schema(sys.argv[1])
