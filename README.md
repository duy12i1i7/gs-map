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
./run.sh download blender-lego
ITERATIONS=7000 ./run.sh train blender-lego
```

Sau khi train, mở viewer:

```bash
./run.sh viewer blender-lego
```

## Notebook cloud

- Colab 1 GPU: `notebooks/gs_map_colab_1gpu.ipynb`
- Kaggle 2 GPU: `notebooks/gs_map_kaggle_2gpu.ipynb`

Hai notebook clone repo rồi cài `requirements.txt` trước khi kiểm tra `torch`/CUDA.
Mặc định notebook chạy `blender-lego`, scene nổi tiếng của NeRF Synthetic, nhẹ hơn Mill19 nhiều.
Kaggle notebook mặc định chạy `NUM_DEVICES=2`. Nếu runtime 2 GPU của Kaggle bị lỗi DDP/Nerfstudio, đổi `NUM_DEVICES = "1"` trong cell cấu hình để fallback sang 1 GPU.

Viewer dùng port `7007` mặc định. Nếu cần đổi:

```bash
PORT=7010 ./run.sh viewer mill19-building
```

## Dataset có sẵn

```bash
./run.sh datasets
```

Các lựa chọn hiện tại:

- `blender-lego`: scene nổi tiếng của NeRF Synthetic, khuyến nghị chạy đầu tiên.
- `blender-chair`, `blender-drums`, `blender-ficus`, `blender-hotdog`, `blender-materials`, `blender-mic`, `blender-ship`: các scene NeRF Synthetic khác.
- `synthetic-map`: dataset map-like sinh local để smoke-test, không cần tải ngoài.
- `mill19-building`: aerial/industrial map-like scene, khuyến nghị chạy đầu tiên nếu muốn dataset liên quan đến map.
- `mill19-rubble`: aerial/industrial map-like scene khác từ Mill 19.
- `nerfstudio-poster`: dataset nhỏ để sanity-check pipeline.

## Lệnh thường dùng

Tải dataset:

```bash
./run.sh download blender-lego
```

Lệnh trên tải riêng scene `lego` từ Hugging Face mirror để tránh lỗi Google Drive/gdown của downloader mặc định. Có thể đổi sang scene `blender-*` khác.

Train:

```bash
ITERATIONS=7000 ./run.sh train blender-lego
```

Chạy multi-GPU khi backend hỗ trợ:

```bash
NUM_DEVICES=2 ITERATIONS=30000 ./run.sh train mill19-building
```

Eval:

```bash
./run.sh eval blender-lego
```

Export splat:

```bash
./run.sh export blender-lego
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
GSMAP_BACKEND=docker ./run.sh train blender-lego
```

Ép native:

```bash
GSMAP_BACKEND=native ./run.sh train blender-lego
```

## Ghi chú cho máy hiện tại

Workspace này đang ở macOS ARM, không thấy NVIDIA GPU. Bạn nên chạy repo này trên server/desktop Linux có NVIDIA GPU, hoặc clone sang Colab/RunPod/Lambda/AWS GPU instance rồi chạy các lệnh ở trên.
