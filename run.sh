#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${DATA_DIR:-${ROOT_DIR}/data}"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/outputs}"
EXPORT_DIR="${EXPORT_DIR:-${ROOT_DIR}/exports}"
CACHE_DIR="${CACHE_DIR:-${HOME}/.cache/gsmap}"
PORT="${PORT:-7007}"
ITERATIONS="${ITERATIONS:-30000}"
NUM_DEVICES="${NUM_DEVICES:-1}"
NERFSTUDIO_IMAGE="${NERFSTUDIO_IMAGE:-ghcr.io/nerfstudio-project/nerfstudio:latest}"
GSMAP_BACKEND="${GSMAP_BACKEND:-auto}"
ALLOW_NO_NVIDIA="${ALLOW_NO_NVIDIA:-0}"

if [[ -t 0 && -t 1 ]]; then
  DOCKER_TTY=(-it)
else
  DOCKER_TTY=()
fi

usage() {
  cat <<'EOF'
Gaussian Splatting map runner

Usage:
  ./run.sh doctor
  ./run.sh setup
  ./run.sh datasets
  ./run.sh download <dataset>
  ./run.sh train <dataset>
  ./run.sh eval <dataset>
  ./run.sh export <dataset>
  ./run.sh viewer <dataset|config.yml>
  ./run.sh shell
  ./run.sh quickstart

Datasets:
  synthetic-map    Local generated map-like smoke-test dataset.
  blender-chair    Classic NeRF Synthetic scene.
  blender-drums    Classic NeRF Synthetic scene.
  blender-ficus    Classic NeRF Synthetic scene.
  blender-hotdog   Classic NeRF Synthetic scene.
  mill19-building  Aerial/industrial map-like scene from Mill 19.
  mill19-rubble    Aerial/industrial map-like scene from Mill 19.
  nerfstudio-poster Small sanity-check dataset.
  blender-lego     Synthetic NeRF dataset scene.
  blender-materials Synthetic NeRF dataset scene.
  blender-mic      Synthetic NeRF dataset scene.
  blender-ship     Synthetic NeRF dataset scene.

Useful env vars:
  ITERATIONS=7000            Reduce train time for a smoke run.
  NUM_DEVICES=2              Use multiple GPUs when available.
  PORT=7007                  Viewer websocket port.
  GSMAP_BACKEND=docker       Force Docker backend.
  GSMAP_BACKEND=native       Use local ns-* commands.
  NERFSTUDIO_IMAGE=...       Override Docker image.
  ALLOW_NO_NVIDIA=1          Skip NVIDIA host check for non-training commands.
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

dataset_path_container() {
  case "${1:-}" in
    synthetic-map) echo "/workspace/data/synthetic-map" ;;
    blender-chair) echo "/workspace/data/blender/chair" ;;
    blender-drums) echo "/workspace/data/blender/drums" ;;
    blender-ficus) echo "/workspace/data/blender/ficus" ;;
    blender-hotdog) echo "/workspace/data/blender/hotdog" ;;
    mill19-building) echo "/workspace/data/mill19/building" ;;
    mill19-rubble) echo "/workspace/data/mill19/rubble" ;;
    nerfstudio-poster) echo "/workspace/data/nerfstudio/poster" ;;
    blender-lego) echo "/workspace/data/blender/lego" ;;
    blender-materials) echo "/workspace/data/blender/materials" ;;
    blender-mic) echo "/workspace/data/blender/mic" ;;
    blender-ship) echo "/workspace/data/blender/ship" ;;
    *) return 1 ;;
  esac
}

dataset_path_host() {
  case "${1:-}" in
    synthetic-map) echo "${DATA_DIR}/synthetic-map" ;;
    blender-chair) echo "${DATA_DIR}/blender/chair" ;;
    blender-drums) echo "${DATA_DIR}/blender/drums" ;;
    blender-ficus) echo "${DATA_DIR}/blender/ficus" ;;
    blender-hotdog) echo "${DATA_DIR}/blender/hotdog" ;;
    mill19-building) echo "${DATA_DIR}/mill19/building" ;;
    mill19-rubble) echo "${DATA_DIR}/mill19/rubble" ;;
    nerfstudio-poster) echo "${DATA_DIR}/nerfstudio/poster" ;;
    blender-lego) echo "${DATA_DIR}/blender/lego" ;;
    blender-materials) echo "${DATA_DIR}/blender/materials" ;;
    blender-mic) echo "${DATA_DIR}/blender/mic" ;;
    blender-ship) echo "${DATA_DIR}/blender/ship" ;;
    *) return 1 ;;
  esac
}

