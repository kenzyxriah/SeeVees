#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Start the main application ---
echo "Starting FastAPI application..."

# Execute the command passed to the docker container,
# or start uvicorn if nothing is passed.
exec uvicorn main:app --host 0.0.0.0 --port 8080 --reload --ws-ping-interval 20 --ws-ping-timeout 20 "$@"



