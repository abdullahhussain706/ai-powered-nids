#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"
VENV_DIR = BASE_DIR / "venv"
VENV_PYTHON = (
    VENV_DIR / "Scripts" / "python.exe"
    if platform.system() == "Windows"
    else VENV_DIR / "bin" / "python"
)

REQUIRED_PYTHON_MODULES = {
    "colorama": "colorama",
    "joblib": "joblib",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "pandas": "pandas",
    "PIL": "pillow",
    "pyqtgraph": "pyqtgraph",
    "PySide6": "PySide6",
    "scipy": "scipy",
    "seaborn": "seaborn",
    "sklearn": "scikit-learn",
    "xgboost": "xgboost",
    "yaml": "PyYAML",
}


@dataclass
class DependencyStatus:
    name: str
    installed: bool
    detail: str = ""


def _run(command, timeout=120, env=None):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def get_project_python():
    return VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)


def _python_can_import(python_executable, module_name):
    result = _run(
        [str(python_executable), "-c", f"import {module_name}"],
        timeout=30,
    )
    return result.returncode == 0, (result.stderr or result.stdout).strip()


def python_dependency_status(python_executable=None):
    python_executable = Path(python_executable or get_project_python())
    statuses = []

    if not python_executable.exists():
        return [
            DependencyStatus(
                "python",
                False,
                f"Python executable not found: {python_executable}",
            )
        ]

    for module_name, package_name in REQUIRED_PYTHON_MODULES.items():
        ok, detail = _python_can_import(python_executable, module_name)
        statuses.append(
            DependencyStatus(
                package_name,
                ok,
                "available" if ok else detail,
            )
        )

    return statuses


def missing_python_dependencies(python_executable=None):
    return [
        status
        for status in python_dependency_status(python_executable)
        if not status.installed
    ]


def create_virtualenv():
    if VENV_PYTHON.exists():
        return True, f"Virtual environment exists: {VENV_DIR}"

    result = _run([sys.executable, "-m", "venv", str(VENV_DIR)], timeout=600)
    if result.returncode == 0 and VENV_PYTHON.exists():
        return True, f"Virtual environment created: {VENV_DIR}"

    return False, (result.stderr or result.stdout or "venv creation failed").strip()


