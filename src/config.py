"""Config loader for jobSearchHelper."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    """Load and return config.yaml as a dict."""
    config_path = PROJECT_ROOT / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
