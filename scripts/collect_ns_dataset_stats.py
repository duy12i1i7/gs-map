#!/usr/bin/env python3
import argparse, json, struct
from pathlib import Path

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}

def count_images(path: Path):
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob('*') if p.is_file() and p.suffix in IMAGE_EXTS and '_depth' not in p.name.lower())

def count_frames(path: Path):
    tf = path / 'transforms.json'
    if not tf.exists():
        return None
    try:
        return len(json.loads(tf.read_text()).get('frames', []))
    except Exception:
        return None

def count_points3d_bin(path: Path):
    if not path.exists():
        return None
    with open(path, 'rb') as f:
        return int(struct.unpack('<Q', f.read(8))[0])

def count_ply_vertices(path: Path):
    if not path.exists():
        return None
    with open(path, 'rb') as f:
        for raw in f:
            line = raw.decode('utf-8', errors='ignore').strip()
            if line.startswith('element vertex'):
                return int(line.split()[-1])
            if line == 'end_header':
                break
    return None

def find_sparse_points(processed_dir: Path):
    for p in [
        processed_dir / 'colmap' / 'sparse' / '0' / 'points3D.bin',
        processed_dir / 'sparse' / '0' / 'points3D.bin',
        processed_dir / 'colmap' / 'sparse' / 'points3D.bin',
    ]:
        n = count_points3d_bin(p)
        if n is not None:
            return n, str(p)
    for p in processed_dir.rglob('points3D.bin'):
        n = count_points3d_bin(p)
        if n is not None:
            return n, str(p)
    for p in [processed_dir / 'sparse_pc.ply', processed_dir / 'points3D.ply']:
        n = count_ply_vertices(p)
        if n is not None:
            return n, str(p)
    for p in processed_dir.rglob('*.ply'):
        n = count_ply_vertices(p)
        if n is not None:
            return n, str(p)
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', required=True)
    ap.add_argument('--processed-dir', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--time-seconds', type=float)
    ap.add_argument('--output-json', required=True)
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)
    sparse_points, sparse_source = find_sparse_points(processed_dir)
    stats = {
        'label': args.label,
        'raw_dir': str(raw_dir),
        'processed_dir': str(processed_dir),
        'raw_image_count': count_images(raw_dir),
        'processed_image_count': count_images(processed_dir / 'images'),
        'transforms_frame_count': count_frames(processed_dir),
        'sparse_point_count': sparse_points,
        'sparse_point_source': sparse_source,
        'process_time_seconds': args.time_seconds,
    }
    out = Path(args.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    main()
