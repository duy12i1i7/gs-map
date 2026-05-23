#!/usr/bin/env python3
"""Download one NeRF Synthetic / Blender scene from a Hugging Face mirror."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from huggingface_hub import snapshot_download


SCENES = {
    "chair",
    "drums",
    "ficus",
    "hotdog",
    "lego",
    "materials",
    "mic",
    "ship",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", choices=sorted(SCENES))
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    scene = args.scene

    if (output_dir / "transforms_train.json").exists() and not args.force:
        print(f"Using existing Blender scene: {output_dir}")
        return 0

    if output_dir.exists():
        shutil.rmtree(output_dir)

    tmp_dir = output_dir.parent / f".{scene}-hf-download"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.parent.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id="rishitdagli/nerf-gs-datasets",
        repo_type="dataset",
        allow_patterns=[f"{scene}/**"],
        local_dir=tmp_dir,
        local_dir_use_symlinks=False,
    )

    scene_dir = tmp_dir / scene
    if not (scene_dir / "transforms_train.json").exists():
        raise SystemExit(f"Downloaded scene is missing transforms_train.json: {scene_dir}")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(scene_dir), str(output_dir))
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"Wrote Blender scene '{scene}' to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
