"""Endpoint catalog for the GoHighLevel gateway.

Builds a searchable catalog of API endpoints from the vendored OpenAPI specs
(``specs/ghl/*.json``) UNION a supplemental list of known-but-undocumented
endpoints (``specs/supplemental.json``).

The vendored spec is incomplete -- roughly 253 real endpoints (standalone
``notes/*``, ``triggers``, ``workflows/{id}/executions``, etc.) are not in it --
so the supplemental list fills gaps the spec misses. Each entry records its
``source`` ("spec" | "supplemental") so callers know when they are on
documented vs. best-effort ground.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import glob
import json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = PROJECT_ROOT / "specs" / "ghl"
SUPPLEMENTAL_PATH = PROJECT_ROOT / "specs" / "supplemental.json"

HTTP_METHODS = ("get", "post", "put", "delete", "patch")


@dataclass(frozen=True)
class EndpointEntry:
    """A single API endpoint in the catalog."""

    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str  # e.g. /contacts/{contactId}/notes
    summary: str
    category: str  # e.g. contacts, invoices
    scope: Optional[str] = None  # e.g. contacts.readonly
    source: str = "spec"  # "spec" | "supplemental"
    operation_id: Optional[str] = None

    def display(self) -> str:
        """Single-line, model-facing rendering."""
        scope = f" [{self.scope}]" if self.scope else ""
        src = "" if self.source == "spec" else " (supplemental)"
        summary = f" — {self.summary}" if self.summary else ""
        return f"{self.method} {self.path}{summary}{scope}{src}"


def _scope_of(op: Dict) -> Optional[str]:
    """Extract the first scope from an operation's security block.

    GHL specs encode scopes as ``security: [{"bearer": ["contacts.readonly"]}]``.
    """
    for sec in op.get("security", []) or []:
        for values in sec.values():
            if values:
                return values[0]
    return None


def load_catalog(
    specs_dir: Path = SPECS_DIR,
    supplemental_path: Optional[Path] = SUPPLEMENTAL_PATH,
) -> List[EndpointEntry]:
    """Load and merge the endpoint catalog from vendored specs + supplemental.

    Spec entries win on conflict; supplemental entries only fill genuine gaps.
    """
    entries: Dict[Tuple[str, str], EndpointEntry] = {}

    for path_str in sorted(glob.glob(str(specs_dir / "*.json"))):
        category = Path(path_str).stem
        spec = json.loads(Path(path_str).read_text())
        for url_path, methods in spec.get("paths", {}).items():
            if not isinstance(methods, dict):
                continue
            for method, op in methods.items():
                if method not in HTTP_METHODS or not isinstance(op, dict):
                    continue
                key = (method.upper(), url_path)
                entries[key] = EndpointEntry(
                    method=method.upper(),
                    path=url_path,
                    summary=op.get("summary") or op.get("operationId") or "",
                    category=category,
                    scope=_scope_of(op),
                    source="spec",
                    operation_id=op.get("operationId"),
                )

    if supplemental_path and Path(supplemental_path).exists():
        sup = json.loads(Path(supplemental_path).read_text())
        for e in sup.get("endpoints", []):
            key = (e["method"].upper(), e["path"])
            if key in entries:
                continue  # never override a documented endpoint
            entries[key] = EndpointEntry(
                method=e["method"].upper(),
                path=e["path"],
                summary=e.get("summary", ""),
                category=e.get("category", "misc"),
                scope=e.get("scope"),
                source="supplemental",
            )

    return list(entries.values())


def search_catalog(
    catalog: List[EndpointEntry],
    query: str,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[EndpointEntry]:
    """Filter the catalog by an AND-of-tokens substring match.

    Matches across method, path, summary, category, and scope. An empty query
    returns everything (optionally filtered by category), up to ``limit``.
    """
    tokens = (query or "").lower().split()
    cat = (category or "").lower().strip()
    results: List[EndpointEntry] = []
    for e in catalog:
        if cat and e.category.lower() != cat:
            continue
        haystack = (
            f"{e.method} {e.path} {e.summary} {e.category} {e.scope or ''}".lower()
        )
        if all(tok in haystack for tok in tokens):
            results.append(e)
    results.sort(key=lambda e: (e.category, e.path, e.method))
    return results[:limit]


_CATALOG_CACHE: Optional[List[EndpointEntry]] = None


def get_catalog() -> List[EndpointEntry]:
    """Return the process-wide catalog, loading it once on first use."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        _CATALOG_CACHE = load_catalog()
    return _CATALOG_CACHE
