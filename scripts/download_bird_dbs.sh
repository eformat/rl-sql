#!/usr/bin/env bash
# Download BIRD benchmark SQLite databases for execution-based reward grading.
#
# The BIRD databases are not included in the ReViSQL repo and must be
# downloaded separately. This script fetches the mini-dev databases
# which cover the evaluation set (bird_eval.parquet, 673 examples).
#
# Usage:
#   ./scripts/download_bird_dbs.sh [output_dir]
#
# Default output: ./data/bird_databases/

set -euo pipefail

OUTPUT_DIR="${1:-./data/bird_databases}"
BIRD_URL="https://bird-bench.github.io"

mkdir -p "$OUTPUT_DIR"

echo "==> Downloading BIRD mini-dev databases..."
echo "    Target: $OUTPUT_DIR"

# BIRD mini-dev databases are distributed as a zip via the BIRD benchmark site.
# If gdown is available, use the Google Drive link; otherwise fall back to manual.
if command -v gdown &>/dev/null; then
    # BIRD mini-dev database archive (Google Drive)
    # Update this ID if the BIRD team changes the download link.
    GDRIVE_ID="1AkT0tjlNrM4dMpQJbLVJzNXXkK5ao3fn"
    ARCHIVE="$OUTPUT_DIR/minidev_databases.zip"
    echo "    Using gdown to fetch from Google Drive..."
    gdown "$GDRIVE_ID" -O "$ARCHIVE"
    echo "    Extracting..."
    unzip -qo "$ARCHIVE" -d "$OUTPUT_DIR"
    rm -f "$ARCHIVE"
else
    echo "ERROR: gdown not installed. Install with: pip install gdown"
    echo ""
    echo "Alternatively, download BIRD databases manually from:"
    echo "  $BIRD_URL"
    echo ""
    echo "Then extract into: $OUTPUT_DIR/"
    echo "Expected structure: $OUTPUT_DIR/<db_id>/<db_id>.sqlite"
    exit 1
fi

# Verify structure
DB_COUNT=$(find "$OUTPUT_DIR" -name "*.sqlite" | wc -l)
echo "==> Done. Found $DB_COUNT SQLite databases in $OUTPUT_DIR"
