import json
import argparse
import sys

def get_batch(json_path, start_idx, batch_size):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        sys.exit(1)
        
    count = 0
    collected = []
    
    for i, item in enumerate(data.get('contents', [])):
        # Skip raw sections or sections without Japanese text
        if item.get('ja') and not item.get('raw'):
            if count >= start_idx and count < start_idx + batch_size:
                collected.append((i, item.get('text', ''), item.get('ja', '')))
            count += 1
            
    for i, text, ja in collected:
        print(f"[{i}] EN: {text}")
        print(f"[{i}] JA: {ja}")
        print("-" * 40)
        
    if not collected:
        print("No more paragraphs found in the given range.")
    else:
        print(f"Showing batch from logical index {start_idx} to {start_idx + len(collected) - 1}.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract a batch of paragraphs from an RFC translation JSON.")
    parser.add_argument("json_path", help="Path to the JSON file (e.g. data/8000/rfc8878-trans.json)")
    parser.add_argument("start_idx", type=int, help="Starting logical index of the translatable paragraphs")
    parser.add_argument("batch_size", type=int, help="Number of paragraphs to extract")
    args = parser.parse_args()
    
    get_batch(args.json_path, args.start_idx, args.batch_size)