def install_python_dependencies():
    if not REQUIREMENTS_FILE.exists():
        return False, f"requirements.txt not found: {REQUIREMENTS_FILE}"

    ok, detail = create_virtualenv()
    if not ok:
        return False, detail

    python_executable = get_project_python()
    commands = [
        [str(python_executable), "-m", "pip", "install", "--upgrade", "pip"],
        [str(python_executable), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
    ]

    output = []
    for command in commands:
        result = _run(command, timeout=1800)
        output.append((command, result.returncode, result.stdout, result.stderr))
        if result.returncode != 0:
            break

    missing = missing_python_dependencies(python_executable)
    if not missing:
        return True, "Python dependencies installed"

    details = "\n".join(
        f"{' '.join(cmd)} -> {code}\n{stdout}\n{stderr}"
        for cmd, code, stdout, stderr in output
    )
    missing_text = ", ".join(status.name for status in missing)
    return False, f"Missing Python dependencies after install: {missing_text}\n{details}"


def ensure_python_dependencies(auto_install=False):
    python_executable = get_project_python()
    missing = missing_python_dependencies(python_executable)
    if not missing:
        return True, f"Python dependencies available ({python_executable})"

    missing_text = ", ".join(status.name for status in missing)
    if not auto_install:
        return False, f"Missing Python dependencies: {missing_text}"

    installed, detail = install_python_dependencies()
    if installed:
        return True, detail

    return False, f"Missing Python dependencies: {missing_text}\n{detail}"


def _is_admin_windows():
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _is_root_linux():
    return hasattr(os, "geteuid") and os.geteuid() == 0


def find_tshark():
    path = shutil.which("tshark")
    if path:
        return Path(path)

    candidates = [
        Path("C:/Program Files/Wireshark/tshark.exe"),
        Path("C:/Program Files (x86)/Wireshark/tshark.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def tshark_status():
    tshark = find_tshark()
    if not tshark:
        return DependencyStatus("tshark", False, "tshark executable not found")

    try:
        result = _run([str(tshark), "-v"], timeout=15)
        if result.returncode == 0:
            first_line = (result.stdout or "").splitlines()[0]
            return DependencyStatus("tshark", True, first_line)
        return DependencyStatus("tshark", False, result.stderr.strip())
    except Exception as e:
        return DependencyStatus("tshark", False, str(e))


def npcap_status():
    if platform.system() != "Windows":
        return DependencyStatus("npcap", True, "not required on this OS")

    driver = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32" / "drivers" / "npcap.sys"
    if driver.exists():
        return DependencyStatus("npcap", True, str(driver))

    try:
        result = _run(["sc", "query", "npcap"], timeout=10)
        if result.returncode == 0:
            return DependencyStatus("npcap", True, "npcap service found")
    except Exception:
        pass

    return DependencyStatus("npcap", False, "Npcap driver/service not found")


def check_capture_dependencies():
    statuses = [tshark_status()]
    if platform.system() == "Windows":
        statuses.append(npcap_status())
    return statuses


def missing_capture_dependencies():
    return [status for status in check_capture_dependencies() if not status.installed]


def _has_command(name):
    return shutil.which(name) is not None


def _install_windows_with_winget():
    if not _has_command("winget"):
        return False, "winget not found. Install Wireshark + Npcap manually or install winget."

    commands = [
        ["winget", "install", "--id", "WiresharkFoundation.Wireshark", "-e", "--accept-package-agreements", "--accept-source-agreements"],
        ["winget", "install", "--id", "Insecure.Npcap", "-e", "--accept-package-agreements", "--accept-source-agreements"],
    ]

    output = []
    for command in commands:
        result = _run(command, timeout=900)
        output.append((command, result.returncode, result.stdout, result.stderr))

    missing = missing_capture_dependencies()
    if not missing:
        return True, "Windows capture dependencies installed"

    details = "\n".join(
        f"{' '.join(cmd)} -> {code}\n{stdout}\n{stderr}"
        for cmd, code, stdout, stderr in output
    )
    return False, details


def _install_linux_with_package_manager():
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"

    if _has_command("apt-get"):
        prefix = [] if _is_root_linux() else ["sudo"]
        commands = [
            prefix + ["apt-get", "update"],
            prefix + ["apt-get", "install", "-y", "tshark"],
        ]
    elif _has_command("dnf"):
        prefix = [] if _is_root_linux() else ["sudo"]
        commands = [prefix + ["dnf", "install", "-y", "wireshark-cli"]]
    elif _has_command("yum"):
        prefix = [] if _is_root_linux() else ["sudo"]
        commands = [prefix + ["yum", "install", "-y", "wireshark-cli"]]
    elif _has_command("pacman"):
        prefix = [] if _is_root_linux() else ["sudo"]
        commands = [prefix + ["pacman", "-Sy", "--noconfirm", "wireshark-cli"]]
    else:
        return False, "No supported Linux package manager found."

    output = []
    for command in commands:
        result = _run(command, timeout=900, env=env)
        output.append((command, result.returncode, result.stdout, result.stderr))
        if result.returncode != 0:
            break

    missing = missing_capture_dependencies()
    if not missing:
        return True, "Linux capture dependencies installed"

    details = "\n".join(
        f"{' '.join(cmd)} -> {code}\n{stdout}\n{stderr}"
        for cmd, code, stdout, stderr in output
    )
    return False, details


def install_capture_dependencies():
    system = platform.system()
    if system == "Windows":
        return _install_windows_with_winget()
    if system == "Linux":
        return _install_linux_with_package_manager()
    return False, f"Automatic capture dependency install is not supported on {system}."


def ensure_capture_dependencies(auto_install=False):
    missing = missing_capture_dependencies()
    if not missing:
        return True, "Capture dependencies available"

    missing_text = ", ".join(status.name for status in missing)
    if not auto_install:
        return False, f"Missing capture dependencies: {missing_text}"

    installed, detail = install_capture_dependencies()
    if installed:
        return True, detail

    return False, f"Missing capture dependencies: {missing_text}\n{detail}"


def print_manual_install_help():
    system = platform.system()
    if system == "Windows":
        print("Install commands:")
        print("  winget install --id WiresharkFoundation.Wireshark -e")
        print("  winget install --id Insecure.Npcap -e")
        print("Then restart the terminal/app.")
    elif system == "Linux":
        print("Install command examples:")
        print("  sudo apt-get update && sudo apt-get install -y tshark")
        print("  sudo dnf install -y wireshark-cli")
        print("  sudo pacman -Sy --noconfirm wireshark-cli")
    else:
        print(f"Install tshark/Wireshark manually for {system}.")


def print_python_install_help():
    print("Python dependency setup:")
    print(f"  {sys.executable} -m venv {VENV_DIR}")
    print(f"  {VENV_PYTHON} -m pip install -r {REQUIREMENTS_FILE}")


def main():
    auto_install = "--install" in sys.argv

    py_ok, py_detail = ensure_python_dependencies(auto_install=auto_install)
    print(py_detail)
    if not py_ok:
        print_python_install_help()
        raise SystemExit(1)

    ok, detail = ensure_capture_dependencies(auto_install=auto_install)
    print(detail)
    if not ok:
        print_manual_install_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
