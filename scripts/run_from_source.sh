#!/usr/bin/env bash
# Starts the app from source (for development) on Linux/macOS without building anything.
# Linux counterpart of scripts/run_from_source.bat.
set -e
cd "$(dirname "$0")/.."
# (the script lives in scripts/ ; everything below runs from the project root)

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 was not found. Install Python 3.10+ (e.g. sudo apt install python3 python3-venv)." >&2
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv || {
        echo "Could not create the virtual environment. On Ubuntu/Debian: sudo apt install python3-venv" >&2
        exit 1
    }
fi

.venv/bin/python -m pip install -q -r requirements.txt
exec .venv/bin/python main.py "$@"
