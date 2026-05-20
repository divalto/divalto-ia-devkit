"""
build_facts.py -- Construit le FOND (facts.json) d'une analyse pre-action UC-100.

Entree : request.json + candidates_x12.json + evidence_x13.json (phases 1-3).
Sortie : preaction-<slug>-<YYYYMMDD>.facts.json (machine-lisible, refs absolues)
        + preaction-<slug>-<YYYYMMDD>.metrics.json (metriques operationnelles, heritage)

Ce script reutilise les helpers de `build_report.py` (seeds, chain_of_blame,
compute_metrics, preflight_check) et les transforme en FactsDocument structure.

Le livrable markdown n'est PAS produit ici -- il est genere par le skill
`rendering-preaction-livrable` qui consomme le facts.json.

Separation fond / forme : le facts.json contient toutes les refs (path:line, status
X.12/X.13, snippet). Le livrable n'en affiche AUCUNE.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_report import (  # noqa: E402
    _clean_resume,
    _filter_keywords,
    build_seeds,
    compute_metrics,
    preflight_check,
    slugify,
)
from content_types import (  # noqa: E402
    ctx_from_json,
    evaluate_catalog,
)
from facts_schema import (  # noqa: E402
    SCHEMA_VERSION,
    ChainNode,
    Claim,
    Coverage,
    FactsDocument,
    Request,
    SelectionEntry,
    Source,
    Verdict,
    to_dict,
    validate_facts_structure,
)


# --- Mapping content_type_id -> layer d'affichage ------------------------

# Decision de mapping : les types "agir" (T4, T10) et "comprendre le chemin"
# (T1 exemples, T3 impact) vont en tactique. Les types "reference" (T7 constantes,
# T8 parametrage) et "meta" (T2 fonctions langage, T6 attention) vont en technique.
# Aucun type ne va en strategique : la couche strategique est synthetisee depuis
# le verdict + la selection, pas depuis les claims bruts.
_LAYER_BY_CTID: dict[int, str] = {
    1: "tactical",
    2: "technical",
    3: "tactical",
    4: "tactical",
    5: "tactical",
    6: "technical",
    7: "technical",
    8: "technical",
    10: "tactical",
}


# --- Utilitaires ---------------------------------------------------------


def _make_id(counter: list[int]) -> str:
    counter[0] += 1
    return f"C{counter[0]}"


def _status_from_str(raw: str) -> str:
    """Normalise les statuts (evidence utilise 'CONFIRME X.13', schema utilise 'CONFIRME_X13')."""
    s = (raw or "").strip().upper().replace(" ", "_").replace(".", "")
    # 'CONFIRME_X13' apres transformation de 'CONFIRME X.13'
    if s in ("CONFIRME_X13", "CONFIRMED_X13"):
        return "CONFIRME_X13"
    if s in ("DISPARU_X13",):
        return "DISPARU_X13"
    if s in ("NOUVEAU_X13", "NEW_X13"):
        return "NOUVEAU_X13"
    if s in ("X12", "X_12", "X12_ADVISORY"):
        return "X.12"
    # Fallback : essayer de reperer X12 ou X13 dans le texte brut
    upper_raw = (raw or "").upper()
    if "X.12" in upper_raw or "X12" in upper_raw:
        return "X.12"
    if "CONFIRME" in upper_raw:
        return "CONFIRME_X13"
    if "DISPARU" in upper_raw:
        return "DISPARU_X13"
    if "NOUVEAU" in upper_raw:
        return "NOUVEAU_X13"
    return "CONFIRME_X13"


# Regex pour detecter les chemins absolus Windows/Unix dans du texte narratif (a nettoyer).
_ABS_PATH_RE = re.compile(
    r'(?:"[A-Za-z]:[/\\][^"]+"|[A-Za-z]:[/\\][A-Za-z][A-Za-z0-9 _\-./\\]+)'
)
# Regex pour detecter les refs fichier:ligne (`foo.dhsp:123`) a enlever des narratifs.
# Le nom de fichier seul (sans :ligne) est conserve -- il aide la navigation.
_FILE_LINE_RE = re.compile(r"\b([a-zA-Z0-9_-]+\.dhs[pqdf]):\d+\b")


def _sanitize_narrative(text: str, erp_root: str = "") -> str:
    """Retire les chemins absolus et les refs fichier:ligne d'un texte narratif.

    Le fond (facts.json) conserve les refs dans `sources[]`. Le champ `claim` est
    un enonce lisible : il ne doit pas reemettre un path absolu ou un `foo.dhsp:123`,
    sinon le rendu du livrable le propagera et declenchera le validator anti-ref.

    Strategies :
    - Chemin absolu `C:/...` ou `/...` : remplacer par "l'arborescence ERP".
    - `foo.dhsp:123` : remplacer par `foo.dhsp` (nom court conserve pour la navigation).
    """
    if not text:
        return text
    text = _ABS_PATH_RE.sub("l'arborescence ERP", text)
    text = _FILE_LINE_RE.sub(r"\1", text)
    return text


def _abs_path_from_erp(relative_or_abs: str, erp_root: str) -> str:
    """Renvoie un chemin absolu. Si `relative_or_abs` est deja absolu, le renvoie tel quel.

    Sinon, le joint a erp_root. `erp_root` peut etre vide : dans ce cas on renvoie
    l'original (le validator detectera une erreur si relatif).
    """
    if not relative_or_abs:
        return ""
    p = relative_or_abs.replace("\\", "/")
    if p.startswith("/") or (len(p) >= 2 and p[1] == ":"):
        return p
    if erp_root:
        root = erp_root.replace("\\", "/").rstrip("/")
        # Strip : separer le fichier d'une eventuelle ":ligne"
        return f"{root}/{p}"
    return p


# --- Transformations seeds -> claims -------------------------------------


def _example_claim(example: dict, ctid: int, counter: list[int]) -> Claim:
    """Transforme un example de seed_type_1 en Claim(kind='example')."""
    file_path = example.get("file") or example.get("file_path") or ""
    line_range = example.get("line_range") or [1, 1]
    line = line_range[0] if isinstance(line_range, list) and line_range else 1
    enclosing_raw = example.get("enclosing")
    if isinstance(enclosing_raw, dict):
        enclosing_name = enclosing_raw.get("name")
    elif isinstance(enclosing_raw, str):
        enclosing_name = enclosing_raw
    else:
        enclosing_name = None
    snippet = example.get("snippet") or ""
    name = example.get("name") or enclosing_name or example.get("targeted_symbol") or "?"
    targeted = example.get("targeted_symbol")
    if targeted:
        claim_text = f"Exemple X.13 autour du symbole `{targeted}` dans `{Path(file_path).name}`."
    elif enclosing_name:
        claim_text = f"Exemple X.13 : procedure `{enclosing_name}` dans `{Path(file_path).name}`."
    else:
        claim_text = f"Exemple X.13 dans `{Path(file_path).name or name}`."

    return Claim(
        id=_make_id(counter),
        content_type_id=ctid,
        layer=_LAYER_BY_CTID[ctid],
        kind="example",
        claim=claim_text,
        sources=[Source(
            status=_status_from_str(example.get("status", "CONFIRME X.13")),
            path=file_path,
            line=line,
            enclosing=enclosing_name,
            snippet=snippet[:600] if snippet else None,
        )],
        confidence="high" if _status_from_str(example.get("status", "")) == "CONFIRME_X13" else "medium",
    )


def _seeds_to_claims_t1(seeds: dict, counter: list[int]) -> list[Claim]:
    claims = []
    for ex in (seeds.get("type_1") or {}).get("examples", []):
        claims.append(_example_claim(ex, ctid=1, counter=counter))
    return claims


def _seeds_to_claims_t2(seeds: dict, counter: list[int]) -> list[Claim]:
    claims = []
    for fn in (seeds.get("type_2") or {}).get("functions_seeded", []):
        name = fn.get("name", "?")
        file_path = fn.get("usage_file", "")
        line = fn.get("usage_line") or 1
        claims.append(Claim(
            id=_make_id(counter),
            content_type_id=2,
            layer=_LAYER_BY_CTID[2],
            kind="function",
            claim=f"La fonction `{name}` est utilisable dans ce contexte (vue dans `{Path(file_path).name}`).",
            sources=[Source(
                status="CONFIRME_X13",
                path=file_path,
                line=line,
                enclosing=name,
            )],
            confidence="medium",
        ))
    return claims


def _seeds_to_claims_t3(
    seeds: dict,
    evidence: dict,
    erp_root: str,
    counter: list[int],
) -> tuple[list[Claim], dict[str, str]]:
    """Retourne (claims_impact_caller, nom_symbole -> claim_id_t1_or_t3).

    Le mapping nom_symbole -> claim_id sert a resoudre source_ref des nodes du call_chain.
    """
    claims: list[Claim] = []
    t3 = seeds.get("type_3") or {}
    for caller in t3.get("callers", []):
        file_path = caller.get("file") or ""
        line = caller.get("line") or 0
        callee = caller.get("callee") or "?"
        raw_status = caller.get("status") or ""
        status = _status_from_str(raw_status)
        advisory = "advisory" in raw_status.lower()
        if advisory:
            status = "X.12"
        # Un file_path advisory X.12 n'est pas un path absolu (ex: "(advisory X.12, ...)").
        # On remplace par erp_root (ancrage absolu) et on signale l'advisory dans le claim.
        looks_absolute = bool(
            file_path and (
                file_path.startswith("/") or (len(file_path) >= 2 and file_path[1] == ":")
            )
        )
        if not looks_absolute:
            file_path = erp_root or "C:/Developpements harmony/Standard/Version X.13"
            line = 0
        claims.append(Claim(
            id=_make_id(counter),
            content_type_id=3,
            layer=_LAYER_BY_CTID[3],
            kind="impact_caller",
            claim=f"`{caller.get('text_excerpt', callee)}` appelle `{callee}` et propage l'impact.",
            sources=[Source(
                status=status,
                path=file_path,
                line=int(line) if line else None,
            )],
            confidence="high" if status == "CONFIRME_X13" else "low",
        ))
    return claims, {}


def _resolve_chain_source_refs(
    chain_nodes: list[dict],
    t1_claims: list[Claim],
) -> list[ChainNode]:
    """Resout le source_ref de chaque node du chain_of_blame.

    Pour chaque node de type fn/fn_noline, cherche un claim T1 dont le source.enclosing
    ou targeted_symbol matche le node.name. Si trouve, ajoute `source_ref = claim.id`.
    """
    # Index des claims T1 par nom de symbole (enclosing ou cle)
    by_symbol: dict[str, str] = {}
    for c in t1_claims:
        for s in c.sources:
            if s.enclosing:
                by_symbol[s.enclosing.lower()] = c.id
            # Essayer aussi de deduire le symbole depuis le claim text
    resolved: list[ChainNode] = []
    for i, n in enumerate(chain_nodes):
        kind = n.get("kind")
        nid = f"N{i}"
        if kind == "ui":
            resolved.append(ChainNode(
                id=nid,
                kind="ui",
                label=n.get("label") or n.get("name"),
            ))
        elif kind in ("fn", "fn_noline"):
            name = n.get("name", "?")
            source_ref = by_symbol.get(name.lower())
            resolved.append(ChainNode(
                id=nid,
                kind=kind,
                name=name,
                source_ref=source_ref,
            ))
        elif kind == "action":
            # Les action_const de build_report.py sont "A5_Action_Generer_Action(C_Action_...)"
            # Dans le schema, on les normalise en kind=action_const avec just le C_Action.
            const = n.get("const") or ""
            resolved.append(ChainNode(
                id=nid,
                kind="action_const",
                const=const,
            ))
        elif kind == "gap":
            resolved.append(ChainNode(
                id=nid,
                kind="gap",
                label=n.get("label"),
            ))
        else:
            # Fallback : convertir en gap pour ne pas casser le chain
            resolved.append(ChainNode(
                id=nid,
                kind="gap",
                label=n.get("label") or str(n),
            ))
    return resolved


def _seeds_to_claims_chain(
    seeds: dict,
    t1_claims: list[Claim],
    counter: list[int],
) -> list[Claim]:
    chain = seeds.get("chain_of_blame") or {}
    if not chain.get("available"):
        return []
    raw_nodes = chain.get("nodes") or []
    nodes = _resolve_chain_source_refs(raw_nodes, t1_claims)
    # Edges : lineaire N0->N1->N2->...
    edges = [[nodes[i].id, nodes[i + 1].id] for i in range(len(nodes) - 1)]
    # Extraire une phrase descriptive
    names_in_chain = [n.name or n.label or n.const or "?" for n in nodes]
    claim_text = (
        "Chaine d'appels : "
        + " -> ".join(str(x) for x in names_in_chain if x)
        + "."
    )
    return [Claim(
        id=_make_id(counter),
        content_type_id=3,
        layer=_LAYER_BY_CTID[3],
        kind="call_chain",
        claim=claim_text,
        sources=[],
        confidence="high",
        nodes=nodes,
        edges=edges,
    )]


def _seeds_to_claims_t4(seeds: dict, counter: list[int]) -> list[Claim]:
    claims = []
    for prop in (seeds.get("type_4") or {}).get("propositions", []):
        title = prop.get("title") or "?"
        file_path = prop.get("file") or ""
        line = prop.get("line") or 1
        enclosing = prop.get("enclosing")
        hypothese = prop.get("hypothese") or f"Investiguer `{title}`."
        action_kind = prop.get("action_kind") or ""
        claim_text = hypothese
        if action_kind:
            claim_text = f"{action_kind.capitalize()}. {hypothese}"
        claims.append(Claim(
            id=_make_id(counter),
            content_type_id=4,
            layer=_LAYER_BY_CTID[4],
            kind="action_site",
            claim=claim_text,
            sources=[Source(
                status="CONFIRME_X13",
                path=file_path,
                line=int(line) if line else None,
                enclosing=enclosing,
            )],
            confidence="high",
        ))
    return claims


def _seeds_to_claims_t5(seeds: dict, erp_root: str, counter: list[int]) -> list[Claim]:
    """Pistes : kind=hint. Les pistes n'ont pas de ref X.13 precise, on pointe vers erp_root."""
    claims = []
    for h in (seeds.get("type_5") or {}).get("hints", []):
        intent = h.get("intent") or "Explorer une piste."
        command = h.get("command") or ""
        expected = h.get("expected") or ""
        claim_text = intent
        if command:
            claim_text += f" Commande : `{command}`."
        if expected:
            claim_text += f" Attendu : {expected}."
        claims.append(Claim(
            id=_make_id(counter),
            content_type_id=5,
            layer=_LAYER_BY_CTID[5],
            kind="hint",
            claim=claim_text,
            sources=[Source(
                status="NOUVEAU_X13",
                path=erp_root or "C:/Developpements harmony/Standard/Version X.13",
                line=1,
                enclosing=None,
                snippet="Piste de recherche complementaire (commande a executer sur l'ERP).",
            )],
            confidence="low",
        ))
    return claims


