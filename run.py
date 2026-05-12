#!/usr/bin/env python3

import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
BACKEND_SCRIPT = BASE_DIR / "core" / "packet_capture.py"
VENV_PYTHON = BASE_DIR / "venv" / "bin" / "python"
PYTHON = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)


def start_process(name, script):
    print(f"Starting {name}: {script.relative_to(BASE_DIR)}")
    return subprocess.Popen([str(PYTHON), str(script)], cwd=BASE_DIR)


def start_frontend():
    print("Starting frontend: ui.main_window")
    return subprocess.Popen([str(PYTHON), "-m", "ui.main_window"], cwd=BASE_DIR)


def stop_process(name, proc):
    if proc.poll() is not None:
        return

    print(f"Stopping {name}...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main():
    print("==== AI Powered NIDS ====")

    backend = start_process("backend", BACKEND_SCRIPT)
    time.sleep(1)
    frontend = start_frontend()

    try:
        while True:
            if frontend.poll() is not None:
                print("Frontend closed.")
                break

            if backend.poll() is not None:
                print("Backend stopped. Restarting...")
                backend = start_process("backend", BACKEND_SCRIPT)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nShutdown requested.")
    finally:
        stop_process("frontend", frontend)
        stop_process("backend", backend)
        print("IDS stopped.")


if __name__ == "__main__":
    main()
