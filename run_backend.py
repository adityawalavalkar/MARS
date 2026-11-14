"""MARS-NAV Backend Server Launcher.

Starts the FastAPI server with Uvicorn.
Usage:
    python run_backend.py
    python run_backend.py --port 8080 --host 0.0.0.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn
from backend.config import HOST, PORT


def main():
    parser = argparse.ArgumentParser(description="Run the MARS-NAV FastAPI server.")
    parser.add_argument("--host", default=HOST, help=f"Host address (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port number (default: {PORT})")
    parser.add_argument("--reload", action="store_true", help="Enable live code reloading")

    args = parser.parse_args()

    print("=" * 60)
    print("MARS-NAV: MARS EXPLORATION & NAVIGATION SYSTEM")
    print(f"Starting server at http://{args.host}:{args.port}")
    print(f"Interactive API Docs: http://localhost:{args.port}/docs")
    print(f"Interactive 3D Terrain: http://localhost:{args.port}/static/jezero_3d_terrain.html")
    print("=" * 60)

    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
