"""
Robots.txt parser with RFC 9309 compliance.

Supports:
- Allow and Disallow directives
- User-agent: * wildcard fallback
- Consecutive User-agent line stacking (RFC 9309)
- Case-insensitive agent matching
- Inline comment stripping
- BOM UTF-8 stripping (§ conformità encoding)
- Limite 500KB sul contenuto (RFC 9309 §2.5)
- Longest-match rule per Allow/Disallow (RFC 9309 §2.2.2)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

# Limite massimo di bytes per il file robots.txt (RFC 9309 §2.5)
_MAX_ROBOTS_BYTES = 500 * 1024

logger = logging.getLogger(__name__)


@dataclass
class AgentRules:
    """Rules for a single User-agent in robots.txt."""

    allow: list[str] = field(default_factory=list)
    disallow: list[str] = field(default_factory=list)


@dataclass
class BotStatus:
    """Classification result for a single bot."""

    bot: str
    description: str
    status: str  # "allowed", "blocked", "partial", "missing"
    matched_agent: str | None = None
    disallow_paths: list[str] = field(default_factory=list)
    # True se il permesso arriva solo dal wildcard (non da regola specifica)
    via_wildcard: bool = False


def parse_robots_txt(content: str) -> dict[str, AgentRules]:
    """
    Parse robots.txt content into a dict of agent → rules.

    Implements RFC 9309:
    - Rimuove BOM UTF-8 se presente (§ encoding)
    - Tronca a 500KB prima del parsing (RFC 9309 §2.5)
    - Consecutive User-agent lines share the same rule block
    - Non-agent directives break the stacking group
    - Allow and Disallow are both tracked

    Args:
        content: Raw robots.txt text

    Returns:
        Dict mapping agent names to their AgentRules
    """
    # #108 — Rimuovi BOM UTF-8 se presente
    content = content.lstrip("\ufeff")

    # #110 — Limita a 500KB (RFC 9309 §2.5): tronca ai byte, poi decodifica sicura
    content_bytes = content.encode("utf-8", errors="replace")
    if len(content_bytes) > _MAX_ROBOTS_BYTES:
        logger.warning(
            "robots.txt supera il limite RFC 9309 di 500KB (%d bytes): "
            "contenuto troncato a %d bytes",
            len(content_bytes),
            _MAX_ROBOTS_BYTES,
        )
        content = content_bytes[:_MAX_ROBOTS_BYTES].decode("utf-8", errors="replace")

    agent_rules: dict[str, AgentRules] = {}
    current_agents: list[str] = []
    last_was_agent = False

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        lower = line.lower()
        if lower.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            agent = agent.split("#")[0].strip()
            if not last_was_agent:
                current_agents = []
            if agent not in agent_rules:
                agent_rules[agent] = AgentRules()
            current_agents.append(agent)
            last_was_agent = True
        elif lower.startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            path = path.split("#")[0].strip()
            for agent in current_agents:
                agent_rules[agent].disallow.append(path)
            last_was_agent = False
        elif lower.startswith("allow:"):
            path = line.split(":", 1)[1].strip()
            path = path.split("#")[0].strip()
            for agent in current_agents:
                agent_rules[agent].allow.append(path)
            last_was_agent = False
        else:
            last_was_agent = False

    return agent_rules


def _is_path_allowed(path: str, rules: AgentRules) -> bool | None:
    """
    Verifica se un path è consentito secondo la regola longest-match (RFC 9309 §2.2.2).

    La regola con il prefisso più lungo che corrisponde al path vince.
    In caso di parità, Allow prevale su Disallow.

    Args:
        path: Il path da verificare (es. "/public/page")
        rules: Le regole dell'agente

    Returns:
        True se consentito, False se bloccato, None se nessuna regola corrisponde
    """
    best_length = -1
    best_decision = None  # True=allow, False=disallow

    # Valuta regole Disallow
    for disallow_path in rules.disallow:
        if not disallow_path:
            # Disallow vuoto = consenti tutto (RFC compliant)
            continue
        if path.startswith(disallow_path) or disallow_path in ("/", "/*"):
            match_len = len(disallow_path)
            if match_len > best_length:
                best_length = match_len
                best_decision = False
            elif match_len == best_length and best_decision is False:
                # Parità: Allow prevale (gestito sotto)
                pass

    # Valuta regole Allow (prevalgono in caso di parità di lunghezza)
    for allow_path in rules.allow:
        if not allow_path:
            continue
        if path.startswith(allow_path) or allow_path in ("/", "/*"):
            match_len = len(allow_path)
            if match_len > best_length:
                best_length = match_len
                best_decision = True
            elif match_len == best_length:
                # Parità: Allow prevale su Disallow (RFC 9309 §2.2.2)
                best_decision = True

    return best_decision


def classify_bot(
    bot: str,
    description: str,
    agent_rules: dict[str, AgentRules],
) -> BotStatus:
    """
    Classify a bot as allowed, blocked, partial, or missing based on robots.txt rules.

    Uses case-insensitive matching and falls back to wildcard User-agent: *.
    Implementa longest-match (RFC 9309 §2.2.2) e classificazione "partial"
    quando il bot ha Disallow: / ma anche Allow specifici (#106).

    Args:
        bot: Bot name (e.g. "GPTBot")
        description: Bot description
        agent_rules: Parsed robots.txt rules

    Returns:
        BotStatus with classification
    """
    # Trova agente corrispondente (case-insensitive), fallback a wildcard *
    found_agent = None
    for agent in agent_rules:
        if agent.lower() == bot.lower():
            found_agent = agent
            break

    via_wildcard = False
    if found_agent is None and "*" in agent_rules:
        found_agent = "*"
        via_wildcard = True

    if found_agent is None:
        return BotStatus(bot=bot, description=description, status="missing")

    rules = agent_rules[found_agent]

    # Verifica se il bot è completamente bloccato (Disallow: / o /*)
    is_blocked_root = any(d in ("/", "/*") for d in rules.disallow)
    has_allow_root = any(a in ("/", "/*") for a in rules.allow)

    # #106 — Se Disallow: / ma ci sono Allow specifici → classificare come "partial"
    if is_blocked_root and not has_allow_root:
        # Verifica se esistono Allow specifici (non root)
        specific_allows = [a for a in rules.allow if a and a not in ("/", "/*")]
        if specific_allows:
            return BotStatus(
                bot=bot,
                description=description,
                status="partial",
                matched_agent=found_agent,
                disallow_paths=rules.disallow,
                via_wildcard=via_wildcard,
            )
        return BotStatus(
            bot=bot,
            description=description,
            status="blocked",
            matched_agent=found_agent,
            disallow_paths=rules.disallow,
            via_wildcard=via_wildcard,
        )
    elif not rules.disallow or all(d == "" for d in rules.disallow):
        return BotStatus(
            bot=bot,
            description=description,
            status="allowed",
            matched_agent=found_agent,
            via_wildcard=via_wildcard,
        )
    else:
        # Usa longest-match per verificare il path radice "/"
        # Se "/" è consentito, il bot è "allowed"
        decision = _is_path_allowed("/", rules)
        if decision is False:
            return BotStatus(
                bot=bot,
                description=description,
                status="blocked",
                matched_agent=found_agent,
                disallow_paths=rules.disallow,
                via_wildcard=via_wildcard,
            )
        return BotStatus(
            bot=bot,
            description=description,
            status="allowed",
            matched_agent=found_agent,
            disallow_paths=rules.disallow,
            via_wildcard=via_wildcard,
        )
