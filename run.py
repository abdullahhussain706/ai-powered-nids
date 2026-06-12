#!/usr/bin/env python3

import subprocess
import time
from pathlib import Path

from services.dependency_service import (
    ensure_capture_dependencies,
    ensure_python_dependencies,
    get_project_python,
    print_manual_install_help,
    print_python_install_help,
)
from services.monitor_service import BackendMonitorService
from services.scheduler import build_default_scheduler


BASE_DIR = Path(__file__).resolve().parent


def start_frontend(python_executable):
    print("Starting frontend: ui.main_window")
    return subprocess.Popen([str(python_executable), "-m", "ui.main_window"], cwd=BASE_DIR)


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

    py_ok, py_detail = ensure_python_dependencies(auto_install=True)
    if not py_ok:
        print(py_detail)
        print_python_install_help()
        return 1
    print(py_detail)

    ok, detail = ensure_capture_dependencies(auto_install=True)
    if not ok:
        print(detail)
        print_manual_install_help()
        return 1
    print(detail)

    python_executable = get_project_python()
    backend = BackendMonitorService(python_executable=python_executable)
    scheduler = build_default_scheduler()
    backend.start()
    scheduler.start()
    time.sleep(1)
    frontend = start_frontend(python_executable)

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