def _seeds_to_claims_t6(seeds: dict, evidence: dict, erp_root: str, counter: list[int]) -> list[Claim]:
    """Points d'attention : kind=overwrite_warning. On retrouve le path absolu depuis evidence."""
    claims = []
    # Index des basenames vers file_path absolu depuis les confirmed
    basename_to_path: dict[str, str] = {}
    for c in evidence.get("confirmed", []):
        fp = c.get("file_path", "")
        if fp:
            basename_to_path[Path(fp).name.lower()] = fp
    for over in (seeds.get("type_6") or {}).get("overwrites", []):
        file_name = over.get("file") or ""
        pattern = over.get("pattern") or ""
        context = over.get("context") or ""
        abs_path = basename_to_path.get(file_name.lower(), "")
        if not abs_path:
            abs_path = _abs_path_from_erp(file_name, erp_root)
        claims.append(Claim(
            id=_make_id(counter),
            content_type_id=6,
            layer=_LAYER_BY_CTID[6],
            kind="overwrite_warning",
            claim=f"Surcharge/effet de bord detecte : `{pattern}` dans `{file_name}`. Contexte : {context}",
            sources=[Source(
                status="CONFIRME_X13",
                path=abs_path,
                snippet=context,
            )],
            confidence="medium",
        ))
    return claims


