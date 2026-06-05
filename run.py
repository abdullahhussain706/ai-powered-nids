#!/usr/bin/env python3

import subprocess
import sys
import time
import platform
from pathlib import Path

from services.dependency_service import ensure_capture_dependencies, print_manual_install_help
from services.monitor_service import BackendMonitorService
from services.scheduler import build_default_scheduler


BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = (
    BASE_DIR / "venv" / "Scripts" / "python.exe"
    if platform.system() == "Windows"
    else BASE_DIR / "venv" / "bin" / "python"
)
PYTHON = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)


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

    ok, detail = ensure_capture_dependencies(auto_install=True)
    if not ok:
        print(detail)
        print_manual_install_help()
        return 1
    print(detail)

    backend = BackendMonitorService(python_executable=PYTHON)
    scheduler = build_default_scheduler()
    backend.start()
    scheduler.start()
    time.sleep(1)
    frontend = start_frontend()

    try:
        while True:
            if frontend.poll() is not None:
                print("Frontend closed.")
                break

            backend.ensure_running()

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nShutdown requested.")
    finally:
        stop_process("frontend", frontend)
        scheduler.stop()
        backend.stop()
        print("IDS stopped.")


if __name__ == "__main__":
    raise SystemExit(main() or 0)
