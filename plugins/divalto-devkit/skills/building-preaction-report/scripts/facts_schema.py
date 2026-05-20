"""
facts_schema.py -- Schema du fond (facts.json) de l'analyse pre-action UC-100.

Separation fond / forme :
- Le fond (ce module) : affirmations atomiques referencees aux sources de verite X.13
  avec disclaimer X.12. Machine-lisible, auditable, regenerable.
- La forme (rendering-preaction-livrable) : livrable markdown 3 couches audience.
  Aucune reference path:line visible. Autonomie documentaire stricte.

Un Claim = une affirmation textuelle + ses sources (path absolu, line, status,
enclosing, snippet). Les donnees structurees (chaine d'appels, table de codes) sont
des claims typees dont les noeuds pointent vers d'autres claims via source_ref.

Le validator `validate_facts_structure` verifie la coherence structurelle (cles
presentes, types, enum valides, unicite des ids, integrite referentielle des
source_ref). Il ne verifie PAS l'existence des fichiers sur disque ni le contenu
des snippets -- c'est le role du skill `reviewing-preaction-facts`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0"


# --- Enums autorises ------------------------------------------------------

SOURCE_STATUSES = ("X.12", "CONFIRME_X13", "DISPARU_X13", "NOUVEAU_X13")
LAYERS = ("strategic", "tactical", "technical")
CONFIDENCES = ("low", "medium", "high")

# kind = nature structurelle du claim (dicte le rendu). Doit rester stable.
CLAIM_KINDS = (
    "example",            # exemple de code confirme ou nouveau (section T1)
    "function",           # fonction du langage DIVA utile (section T2)
    "call_chain",         # chaine d'appels structuree (section T3)
    "impact_caller",      # site appelant une fonction de la chain (section T3)
    "action_site",        # proposition d'endroit ou agir (section T4)
    "hint",               # piste de recherche complementaire (section T5)
    "overwrite_warning",  # point d'attention surcharge/effet de bord (section T6)
    "literal_table",      # table de codes metier (Ce4, TiCod...) (section T7)
    "dossier_param",      # parametrage dossier / systeme (section T8)
    "verification",       # commande a lancer avant d'agir (section T10)
)

# Node kinds dans un call_chain. "fn_noline" = fonction connue mais sans ligne precise.
CHAIN_NODE_KINDS = ("ui", "fn", "fn_noline", "action_const", "gap")


# --- Dataclasses ---------------------------------------------------------


@dataclass
class Source:
    """Reference absolue a une source de verite. Jamais rendue dans le livrable."""
    status: str                     # "X.12" | "CONFIRME_X13" | "DISPARU_X13" | "NOUVEAU_X13"
    path: str                       # toujours absolu (C:/... ou /...)
    line: int | None = None
    enclosing: str | None = None    # procedure/function englobante
    snippet: str | None = None


@dataclass
class ChainNode:
    """Noeud dans un call_chain. Peut pointer vers un Claim existant via source_ref."""
    id: str                         # "N0", "N1", ...
    kind: str                       # "ui" | "fn" | "fn_noline" | "action_const" | "gap"
    label: str | None = None        # libelle humain (ui, gap)
    name: str | None = None         # nom symbole (fn, fn_noline)
    const: str | None = None        # nom constante (action_const)
    source_ref: str | None = None   # id d'un Claim dont les sources documentent ce noeud


@dataclass
class Claim:
    """Affirmation atomique + ses sources. Unite de base du fond."""
    id: str                         # "C1", "C2", ...
    content_type_id: int            # 1..10 -> CATALOG de content_types.py
    layer: str                      # "strategic" | "tactical" | "technical"
    kind: str                       # cf CLAIM_KINDS
    claim: str                      # enonce textuel de l'affirmation
    sources: list[Source] = field(default_factory=list)
    confidence: str = "medium"      # "low" | "medium" | "high"
    # call_chain uniquement :
    nodes: list[ChainNode] | None = None
    edges: list[list[str]] | None = None   # [["N0","N1"], ...]


@dataclass
class Request:
    type: str                       # "feature" | "ticket" | "unknown"
    domaine: str                    # "GT_" | "RT_" | ...
    titre: str
    resume: str


@dataclass
class Verdict:
    """Synthese une-ligne du document, derivee des claims."""
    kind: str                       # "investigate" | "create" | "modify"
    one_line: str
    action_critique_id: str | None = None   # ref vers un Claim.id (type action_site)


@dataclass
class Coverage:
    neo4j_status: str               # "available" | "partial" | "unavailable"
    signal_ratio: float             # 0.0 .. 1.0
    confiance: str                  # "forte" | "moyenne" | "faible"


@dataclass
class SelectionEntry:
    """Trace de la decision d'inclusion d'un type de contenu (CA10)."""
    id: int
    slug: str
    score: float
    included: bool
    layer: str                      # strategic | tactical | technical
    reason: str


@dataclass
class FactsDocument:
    schema_version: str
    slug: str
    date: str                       # YYYY-MM-DD
    request: Request
    verdict: Verdict
    coverage: Coverage
    claims: list[Claim]
    selection: list[SelectionEntry]


# --- Serialisation --------------------------------------------------------


def to_dict(doc: FactsDocument) -> dict[str, Any]:
    """Serialize une FactsDocument en dict pret pour json.dumps. Nettoie les None."""
    raw = asdict(doc)
    return _strip_none(raw)


def _strip_none(value: Any) -> Any:
    """Retire recursivement les cles dont la valeur est None (dataclass default)."""
    if isinstance(value, dict):
        return {k: _strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_none(x) for x in value]
    return value


# --- Validator ------------------------------------------------------------


def validate_facts_structure(doc: dict[str, Any]) -> list[str]:
    """Verifie la coherence structurelle d'un facts.json serialise en dict.

    Retourne une liste de chaines d'erreur. Liste vide = document valide.

    Ce validator ne touche pas au disque. Il verifie :
    - schema_version correct
    - cles obligatoires top-level presentes
    - request / verdict / coverage / selection : cles obligatoires
    - claims : id unique, layer/confidence/kind valides, sources avec path absolu
    - sources[].status : enum valide
    - call_chain : nodes/edges coherents, source_ref pointe vers un claim existant
    - coherence selection <-> claims : chaque type inclus a au moins 1 claim (F4)

    Les verifications d'existence de fichier et de snippet sont hors-scope -- elles
    relevent du skill reviewing-preaction-facts (categories F2/F3).
    """
    errors: list[str] = []

    # 1. Schema version
    if doc.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version must be '{SCHEMA_VERSION}', got '{doc.get('schema_version')}'"
        )

    # 2. Cles obligatoires top-level
    for key in ("slug", "date", "request", "verdict", "coverage", "claims", "selection"):
        if key not in doc:
            errors.append(f"missing required top-level key: '{key}'")

    # 3. request
    req = doc.get("request", {})
    if isinstance(req, dict):
        for key in ("type", "domaine", "titre", "resume"):
            if key not in req:
                errors.append(f"request missing required key: '{key}'")
    else:
        errors.append(f"request must be an object, got {type(req).__name__}")

    # 4. verdict
    verdict = doc.get("verdict", {})
    if isinstance(verdict, dict):
        for key in ("kind", "one_line"):
            if key not in verdict:
                errors.append(f"verdict missing required key: '{key}'")
    else:
        errors.append(f"verdict must be an object, got {type(verdict).__name__}")

    # 5. coverage
    cov = doc.get("coverage", {})
    if isinstance(cov, dict):
        for key in ("neo4j_status", "signal_ratio", "confiance"):
            if key not in cov:
                errors.append(f"coverage missing required key: '{key}'")
    else:
        errors.append(f"coverage must be an object, got {type(cov).__name__}")

    # 6. claims
    claims = doc.get("claims", [])
    claim_ids: set[str] = set()
    if not isinstance(claims, list):
        errors.append(f"claims must be a list, got {type(claims).__name__}")
    else:
        for i, c in enumerate(claims):
            if not isinstance(c, dict):
                errors.append(f"claim #{i}: must be an object, got {type(c).__name__}")
                continue
            cid = c.get("id", f"<claim #{i}>")
            # Cles obligatoires
            for key in ("id", "content_type_id", "layer", "kind", "claim"):
                if key not in c:
                    errors.append(f"claim {cid}: missing required key '{key}'")
            # Unicite
            if cid in claim_ids:
                errors.append(f"duplicate claim id: '{cid}'")
            claim_ids.add(cid)
            # Enums
            layer = c.get("layer")
            if layer is not None and layer not in LAYERS:
                errors.append(
                    f"claim {cid}: invalid layer '{layer}' (must be one of {LAYERS})"
                )
            conf = c.get("confidence", "medium")
            if conf not in CONFIDENCES:
                errors.append(
                    f"claim {cid}: invalid confidence '{conf}' (must be one of {CONFIDENCES})"
                )
            kind = c.get("kind")
            if kind is not None and kind not in CLAIM_KINDS:
                errors.append(
                    f"claim {cid}: invalid kind '{kind}' (must be one of {CLAIM_KINDS})"
                )
            # Au moins 1 source requise (sauf call_chain dont les refs sont dans les nodes)
            sources = c.get("sources", [])
            if not isinstance(sources, list):
                errors.append(f"claim {cid}: sources must be a list")
                sources = []
            if kind != "call_chain" and not sources:
                errors.append(
                    f"claim {cid}: kind='{kind}' requires at least 1 source"
                )
            # Validation de chaque source
            for j, s in enumerate(sources):
                if not isinstance(s, dict):
                    errors.append(f"claim {cid} source #{j}: must be an object")
                    continue
                for key in ("status", "path"):
                    if key not in s:
                        errors.append(
                            f"claim {cid} source #{j}: missing required key '{key}'"
                        )
                status = s.get("status")
                if status is not None and status not in SOURCE_STATUSES:
                    errors.append(
                        f"claim {cid} source #{j}: invalid status '{status}' "
                        f"(must be one of {SOURCE_STATUSES})"
                    )
                path = s.get("path", "")
                # Sanity : chemin absolu (Unix-style ou Windows-style)
                if path and not (path.startswith("/") or (len(path) >= 2 and path[1] == ":")):
                    errors.append(
                        f"claim {cid} source #{j}: path must be absolute, got '{path}'"
                    )
            # call_chain : valider nodes/edges
            if kind == "call_chain":
                nodes = c.get("nodes") or []
                edges = c.get("edges") or []
                if not nodes:
                    errors.append(f"claim {cid}: call_chain must have 'nodes'")
                node_ids: set[str] = set()
                for n in nodes:
                    if not isinstance(n, dict):
                        errors.append(f"claim {cid}: node must be an object")
                        continue
                    nid = n.get("id")
                    if not nid:
                        errors.append(f"claim {cid}: node missing 'id'")
                        continue
                    node_ids.add(nid)
                    nkind = n.get("kind")
                    if nkind not in CHAIN_NODE_KINDS:
                        errors.append(
                            f"claim {cid} node {nid}: invalid kind '{nkind}' "
                            f"(must be one of {CHAIN_NODE_KINDS})"
                        )
                # Edges bien formes
                for e in edges:
                    if not (isinstance(e, list) and len(e) == 2):
                        errors.append(
                            f"claim {cid}: edge must be [from,to] pair, got {e}"
                        )
                        continue
                    if e[0] not in node_ids or e[1] not in node_ids:
                        errors.append(
                            f"claim {cid}: edge references unknown node: {e}"
                        )

        # Post-pass : source_ref doit pointer vers un claim existant
        for c in claims:
            if not isinstance(c, dict) or c.get("kind") != "call_chain":
                continue
            cid = c.get("id")
            for n in c.get("nodes") or []:
                if not isinstance(n, dict):
                    continue
                sr = n.get("source_ref")
                if sr and sr not in claim_ids:
                    errors.append(
                        f"claim {cid} node {n.get('id')}: source_ref='{sr}' "
                        f"but no claim with that id exists"
                    )

    # 7. selection
    selection = doc.get("selection", [])
    included_ctids: set[int] = set()
    if not isinstance(selection, list):
        errors.append(f"selection must be a list, got {type(selection).__name__}")
    else:
        for i, s in enumerate(selection):
            if not isinstance(s, dict):
                errors.append(f"selection #{i}: must be an object")
                continue
            for key in ("id", "slug", "score", "included", "layer", "reason"):
                if key not in s:
                    errors.append(f"selection #{i}: missing required key '{key}'")
            layer = s.get("layer")
            if layer is not None and layer not in LAYERS:
                errors.append(
                    f"selection #{i}: invalid layer '{layer}' (must be one of {LAYERS})"
                )
            if s.get("included"):
                ctid = s.get("id")
                if isinstance(ctid, int):
                    included_ctids.add(ctid)

    # 8. Coherence selection <-> claims (F4 structurel)
    if isinstance(claims, list):
        claim_ctids = {
            c.get("content_type_id")
            for c in claims
            if isinstance(c, dict) and isinstance(c.get("content_type_id"), int)
        }
        missing = included_ctids - claim_ctids
        for ctid in sorted(missing):
            errors.append(
                f"selection: content_type_id={ctid} is included but no claim has that id"
            )

    return errors


# --- CLI pour validation ad-hoc -------------------------------------------


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="Valide la structure d'un facts.json."
    )
    parser.add_argument(
        "facts",
        help="Chemin vers le fichier .facts.json a valider.",
    )
    args = parser.parse_args()

    with open(args.facts, encoding="utf-8") as f:
        doc = json.load(f)

    errs = validate_facts_structure(doc)
    if not errs:
        print(f"OK: {args.facts} -- 0 erreur")
        sys.exit(0)
    for e in errs:
        print(f"ERROR: {e}", file=sys.stderr)
    print(f"FAIL: {len(errs)} erreur(s)", file=sys.stderr)
    sys.exit(1)