def _seeds_to_claims_t7(seeds: dict, erp_root: str, counter: list[int]) -> list[Claim]:
    """Constantes metier : kind=literal_table. canonical_source_code est relatif a ERP."""
    claims = []
    for lit in (seeds.get("type_7") or {}).get("literals", []):
        name = lit.get("name", "?")
        canonical = lit.get("canonical_source_code") or ""
        note = lit.get("note") or ""
        table = lit.get("table") or []
        # Parser "relative/path.dhsq:453" -> path + line
        path_rel, _, line_str = canonical.partition(":")
        abs_path = _abs_path_from_erp(path_rel, erp_root)
        try:
            line = int(line_str) if line_str else None
        except ValueError:
            line = None
        # Claim textuel = synthese de la table
        table_str = ""
        if table:
            rows = [f"{row.get('valeur', '?')}={row.get('libelle', '?')}" for row in table[:7]]
            table_str = " Table : " + ", ".join(rows) + "."
        claim_text = f"Table de codes metier {name}.{table_str} {note}".strip()
        claims.append(Claim(
            id=_make_id(counter),
            content_type_id=7,
            layer=_LAYER_BY_CTID[7],
            kind="literal_table",
            claim=claim_text,
            sources=[Source(
                status="CONFIRME_X13",
                path=abs_path,
                line=line,
                enclosing=None,
                snippet=f"Table canonique {name} : voir le RecordSql ou le dictionnaire.",
            )],
            confidence="high",
        ))
    return claims


