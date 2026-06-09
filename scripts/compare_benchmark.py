#!/usr/bin/env python3
import argparse, csv, json
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text())

def ratio_reduction(pruned, base):
    if pruned is None or base in (None, 0):
        return None
    return 1 - pruned / base

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline-json', required=True)
    ap.add_argument('--pruned-json', required=True)
    ap.add_argument('--output-csv', required=True)
    ap.add_argument('--output-json', required=True)
    args = ap.parse_args()

    base = load(args.baseline_json)
    pruned = load(args.pruned_json)
    comparison = {
        'baseline': base,
        'pruned': pruned,
        'reduction': {
            'image_count_reduction_ratio': ratio_reduction(pruned.get('raw_image_count'), base.get('raw_image_count')),
            'process_time_reduction_ratio': ratio_reduction(pruned.get('process_time_seconds'), base.get('process_time_seconds')),
            'sparse_point_reduction_ratio': ratio_reduction(pruned.get('sparse_point_count'), base.get('sparse_point_count')),
        }
    }
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_json).write_text(json.dumps(comparison, indent=2))

    rows = []
    for item in [base, pruned]:
        rows.append({
            'label': item.get('label'),
            'raw_images': item.get('raw_image_count'),
            'processed_images': item.get('processed_image_count'),
            'frames': item.get('transforms_frame_count'),
            'sparse_points': item.get('sparse_point_count'),
            'process_time_seconds': item.get('process_time_seconds'),
        })
    with open(args.output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {args.output_csv}')
    print(f'Wrote {args.output_json}')

if __name__ == '__main__':
    main()