download_command() {
  case "${1:-}" in
    synthetic-map) echo "python3 scripts/make_synthetic_map.py /workspace/data/synthetic-map" ;;
    blender-chair|blender-drums|blender-ficus|blender-hotdog|blender-lego|blender-materials|blender-mic|blender-ship)
      local scene="${1#blender-}"
      echo "python3 scripts/download_blender_scene.py '${scene}' '/workspace/data/blender/${scene}'"
      ;;
    mill19-building) echo "ns-download-data mill19 --capture-name building --save-dir /workspace/data" ;;
    mill19-rubble) echo "ns-download-data mill19 --capture-name rubble --save-dir /workspace/data" ;;
    nerfstudio-poster) echo "ns-download-data nerfstudio --capture-name poster --save-dir /workspace/data" ;;
    *) return 1 ;;
  esac
}

dataparser_command() {
  case "${1:-}" in
    blender-chair|blender-drums|blender-ficus|blender-hotdog|blender-lego|blender-materials|blender-mic|blender-ship) echo "blender-data" ;;
    *) echo "" ;;
  esac
}

ensure_dataset_name() {
  dataset_path_container "$1" >/dev/null || die "unknown dataset '$1'. Run './run.sh datasets'."
}

backend() {
  case "${GSMAP_BACKEND}" in
    native|docker) echo "${GSMAP_BACKEND}" ;;
    auto)
      if have ns-train && have ns-download-data; then
        echo "native"
      else
        echo "docker"
      fi
      ;;
    *) die "GSMAP_BACKEND must be auto, docker, or native" ;;
  esac
}

docker_available_or_die() {
  have docker || die "Docker is not installed. Install Docker + NVIDIA Container Toolkit, or set GSMAP_BACKEND=native after installing Nerfstudio."
}

gpu_available_or_die() {
  if [[ "${ALLOW_NO_NVIDIA}" == "1" ]]; then
    return
  fi
  if ! have nvidia-smi; then
    die "No NVIDIA GPU detected on the host. Train on Linux with NVIDIA/CUDA, or set ALLOW_NO_NVIDIA=1 for download/shell only."
  fi
}

docker_run() {
  docker_available_or_die
  mkdir -p "${DATA_DIR}" "${OUTPUT_DIR}" "${EXPORT_DIR}" "${CACHE_DIR}"

  local docker_gpu_args=()
  if [[ "${ALLOW_NO_NVIDIA}" != "1" ]]; then
    gpu_available_or_die
    docker_gpu_args=(--gpus all)
  fi

  docker run --rm "${DOCKER_TTY[@]}" \
    "${docker_gpu_args[@]}" \
    --shm-size=12g \
    -p "${PORT}:${PORT}" \
    -e HOME=/workspace/.home \
    -e MPLCONFIGDIR=/workspace/.cache/matplotlib \
    -e PYTHONUNBUFFERED=1 \
    -v "${ROOT_DIR}:/workspace" \
    -v "${CACHE_DIR}:/workspace/.home/.cache" \
    -w /workspace \
    "${NERFSTUDIO_IMAGE}" \
    bash -lc "$*"
}

native_run() {
  have ns-train || die "ns-train not found. Run './run.sh setup' for Docker, or install Nerfstudio and set GSMAP_BACKEND=native."
  have ns-download-data || die "ns-download-data not found. Install Nerfstudio and set GSMAP_BACKEND=native."
  local command="$*"
  command="${command//\/workspace\/data/${DATA_DIR}}"
  command="${command//\/workspace\/outputs/${OUTPUT_DIR}}"
  command="${command//\/workspace\/exports/${EXPORT_DIR}}"
  command="${command//\/workspace\/.home\/.cache/${CACHE_DIR}}"
  bash -lc "${command}"
}

run_backend() {
  case "$(backend)" in
    native) native_run "$@" ;;
    docker) docker_run "$@" ;;
  esac
}

latest_config() {
  local dataset="$1"
  local match
  match="$(find "${OUTPUT_DIR}/${dataset}" -path '*/config.yml' -type f 2>/dev/null | sort | tail -n 1 || true)"
  [[ -n "${match}" ]] || return 1
  echo "${match}"
}

config_arg_container() {
  local arg="$1"
  if [[ -f "${arg}" ]]; then
    case "$(backend)" in
      native) echo "${arg}" ;;
      docker) echo "/workspace/${arg#"${ROOT_DIR}/"}" ;;
    esac
    return
  fi

  ensure_dataset_name "${arg}"
  local config
  config="$(latest_config "${arg}")" || die "No config.yml found for '${arg}'. Train it first."
  case "$(backend)" in
    native) echo "${config}" ;;
    docker) echo "/workspace/${config#"${ROOT_DIR}/"}" ;;
  esac
}