def _seeds_to_claims_t8(seeds: dict, erp_root: str, counter: list[int]) -> list[Claim]:
    """Parametrage dossier : kind=dossier_param. On pointe vers gtfdd.dhsd."""
    t8 = seeds.get("type_8") or {}
    triggers = t8.get("triggers_hit") or []
    grep_hint = t8.get("grep_hint") or ""
    if not triggers and not grep_hint:
        return []
    claim_text = (
        f"Parametrage dossier suggere par les mots-cles {triggers}. "
        f"Commande d'exploration : `{grep_hint}`."
    )
    abs_path = _abs_path_from_erp("Fichier/gtfdd.dhsd", erp_root)
    return [Claim(
        id=_make_id(counter),
        content_type_id=8,
        layer=_LAYER_BY_CTID[8],
        kind="dossier_param",
        claim=claim_text,
        sources=[Source(
            status="NOUVEAU_X13",
            path=abs_path,
            line=1,
            enclosing=None,
            snippet="Dictionnaire des champs communs incluant les champs dossier.",
        )],
        confidence="medium",
    )]


def _seeds_to_claims_t10(seeds: dict, evidence: dict, counter: list[int]) -> list[Claim]:
    """Verifications prealables : kind=verification."""
    claims = []
    # On prend le premier confirmed comme ancrage de source pour toutes les verifs
    confirmed = evidence.get("confirmed") or []
    anchor_path = confirmed[0].get("file_path", "") if confirmed else ""
    anchor_line = 1
    if confirmed:
        lr = confirmed[0].get("line_range") or [1, 1]
        anchor_line = lr[0] if isinstance(lr, list) else 1
    for v in (seeds.get("type_10") or {}).get("verifications", []):
        intent = v.get("intent") or "Verifier un prealable."
        command = v.get("command") or ""
        expected = v.get("expected") or ""
        claim_text = intent
        if command:
            claim_text += f" Commande : `{command}`."
        if expected:
            claim_text += f" Attendu : {expected}."
        claims.append(Claim(
            id=_make_id(counter),
            content_type_id=10,
            layer=_LAYER_BY_CTID[10],
            kind="verification",
            claim=claim_text,
            sources=[Source(
                status="CONFIRME_X13",
                path=anchor_path,
                line=anchor_line,
                enclosing=None,
                snippet="Verification prealable (commande a executer sur l'ERP).",
            )],
            confidence="medium",
        ))
    return claims


