#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d flowmanager ]; then
    echo "flowmanager submodule not found. Run: git submodule update --init" >&2
    exit 1
fi

echo "Creating virtual environment in flowmanager/.venv..."
python3 -m venv flowmanager/.venv
source flowmanager/.venv/bin/activate
pip install --no-cache-dir -r flowmanager/requirements.txt
echo "Done. SDN controller environment ready."
