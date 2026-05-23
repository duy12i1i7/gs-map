# Gaussian Splatting Map Runner

Project này là wrapper để train và xem **3D Gaussian Splatting** trên các dataset kiểu map/urban scene. Backend mặc định là **Nerfstudio `splatfacto`**, vì có Docker image, downloader dataset, viewer realtime và export Gaussian splat `.ply`.

## Yêu cầu

Train cần máy **Linux + NVIDIA GPU + CUDA driver**. Máy macOS ARM có thể chỉnh code/tải nhẹ, nhưng không phù hợp để train Gaussian Splatting realtime bằng CUDA.

Nếu dùng Docker:

- Docker
- NVIDIA driver
- NVIDIA Container Toolkit

## Chạy nhanh

```bash
chmod +x run.sh
./run.sh doctor
./run.sh setup
./run.sh download synthetic-map
ITERATIONS=1000 ./run.sh train synthetic-map
```

Sau khi train, mở viewer:

```bash
./run.sh viewer synthetic-map
```

Viewer dùng port `7007` mặc định. Nếu cần đổi:

```bash
PORT=7010 ./run.sh viewer mill19-building
```

## Dataset có sẵn

```bash
./run.sh datasets
```

Các lựa chọn hiện tại:

- `synthetic-map`: dataset map-like sinh local để smoke-test, không cần tải ngoài.
- `mill19-building`: aerial/industrial map-like scene, khuyến nghị chạy đầu tiên nếu muốn dataset liên quan đến map.
- `mill19-rubble`: aerial/industrial map-like scene khác từ Mill 19.
- `nerfstudio-poster`: dataset nhỏ để sanity-check pipeline.
- `blender-lego`: scene synthetic kinh điển của NeRF.

## Lệnh thường dùng

Tải dataset:

```bash
./run.sh download synthetic-map
```

Train:

```bash
ITERATIONS=30000 ./run.sh train synthetic-map
```

Eval:

```bash
./run.sh eval mill19-building
```

Export splat:

```bash
./run.sh export mill19-building
```

Kết quả chính nằm ở:

- `data/`: dataset đã tải
- `outputs/`: checkpoint và `config.yml`
- `exports/`: Gaussian splat export

## Backend

Mặc định `run.sh` tự chọn:

- nếu máy có `ns-train` và `ns-download-data`, dùng native Nerfstudio
- nếu không, dùng Docker image `ghcr.io/nerfstudio-project/nerfstudio:latest`

Ép Docker:

```bash
GSMAP_BACKEND=docker ./run.sh train mill19-building
```

Ép native:

```bash
GSMAP_BACKEND=native ./run.sh train mill19-building
```

## Ghi chú cho máy hiện tại

Workspace này đang ở macOS ARM, không thấy NVIDIA GPU. Bạn nên chạy repo này trên server/desktop Linux có NVIDIA GPU, hoặc clone sang Colab/RunPod/Lambda/AWS GPU instance rồi chạy các lệnh ở trên.
