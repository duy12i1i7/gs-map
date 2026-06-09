#!/usr/bin/env python3
import argparse, json, shutil
from pathlib import Path
import cv2
import numpy as np

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}

def is_rgb_image_file(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix in IMAGE_EXTS and '_depth' not in name and 'depth' not in [p.lower() for p in path.parts]

def sharpness_score(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def texture_score(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    return float(np.count_nonzero(edges) / edges.size)

def color_hist(img):
    small = cv2.resize(img, (160, 90))
    hist = cv2.calcHist([small], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    return cv2.normalize(hist, hist).flatten()

def similarity(hist_a, hist_b):
    return float(cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL))

def normalize(values):
    arr = np.array(values, dtype=np.float64)
    if len(arr) == 0:
        return arr
    if arr.max() - arr.min() < 1e-9:
        return np.ones_like(arr)
    return (arr - arr.min()) / (arr.max() - arr.min())

def find_image_dir(dataset_dir: Path) -> Path:
    candidates = [dataset_dir / 'images', dataset_dir / 'rgb', dataset_dir / 'train', dataset_dir / 'val', dataset_dir / 'test', dataset_dir]
    for c in candidates:
        if c.exists() and c.is_dir():
            imgs = [p for p in c.iterdir() if p.is_file() and is_rgb_image_file(p)]
            if imgs:
                return c
    imgs = []
    for ext in IMAGE_EXTS:
        imgs.extend([p for p in dataset_dir.rglob(f'*{ext}') if p.is_file() and is_rgb_image_file(p)])
    if imgs:
        counts = {}
        for p in imgs:
            counts[p.parent] = counts.get(p.parent, 0) + 1
        return max(counts.items(), key=lambda x: x[1])[0]
    raise FileNotFoundError(f'Cannot find image folder inside {dataset_dir}')

def copy_raw_image_folder(src_dataset, dst_dataset, src_image_dir, selected_files):
    if dst_dataset.exists():
        shutil.rmtree(dst_dataset)
    dst_images = dst_dataset / 'images'
    dst_images.mkdir(parents=True, exist_ok=True)
    for p in selected_files:
        shutil.copy2(p, dst_images / p.name)
    return dst_images

def copy_dataset_structure(src_dataset, dst_dataset, src_image_dir, selected_files):
    if dst_dataset.exists():
        shutil.rmtree(dst_dataset)
    dst_dataset.mkdir(parents=True, exist_ok=True)
    selected_names = set(p.name for p in selected_files)

    for p in src_dataset.iterdir():
        if p.is_file():
            shutil.copy2(p, dst_dataset / p.name)

    skip_dirs = {'train', 'val', 'test', 'images', 'rgb'}
    for p in src_dataset.iterdir():
        if p.is_dir() and p.name not in skip_dirs:
            shutil.copytree(p, dst_dataset / p.name)

    rel_image_dir = src_image_dir.relative_to(src_dataset)
    dst_image_dir = dst_dataset / rel_image_dir
    dst_image_dir.mkdir(parents=True, exist_ok=True)

    for p in selected_files:
        shutil.copy2(p, dst_image_dir / p.name)

    for split in ['val', 'test']:
        src_split = src_dataset / split
        dst_split = dst_dataset / split
        if src_split.exists() and src_split.is_dir():
            shutil.copytree(src_split, dst_split)

    for tf_name in ['transforms_train.json', 'transforms.json']:
        src_tf = src_dataset / tf_name
        dst_tf = dst_dataset / tf_name
        if src_tf.exists():
            data = json.loads(src_tf.read_text())
            if 'frames' in data:
                new_frames = []
                for frame in data['frames']:
                    fp = frame.get('file_path', '')
                    name = Path(fp).name
                    stem = Path(fp).stem
                    if name in selected_names or f'{stem}.png' in selected_names or f'{stem}.jpg' in selected_names:
                        new_frames.append(frame)
                data['frames'] = new_frames
            dst_tf.write_text(json.dumps(data, indent=2))
    return dst_image_dir

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--keep-ratio', type=float, default=0.5)
    ap.add_argument('--min-sharpness', type=float, default=20.0)
    ap.add_argument('--min-texture', type=float, default=0.005)
    ap.add_argument('--alpha', type=float, default=0.45)
    ap.add_argument('--beta', type=float, default=0.35)
    ap.add_argument('--gamma', type=float, default=0.20)
    ap.add_argument('--redundancy-threshold', type=float, default=0.96)
    ap.add_argument('--raw', action='store_true')
    args = ap.parse_args()

    src_dataset = Path(args.input).resolve()
    dst_dataset = Path(args.output).resolve()
    src_image_dir = find_image_dir(src_dataset)
    image_paths = sorted([p for p in src_image_dir.iterdir() if p.is_file() and is_rgb_image_file(p)])
    if not image_paths:
        raise RuntimeError(f'No RGB images found in {src_image_dir}')

    records = []
    for p in image_paths:
        img = cv2.imread(str(p))
        if img is None:
            continue
        records.append({'path': p, 'sharpness': sharpness_score(img), 'texture': texture_score(img), 'hist': color_hist(img)})

    sharp_norm = normalize([r['sharpness'] for r in records])
    tex_norm = normalize([r['texture'] for r in records])
    for i, r in enumerate(records):
        r['sharpness_norm'] = float(sharp_norm[i])
        r['texture_norm'] = float(tex_norm[i])
        r['base_score'] = args.alpha * r['sharpness_norm'] + args.beta * r['texture_norm']

    candidates = [r for r in records if r['sharpness'] >= args.min_sharpness and r['texture'] >= args.min_texture] or records
    target_count = max(1, int(round(len(records) * args.keep_ratio)))
    candidates = sorted(candidates, key=lambda x: x['base_score'], reverse=True)

    selected = []
    for r in candidates:
        if len(selected) >= target_count:
            break
        if not selected:
            r['novelty'] = 1.0
            r['max_similarity'] = 0.0
            r['final_score'] = r['base_score'] + args.gamma
            selected.append(r)
            continue
        max_sim = max(similarity(r['hist'], s['hist']) for s in selected)
        novelty = 1.0 - max_sim
        r['novelty'] = float(novelty)
        r['max_similarity'] = float(max_sim)
        r['final_score'] = float(r['base_score'] + args.gamma * novelty)
        if max_sim < args.redundancy_threshold:
            selected.append(r)

    if len(selected) < target_count:
        selected_paths = {s['path'] for s in selected}
        for r in candidates:
            if len(selected) >= target_count:
                break
            if r['path'] not in selected_paths:
                r.setdefault('novelty', None)
                r.setdefault('max_similarity', None)
                r.setdefault('final_score', r['base_score'])
                selected.append(r)
                selected_paths.add(r['path'])

    selected_files = [r['path'] for r in selected]
    output_image_dir = copy_raw_image_folder(src_dataset, dst_dataset, src_image_dir, selected_files) if args.raw else copy_dataset_structure(src_dataset, dst_dataset, src_image_dir, selected_files)

    report = {
        'input_dataset': str(src_dataset),
        'input_image_dir': str(src_image_dir),
        'output_dataset': str(dst_dataset),
        'output_image_dir': str(output_image_dir),
        'raw_mode': bool(args.raw),
        'input_images': len(records),
        'selected_images': len(selected),
        'keep_ratio_target': args.keep_ratio,
        'actual_keep_ratio': len(selected) / len(records),
        'selected': [{'file': r['path'].name, 'sharpness': r['sharpness'], 'texture': r['texture'], 'base_score': r['base_score'], 'novelty': r.get('novelty'), 'max_similarity': r.get('max_similarity'), 'final_score': r.get('final_score')} for r in selected],
    }
    report_path = dst_dataset / 'view_pruning_report.json'
    report_path.write_text(json.dumps(report, indent=2))
    print(f'Input images: {len(records)}')
    print(f'Selected images: {len(selected)}')
    print(f'Output dataset: {dst_dataset}')
    print(f'Output image dir: {output_image_dir}')
    print(f'Report: {report_path}')

if __name__ == '__main__':
    main()
