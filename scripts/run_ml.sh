#!/usr/bin/env bash
set -euo pipefail

echo "▶ RFM segmentation..."
python -m openbi.ml.segmentation.rfm_kmeans

echo ""
echo "▶ Sales forecasting..."
python -m openbi.ml.forecasting.run_forecast

echo ""
echo "✓ ML complete."
