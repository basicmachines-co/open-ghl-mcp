"""Unit tests for gateway spec-drift helpers."""

from src.gateway.catalog import EndpointEntry
from src.gateway.drift import diff_catalogs, unclassified_endpoints


def _e(method, path, scope=None, category="misc"):
    return EndpointEntry(method, path, "summary", category, scope, "spec")


def test_diff_catalogs_added_and_removed():
    old = [_e("GET", "/a"), _e("GET", "/b")]
    new = [_e("GET", "/b"), _e("POST", "/c")]
    diff = diff_catalogs(old, new)
    assert diff["added"] == ["POST /c"]
    assert diff["removed"] == ["GET /a"]


def test_diff_catalogs_no_change():
    cat = [_e("GET", "/a")]
    diff = diff_catalogs(cat, cat)
    assert diff == {"added": [], "removed": []}


def test_unclassified_endpoints_flags_unknown_scopes():
    cat = [
        _e("GET", "/contacts/", "contacts.readonly", "contacts"),  # classified
        _e("GET", "/companies/x", "companies.readonly", "companies"),  # agency cat
        _e("GET", "/mystery/", None, "mystery"),  # unknown -> flagged
    ]
    flagged = unclassified_endpoints(cat)
    paths = {e.path for e in flagged}
    assert "/mystery/" in paths
    assert "/contacts/" not in paths
    assert "/companies/x" not in paths
