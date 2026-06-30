#!/bin/bash
# Save this file as 'update_and_run.sh' in your project root
# Make it executable by running: chmod +x update_and_run.sh

echo "Checking for updates..."
git pull origin main

echo "Building/Updating Docker image..."
docker build -t receipt-vault .

echo "Starting Application..."
# The --rm flag ensures the container is cleaned up after closing
# The -v flag ensures your SQLite database persists outside the container
docker run --rm \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "$(pwd)/bills_data.db:/app/bills_data.db" \
    receipt-vault
