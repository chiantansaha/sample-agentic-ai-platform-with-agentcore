#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$LAYER_DIR/python"
ZIP_FILE="$LAYER_DIR/kb-dependencies-layer.zip"

echo -e "${BLUE}🚀 Building Lambda Layer...${NC}"
echo -e "${BLUE}Layer directory: $LAYER_DIR${NC}"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo -e "${YELLOW}🧹 Cleaning previous build...${NC}"
    rm -rf "$BUILD_DIR"
fi

if [ -f "$ZIP_FILE" ]; then
    echo -e "${YELLOW}🗑️  Removing old zip file...${NC}"
    rm -f "$ZIP_FILE"
fi

# Create build directory
mkdir -p "$BUILD_DIR"

echo -e "${BLUE}📦 Installing dependencies...${NC}"

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Using Docker for Lambda-compatible build${NC}"

    # Build using Lambda Python runtime container
    docker run --rm --entrypoint="" \
        -v "$LAYER_DIR:/var/task" \
        -w /var/task \
        public.ecr.aws/lambda/python:3.11 \
        pip install -r requirements.txt -t python/ --no-cache-dir
else
    echo -e "${YELLOW}⚠️  Docker not found, using local pip (may not be Lambda-compatible on non-Linux systems)${NC}"
    pip install -r "$LAYER_DIR/requirements.txt" -t "$BUILD_DIR" --no-cache-dir
fi

# Create zip file
echo -e "${BLUE}📦 Creating zip archive...${NC}"
cd "$LAYER_DIR"
zip -r9 -q "$ZIP_FILE" python/

# Get zip file size
ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)

echo -e "${GREEN}✅ Lambda Layer built successfully!${NC}"
echo -e "${GREEN}   Output: $ZIP_FILE${NC}"
echo -e "${GREEN}   Size: $ZIP_SIZE${NC}"
echo -e "${BLUE}💡 Tip: This zip file is excluded from git (see .gitignore)${NC}"
