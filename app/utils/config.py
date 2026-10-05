"""
Configuration loader supporting both YAML and standard JSON formats.
Includes graceful fallback if PyYAML is not installed.
"""
from pathlib import Path
from typing import Any, Dict
import json

# Optional YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


DEFAULT_CONFIG: Dict[str, Any] = {
    "pipeline": {
        "name": "Student Data Integration Pipeline",
        "version": "1.0.0"
    },
    "paths": {
        "csv_raw": "data/raw/students.csv",
        "database_path": "database/students.db",
        "processed_output": "data/processed/final_dataset.csv",
        "rejected_output": "data/rejected/rejected_records.csv",
        "log_file": "logs/pipeline.log",
        "state_file": "logs/pipeline_state.json"
    },
    "api": {
        "base_url": "http://127.0.0.1:8000/api/students",
        "timeout_seconds": 5,
        "mock_data_fallback": "data/raw/students_api.json",
        "auto_start_mock": True
    },
    "validation": {
        "age_min": 16,
        "age_max": 80,
        "gpa_min": 0.0,
        "gpa_max": 4.0,
        "attendance_min": 0.0,
        "attendance_max": 100.0,
        "score_min": 0.0,
        "score_max": 100.0
    },
    "imputation": {
        "gpa": "median",
        "attendance": "median",
        "score": "mean"
    }
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to deeply merge configuration dictionaries."""
    merged = base.copy()
    for key, val in override.items():
        if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Loads configuration from YAML or JSON file.
    If PyYAML is missing or config.yaml is not found, automatically falls back to config.json
    or built-in defaults.
    """
    target = Path(config_path)

    # 1. Try loading YAML if PyYAML is available and file exists
    if HAS_YAML and target.exists() and target.suffix in [".yaml", ".yml"]:
        try:
            with open(target, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
                return _deep_merge(DEFAULT_CONFIG, user_cfg)
        except Exception:
            pass

    # 2. Try loading JSON (either config.json or path with .json)
    json_path = Path("config.json") if target.suffix in [".yaml", ".yml"] else target
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f) or {}
                return _deep_merge(DEFAULT_CONFIG, user_cfg)
        except Exception:
            pass

    # 3. Fallback to default configuration
    return DEFAULT_CONFIG
