"""
Audit AI discovery endpoints (geo-checklist.dev standard).

Estratto da audit.py (#402-bis) — separazione responsabilità.
Tutte le funzioni ritornano dataclass, MAI stampano.
"""

from __future__ import annotations

import json
from urllib.parse import urljoin

from geo_optimizer.models.config import (
    AI_DISCOVERY_FAQ_ANSWER_MIN_LEN,
    AI_DISCOVERY_FAQ_QUESTION_MIN_LEN,
    AI_DISCOVERY_SERVICE_NAME_MIN_LEN,
    AI_DISCOVERY_SUMMARY_DESC_MIN_LEN,
    AI_DISCOVERY_SUMMARY_NAME_MIN_LEN,
)
from geo_optimizer.models.results import AiDiscoveryResult
from geo_optimizer.utils.http import fetch_url


def audit_ai_discovery(base_url: str) -> AiDiscoveryResult:
    """Check AI discovery endpoints (geo-checklist.dev standard).

    Checks for:
    - /.well-known/ai.txt (HTTP 200)
    - /ai/summary.json (HTTP 200 + JSON valido con name e description)
    - /ai/faq.json (HTTP 200 + JSON valido)
    - /ai/service.json (HTTP 200 + JSON valido)

    Args:
        base_url: URL base del sito (normalizzato).

    Returns:
        AiDiscoveryResult con i risultati dei check.
    """
    result = AiDiscoveryResult()

    # Verifica /.well-known/ai.txt
    ai_txt_url = urljoin(base_url, "/.well-known/ai.txt")
    r, err = fetch_url(ai_txt_url)
    if r and not err and r.status_code == 200 and len(r.text.strip()) > 0:
        result.has_well_known_ai = True
        result.endpoints_found += 1

    # Verifica /ai/summary.json
    summary_url = urljoin(base_url, "/ai/summary.json")
    r, err = fetch_url(summary_url)
    if r and not err and r.status_code == 200:
        try:
            data = json.loads(r.text)
            result.has_summary = True
            result.endpoints_found += 1
            # Fix #389: name >= 3 char, description >= 20 char
            if (
                isinstance(data, dict)
                and len(str(data.get("name", ""))) >= AI_DISCOVERY_SUMMARY_NAME_MIN_LEN
                and len(str(data.get("description", ""))) >= AI_DISCOVERY_SUMMARY_DESC_MIN_LEN
            ):
                result.summary_valid = True
        except (json.JSONDecodeError, ValueError):
            pass

    # Verifica /ai/faq.json
    faq_url = urljoin(base_url, "/ai/faq.json")
    r, err = fetch_url(faq_url)
    if r and not err and r.status_code == 200:
        try:
            data = json.loads(r.text)
            result.has_faq = True
            result.endpoints_found += 1
            # Fix #389: faqs lista non vuota, ogni item con question >= 10 char e answer >= 20 char
            faqs = data if isinstance(data, list) else data.get("faqs", []) if isinstance(data, dict) else []
            if isinstance(faqs, list):
                valid = [
                    f
                    for f in faqs
                    if isinstance(f, dict)
                    and len(str(f.get("question", ""))) >= AI_DISCOVERY_FAQ_QUESTION_MIN_LEN
                    and len(str(f.get("answer", ""))) >= AI_DISCOVERY_FAQ_ANSWER_MIN_LEN
                ]
                result.faq_count = len(valid)
        except (json.JSONDecodeError, ValueError):
            pass

    # Verifica /ai/service.json
    service_url = urljoin(base_url, "/ai/service.json")
    r, err = fetch_url(service_url)
    if r and not err and r.status_code == 200:
        try:
            data = json.loads(r.text)
            # Fix #389: name >= 3 char + capabilities lista non vuota
            if (
                isinstance(data, dict)
                and len(str(data.get("name", ""))) >= AI_DISCOVERY_SERVICE_NAME_MIN_LEN
                and isinstance(data.get("capabilities"), list)
                and len(data["capabilities"]) > 0
            ):
                result.has_service = True
                result.endpoints_found += 1
        except (json.JSONDecodeError, ValueError):
            pass

    return result


def _audit_ai_discovery_from_responses(r_ai_txt, r_summary, r_faq, r_service) -> AiDiscoveryResult:
    """Analyze AI discovery from pre-fetched HTTP responses (async path).

    Args:
        r_ai_txt: HTTP response for /.well-known/ai.txt (or None).
        r_summary: HTTP response for /ai/summary.json (or None).
        r_faq: HTTP response for /ai/faq.json (or None).
        r_service: HTTP response for /ai/service.json (or None).

    Returns:
        AiDiscoveryResult con i risultati dei check.
    """
    result = AiDiscoveryResult()

    # /.well-known/ai.txt
    if r_ai_txt and r_ai_txt.status_code == 200 and len(r_ai_txt.text.strip()) > 0:
        result.has_well_known_ai = True
        result.endpoints_found += 1

    # /ai/summary.json
    if r_summary and r_summary.status_code == 200:
        try:
            data = json.loads(r_summary.text)
            result.has_summary = True
            result.endpoints_found += 1
            # Fix #389: name >= 3 char, description >= 20 char
            if (
                isinstance(data, dict)
                and len(str(data.get("name", ""))) >= AI_DISCOVERY_SUMMARY_NAME_MIN_LEN
                and len(str(data.get("description", ""))) >= AI_DISCOVERY_SUMMARY_DESC_MIN_LEN
            ):
                result.summary_valid = True
        except (json.JSONDecodeError, ValueError):
            pass

    # /ai/faq.json
    if r_faq and r_faq.status_code == 200:
        try:
            data = json.loads(r_faq.text)
            result.has_faq = True
            result.endpoints_found += 1
            # Fix #389: faqs lista non vuota, ogni item con question >= 10 char e answer >= 20 char
            faqs = data if isinstance(data, list) else data.get("faqs", []) if isinstance(data, dict) else []
            if isinstance(faqs, list):
                valid = [
                    f
                    for f in faqs
                    if isinstance(f, dict)
                    and len(str(f.get("question", ""))) >= AI_DISCOVERY_FAQ_QUESTION_MIN_LEN
                    and len(str(f.get("answer", ""))) >= AI_DISCOVERY_FAQ_ANSWER_MIN_LEN
                ]
                result.faq_count = len(valid)
        except (json.JSONDecodeError, ValueError):
            pass

    # /ai/service.json
    if r_service and r_service.status_code == 200:
        try:
            data = json.loads(r_service.text)
            # Fix #389: name >= 3 char + capabilities lista non vuota
            if (
                isinstance(data, dict)
                and len(str(data.get("name", ""))) >= AI_DISCOVERY_SERVICE_NAME_MIN_LEN
                and isinstance(data.get("capabilities"), list)
                and len(data["capabilities"]) > 0
            ):
                result.has_service = True
                result.endpoints_found += 1
        except (json.JSONDecodeError, ValueError):
            pass

    return result
