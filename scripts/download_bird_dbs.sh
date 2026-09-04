#!/usr/bin/env bash
# Download BIRD benchmark SQLite databases for execution-based reward grading.
#
# Downloads from HuggingFace (birdsql/bird_mini_dev) which hosts the
# BIRD mini-dev databases publicly. Falls back to the full BIRD train
# databases if needed.
#
# Usage:
#   ./scripts/download_bird_dbs.sh [output_dir]
#
# Default output: ./data/bird_databases/

set -euo pipefail

OUTPUT_DIR="${1:-./data/bird_databases}"
mkdir -p "$OUTPUT_DIR"

echo "==> Downloading BIRD databases from HuggingFace..."
echo "    Target: $OUTPUT_DIR"

# Install huggingface_hub if needed
python3 -c "import huggingface_hub" 2>/dev/null || pip install -q huggingface_hub

python3 -c "
import os, zipfile, glob, shutil
from huggingface_hub import hf_hub_download, list_repo_tree

output = '$OUTPUT_DIR'

# Download BIRD mini-dev dataset (includes SQLite databases)
print('  Downloading birdsql/bird_mini_dev...')
try:
    # The mini-dev repo has databases in a zip or as individual files
    from huggingface_hub import snapshot_download
    local_dir = snapshot_download(
        repo_id='birdsql/bird_mini_dev',
        repo_type='dataset',
        local_dir=os.path.join(output, '_hf_download'),
        allow_patterns=['*.sqlite', '*.zip', 'databases/**'],
    )
    print(f'  Downloaded to: {local_dir}')

    # Find and extract any zip files
    for zf in glob.glob(os.path.join(local_dir, '**/*.zip'), recursive=True):
        print(f'  Extracting {os.path.basename(zf)}...')
        with zipfile.ZipFile(zf, 'r') as z:
            z.extractall(output)

    # Move any sqlite files into the expected structure
    for db_file in glob.glob(os.path.join(local_dir, '**/*.sqlite'), recursive=True):
        db_id = os.path.splitext(os.path.basename(db_file))[0]
        dest_dir = os.path.join(output, db_id)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(db_file))
        if not os.path.exists(dest):
            shutil.copy2(db_file, dest)

    # Also check for databases/ subdirectory structure
    db_dir = os.path.join(local_dir, 'databases')
    if os.path.isdir(db_dir):
        for item in os.listdir(db_dir):
            src = os.path.join(db_dir, item)
            dst = os.path.join(output, item)
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst)

except Exception as e:
    print(f'  Error: {e}')
    print('  Trying alternative: xu3kev/BIRD-SQL-data-train...')
    try:
        local_dir = snapshot_download(
            repo_id='xu3kev/BIRD-SQL-data-train',
            repo_type='dataset',
            local_dir=os.path.join(output, '_hf_download_alt'),
            allow_patterns=['*.sqlite', '*.zip', 'databases/**'],
        )
        for db_file in glob.glob(os.path.join(local_dir, '**/*.sqlite'), recursive=True):
            db_id = os.path.splitext(os.path.basename(db_file))[0]
            dest_dir = os.path.join(output, db_id)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(db_file, os.path.join(dest_dir, os.path.basename(db_file)))
    except Exception as e2:
        print(f'  Error: {e2}')
        raise

# Count results
db_count = len(glob.glob(os.path.join(output, '*/*.sqlite')))
print(f'  Found {db_count} SQLite databases')
"

# Cleanup temp download dir
rm -rf "$OUTPUT_DIR/_hf_download" "$OUTPUT_DIR/_hf_download_alt" 2>/dev/null || true

DB_COUNT=$(find "$OUTPUT_DIR" -name "*.sqlite" | wc -l)
echo "==> Done. Found $DB_COUNT SQLite databases in $OUTPUT_DIR"
