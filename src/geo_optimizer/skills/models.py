"""Modelli tipizzati per il catalogo skill interno."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SkillStepSpec:
    """Step esplicito di una skill.

    Attributes:
        step_id: Identificatore stabile dello step.
        title: Titolo leggibile dello step.
        goal: Obiettivo operativo dello step.
        uses: Superfici motore usate nello step.
        outputs: Artefatti prodotti dallo step.
    """

    step_id: str
    title: str
    goal: str
    uses: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


@dataclass
class SkillSpec:
    """Spec strutturata di una skill GEO.

    Attributes:
        schema_version: Versione dello schema della spec.
        skill_id: Identificatore canonico della skill.
        name: Nome leggibile.
        version: Versione della skill.
        kind: Categoria operativa della skill.
        summary: Descrizione breve dello scopo.
        when_to_use: Trigger espliciti per l'uso.
        required_inputs: Input minimi richiesti.
        expected_outputs: Output richiesti.
        engine_surfaces: Contratti verso engine, MCP, plugin hook o docs.
        workflow: Sequenza operativa esplicita.
        guardrails: Vincoli operativi non negoziabili.
        prompt_file: Nome file del prompt associato.
        prompt_text: Prompt markdown caricato dal catalogo.
        source_dir: Directory sorgente della skill.
    """

    schema_version: int
    skill_id: str
    name: str
    version: str
    kind: str
    summary: str
    when_to_use: list[str] = field(default_factory=list)
    required_inputs: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    engine_surfaces: list[str] = field(default_factory=list)
    workflow: list[SkillStepSpec] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    prompt_file: str = "prompt.md"
    prompt_text: str = ""
    source_dir: Path = field(default_factory=Path)

    @property
    def prompt_path(self) -> Path:
        """Ritorna il path assoluto del prompt markdown."""
        return self.source_dir / self.prompt_file