# --- Verdict synthetique -------------------------------------------------


def _build_verdict(
    request: dict,
    t4_claims: list[Claim],
    chain_claims: list[Claim],
) -> Verdict:
    """Construit le verdict synthetique (one-liner). Prefere la 1re proposition T4."""
    request_type = request.get("type", "unknown")
    kind = {"ticket": "investigate", "feature": "create"}.get(request_type, "modify")
    action_id = None
    one_line = ""
    if t4_claims:
        first = t4_claims[0]
        action_id = first.id
        # Extraire le one-liner depuis le claim (limite a 200 chars)
        one_line = first.claim.split(".")[0][:200].strip() + "."
    elif chain_claims:
        one_line = chain_claims[0].claim[:200]
    else:
        one_line = f"Analyser les elements trouves pour {request.get('titre', 'cette demande')}."
    return Verdict(kind=kind, one_line=one_line, action_critique_id=action_id)


# --- Coverage ------------------------------------------------------------


def _build_coverage(metrics: dict) -> Coverage:
    return Coverage(
        neo4j_status=_neo4j_status_canonical(metrics.get("couverture_neo4j", "disponible")),
        signal_ratio=float(metrics.get("signal_ratio", 0.0)),
        confiance=metrics.get("confiance_globale", "moyenne"),
    )