print_datasets() {
  cat <<'EOF'
Available datasets:
  synthetic-map     Local generated map-like smoke-test dataset, no download needed.
  blender-lego      Recommended famous lightweight benchmark scene.
  blender-chair     Classic NeRF Synthetic scene.
  blender-drums     Classic NeRF Synthetic scene.
  blender-ficus     Classic NeRF Synthetic scene.
  blender-hotdog    Classic NeRF Synthetic scene.
  blender-materials Classic NeRF Synthetic scene.
  blender-mic       Classic NeRF Synthetic scene.
  blender-ship      Classic NeRF Synthetic scene.
  mill19-building   Recommended map-like run. Large aerial/industrial scene.
  mill19-rubble     Recommended map-like run. Large aerial/industrial scene.
  nerfstudio-poster Small sanity-check dataset before spending GPU time.

Suggested first GPU run:
  ./run.sh download blender-lego
  ITERATIONS=7000 ./run.sh train blender-lego
  ./run.sh viewer blender-lego
EOF
}

doctor() {
  echo "Root: ${ROOT_DIR}"
  echo "Backend: $(backend)"
  echo "Image: ${NERFSTUDIO_IMAGE}"
  echo "Data: ${DATA_DIR}"
  echo "Outputs: ${OUTPUT_DIR}"
  echo "Exports: ${EXPORT_DIR}"
  echo "Num devices: ${NUM_DEVICES}"
  echo
  printf "docker: "; have docker && docker --version || echo "not found"
  printf "nvidia-smi: "; have nvidia-smi && nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || echo "not found"
  printf "ns-train: "; have ns-train && command -v ns-train || echo "not found"
  printf "ns-download-data: "; have ns-download-data && command -v ns-download-data || echo "not found"
}

setup() {
  case "$(backend)" in
    native)
      echo "Native Nerfstudio commands found."
      ns-train --help >/dev/null
      ;;
    docker)
      docker_available_or_die
      echo "Pulling ${NERFSTUDIO_IMAGE} ..."
      docker pull "${NERFSTUDIO_IMAGE}"
      ;;
  esac
}

download_dataset() {
  local dataset="$1"
  ensure_dataset_name "${dataset}"
  local command
  command="$(download_command "${dataset}")"
  run_backend "mkdir -p /workspace/data && ${command}"
}

train_dataset() {
  local dataset="$1"
  ensure_dataset_name "${dataset}"
  local data_path
  local dataparser
  data_path="$(dataset_path_container "${dataset}")"
  dataparser="$(dataparser_command "${dataset}")"
  run_backend "test -d '${data_path}' || { echo 'Dataset missing: ${data_path}. Run ./run.sh download ${dataset} first.' >&2; exit 2; }
    mkdir -p /workspace/outputs &&
    ns-train splatfacto \
      --data '${data_path}' \
      --experiment-name '${dataset}' \
      --output-dir /workspace/outputs \
      --machine.num-devices '${NUM_DEVICES}' \
      --max-num-iterations '${ITERATIONS}' \
      --viewer.websocket-host 0.0.0.0 \
      --viewer.websocket-port '${PORT}' \
      ${dataparser}"
}

eval_dataset() {
  local dataset="$1"
  local config
  config="$(config_arg_container "${dataset}")"
  local output="/workspace/outputs/${dataset}/eval.json"
  run_backend "mkdir -p /workspace/outputs/${dataset} && ns-eval --load-config '${config}' --output-path '${output}'"
}

export_dataset() {
  local dataset="$1"
  local config
  config="$(config_arg_container "${dataset}")"
  run_backend "mkdir -p /workspace/exports/${dataset} && ns-export gaussian-splat --load-config '${config}' --output-dir /workspace/exports/${dataset}"
}

viewer() {
  local target="$1"
  local config
  config="$(config_arg_container "${target}")"
  run_backend "ns-viewer --load-config '${config}' --viewer.websocket-host 0.0.0.0 --viewer.websocket-port '${PORT}'"
}

quickstart() {
  setup
  download_dataset blender-lego
  train_dataset blender-lego
}

main() {
  local command="${1:-help}"
  shift || true

  case "${command}" in
    help|-h|--help) usage ;;
    doctor) doctor ;;
    setup) setup ;;
    datasets) print_datasets ;;
    download) [[ $# -eq 1 ]] || die "usage: ./run.sh download <dataset>"; download_dataset "$1" ;;
    train) [[ $# -eq 1 ]] || die "usage: ./run.sh train <dataset>"; train_dataset "$1" ;;
    eval) [[ $# -eq 1 ]] || die "usage: ./run.sh eval <dataset>"; eval_dataset "$1" ;;
    export) [[ $# -eq 1 ]] || die "usage: ./run.sh export <dataset>"; export_dataset "$1" ;;
    viewer) [[ $# -eq 1 ]] || die "usage: ./run.sh viewer <dataset|config.yml>"; viewer "$1" ;;
    shell) run_backend "bash" ;;
    quickstart) quickstart ;;
    *) die "unknown command '${command}'. Run './run.sh help'." ;;
  esac
}

main "$@"
