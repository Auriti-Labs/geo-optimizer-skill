"""
Configurazione per progetto via .geo-optimizer.yml.

Carica un file YAML opzionale dalla directory di lavoro per definire
defaults del progetto: URL, formato output, cache, bot extra, schema extra.

Richiede PyYAML come dipendenza opzionale:
    pip install geo-optimizer-skill[config]
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Nome del file di configurazione cercato nella directory corrente
CONFIG_FILENAME = ".geo-optimizer.yml"
CONFIG_FILENAME_ALT = ".geo-optimizer.yaml"


@dataclass
class AuditConfig:
    """Configurazione defaults per il comando audit."""

    url: Optional[str] = None
    format: str = "text"
    output: Optional[str] = None
    min_score: int = 0
    cache: bool = False
    verbose: bool = False


@dataclass
class LlmsConfig:
    """Configurazione defaults per il comando llms."""

    base_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    max_urls: int = 50


@dataclass
class SchemaConfig:
    """Configurazione defaults per il comando schema."""

    types: List[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    """Configurazione completa del progetto."""

    audit: AuditConfig = field(default_factory=AuditConfig)
    llms: LlmsConfig = field(default_factory=LlmsConfig)
    schema: SchemaConfig = field(default_factory=SchemaConfig)
    extra_bots: Dict[str, str] = field(default_factory=dict)


def _is_yaml_available() -> bool:
    """Verifica se PyYAML è installato."""
    try:
        import yaml  # noqa: F401

        return True
    except ImportError:
        return False


def find_config_file(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Cerca il file di configurazione nella directory corrente.

    Cerca prima .geo-optimizer.yml, poi .geo-optimizer.yaml.
    """
    search_dir = start_dir or Path.cwd()

    for name in (CONFIG_FILENAME, CONFIG_FILENAME_ALT):
        config_path = search_dir / name
        if config_path.is_file():
            return config_path

    return None


def load_config(config_path: Optional[Path] = None) -> ProjectConfig:
    """Carica configurazione da file YAML.

    Se config_path è None, cerca automaticamente nella directory corrente.
    Ritorna ProjectConfig con defaults se il file non esiste o PyYAML non è installato.
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
    except (yaml.YAMLError, OSError):
        return ProjectConfig()

    if not isinstance(raw, dict):
        return ProjectConfig()

    return _parse_config(raw)


def _parse_config(raw: dict) -> ProjectConfig:
    """Converte dizionario YAML in ProjectConfig tipizzato."""
    config = ProjectConfig()

    # Sezione audit
    audit_raw = raw.get("audit", {})
    if isinstance(audit_raw, dict):
        config.audit = AuditConfig(
            url=audit_raw.get("url"),
            format=str(audit_raw.get("format", "text")),
            output=audit_raw.get("output"),
            min_score=int(audit_raw.get("min_score", 0)),
            cache=bool(audit_raw.get("cache", False)),
            verbose=bool(audit_raw.get("verbose", False)),
        )

    # Sezione llms
    llms_raw = raw.get("llms", {})
    if isinstance(llms_raw, dict):
        config.llms = LlmsConfig(
            base_url=llms_raw.get("base_url"),
            title=llms_raw.get("title"),
            description=llms_raw.get("description"),
            max_urls=int(llms_raw.get("max_urls", 50)),
        )

    # Sezione schema
    schema_raw = raw.get("schema", {})
    if isinstance(schema_raw, dict):
        types = schema_raw.get("types", [])
        if isinstance(types, list):
            config.schema = SchemaConfig(types=[str(t) for t in types])

    # Bot extra
    extra_bots = raw.get("extra_bots", {})
    if isinstance(extra_bots, dict):
        config.extra_bots = {str(k): str(v) for k, v in extra_bots.items()}

    return config
