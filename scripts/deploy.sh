#!/usr/bin/env bash
# Deploys the project to the Raspberry Pi over SSH using rsync.
#
# Usage:
#   PI_HOST=pi@192.168.1.42 bash scripts/deploy.sh
#
# Optional overrides:
#   REMOTE_DIR   — destination directory on the Pi (default: ~/gardenguard)
#   VENV_DIR     — venv directory on the Pi (default: ~/gardenguard-env)
set -euo pipefail

PI_HOST="${PI_HOST:?Set PI_HOST, e.g. PI_HOST=pi@192.168.1.42}"
REMOTE_DIR="${REMOTE_DIR:-~/gardenguard}"
VENV_DIR="${VENV_DIR:-~/gardenguard-env}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

echo "Deploying to ${PI_HOST}:${REMOTE_DIR} ..."

# Ensure remote directory exists
ssh "${PI_HOST}" "mkdir -p ${REMOTE_DIR}/{captures,logs,models}"

rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    "${PROJECT_ROOT}/src/" "${PI_HOST}:${REMOTE_DIR}/src/"

rsync -avz --delete \
    "${PROJECT_ROOT}/config/" "${PI_HOST}:${REMOTE_DIR}/config/"

rsync -avz --delete \
    "${PROJECT_ROOT}/tests/" "${PI_HOST}:${REMOTE_DIR}/tests/"

rsync -avz \
    "${PROJECT_ROOT}/pyproject.toml" "${PI_HOST}:${REMOTE_DIR}/pyproject.toml"

# Install/update the project in editable mode so src-layout imports resolve.
ssh "${PI_HOST}" "bash -lc 'source ${VENV_DIR}/bin/activate && pip install --quiet --editable ${REMOTE_DIR}'"

echo ""
echo "Deploy complete. To run on the Pi:"
echo "  ssh ${PI_HOST}"
echo "  source ~/gardenguard-env/bin/activate"
echo "  cd ${REMOTE_DIR} && python -m gardenguard.main"
