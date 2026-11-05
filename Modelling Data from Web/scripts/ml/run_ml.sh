#!/usr/bin/env bash
# Run an ML script in the dedicated environment, e.g.:
#   bash scripts/ml/run_ml.sh scripts/ml/stage2_models.py
# LightGBM and XGBoost wheels need libomp; PyTorch ships one, so point the
# loader at it instead of installing a system copy (D-079).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/.venv-ml"
export DYLD_LIBRARY_PATH="$VENV/lib/python3.13/site-packages/torch/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export PYTHONHASHSEED=12086
exec "$VENV/bin/python" "$@"
