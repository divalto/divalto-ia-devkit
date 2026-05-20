"""
verify_x13.py -- Verifie les candidats X.12 dans les sources X.13 et produit
evidence_x13.json.

Source de verite : le filesystem ERP (`--erp-root`). Toute info Neo4j [X.12] passe en
[CONFIRME X.13], [DISPARU X.13] ou est completee par [NOUVEAU X.13].

Bornes : --max-matches, --max-files, --timeout pour gerer la volumetrie (~7000 fichiers).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Vendored
sys.path.insert(0, str(Path(__file__).parent))
from _structural_parser import (  # noqa: E402
    parse_blocks, find_enclosing_block, extract_snippet, read_diva_file,
)

# Vendored SVN wrapper (import optionnel -- si absent, enrichment SVN desactive)
try:
    from svn_consult import svn_log as _svn_log  # noqa: E402
    _SVN_AVAILABLE_MODULE = True
except ImportError:
    _svn_log = None
    _SVN_AVAILABLE_MODULE = False

# --- Mapping prefix module -> sous-repertoires ERP ----------------------

# Aligne sur docs/MODULES-ERP.md section 1 + 2 (sous-modules Achat-Vente)
MODULE_DIRS = {
    "GT_": ["Achat-Vente/source/Dav", "Achat-Vente/source"],
    "RT_": ["Achat-Vente/source/Retail"],
    "GG_": ["Achat-Vente/source/Prod", "Achat-Vente/source/Atelier"],
    "CC_": ["Comptabilite/source", "Comptabilit\u00e9/source"],
    "RC_": ["Reglement/source", "R\u00e8glement/source"],
    "PP_": ["Paie/source"],
    "GA_": ["Affaires/source"],
    "CO_": ["Controle/source", "Contr\u00f4le/source"],
    "GM_": ["Gestion Ressources Materiels/source", "Gestion Ressources Mat\u00e9riels/source"],
    "PV_": ["Point de vente/source"],
    "QU_": ["Qualite/source", "Qualit\u00e9/source"],
    "GR_": ["Relation-Tiers/source"],
    "DO_": ["Documentation/source"],
    "SP_": ["Processus/source"],
    "MO_": ["Mobilite/source", "Mobilit\u00e9/source"],
    "A5": ["A5/source"],
}

# Mapping NOM DE DOMAINE COMPLET -> sous-repertoires ERP. Utilise en mode "auto"
# quand les candidats Neo4j remontent plusieurs domaines (ex: mix Relation-Tiers + Achat-Vente).
# Les variantes accentuees / non-accentuees pointent vers les 2 formes du repertoire
# (l'existence est verifiee a l'execution par .exists()).
DOMAIN_NAME_DIRS = {
    "Achat-Vente": ["Achat-Vente/source/Dav", "Achat-Vente/source",
                    "Achat-Vente/source/Retail", "Achat-Vente/source/Prod",
                    "Achat-Vente/source/Atelier", "Achat-Vente/source/Wms"],
    "Relation-Tiers": ["Relation-Tiers/source"],
    "Comptabilite": ["Comptabilite/source", "Comptabilit\u00e9/source"],
    "Comptabilit\u00e9": ["Comptabilite/source", "Comptabilit\u00e9/source"],
    "Reglement": ["Reglement/source", "R\u00e8glement/source"],
    "R\u00e8glement": ["Reglement/source", "R\u00e8glement/source"],
    "Paie": ["Paie/source"],
    "Affaires": ["Affaires/source"],
    "Controle": ["Controle/source", "Contr\u00f4le/source"],
    "Contr\u00f4le": ["Controle/source", "Contr\u00f4le/source"],
    "Qualite": ["Qualite/source", "Qualit\u00e9/source"],
    "Qualit\u00e9": ["Qualite/source", "Qualit\u00e9/source"],
    "Mobilite": ["Mobilite/source", "Mobilit\u00e9/source"],
    "Mobilit\u00e9": ["Mobilite/source", "Mobilit\u00e9/source"],
    "A5": ["A5/source"],
    "Documentation": ["Documentation/source"],
    "Processus": ["Processus/source"],
    "Point de vente": ["Point de vente/source"],
    "Gestion Ressources Materiels": ["Gestion Ressources Materiels/source",
                                      "Gestion Ressources Mat\u00e9riels/source"],
    "Gestion Ressources Mat\u00e9riels": ["Gestion Ressources Materiels/source",
                                           "Gestion Ressources Mat\u00e9riels/source"],
}

# --- Utilitaires ---------------------------------------------------------


@dataclass
class Deadline:
    end_time: float

    def expired(self) -> bool:
        return time.time() >= self.end_time


def domain_scope_dirs(erp_root: Path, domain: str | None, mode: str,
                       candidate_domain_names: list[str] | None = None) -> list[Path]:
    """Retourne les sous-repertoires a explorer selon le scope demande.

    Mode "auto" : union des sous-repertoires de **tous** les domaines presents parmi
    les candidats Neo4j (via `candidate_domain_names`) + le domaine pressenti. Evite
    les faux "DISPARU X.13" quand les candidats sont repartis sur plusieurs domaines
    alors que `domaine_pressenti` ne couvre que l'un d'eux (RETEX 2026-04-23).
    """
    if mode == "all":
        return [erp_root]
    if mode == "auto":
        seen: set[str] = set()
        result: list[Path] = []
        # 1. Domaine pressenti (compatibilite ascendante : garde le comportement historique)
        if domain and domain in MODULE_DIRS:
            for d in MODULE_DIRS[domain]:
                p = erp_root / d
                if d not in seen and p.exists():
                    seen.add(d)
                    result.append(p)
        # 2. Tous les domaines extraits des candidats (correctif bug faux DISPARU)
        for name in candidate_domain_names or []:
            for d in DOMAIN_NAME_DIRS.get(name, []):
                p = erp_root / d
                if d not in seen and p.exists():
                    seen.add(d)
                    result.append(p)
        return result if result else [erp_root]
    # Mode custom : un sous-repertoire nomme explicitement
    custom = erp_root / mode
    if custom.exists():
        return [custom]
    return [erp_root]


def find_program_file(dirs: list[Path], program_name: str,
                       max_dirs: int = 50, deadline: Deadline | None = None) -> Path | None:
    """Cherche <program_name>.dhsp dans les sous-repertoires."""
    for base in dirs:
        if deadline and deadline.expired():
            return None
        for ext in (".dhsp", ".dhsq"):
            for path in base.rglob(f"{program_name}{ext}"):
                return path
    return None


def grep_text(dirs: list[Path], pattern: re.Pattern, max_files: int, max_matches: int,
               deadline: Deadline) -> list[dict]:
    """Grep recursif avec bornes strictes. Retourne liste de {file, line, text}."""
    results: list[dict] = []
    files_examined = 0
    for base in dirs:
        if deadline.expired():
            break
        for path in base.rglob("*.dhs*"):
            if deadline.expired() or files_examined >= max_files:
                break
            if len(results) >= max_matches:
                break
            files_examined += 1
            try:
                with open(path, "r", encoding="iso-8859-1", errors="replace") as f:
                    for lineno, line in enumerate(f, start=1):
                        if pattern.search(line):
                            results.append({
                                "file_path": str(path),
                                "line": lineno,
                                "text": line.rstrip("\r\n")[:200],
                            })
                            if len(results) >= max_matches:
                                break
            except OSError:
                continue
    return results


def extract_context_for(file_path: Path, line_no: int | None = None,
                         window: int = 30) -> dict:
    """Retourne un snippet + bloc englobant. Si line_no is None, prend la ligne milieu."""
    try:
        lines = read_diva_file(file_path)
    except OSError:
        return {}
    total = len(lines)
    target = line_no if line_no is not None else min(total, max(1, total // 2))
    blocks = parse_blocks(lines)
    block = find_enclosing_block(blocks, target)
    start, end, snippet = extract_snippet(lines, target, window=window, block=block)
    return {
        "line": target,
        "enclosing_block": (
            {"kind": block.kind, "name": block.name,
             "decl_line": block.decl_line, "end_line": block.end_line}
            if block else None
        ),
        "snippet_start": start,
        "snippet_end": end,
        "snippet": snippet,
    }


def find_symbol_decl_line(file_path: Path, symbol_names: list[str]) -> tuple[int, str] | None:
    """Cherche le premier symbole (Function/Procedure/DObj) dont le nom matche (case-insensitive).

    Retourne (decl_line, symbol_matche) ou None si aucun. Le match est insensible a la casse,
    le premier symbole trouve dans l'ordre de declaration gagne.
    """
    if not symbol_names:
        return None
    try:
        lines = read_diva_file(file_path)
    except OSError:
        return None
    blocks = parse_blocks(lines)
    wanted = {s.lower() for s in symbol_names}
    for block in blocks:
        if block.name and block.name.lower() in wanted:
            return (block.decl_line, block.name)
    return None


_HEADER_LINE_PAT = re.compile(
    r"^\s*(?://|;|SetModuleInfo|Include\b|ProtectedSpace|Protected\s+Space|xmeload\b)",
    re.IGNORECASE,
)


def _is_header_line(line: str) -> bool:
    """Vrai si la ligne est administrative (commentaire, SetModuleInfo, Include, ...).

    Le nom d'un programme (ex: grpp001) apparait systematiquement dans l'en-tete
    via `SetModuleInfo('$Id: grpp001.dhsp ...')` et les commentaires de cartouche,
    ce qui polluait l'ancrage du snippet (RETEX 2026-04-23 : tous les snippets en L1-16).
    """
    return bool(_HEADER_LINE_PAT.match(line)) or not line.strip()


def _build_term_pattern(term: str) -> re.Pattern:
    """Construit le regex d'un terme : \\b...\\b si le terme est purement alphanum,
    sinon grep litteral sans word-boundaries (car `\\b` ne s'applique pas autour
    de `(`, `.`, `:` qui sont non-word)."""
    if re.fullmatch(r"\w+", term):
        return re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
    return re.compile(re.escape(term), re.IGNORECASE)


def find_candidate_anchor_line(file_path: Path, candidate_name: str,
                                keywords_techniques: list[str]) -> int | None:
    """Cherche une ligne d'ancrage significative dans un fichier DIVA.

    Utilise quand aucun --symbols explicite n'est cible : evite que le snippet
    tombe sur l'en-tete du fichier ou au milieu aleatoire (RETEX UC-100 :
    snippets hors-sujet a L1-16 parce que le nom du programme apparait dans
    `SetModuleInfo('$Id: ...')` et les commentaires).

    Strategie :
    1. Priorite aux keywords techniques du request (plus specifiques que le nom du program).
    2. Fallback sur le nom du candidat. Dans les deux cas, les lignes d'en-tete
       administratif (commentaires, SetModuleInfo, Include, xmeload, ProtectedSpace)
       sont ignorees pour eviter l'ancrage en L1-16.
    3. Si rien ne matche en dehors de l'en-tete, retourne None (fallback milieu).
    """
    try:
        lines = read_diva_file(file_path)
    except OSError:
        return None

    # 1. Keywords techniques du request (plus specifiques au sujet)
    for kw in keywords_techniques or []:
        if not kw:
            continue
        pat = _build_term_pattern(kw)
        for i, line in enumerate(lines, start=1):
            if _is_header_line(line):
                continue
            if pat.search(line):
                return i

    # 2. Nom du candidat, hors en-tete
    if candidate_name:
        pat = _build_term_pattern(candidate_name)
        for i, line in enumerate(lines, start=1):
            if _is_header_line(line):
                continue
            if pat.search(line):
                return i
    return None


# --- Coeur du workflow ---------------------------------------------------


# --- Enrichissement SVN (S-14) ------------------------------------------
# Rate-limit applicatif : max 10 appels svn_log total par run (memory
# feedback_svn_rate_limit.md). Jamais parallelise. Pas de svn blame
# (trop couteux meme sur petits fichiers, cf S-12 : 39s / 1 KB).


def _enrich_confirmed_with_svn_log(confirmed: list[dict],
                                     max_calls: int = 10,
                                     limit_per_call: int = 5) -> dict:
    """Enrichit chaque entry de `confirmed` avec `svn_log_recent` : 5 derniers commits
    du fichier. Rate-limite, sequentiel, degradation gracieuse.

    Retourne un dict `svn_stats` : {calls, successes, available}.
    """
    stats = {"calls": 0, "successes": 0, "available": True, "skipped_rate_limit": 0}
    if not _SVN_AVAILABLE_MODULE or _svn_log is None:
        stats["available"] = False
        return stats
    for entry in confirmed:
        if stats["calls"] >= max_calls:
            stats["skipped_rate_limit"] += 1
            continue
        fp = entry.get("file_path")
        if not fp:
            continue
        r = _svn_log(fp, limit=limit_per_call)
        stats["calls"] += 1
        if not r.get("available", False):
            stats["available"] = False
            break  # SVN indisponible : arret propre, pas de retry
        if r.get("ok"):
            entry["svn_log_recent"] = r.get("data", [])
            stats["successes"] += 1
    return stats


def verify(candidates: dict, request: dict, erp_root: Path, domain_scope: str,
            max_matches: int, max_files: int, timeout: int,
            target_symbols: list[str] | None = None,
            svn_enrich: bool = False) -> dict:
    deadline = Deadline(time.time() + timeout)
    start_wall = time.time()

    neo4j_status = candidates.get("neo4j_status", "ok")
    domain = request.get("domaine_pressenti")
    # Extraire tous les domaines distincts presents parmi les candidats Neo4j :
    # en mode "auto", le scan doit couvrir tous ces domaines, pas seulement le pressenti
    # (sinon faux "DISPARU X.13" sur les candidats hors domaine pressenti, RETEX 2026-04-23).
    candidate_domain_names = sorted({
        p.get("domain") for p in candidates.get("programs", [])
        if p.get("domain") and p.get("domain") != "unknown"
    })
    dirs = domain_scope_dirs(erp_root, domain, domain_scope, candidate_domain_names)

    confirmed: list[dict] = []
    disappeared: list[dict] = []
    new_findings: list[dict] = []
    impact_callers: list[dict] = []

    files_examined_total = 0

    # 1. Verifier l'existence des programs candidats
    for program in candidates.get("programs", []):
        if deadline.expired():
            break
        name = program.get("name")
        if not name:
            continue
        path = find_program_file(dirs, name, deadline=deadline)
        if path is not None:
            files_examined_total += 1
            # Si des symboles sont cibles, extraire le snippet autour de leur declaration
            # plutot qu'au milieu du fichier.
            targeted_line = None
            targeted_symbol = None
            if target_symbols:
                hit = find_symbol_decl_line(path, target_symbols)
                if hit is not None:
                    targeted_line, targeted_symbol = hit
            if targeted_line is None:
                targeted_line = find_candidate_anchor_line(
                    path, name, request.get("keywords_techniques", []))
            context = extract_context_for(path, line_no=targeted_line)
            entry = {
                "from_x12": name,
                "file_path": str(path),
                "line_range": [context.get("snippet_start", 1),
                                context.get("snippet_end", 0)],
                "status": "CONFIRME X.13",
                "context_sample": context,
                "domain": program.get("domain"),
            }
            if targeted_symbol:
                entry["targeted_symbol"] = targeted_symbol
            confirmed.append(entry)
        else:
            disappeared.append({
                "from_x12": name,
                "status": "DISPARU X.13",
                "reason_hypothesis": "non_trouve_via_glob",
                "domain": program.get("domain"),
            })

    # 2. Rechercher les keywords techniques (mode direct si Neo4j indispo, sinon complement)
    keywords = request.get("keywords_techniques", [])
    if neo4j_status == "unavailable":
        keywords = keywords + request.get("keywords_metier", [])[:5]

    confirmed_files = {c["file_path"] for c in confirmed}
    for kw in keywords[:5]:
        if deadline.expired():
            break
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        matches = grep_text(dirs, pattern, max_files=max_files,
                            max_matches=max_matches, deadline=deadline)
        files_examined_total += len(matches)
        for m in matches:
            if m["file_path"] in confirmed_files:
                continue
            context = extract_context_for(Path(m["file_path"]), line_no=m["line"])
            # --- Scoring de pertinence (RETEX 2026-04-18) ---
            # relevance_score = somme des keywords distincts trouves dans le snippet.
            # Permet au consommateur de trier et garder le top N pertinent au lieu
            # du premier N chronologique (qui noyait le signal).
            snippet = context.get("snippet", "") or ""
            all_kws = request.get("keywords_techniques", []) + request.get("keywords_metier", [])[:5]
            rel = sum(
                1 for k in all_kws
                if k and re.search(re.escape(k), snippet, re.IGNORECASE)
            )
            # Bonus : pattern d'affectation Ce4 = 'X' ou ENT.field = 'X' = signal fort
            if re.search(r"\b(?:ENT|MOUV|CLI|FOU)\.\w+\s*=\s*['\"]\w", snippet):
                rel += 1
            new_findings.append({
                "file_path": m["file_path"],
                "line_range": [context.get("snippet_start", m["line"]),
                                context.get("snippet_end", m["line"])],
                "pattern": kw,
                "status": "NOUVEAU X.13",
                "relevance_score": rel,
                "context_sample": context,
            })
            if len(new_findings) >= max_matches:
                break

    # Tri decroissant par relevance_score pour mettre le signal en tete
    new_findings.sort(key=lambda f: f.get("relevance_score", 0), reverse=True)

    # 3. Impact analysis : chercher les callers des functions candidates
    for fn in candidates.get("functions", [])[:5]:
        if deadline.expired():
            break
        fn_name = fn.get("name")
        if not fn_name:
            continue
        call_pat = re.compile(
            rf'\b(?:Call|Execute)\s+[\'"]?{re.escape(fn_name)}[\'"]?|'
            rf'\b{re.escape(fn_name)}\s*\(',
            re.IGNORECASE,
        )
        matches = grep_text(dirs, call_pat, max_files=max_files,
                            max_matches=20, deadline=deadline)
        for m in matches:
            impact_callers.append({
                "file_path": m["file_path"],
                "line": m["line"],
                "text": m["text"],
                "callee": fn_name,
                "status": "CONFIRME X.13",
            })

    # 4. Enrichissement SVN (opt-in, S-14) : svn_log 5 derniers commits par confirme
    svn_stats = None
    if svn_enrich and confirmed:
        svn_stats = _enrich_confirmed_with_svn_log(confirmed, max_calls=10, limit_per_call=5)

    duration = time.time() - start_wall
    scope_dict = {
        "erp_root": str(erp_root),
        "domains_searched": [str(d) for d in dirs],
        "domain_scope_mode": domain_scope,
        "files_examined": files_examined_total,
        "matches_truncated": deadline.expired(),
        "duration_seconds": round(duration, 2),
        "neo4j_status_upstream": neo4j_status,
    }
    if svn_stats is not None:
        scope_dict["svn_enrichment"] = svn_stats
    return {
        "scope": scope_dict,
        "confirmed": confirmed,
        "disappeared": disappeared,
        "new_findings": new_findings,
        "impact": {"callers": impact_callers},
    }


# --- CLI -----------------------------------------------------------------


def _cli() -> int:
    # Windows : stdout par defaut cp1252 -> corrompt les caracteres DIVA (e avec accent).
    # On force UTF-8 pour coherence avec les downstream scripts.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Verifie les candidats X.12 dans l'ERP X.13 et extrait le contexte.")
    ap.add_argument("--candidates", required=True, help="Chemin candidates_x12.json.")
    ap.add_argument("--request", required=True, help="Chemin request.json.")
    ap.add_argument("--erp-root", required=True, help="Racine ERP X.13 (placeholder CHEMIN_ERP_STANDARD).")
    ap.add_argument("--domain-scope", default="auto", help="auto|all|<prefix>")
    ap.add_argument("--max-matches", type=int, default=50)
    ap.add_argument("--max-files", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--symbols", default="",
                    help="Liste CSV de symboles (Function/Procedure/DObj) a cibler pour le snippet. "
                         "Si fourni, le context_sample d'un program confirme est extrait autour "
                         "de la declaration du premier symbole trouve plutot qu'au milieu du fichier.")
    ap.add_argument("--svn-enrich", action="store_true",
                    help="Enrichit chaque confirme avec les 5 derniers commits SVN (svn log). "
                         "Opt-in, rate-limite a 10 appels max. Degradation gracieuse si SVN indispo. "
                         "Pas de svn blame (trop couteux meme petit fichier, cf docs/SVN-CONSULTATION.md 7.5).")
    args = ap.parse_args()

    erp_root = Path(args.erp_root)
    if not erp_root.exists():
        print(f"ERP root introuvable : {erp_root}", file=sys.stderr)
        return 2

    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))

    target_symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] or None

    out = verify(
        candidates=candidates, request=request, erp_root=erp_root,
        domain_scope=args.domain_scope,
        max_matches=args.max_matches, max_files=args.max_files, timeout=args.timeout,
        target_symbols=target_symbols,
        svn_enrich=args.svn_enrich,
    )
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
