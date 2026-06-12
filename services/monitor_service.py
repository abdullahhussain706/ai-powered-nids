#!/usr/bin/env python3

import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_SCRIPT = BASE_DIR / "core" / "packet_capture.py"
VENV_PYTHON = (
    BASE_DIR / "venv" / "Scripts" / "python.exe"
    if platform.system() == "Windows"
    else BASE_DIR / "venv" / "bin" / "python"
)
PYTHON = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)


@dataclass
class BackendStatus:
    name: str
    running: bool
    pid: Optional[int]
    return_code: Optional[int]
    started_at: Optional[float]
    restart_count: int

    @property
    def uptime_seconds(self):
        if not self.running or self.started_at is None:
            return 0
        return max(0, int(time.time() - self.started_at))

    def to_dict(self):
        return {
            "name": self.name,
            "running": self.running,
            "pid": self.pid,
            "return_code": self.return_code,
            "started_at": self.started_at,
            "uptime_seconds": self.uptime_seconds,
            "restart_count": self.restart_count,
        }


class BackendMonitorService:
    def __init__(
        self,
        script=BACKEND_SCRIPT,
        python_executable=PYTHON,
        cwd=BASE_DIR,
        name="backend",
        auto_restart=True,
    ):
        self.script = Path(script)
        self.python_executable = Path(python_executable)
        self.cwd = Path(cwd)
        self.name = name
        self.auto_restart = auto_restart
        self.process = None
        self.started_at = None
        self.restart_count = 0

    def start(self):
        if self.is_running():
            return self.process

        if not self.script.exists():
            raise FileNotFoundError(f"Backend script not found: {self.script}")

        print(f"Starting {self.name}: {self.script.relative_to(self.cwd)}")
        self.process = subprocess.Popen(
            [str(self.python_executable), str(self.script)],
            cwd=self.cwd,
        )
        self.started_at = time.time()
        return self.process

    def stop(self, timeout=5):
        if not self.process or self.process.poll() is not None:
            return

        print(f"Stopping {self.name}...")
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)

    def restart(self):
        self.stop()
        self.restart_count += 1
        return self.start()

    def poll(self):
        if not self.process:
            return None
        return self.process.poll()

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def ensure_running(self):
        if self.is_running():
            return self.process

        if self.process is None:
            return self.start()

        if self.auto_restart:
            print(f"{self.name.capitalize()} stopped. Restarting...")
            return self.restart()

        return None

    def status(self):
        return BackendStatus(
            name=self.name,
            running=self.is_running(),
            pid=self.process.pid if self.process else None,
            return_code=self.process.poll() if self.process else None,
            started_at=self.started_at,
            restart_count=self.restart_count,
        )


def main():
    service = BackendMonitorService(auto_restart=True)
    service.start()

    try:
        while True:
            service.ensure_running()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nBackend service shutdown requested.")
    finally:
        service.stop()


if __name__ == "__main__":
    main()
