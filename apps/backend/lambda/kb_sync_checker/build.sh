#!/bin/bash
# Build Lambda deployment package for KB Sync Checker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_FILE="$SCRIPT_DIR/kb_sync_checker.zip"

echo "Building KB Sync Checker Lambda package..."

# Remove old zip if exists
if [ -f "$ZIP_FILE" ]; then
    rm -f "$ZIP_FILE"
fi

# Create zip with handler.py only (boto3 is included in Lambda runtime)
cd "$SCRIPT_DIR"
zip -j "$ZIP_FILE" handler.py

echo "Lambda package created: $ZIP_FILE"
ls -lh "$ZIP_FILE"
