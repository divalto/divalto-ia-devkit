"""
render_livrable.py -- Rend le livrable (forme) d'une analyse pre-action UC-100.

Entree : preaction-<slug>-<YYYYMMDD>.facts.json
Sortie : preaction-<slug>-<YYYYMMDD>.md (UTF-8 + LF, 3 couches)

Separation fond / forme stricte :
- Le livrable NE contient PAS de path absolu, PAS de balise [X.12]/[CONFIRME X.13],
  PAS de chemin C:/. Ces informations restent dans le facts.json.
- Le livrable est autonome : un lecteur ne doit pas avoir besoin de consulter
  d'autres documents (refs, biblio) pour le comprendre et agir.

Le validator refuse tout rendu qui enfreint ces regles (exit 4).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"


# --- Validator "separation fond/forme" ----------------------------------

# Patterns interdits dans TOUS les livrables (externe ET interne) : stubs LLM,
# fragments de phrase, balises HTML Mermaid... Regression-proof heritage.
_FORBIDDEN_PATTERNS_COMMON: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"LLM\s*\(CP\d+\)\s*:", re.IGNORECASE), "directive LLM residuelle"),
    (re.compile(r"a?\s*(?:preciser|completer|definir|rediger|enrichir)\s+par\s+le\s+LLM", re.IGNORECASE), "placeholder d'enrichissement LLM"),
    (re.compile(r"\[a\s+(?:definir|preciser|completer)\]", re.IGNORECASE), "placeholder a remplir"),
    (re.compile(r"\bTODO\s+LLM\b", re.IGNORECASE), "TODO LLM residuel"),
    (re.compile(r"A\s+completer\s+(?:au\s+)?CP\d+", re.IGNORECASE), "action CP residuelle"),
    (re.compile(r"^\s*-\s*\*\*[\w\s]+\*\*\s*:\s*(?:qui|que|qu['\u2019]|dont|ou|ni)[\s,]", re.MULTILINE), "fragment de phrase (pronom relatif apres label)"),
    (re.compile(r"_[^_\n]*<[a-z][a-z0-9_-]*>[^_\n]*_"), "italique avec placeholder HTML-like"),
    (re.compile(r"\(\s*cf\.?\s+ticket\s+d['\u2019]?origine\s*\)", re.IGNORECASE), "stub inutile '(cf. ticket d'origine)'"),
    (re.compile(r"\b(?:a\s+completer)\b", re.IGNORECASE), "placeholder 'a completer'"),
    (re.compile(r"\b(?:FIXME|XXX)\b"), "marqueur TODO/FIXME/XXX residuel"),
    (re.compile(r"\bTODO\b(?!\s+LLM)", re.IGNORECASE), "TODO residuel"),
    (re.compile(r"<(?:code|em|span|strong)\b[^>]*>"), "balise HTML non rendue (Mermaid/MD fragile)"),
]

# Patterns anti-ref : interdits UNIQUEMENT en audience externe (autonomie
# documentaire). En audience interne, les refs sont autorisees (l'equipe a
# besoin de tracer les sources pour audit).
_FORBIDDEN_PATTERNS_EXTERNE_ONLY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[A-Za-z]:[/\\][A-Za-z][A-Za-z0-9 _\-.]*[/\\]"), "chemin absolu dans le livrable externe (doit rester dans facts.json)"),
    (re.compile(r"\[X\.1[23]\]|\[(?:CONFIRME|DISPARU|NOUVEAU)\s+X\.1[23]\]"), "marqueur de statut X.12/X.13 dans le livrable externe (doit rester dans facts.json)"),
    (re.compile(r"\b[a-zA-Z0-9_-]+\.dhs[pqdf]:\d+\b"), "reference fichier:ligne dans le livrable externe (doit rester dans facts.json)"),
]


def validate_livrable(markdown: str, audience: str = "externe") -> list[str]:
    """Retourne la liste des violations. Liste vide = livrable conforme.

    audience = "externe" : applique les patterns anti-ref en plus des communs.
    audience = "interne" : seuls les patterns communs s'appliquent ; les refs
                           (path:line, [CONFIRME X.13], chemins absolus) sont
                           autorisees car le livrable interne vise l'audit.
    """
    violations: list[str] = []
    patterns = list(_FORBIDDEN_PATTERNS_COMMON)
    if audience == "externe":
        patterns.extend(_FORBIDDEN_PATTERNS_EXTERNE_ONLY)
    for pattern, label in patterns:
        for m in pattern.finditer(markdown):
            line_no = markdown[:m.start()].count("\n") + 1
            excerpt = markdown[max(0, m.start() - 20):m.end() + 30].replace("\n", " ")
            violations.append(f"ligne {line_no} : {label} -- ...{excerpt}...")
    return violations


# --- Preparation du contexte Jinja -------------------------------------


def _ref_inline(claim: dict[str, Any], audience: str) -> str:
    """Formate la reference source inline pour un claim en mode interne.

    Renvoie chaine vide si audience=externe ou si le claim n'a pas de source.
    Format interne : ` _(source : gttmaction.dhsp:567 [CONFIRME X.13], procedure Foo)_`
    """
    if audience != "interne":
        return ""
    sources = claim.get("sources") or []
    if not sources:
        return ""
    s = sources[0]
    path = s.get("path") or ""
    basename = Path(path).name if path else ""
    line = s.get("line")
    status = (s.get("status") or "").replace("_", " ")
    enclosing = s.get("enclosing")
    parts: list[str] = []
    if basename:
        parts.append(f"{basename}:{line}" if line else basename)
    if status:
        parts.append(f"[{status}]")
    if enclosing:
        parts.append(f"procedure {enclosing}")
    if not parts:
        return ""
    return " _(source : " + ", ".join(parts) + ")_"


def _prepare_context(facts: dict[str, Any], audience: str = "externe") -> dict[str, Any]:
    """Extrait les donnees utiles au template. Le renderer ne touche pas aux sources."""
    claims = facts.get("claims", [])
    selection = facts.get("selection", [])
    included_ctids = {s["id"] for s in selection if s.get("included")}
    # Filtrer les claims dont le type est inclus par la selection
    visible_claims = [c for c in claims if c.get("content_type_id") in included_ctids]

    # Enrichir chaque claim avec son ref_text (vide en externe)
    for c in visible_claims:
        c["ref_text"] = _ref_inline(c, audience)

    # Pour la couche interne : preparer la liste complete des claims-avec-sources
    # destinee a l'annexe "Sources consultees".
    full_sources: list[dict[str, Any]] = []
    if audience == "interne":
        for c in claims:
            if c.get("sources"):
                full_sources.append(c)

    # Identifier l'action critique (premier claim action_site)
    action_critique = None
    if facts.get("verdict", {}).get("action_critique_id"):
        crit_id = facts["verdict"]["action_critique_id"]
        for c in visible_claims:
            if c.get("id") == crit_id:
                action_critique = c
                break
    if not action_critique:
        for c in visible_claims:
            if c.get("kind") == "action_site":
                action_critique = c
                break

    return {
        "audience": audience,
        "request": facts.get("request", {}),
        "verdict": facts.get("verdict", {}),
        "coverage": facts.get("coverage", {}),
        "claims": visible_claims,
        "selection": selection,
        "action_critique": action_critique,
        "full_sources": full_sources,
    }


def _render(facts: dict[str, Any], audience: str = "externe") -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    tpl = env.get_template("livrable.md.j2")
    context = _prepare_context(facts, audience=audience)
    return tpl.render(**context)


# --- CLI -----------------------------------------------------------------


def _cli() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Rend le livrable (forme) d'une analyse pre-action UC-100 depuis un facts.json."
    )
    ap.add_argument("--facts", required=True, help="Chemin vers le fichier .facts.json")
    ap.add_argument(
        "--output-dir",
        default="output",
        help="Repertoire de sortie (default: output/)",
    )
    ap.add_argument(
        "--audience",
        choices=("externe", "interne"),
        default="externe",
        help=(
            "Audience cible du livrable. 'externe' (defaut) : autonomie documentaire "
            "stricte, aucune ref source visible. 'interne' : refs inline + annexe "
            "Sources consultees pour audit equipe interne."
        ),
    )
    args = ap.parse_args()

    facts_path = Path(args.facts)
    facts = json.loads(facts_path.read_text(encoding="utf-8"))

    rendered = _render(facts, audience=args.audience)

    # Validation stricte avant ecriture (les patterns anti-ref ne s'appliquent
    # pas en audience interne).
    violations = validate_livrable(rendered, audience=args.audience)
    if violations:
        print("ERREUR : livrable non conforme (violations detectees) :", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print("Corriger les templates Jinja2 ou le facts.json amont.", file=sys.stderr)
        return 4

    # Ecriture. Suffixe .interne.md en audience interne, .md sinon (defaut).
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".interne.md" if args.audience == "interne" else ".md"
    base = facts_path.name.replace(".facts.json", suffix)
    md_path = out_dir / base
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(rendered)

    result = {
        "livrable_path": str(md_path),
        "audience": args.audience,
        "size_lines": len(rendered.splitlines()),
        "size_bytes": len(rendered.encode("utf-8")),
        "claims_rendered": len(facts.get("claims", [])),
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
