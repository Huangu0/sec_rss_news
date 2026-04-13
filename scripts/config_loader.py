"""
config_loader.py
加载 YAML/JSON 配置文件，与默认配置深度合并后返回。

支持格式：
  .yaml / .yml — 需要安装 PyYAML
  .json        — 标准库 json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _load_file(path: Path) -> Dict[str, Any]:
    """Load a YAML or JSON file and return its contents as a dict."""
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            return yaml.safe_load(content) or {}
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required to load YAML config files. "
                "Run: pip install pyyaml"
            ) from exc
    return json.loads(content)


def load_config(config_path: str | None = None) -> Dict[str, Any]:
    """Load configuration, merging user overrides onto the default config.

    Args:
        config_path: Path to a user-supplied YAML or JSON config file.
                     If *None*, the default config is returned as-is.

    Returns:
        Fully-merged configuration dict.
    """
    # Load built-in defaults
    default: Dict[str, Any] = {}
    if _DEFAULT_CONFIG_PATH.exists():
        try:
            default = _load_file(_DEFAULT_CONFIG_PATH)
        except Exception as exc:
            print(f"[CONFIG] 无法加载默认配置: {exc}")

    if config_path is None:
        return default

    path = Path(config_path)
    if not path.exists():
        print(f"[CONFIG] 配置文件不存在: {config_path}，使用默认配置")
        return default

    try:
        user_cfg = _load_file(path)
        merged = _deep_merge(default, user_cfg)
        print(f"[CONFIG] 已加载配置文件: {config_path}")
        return merged
    except Exception as exc:
        print(f"[CONFIG] 配置文件解析失败: {exc}，使用默认配置")
        return default
