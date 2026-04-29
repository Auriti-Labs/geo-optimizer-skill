"""
Per-project configuration via .geo-optimizer.yml.

Loads an optional YAML file from the working directory to define
project defaults: URL, output format, cache, extra bots, extra schemas.

Requires PyYAML as an optional dependency:
    pip install geo-optimizer-skill[config]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Name of the configuration file searched in the current directory
CONFIG_FILENAME = ".geo-optimizer.yml"
CONFIG_FILENAME_ALT = ".geo-optimizer.yaml"


def _safe_int(value, default: int = 0) -> int:
    """Convert value to int with fallback to default on error (fix H-11)."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


@dataclass
class AuditConfig:
    """Default configuration for the audit command."""

    url: str | None = None
    format: str = "text"
    output: str | None = None
    min_score: int = 0
    cache: bool = False
    verbose: bool = False


@dataclass
class LlmsConfig:
    """Default configuration for the llms command."""

    base_url: str | None = None
    title: str | None = None
    description: str | None = None
    max_urls: int = 50


@dataclass
class SchemaConfig:
    """Default configuration for the schema command."""

    types: list[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    """Complete project configuration."""

    audit: AuditConfig = field(default_factory=AuditConfig)
    llms: LlmsConfig = field(default_factory=LlmsConfig)
    schema: SchemaConfig = field(default_factory=SchemaConfig)
    extra_bots: dict[str, str] = field(default_factory=dict)


def _is_yaml_available() -> bool:
    """Check whether PyYAML is installed."""
    try:
        import yaml  # noqa: F401

        return True
    except ImportError:
        return False


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Search for the configuration file in the current directory.

    Looks first for .geo-optimizer.yml, then .geo-optimizer.yaml.
    """
    search_dir = start_dir or Path.cwd()

    for name in (CONFIG_FILENAME, CONFIG_FILENAME_ALT):
        config_path = search_dir / name
        if config_path.is_file():
            return config_path

    return None


def load_config(config_path: Path | None = None) -> ProjectConfig:
    """Load configuration from YAML file.

    If config_path is None, searches automatically in the current directory.
    Returns ProjectConfig with defaults if the file does not exist or PyYAML is not installed.
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None:
        return ProjectConfig()

    if not _is_yaml_available():
        return ProjectConfig()

    import yaml

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as e:
        # Fix #461: log warning so users know config wasn't applied
        logger.warning("Failed to load %s: %s — using defaults", config_path, e)
        return ProjectConfig()

    if not isinstance(raw, dict):
        return ProjectConfig()

    return _parse_config(raw)


def _parse_config(raw: dict) -> ProjectConfig:
    """Convert YAML dictionary to typed ProjectConfig."""
    config = ProjectConfig()

    # audit section
    audit_raw = raw.get("audit", {})
    if isinstance(audit_raw, dict):
        # Fix H-11: use _safe_int to prevent crash on non-numeric YAML values
        config.audit = AuditConfig(
            url=audit_raw.get("url"),
            format=str(audit_raw.get("format", "text")),
            output=audit_raw.get("output"),
            min_score=_safe_int(audit_raw.get("min_score", 0)),
            cache=bool(audit_raw.get("cache", False)),
            verbose=bool(audit_raw.get("verbose", False)),
        )

    # llms section
    llms_raw = raw.get("llms", {})
    if isinstance(llms_raw, dict):
        config.llms = LlmsConfig(
            base_url=llms_raw.get("base_url"),
            title=llms_raw.get("title"),
            description=llms_raw.get("description"),
            max_urls=_safe_int(llms_raw.get("max_urls", 50), default=50),
        )

    # schema section
    schema_raw = raw.get("schema", {})
    if isinstance(schema_raw, dict):
        types = schema_raw.get("types", [])
        if isinstance(types, list):
            config.schema = SchemaConfig(types=[str(t) for t in types])

    # Extra bots
    extra_bots = raw.get("extra_bots", {})
    if isinstance(extra_bots, dict):
        config.extra_bots = {str(k): str(v) for k, v in extra_bots.items()}

    return config
