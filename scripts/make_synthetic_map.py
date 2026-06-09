#!/usr/bin/env python3
"""Generate a tiny Nerfstudio-format map-like dataset for smoke tests."""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover - exercised by user environment.
    raise SystemExit("Pillow is required. Install it with: python3 -m pip install pillow") from exc


WIDTH = 512
HEIGHT = 512
NUM_FRAMES = 36


def normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(sum(component * component for component in vector))
    return tuple(component / length for component in vector)


def cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def look_at(
    eye: tuple[float, float, float],
    target: tuple[float, float, float] = (0.0, 0.0, 0.0),
    world_up: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> list[list[float]]:
    forward = normalize(tuple(target[i] - eye[i] for i in range(3)))
    right = normalize(cross(forward, world_up))
    up = cross(right, forward)
    back = tuple(-component for component in forward)

    return [
        [right[0], up[0], back[0], eye[0]],
        [right[1], up[1], back[1], eye[1]],
        [right[2], up[2], back[2], eye[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def make_base_map() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (42, 56, 50))
    draw = ImageDraw.Draw(image)

    for x in range(0, WIDTH, 32):
        draw.line((x, 0, x, HEIGHT), fill=(59, 77, 70), width=1)
    for y in range(0, HEIGHT, 32):
        draw.line((0, y, WIDTH, y), fill=(59, 77, 70), width=1)

    roads = [
        ((-80, 210), (600, 250), 42),
        ((230, -40), (268, 560), 36),
        ((-40, 130), (530, 20), 24),
        ((50, 560), (470, -40), 20),
    ]
    for line_start, line_end, width in roads:
        draw.line((*line_start, *line_end), fill=(196, 189, 164), width=width)
        draw.line((*line_start, *line_end), fill=(88, 87, 80), width=max(2, width // 9))

    blocks = [
        (78, 78, 160, 145, (88, 128, 180)),
        (178, 78, 242, 150, (181, 98, 87)),
        (300, 72, 426, 156, (91, 151, 118)),
        (88, 294, 202, 414, (196, 144, 72)),
        (330, 286, 440, 402, (125, 102, 172)),
    ]
    for x0, y0, x1, y1, color in blocks:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=4, fill=color, outline=(28, 36, 34), width=3)

    parks = [
        (22, 350, 74, 434),
        (448, 110, 498, 206),
        (242, 330, 304, 430),
    ]
    for x0, y0, x1, y1 in parks:
        draw.ellipse((x0, y0, x1, y1), fill=(71, 126, 69), outline=(34, 70, 42), width=2)

    return image


def write_images(output_dir: Path) -> list[dict[str, object]]:
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    base = make_base_map()
    frames: list[dict[str, object]] = []
    focal = 0.5 * WIDTH / math.tan(math.radians(58.0) / 2.0)

    for index in range(NUM_FRAMES):
        angle = 2.0 * math.pi * index / NUM_FRAMES
        radius = 4.2 + 0.35 * math.sin(angle * 3.0)
        eye = (
            radius * math.cos(angle),
            radius * math.sin(angle),
            3.0 + 0.35 * math.cos(angle * 2.0),
        )
        filename = f"frame_{index:03d}.png"

        rotated = base.rotate(
            math.degrees(angle),
            resample=Image.Resampling.BICUBIC,
            fillcolor=(42, 56, 50),
        )
        crop = rotated.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC)
        crop.save(images_dir / filename)

        frames.append(
            {
                "file_path": f"images/{filename}",
                "transform_matrix": look_at(eye),
                "fl_x": focal,
                "fl_y": focal,
                "cx": WIDTH / 2.0,
                "cy": HEIGHT / 2.0,
                "w": WIDTH,
                "h": HEIGHT,
            }
        )

    return frames


def write_point_cloud(output_dir: Path) -> None:
    points: list[tuple[float, float, float, int, int, int]] = []

    for ix in range(-28, 29):
        for iy in range(-28, 29):
            x = ix / 8.0
            y = iy / 8.0
            road = abs(y - 0.2 * math.sin(x * 1.4)) < 0.18 or abs(x + 0.15 * math.sin(y * 1.6)) < 0.16
            if road:
                color = (196, 189, 164)
                z = 0.01
            elif (ix + iy) % 7 == 0:
                color = (91, 151, 118)
                z = 0.04
            else:
                color = (52, 83, 64)
                z = 0.0
            points.append((x, y, z, *color))

    buildings = [
        (-1.9, -1.6, 0.7, 0.6, 0.75, (88, 128, 180)),
        (-0.5, -1.5, 0.6, 0.8, 0.95, (181, 98, 87)),
        (1.3, -1.4, 1.0, 0.7, 0.65, (91, 151, 118)),
        (-1.4, 1.3, 1.1, 1.1, 0.8, (196, 144, 72)),
        (1.7, 1.2, 1.0, 1.0, 1.0, (125, 102, 172)),
    ]
    for cx, cy, sx, sy, height, color in buildings:
        for ix in range(10):
            for iy in range(10):
                x = cx + sx * (ix / 9.0 - 0.5)
                y = cy + sy * (iy / 9.0 - 0.5)
                points.append((x, y, height, *color))

    ply_path = output_dir / "sparse_pc.ply"
    with ply_path.open("w", encoding="ascii") as ply:
        ply.write("ply\n")
        ply.write("format ascii 1.0\n")
        ply.write(f"element vertex {len(points)}\n")
        ply.write("property float x\n")
        ply.write("property float y\n")
        ply.write("property float z\n")
        ply.write("property uchar red\n")
        ply.write("property uchar green\n")
        ply.write("property uchar blue\n")
        ply.write("end_header\n")
        for point in points:
            ply.write("%f %f %f %d %d %d\n" % point)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: make_synthetic_map.py <output-dir>", file=sys.stderr)
        return 2

    output_dir = Path(sys.argv[1]).expanduser().resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    frames = write_images(output_dir)
    write_point_cloud(output_dir)

    transforms = {
        "camera_model": "OPENCV",
        "orientation_override": "none",
        "applied_transform": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        "ply_file_path": "sparse_pc.ply",
        "frames": frames,
    }
    with (output_dir / "transforms.json").open("w", encoding="utf-8") as handle:
        json.dump(transforms, handle, indent=2)
        handle.write("\n")

    print(f"Wrote synthetic map dataset to {output_dir}")
    print(f"Frames: {len(frames)}")
    print("Point cloud: sparse_pc.ply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
