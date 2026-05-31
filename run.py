"""
EY Data Classification Tool — Run Script
Starts both backend (port 8000) and frontend (port 5173).

Usage:
    python run.py

Prerequisites:
    pip install -r backend/requirements.txt
    cd frontend && npm install
"""
import subprocess
import sys
import os
import signal
import time

def main():
    procs = []

    # Start backend
    print("Starting backend on http://localhost:8000 ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=os.path.join(os.path.dirname(__file__), "backend"),
    )
    procs.append(backend)
    time.sleep(2)

    # Start frontend
    print("Starting frontend on http://localhost:5173 ...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=os.path.join(os.path.dirname(__file__), "frontend"),
    )
    procs.append(frontend)

    print("\n" + "=" * 50)
    print("  EY Data Classification Tool")
    print("  Frontend: http://localhost:5173")
    print("  Backend:  http://localhost:8000")
    print("  API docs: http://localhost:8000/docs")
    print("=" * 50 + "\n")

    # Wait for Ctrl+C
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()
        print("Done.")

if __name__ == "__main__":
    main()
