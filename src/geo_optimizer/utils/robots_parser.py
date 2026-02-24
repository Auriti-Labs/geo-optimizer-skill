"""
Robots.txt parser with RFC 9309 compliance.

Supports:
- Allow and Disallow directives
- User-agent: * wildcard fallback
- Consecutive User-agent line stacking (RFC 9309)
- Case-insensitive agent matching
- Inline comment stripping
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AgentRules:
    """Rules for a single User-agent in robots.txt."""
    allow: List[str] = field(default_factory=list)
    disallow: List[str] = field(default_factory=list)


@dataclass
class BotStatus:
    """Classification result for a single bot."""
    bot: str
    description: str
    status: str  # "allowed", "blocked", "missing"
    matched_agent: Optional[str] = None
    disallow_paths: List[str] = field(default_factory=list)


def parse_robots_txt(content: str) -> Dict[str, AgentRules]:
    """
    Parse robots.txt content into a dict of agent → rules.

    Implements RFC 9309:
    - Consecutive User-agent lines share the same rule block
    - Non-agent directives break the stacking group
    - Allow and Disallow are both tracked

    Args:
        content: Raw robots.txt text

    Returns:
        Dict mapping agent names to their AgentRules
    """
    agent_rules: Dict[str, AgentRules] = {}
    current_agents: List[str] = []
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


def classify_bot(
    bot: str,
    description: str,
    agent_rules: Dict[str, AgentRules],
) -> BotStatus:
    """
    Classify a bot as allowed, blocked, or missing based on robots.txt rules.

    Uses case-insensitive matching and falls back to wildcard User-agent: *.

    Args:
        bot: Bot name (e.g. "GPTBot")
        description: Bot description
        agent_rules: Parsed robots.txt rules

    Returns:
        BotStatus with classification
    """
    # Find matching agent (case-insensitive), fallback to wildcard *
    found_agent = None
    for agent in agent_rules:
        if agent.lower() == bot.lower():
            found_agent = agent
            break

    if found_agent is None and "*" in agent_rules:
        found_agent = "*"

    if found_agent is None:
        return BotStatus(bot=bot, description=description, status="missing")

    rules = agent_rules[found_agent]
    is_blocked = any(d in ["/", "/*"] for d in rules.disallow)
    has_allow_root = any(a in ["/", "/*"] for a in rules.allow)

    if is_blocked and not has_allow_root:
        return BotStatus(
            bot=bot, description=description, status="blocked",
            matched_agent=found_agent, disallow_paths=rules.disallow,
        )
    elif not rules.disallow or all(d == "" for d in rules.disallow):
        return BotStatus(
            bot=bot, description=description, status="allowed",
            matched_agent=found_agent,
        )
    else:
        return BotStatus(
            bot=bot, description=description, status="allowed",
            matched_agent=found_agent, disallow_paths=rules.disallow,
        )
