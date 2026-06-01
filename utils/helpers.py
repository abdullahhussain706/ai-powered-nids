import logging
from pathlib import Path
import yaml

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


def load_config(filename: str) -> dict:
    """Load settings from a YAML configuration file under the config/ directory.

    If the file does not exist or fails to parse, an empty dictionary is
    returned and an error is logged.
    """
    config_path = CONFIG_DIR / filename
    if not config_path.exists():
        logging.warning(
            f"⚠️ Configuration file not found: {config_path.name}. "
            "Falling back to environment variables and default values."
        )
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            if config_data is None:
                return {}
            if not isinstance(config_data, dict):
                logging.error(
                    f"❌ Invalid YAML structure in {filename}. Expected a key-value dictionary."
                )
                return {}
            return config_data
    except Exception as e:
        logging.error(f"❌ Failed to parse configuration file {filename}: {e}")
        return {}
