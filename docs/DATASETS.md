# Dataset Notes

## Lightweight famous datasets

### NeRF Synthetic / Blender: `blender-lego`, `blender-chair`, `blender-drums`, `blender-ficus`, `blender-hotdog`, `blender-materials`, `blender-mic`, `blender-ship`

Đây là benchmark kinh điển của NeRF, nổi tiếng hơn `synthetic-map` và nhẹ hơn Mill19 rất nhiều. `run.sh download blender-lego` tải riêng scene `lego` từ Hugging Face mirror để tránh lỗi Google Drive/gdown của downloader mặc định.

```bash
./run.sh download blender-lego
ITERATIONS=7000 ./run.sh train blender-lego
```

Đổi scene:

```bash
ITERATIONS=7000 ./run.sh train blender-hotdog
ITERATIONS=7000 ./run.sh train blender-chair
```

## Recommended map-like datasets

### `synthetic-map`

`synthetic-map` là dataset map-like sinh local để smoke-test pipeline khi các nguồn dataset public bị chặn hoặc bạn chưa muốn tải scene lớn. Nó tạo ảnh, `transforms.json` và point cloud `.ply` theo format Nerfstudio.

```bash
./run.sh download synthetic-map
ITERATIONS=1000 ./run.sh train synthetic-map
```

### Mill 19: `mill19-building`, `mill19-rubble`

Mill 19 là dataset large-scale aerial/industrial scene từ Mega-NeRF. Trong project này, dataset được tải bằng `ns-download-data mill19` và train bằng Nerfstudio `splatfacto`.

```bash
./run.sh download mill19-building
ITERATIONS=30000 ./run.sh train mill19-building
```

Chạy thử nhanh:

```bash
ITERATIONS=7000 ./run.sh train mill19-building
```

### MatrixCity

MatrixCity là dataset city-scale neural rendering rất hợp nếu muốn scene kiểu thành phố/bản đồ 3D. Dataset lớn hơn và quy trình chuẩn bị phụ thuộc subset bạn chọn, nên chưa bật thành command mặc định trong `run.sh`.

Workflow nên làm:

1. Tải subset MatrixCity bạn cần.
2. Chuyển camera/images sang format Nerfstudio hoặc COLMAP.
3. Train bằng `splatfacto` hoặc official 3DGS.

### Argoverse 2, nuScenes, Waymo, KITTI-360

Các dataset này mạnh về autonomous driving và HD map. Chúng không phải dataset Gaussian Splatting "drop-in" vì thường cần converter:

- camera calibration
- ego/camera pose
- frame selection
- mask vật thể động
- map/lane annotation nếu muốn render hoặc overlay

Nên dùng khi mục tiêu là road/lane/HD-map research, không phải chỉ benchmark novel-view synthesis.

## Smaller sanity datasets

### `nerfstudio-poster`

Dataset nhỏ để kiểm tra Docker, viewer và GPU trước khi tải Mill 19.

```bash
./run.sh download nerfstudio-poster
ITERATIONS=1000 ./run.sh train nerfstudio-poster
```

### `blender-lego`

Synthetic dataset kinh điển của NeRF. Không phải map, nhưng tốt để kiểm tra pipeline.

```bash
./run.sh download blender-lego
ITERATIONS=3000 ./run.sh train blender-lego
```
