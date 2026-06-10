"""Unit tests for the gateway endpoint catalog (reads vendored specs)."""

import json

import pytest

from src.gateway.catalog import (
    EndpointEntry,
    load_catalog,
    search_catalog,
    match_endpoint,
    SPECS_DIR,
    SUPPLEMENTAL_PATH,
)


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


class TestLoadCatalog:
    def test_loads_full_documented_surface(self, catalog):
        # 41 vendored specs, ~576 documented operations
        spec_entries = [e for e in catalog if e.source == "spec"]
        assert len(spec_entries) >= 550

    def test_scope_is_extracted_from_security(self, catalog):
        # e.g. GET /contacts/ carries contacts.readonly
        contacts_reads = [
            e
            for e in catalog
            if e.category == "contacts" and e.scope == "contacts.readonly"
        ]
        assert contacts_reads, "expected contacts endpoints with contacts.readonly"

    def test_entries_have_summaries(self, catalog):
        spec_entries = [e for e in catalog if e.source == "spec"]
        assert all(e.summary for e in spec_entries)

    def test_supplemental_endpoints_present_and_tagged(self, catalog):
        keys = {(e.method, e.path): e for e in catalog}
        note = keys.get(("POST", "/notes/"))
        assert note is not None, "standalone POST /notes/ should be in catalog"
        assert note.source == "supplemental"
        assert note.category == "notes"

    def test_spec_wins_over_supplemental_on_conflict(self, tmp_path):
        # a supplemental file that duplicates a spec endpoint must not override it
        sup = tmp_path / "supplemental.json"
        sup.write_text(
            json.dumps(
                {
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": "/contacts/",
                            "category": "BOGUS",
                            "summary": "bogus",
                        }
                    ]
                }
            )
        )
        cat = load_catalog(specs_dir=SPECS_DIR, supplemental_path=sup)
        entry = next(e for e in cat if e.method == "GET" and e.path == "/contacts/")
        assert entry.source == "spec"
        assert entry.category == "contacts"


class TestSearchCatalog:
    def test_search_by_term(self, catalog):
        results = search_catalog(catalog, "invoice")
        assert results
        assert all("invoice" in r.display().lower() for r in results)

    def test_and_token_matching(self, catalog):
        # both tokens must appear somewhere in the entry
        results = search_catalog(catalog, "create invoice")
        assert any(r.method == "POST" for r in results)

    def test_category_filter(self, catalog):
        results = search_catalog(catalog, "", category="payments")
        assert results
        assert all(r.category == "payments" for r in results)

    def test_limit_is_respected(self, catalog):
        results = search_catalog(catalog, "", limit=5)
        assert len(results) == 5

    def test_empty_query_returns_everything(self, catalog):
        results = search_catalog(catalog, "", limit=10_000)
        assert len(results) == len(catalog)


class TestEndpointEntryDisplay:
    def test_display_spec(self):
        e = EndpointEntry(
            method="GET",
            path="/contacts/",
            summary="Get Contacts",
            category="contacts",
            scope="contacts.readonly",
            source="spec",
        )
        assert e.display() == "GET /contacts/ — Get Contacts [contacts.readonly]"

    def test_display_supplemental_marker(self):
        e = EndpointEntry(
            method="POST",
            path="/notes/",
            summary="Create a note",
            category="notes",
            scope="contacts.write",
            source="supplemental",
        )
        assert e.display().endswith("(supplemental)")


class TestMatchEndpoint:
    def test_concrete_path_matches_templated_entry(self, catalog):
        e = match_endpoint(catalog, "GET", "/contacts/abc123XYZ")
        assert e is not None
        assert e.path == "/contacts/{contactId}"

    def test_method_must_match(self, catalog):
        # there's no PATCH on that path
        assert match_endpoint(catalog, "PATCH", "/contacts/abc123XYZ") is None

    def test_query_string_ignored(self, catalog):
        e = match_endpoint(catalog, "GET", "/contacts/?limit=10")
        assert e is not None

    def test_no_match_returns_none(self, catalog):
        assert match_endpoint(catalog, "GET", "/totally/made/up") is None


def test_supplemental_file_is_valid_json():
    data = json.loads(SUPPLEMENTAL_PATH.read_text())
    assert "endpoints" in data
    for e in data["endpoints"]:
        assert {"method", "path"} <= set(e)
