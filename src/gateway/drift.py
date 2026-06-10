"""Spec-drift helpers for the gateway catalog.

Pure functions used by ``scripts/refresh_specs.py`` (and tested directly):
compare two catalogs and surface endpoints whose token level resolves by
default (i.e. their scope's Sub-Account/Agency tag has not been confirmed),
so new sharp edges get classified rather than silently shipped.
"""

from typing import Dict, List

from .catalog import EndpointEntry
from .registry import is_classified


def diff_catalogs(
    old: List[EndpointEntry], new: List[EndpointEntry]
) -> Dict[str, List[str]]:
    """Return added/removed endpoints (by "METHOD path") between two catalogs."""
    old_keys = {f"{e.method} {e.path}" for e in old}
    new_keys = {f"{e.method} {e.path}" for e in new}
    return {
        "added": sorted(new_keys - old_keys),
        "removed": sorted(old_keys - new_keys),
    }


def unclassified_endpoints(catalog: List[EndpointEntry]) -> List[EndpointEntry]:
    """Endpoints whose token level is only a default guess (scope tag unknown).

    These should be confirmed against the marketplace Auth UI scope tags.
    """
    return [e for e in catalog if not is_classified(e.scope, e.category)]