def _neo4j_status_canonical(couverture: str) -> str:
    return {
        "disponible": "available",
        "partielle": "partial",
        "absente": "unavailable",
    }.get(couverture, "available")


# --- Pipeline principal -------------------------------------------------


def build_facts_document(
    request: dict,
    candidates: dict,
    evidence: dict,
    slug: str,
    date_str: str,
    erp_root: str,
) -> FactsDocument:
    """Construit la FactsDocument complete depuis les 3 JSON d'entree."""
    # Reutilise exactement la logique de prepare_context (seeds + selection + metrics)
    ctx = ctx_from_json(request, candidates, evidence)
    cleaned_request = dict(request)
    cleaned_request["resume"] = _clean_resume(request.get("resume", ""))
    cleaned_request["keywords_metier"] = _filter_keywords(request.get("keywords_metier", []))
    selection_raw = evaluate_catalog(ctx)
    seeds = build_seeds(ctx, cleaned_request, candidates, evidence)
    metrics = compute_metrics(cleaned_request, candidates, evidence, selection_raw)

    # Generer les claims dans l'ordre du CATALOG (mais T1 d'abord pour faire la resolution
    # source_ref depuis chain_of_blame).
    counter = [0]
    t1_claims = _seeds_to_claims_t1(seeds, counter)
    # chain en T3, utilise T1 pour source_ref
    chain_claims = _seeds_to_claims_chain(seeds, t1_claims, counter)
    impact_claims, _ = _seeds_to_claims_t3(seeds, evidence, erp_root, counter)
    t4_claims = _seeds_to_claims_t4(seeds, counter)
    t5_claims = _seeds_to_claims_t5(seeds, erp_root, counter)
    t6_claims = _seeds_to_claims_t6(seeds, evidence, erp_root, counter)
    t7_claims = _seeds_to_claims_t7(seeds, erp_root, counter)
    t8_claims = _seeds_to_claims_t8(seeds, erp_root, counter)
    t10_claims = _seeds_to_claims_t10(seeds, evidence, counter)
    t2_claims = _seeds_to_claims_t2(seeds, counter)

    all_claims = (
        t1_claims
        + chain_claims
        + impact_claims
        + t4_claims
        + t5_claims
        + t6_claims
        + t7_claims
        + t8_claims
        + t10_claims
        + t2_claims
    )

    # Post-traitement : nettoyer les paths absolus des textes narratifs. Les paths
    # restent dans `sources[]`. Ce passage evite que le renderer du livrable
    # reemette un chemin `C:/...` et declenche son validator anti-ref.
    for c in all_claims:
        c.claim = _sanitize_narrative(c.claim)

    # Selection : enrichir avec le layer. Si un type est scoring-included mais aucun
    # claim n'a ete produit (seed vide, filtre interne), forcer included=false avec
    # une raison claire -- sinon le validator detecterait une incoherence F4.
    produced_ctids = {c.content_type_id for c in all_claims}
    selection: list[SelectionEntry] = []
    for s in selection_raw:
        included = s["included"]
        reason = s["reason"]
        if included and s["id"] not in produced_ctids:
            included = False
            reason = f"{reason} ; aucun claim produit (seed vide apres filtrage)"
        selection.append(SelectionEntry(
            id=s["id"],
            slug=s["slug"],
            score=s["score"],
            included=included,
            layer=_LAYER_BY_CTID.get(s["id"], "technical"),
            reason=reason,
        ))

    verdict = _build_verdict(cleaned_request, t4_claims, chain_claims)
    coverage = _build_coverage(metrics)

    return FactsDocument(
        schema_version=SCHEMA_VERSION,
        slug=slug,
        date=date_str,
        request=Request(
            type=cleaned_request.get("type", "unknown"),
            domaine=cleaned_request.get("domaine_pressenti") or cleaned_request.get("domaine", ""),
            titre=cleaned_request.get("titre") or cleaned_request.get("resume", "")[:100],
            resume=cleaned_request.get("resume", ""),
        ),
        verdict=verdict,
        coverage=coverage,
        claims=all_claims,
        selection=selection,
    )


