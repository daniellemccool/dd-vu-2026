#!/bin/bash
set -e
export NODE_ENV=production

NAME=${PWD##*/}
BRANCH=${1:-$(git branch --show-current)}
BRANCH=${BRANCH//\//-}
TIMESTAMP=$(date '+%Y-%m-%d')
BUILD_NR=${2:-local}

# Add platforms here as they are activated in script.py
platforms=("LinkedIn" "X")

mkdir -p releases

for PLATFORM in "${platforms[@]}"; do
    echo "Building for platform: ${PLATFORM}..."
    export VITE_PLATFORM=$PLATFORM
    pnpm run build

    RELEASE_NAME="${NAME}_${PLATFORM}_${BRANCH}_${TIMESTAMP}_${BUILD_NR}.zip"
    cd packages/data-collector/dist
    zip -r ../../../releases/${RELEASE_NAME} .
    cd ../../..
    echo "Created: releases/${RELEASE_NAME}"
done