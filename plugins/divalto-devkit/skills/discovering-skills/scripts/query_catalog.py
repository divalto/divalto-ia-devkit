"""Consulte le catalog.json des skills DIVA selon plusieurs modes.

Modes :
  overview               Panorama des 8 workflows avec skills et summaries
  detail <nom>           Fiche complete d'un skill
  search <mots-cles>     Recherche insensible a la casse
  workflow <id>          Liste les skills d'un workflow
  verb <verbe>           Liste les skills d'un verbe (1er segment du nom)

Sortie par defaut : texte markdown lisible. Option --json pour le brut.

Exit codes :
  0 = OK
  1 = erreur d'argument (mode, nom, id, verbe inconnu)
  2 = erreur interne (catalog.json introuvable ou invalide)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / "reference" / "catalog.json"


def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        print(f"ERREUR: catalog.json introuvable : {CATALOG_PATH}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERREUR: catalog.json invalide : {exc}", file=sys.stderr)
        sys.exit(2)


def render_overview(catalog: dict) -> str:
    lines = [
        f"# Panorama des skills DIVA ({catalog['total_skills']} skills, {len(catalog['workflows'])} workflows)",
        "",
        f"_Genere le {catalog['generated_at']}_",
        "",
    ]
    for wf in catalog["workflows"]:
        lines.append(f"## {wf['label']}  `workflow={wf['id']}`")
        lines.append("")
        lines.append(wf["description"])
        lines.append("")
        for name in wf["skills"]:
            skill = catalog["skills"][name]
            orch = " **[orchestrateur]**" if skill["is_orchestrator"] else ""
            lines.append(f"- **{name}**{orch} -- {skill['summary']}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Pour le detail d'un skill : `query_catalog.py detail <nom>`")
    lines.append("Pour une recherche : `query_catalog.py search <mots-cles>`")
    return "\n".join(lines)


def render_detail(catalog: dict, name: str) -> str:
    skill = catalog["skills"].get(name)
    if not skill:
        return ""
    wf_label = next(
        (w["label"] for w in catalog["workflows"] if w["id"] == skill["workflow"]),
        skill["workflow"],
    )
    lines = [
        f"# {skill['name']}",
        "",
        f"**Workflow** : {wf_label} (`{skill['workflow']}`)",
        f"**Verbe** : `{skill['verb']}`",
        f"**Orchestrateur** : {'oui' if skill['is_orchestrator'] else 'non'}"
        + (f" ({skill['checkpoint_count']} checkpoints)" if skill["checkpoint_count"] else ""),
        "",
        "## Description",
        "",
        skill["description"],
        "",
    ]
    if skill["when_to_use"] and skill["when_to_use"] != skill["description"]:
        lines += ["## Quand l'utiliser", "", skill["when_to_use"], ""]

    if skill["scripts"]:
        lines.append("## Scripts")
        lines.append("")
        for s in skill["scripts"]:
            lines.append(f"- `{s}`")
        lines.append("")

    if skill["references"]:
        lines.append("## References locales")
        lines.append("")
        for r in skill["references"]:
            lines.append(f"- `reference/{r}`")
        lines.append("")

    if skill["related_skills"]:
        lines.append("## Skills lies")
        lines.append("")
        for r in skill["related_skills"]:
            lines.append(f"- `{r}`")
        lines.append("")

    if skill["prerequisites"]:
        lines.append("## Prerequis externes")
        lines.append("")
        for p in skill["prerequisites"]:
            lines.append(f"- {p}")
        lines.append("")

    return "\n".join(lines)


def _match_skill(skill: dict, term: str) -> bool:
    needle = term.lower()
    haystacks = [
        skill["name"],
        skill["description"],
        skill["summary"],
        skill["when_to_use"],
        skill["verb"],
        skill["workflow"],
        " ".join(skill["scripts"]),
        " ".join(skill["related_skills"]),
        " ".join(skill["prerequisites"]),
    ]
    return any(needle in h.lower() for h in haystacks)


def render_search(catalog: dict, term: str) -> str:
    matches = [s for s in catalog["skills"].values() if _match_skill(s, term)]
    if not matches:
        return f"Aucun skill trouve pour : `{term}`"
    lines = [f"# Recherche : `{term}` ({len(matches)} resultat(s))", ""]
    for skill in sorted(matches, key=lambda s: s["name"]):
        orch = " **[orchestrateur]**" if skill["is_orchestrator"] else ""
        lines.append(f"- **{skill['name']}**{orch} -- {skill['summary']}")
    lines.append("")
    lines.append("Pour plus de details : `query_catalog.py detail <nom>`")
    return "\n".join(lines)


def render_workflow(catalog: dict, wid: str) -> str:
    wf = next((w for w in catalog["workflows"] if w["id"] == wid), None)
    if not wf:
        return ""
    lines = [
        f"# Workflow : {wf['label']}",
        "",
        wf["description"],
        "",
        f"**{len(wf['skills'])} skill(s)** :",
        "",
    ]
    for name in wf["skills"]:
        skill = catalog["skills"][name]
        orch = " **[orchestrateur]**" if skill["is_orchestrator"] else ""
        lines.append(f"- **{name}**{orch} -- {skill['summary']}")
    return "\n".join(lines)


def render_verb(catalog: dict, verb: str) -> str:
    names = catalog["verbs"].get(verb)
    if not names:
        return ""
    lines = [f"# Verbe : `{verb}` ({len(names)} skill(s))", ""]
    for name in names:
        skill = catalog["skills"][name]
        lines.append(f"- **{name}** -- {skill['summary']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulte le catalog.json des skills DIVA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("overview", help="Panorama de tous les workflows")

    p_detail = sub.add_parser("detail", help="Fiche complete d'un skill")
    p_detail.add_argument("name", help="Nom du skill (ex: creating-diva-entity)")

    p_search = sub.add_parser("search", help="Recherche par mot-cle")
    p_search.add_argument("term", help="Terme a chercher")

    p_wf = sub.add_parser("workflow", help="Liste les skills d'un workflow")
    p_wf.add_argument("id", help="Id du workflow (analyze, create, modify, files, isam, validate, test_doc, reference)")

    p_verb = sub.add_parser("verb", help="Liste les skills d'un verbe")
    p_verb.add_argument("verb", help="Verbe (generating, reading, writing, managing, ...)")

    parser.add_argument("--json", action="store_true", help="Sortie JSON brut")
    args = parser.parse_args()

    catalog = load_catalog()

    if args.mode == "overview":
        payload = catalog if args.json else render_overview(catalog)
    elif args.mode == "detail":
        if args.name not in catalog["skills"]:
            print(f"ERREUR: skill inconnu : {args.name}", file=sys.stderr)
            available = sorted(catalog["skills"].keys())
            print(f"Skills disponibles : {', '.join(available)}", file=sys.stderr)
            return 1
        skill = catalog["skills"][args.name]
        payload = skill if args.json else render_detail(catalog, args.name)
    elif args.mode == "search":
        matches = [s for s in catalog["skills"].values() if _match_skill(s, args.term)]
        payload = matches if args.json else render_search(catalog, args.term)
    elif args.mode == "workflow":
        wf = next((w for w in catalog["workflows"] if w["id"] == args.id), None)
        if not wf:
            print(f"ERREUR: workflow inconnu : {args.id}", file=sys.stderr)
            ids = [w["id"] for w in catalog["workflows"]]
            print(f"Ids disponibles : {', '.join(ids)}", file=sys.stderr)
            return 1
        payload = wf if args.json else render_workflow(catalog, args.id)
    elif args.mode == "verb":
        if args.verb not in catalog["verbs"]:
            print(f"ERREUR: verbe inconnu : {args.verb}", file=sys.stderr)
            verbs = sorted(catalog["verbs"].keys())
            print(f"Verbes disponibles : {', '.join(verbs)}", file=sys.stderr)
            return 1
        payload = catalog["verbs"][args.verb] if args.json else render_verb(catalog, args.verb)
    else:
        parser.print_help()
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
