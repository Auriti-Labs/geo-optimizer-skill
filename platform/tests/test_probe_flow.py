"""End-to-end probe flow with the engine/provider stubbed (no network)."""

from __future__ import annotations

import geoready_platform.services.probe.runner as runner
from geoready_platform.core_bridge.probe_adapter import ProbeResponse


def _make_entity(client, headers, *, city="Austin"):
    body = {"canonical_name": "Acme Plumbing", "website_url": "https://acme.com", "category": "plumbers"}
    if city:
        body["geo"] = city
    return client.post("/v1/entities", json=body, headers=headers).json()["id"]


def _stub_provider(monkeypatch):
    monkeypatch.setattr(runner, "resolve_probe_provider", lambda p=None: ("perplexity", "test-key"))


def _fake_run_prompt(prompt, *, provider, api_key):
    # Recommendation prompts mention the brand; one factual answer says "closed".
    if "best" in prompt.lower() or "recommend" in prompt.lower() or "hire" in prompt.lower():
        return ProbeResponse(
            prompt=prompt, provider="perplexity", model="sonar",
            text="The best option is Acme Plumbing. Globex is also notable.",
            # Includes a real competitor plus reference/review sites that must be filtered out.
            citations=["https://acme.com", "https://globex.com", "https://yelp.com/biz/x", "https://reddit.com/r/x"],
        )
    if "hours" in prompt.lower() or "services" in prompt.lower():
        return ProbeResponse(
            prompt=prompt, provider="perplexity", model="sonar",
            text="Acme Plumbing appears to be permanently closed.",
            citations=["https://acme.com"],
        )
    return ProbeResponse(
        prompt=prompt, provider="perplexity", model="sonar",
        text="Acme Plumbing is a plumbing company in Austin.",
        citations=["https://acme.com"],
    )


def test_probe_does_not_require_verification(client, org_key, monkeypatch):
    """Approved decision: probes need auth + quota only, NO ownership gate."""
    headers = org_key["headers"]
    _stub_provider(monkeypatch)
    monkeypatch.setattr(runner, "run_prompt", _fake_run_prompt)

    eid = _make_entity(client, headers)  # never verified
    resp = client.post(f"/v1/entities/{eid}/probes", headers=headers)
    assert resp.status_code == 202, resp.text


def test_full_probe_pipeline_and_provenance(client, org_key, monkeypatch):
    headers = org_key["headers"]
    _stub_provider(monkeypatch)
    monkeypatch.setattr(runner, "run_prompt", _fake_run_prompt)

    eid = _make_entity(client, headers)
    run_id = client.post(f"/v1/entities/{eid}/probes", headers=headers).json()["probe_run_id"]

    run = client.get(f"/v1/probes/{run_id}", headers=headers).json()
    assert run["status"] == "complete"
    assert run["provider"] == "perplexity"
    assert run["model"] == "sonar"
    assert run["taxonomy_version"]
    assert run["share_of_model"] is not None and run["share_of_model"] > 0
    assert run["prompt_count"] >= 1
    # Competitor surfaced from citations; reference/review sites filtered out.
    competitor_names = {c["name"] for c in run["competitors"]}
    assert "globex.com" in competitor_names
    assert "yelp.com" not in competitor_names
    assert "reddit.com" not in competitor_names
    # Hallucination flag surfaced at run level.
    assert any(f["type"] == "claims_closed" for f in run["flags"])

    # Per-response provenance persisted for every row.
    responses = client.get(f"/v1/probes/{run_id}/responses", headers=headers).json()
    assert responses
    for r in responses:
        assert r["provider"] == "perplexity"
        assert r["model"] == "sonar"
        assert r["taxonomy_version"]
        assert r["prompt"]
        assert r["raw_response"]
        assert r["prompt_category"]


def test_probe_quota_enforced(client, org_key, monkeypatch):
    headers = org_key["headers"]
    _stub_provider(monkeypatch)
    monkeypatch.setattr(runner, "run_prompt", _fake_run_prompt)
    eid = _make_entity(client, headers)

    # free_probes_per_day defaults to 3 in test env.
    statuses = [client.post(f"/v1/entities/{eid}/probes", headers=headers).status_code for _ in range(4)]
    assert statuses[:3] == [202, 202, 202]
    assert statuses[3] == 429


def test_probe_history_listed_for_entity(client, org_key, monkeypatch):
    headers = org_key["headers"]
    _stub_provider(monkeypatch)
    monkeypatch.setattr(runner, "run_prompt", _fake_run_prompt)
    eid = _make_entity(client, headers)
    client.post(f"/v1/entities/{eid}/probes", headers=headers)

    runs = client.get(f"/v1/entities/{eid}/probes", headers=headers).json()
    assert len(runs) >= 1
    assert runs[0]["entity_id"] == eid


def test_provider_exception_marks_run_failed_not_500(client, org_key, monkeypatch):
    """A raising provider must mark the run failed, never leave it 'running' or 500."""
    headers = org_key["headers"]
    _stub_provider(monkeypatch)

    def _boom(prompt, *, provider, api_key):
        raise RuntimeError("provider SDK exploded")

    monkeypatch.setattr(runner, "run_prompt", _boom)
    eid = _make_entity(client, headers)

    resp = client.post(f"/v1/entities/{eid}/probes", headers=headers)
    assert resp.status_code == 202, resp.text
    run = client.get(f"/v1/probes/{resp.json()['probe_run_id']}", headers=headers).json()
    assert run["status"] == "failed"
    assert "exploded" in run["error"]


def test_no_provider_marks_run_failed(client, org_key, monkeypatch):
    headers = org_key["headers"]
    monkeypatch.setattr(runner, "resolve_probe_provider", lambda p=None: (None, None))
    eid = _make_entity(client, headers)
    run_id = client.post(f"/v1/entities/{eid}/probes", headers=headers).json()["probe_run_id"]
    run = client.get(f"/v1/probes/{run_id}", headers=headers).json()
    assert run["status"] == "failed"
    assert "provider" in run["error"].lower()
