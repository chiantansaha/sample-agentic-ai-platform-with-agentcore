#!/bin/bash
# Build Lambda deployment package

set -e

echo "🔨 Building Lambda deployment package..."

# Create temp directory
rm -rf package
mkdir -p package

# Install dependencies
pip3 install -r requirements.txt -t package/

# Copy handler
cp handler.py package/

# Create zip
cd package
zip -r ../kb_creation_handler.zip .
cd ..

# Clean up
rm -rf package

echo "✅ Lambda package created: kb_creation_handler.zip"
ls -lh kb_creation_handler.zip