def _fmt_date_iso(raw_date: str | None) -> str:
    """YYYYMMDD -> YYYY-MM-DD. Si None, retourne aujourd'hui."""
    if raw_date and len(raw_date) == 8 and raw_date.isdigit():
        return f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    return datetime.now().strftime("%Y-%m-%d")


# --- CLI -----------------------------------------------------------------


def _cli() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Construit le fond (facts.json) d'une analyse pre-action UC-100."
    )
    ap.add_argument("--request", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--output-dir", default="output")
    ap.add_argument("--slug")
    ap.add_argument("--date", help="Format YYYYMMDD")
    ap.add_argument(
        "--erp-root",
        default="C:/Developpements harmony/Standard/Version X.13",
        help="Racine ERP pour reconstruire les chemins absolus.",
    )
    args = ap.parse_args()

    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))

    # Pre-flight : heritage direct de build_report.py
    pf_errors, pf_warnings = preflight_check(request, candidates, evidence)
    if pf_errors:
        print("ERREUR : inputs JSON degrades, facts.json ne sera pas genere :", file=sys.stderr)
        for e in pf_errors:
            print(f"  - {e}", file=sys.stderr)
        if pf_warnings:
            print("\nAvertissements supplementaires :", file=sys.stderr)
            for w in pf_warnings:
                print(f"  ! {w}", file=sys.stderr)
        return 3
    if pf_warnings:
        print("Pre-flight avertissements :", file=sys.stderr)
        for w in pf_warnings:
            print(f"  ! {w}", file=sys.stderr)

    slug = args.slug or slugify(
        request.get("titre", request.get("resume", "sans-titre"))[:60]
    )
    date_str_compact = args.date or datetime.now().strftime("%Y%m%d")
    date_iso = _fmt_date_iso(date_str_compact)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    facts_path = out_dir / f"preaction-{slug}-{date_str_compact}.facts.json"
    metrics_path = out_dir / f"preaction-{slug}-{date_str_compact}.metrics.json"

    # Construction du FactsDocument
    facts_doc = build_facts_document(
        request=request,
        candidates=candidates,
        evidence=evidence,
        slug=slug,
        date_str=date_iso,
        erp_root=args.erp_root,
    )
    facts_dict = to_dict(facts_doc)

    # Validation stricte avant ecriture
    validation_errors = validate_facts_structure(facts_dict)
    if validation_errors:
        print("ERREUR : facts.json invalide (validator a remonte des erreurs) :", file=sys.stderr)
        for e in validation_errors:
            print(f"  - {e}", file=sys.stderr)
        return 4

    # Ecriture facts.json (UTF-8 + LF)
    with open(facts_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(facts_dict, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Metriques operationnelles (heritage du build_report.json parallele)
    selection_raw = evaluate_catalog(ctx_from_json(request, candidates, evidence))
    metrics = compute_metrics(request, candidates, evidence, selection_raw)
    metrics_out: dict[str, Any] = {
        "date": date_iso,
        "slug": slug,
        "request_type": request.get("type"),
        "domaine": request.get("domaine_pressenti"),
        "metrics": metrics,
        "confiance_globale": metrics["confiance_globale"],
        "couverture_neo4j": metrics["couverture_neo4j"],
        "facts_path": str(facts_path),
        "preflight_warnings": len(pf_warnings),
    }
    with open(metrics_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(metrics_out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Reporting CLI
    result = {
        "facts_path": str(facts_path),
        "metrics_path": str(metrics_path),
        "schema_version": SCHEMA_VERSION,
        "claims_count": len(facts_doc.claims),
        "selection_included": [s.id for s in facts_doc.selection if s.included],
        "selection_omitted": [s.id for s in facts_doc.selection if not s.included],
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
