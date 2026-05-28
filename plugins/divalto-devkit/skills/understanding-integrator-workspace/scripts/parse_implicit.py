#!/usr/bin/env python3
"""
Parse un fichier implicite Divalto (R-2 + R-6 du skill understanding-integrator-workspace).

Lit un fichier implicite (typiquement `<DIVA_ROOT>/sys/<nom>.txt`), parse ligne par ligne
selon la grammaire R-6 (commentaires `;`, lignes vides, espaces strippes, casse
insensible), et produit en JSON la table des entrees typees.

Usage:
    py parse_implicit.py --path <chemin_du_fichier_implicite> --confirmed-by-user
    py parse_implicit.py --path <chemin> --encoding utf-8 --confirmed-by-user

Le flag `--confirmed-by-user` est OBLIGATOIRE : il materialise la confirmation
R-1/P-B (le collaborateur a explicitement valide le fichier implicite avant son
parsing). Sans le flag : warning sur stderr et exit code 3.

Types produits :
- "harmony_path"  : /<alias>/<segments...>
- "windows_path"  : <lettre>:\\<segments...>
- "sql_url"       : //<host>/<database>
- "comment"       : ligne commencant par ;
- "empty"         : ligne vide ou whitespace-only
- "unknown"       : ne matche aucun des patterns ci-dessus -> declenche un warning (P-A)

Exit codes :
    0 = succes, aucun "unknown"
    1 = au moins une ligne "unknown" detectee (P-A : demander au collaborateur)
    2 = erreur (fichier introuvable, probleme d'encodage)
    3 = --confirmed-by-user absent (R-1/P-B viole)
"""
import argparse
import json
import re
import sys
from pathlib import Path


def parse_line(raw_line: str, line_num: int) -> dict:
    """Classifie une ligne du fichier implicite selon R-6."""
    stripped = raw_line.strip()

    # Ligne vide
    if not stripped:
        return {"line": line_num, "raw": raw_line.rstrip(), "type": "empty"}

    # Commentaire
    if stripped.startswith(";"):
        return {"line": line_num, "raw": stripped, "type": "comment"}

    # URL SQL : //host/db (forme stricte, pas de port, pas de credentials)
    sql_match = re.match(r"^//([^/]+)/(.+?)/?$", stripped)
    if sql_match:
        return {
            "line": line_num,
            "raw": stripped,
            "type": "sql_url",
            "host": sql_match.group(1),
            "database": sql_match.group(2),
        }

    # Chemin Windows absolu : <lettre>:\segments (ou /segments)
    windows_match = re.match(r"^([A-Za-z]):[\\/](.*)$", stripped)
    if windows_match:
        return {
            "line": line_num,
            "raw": stripped,
            "type": "windows_path",
            "drive": windows_match.group(1).upper() + ":",
            "path": stripped,
        }

    # Chemin harmony : /<alias>/<segments>
    harmony_match = re.match(r"^/([^/]+)/?(.*)$", stripped)
    if harmony_match:
        alias = harmony_match.group(1)
        rest = harmony_match.group(2).rstrip("/")
        segments = rest.split("/") if rest else []
        return {
            "line": line_num,
            "raw": stripped,
            "type": "harmony_path",
            "alias": alias,
            "segments": segments,
        }

    # Aucun pattern reconnu -> P-A : demander au collaborateur
    return {"line": line_num, "raw": stripped, "type": "unknown"}


def main():
    parser = argparse.ArgumentParser(
        description="Parse un fichier implicite Divalto (R-2 + R-6 du skill "
        "understanding-integrator-workspace).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--path", required=True, help="Chemin du fichier implicite")
    parser.add_argument(
        "--encoding",
        default="iso-8859-1",
        help="Encodage du fichier (defaut: iso-8859-1 ; UTF-8 aussi valide per R-6 B1). "
        "Fallback automatique sur UTF-8 si l'encodage specifie echoue.",
    )
    parser.add_argument(
        "--confirmed-by-user",
        action="store_true",
        help=(
            "OBLIGATOIRE : confirme que le collaborateur a explicitement valide le "
            "fichier implicite passe en --path (R-1/P-B). Sans ce flag, le script "
            "refuse de demarrer (exit 3)."
        ),
    )
    args = parser.parse_args()

    # Garde-fou R-1/P-B : refuser le parsing sans confirmation explicite du fichier implicite
    if not args.confirmed_by_user:
        print(
            f"WARNING: Selection du fichier implicite '{args.path}' non confirmee "
            f"par l'utilisateur (R-1/P-B). Le skill understanding-integrator-workspace "
            f"exige que le fichier implicite soit confirme par le collaborateur avant "
            f"tout parsing. Relancer avec --confirmed-by-user apres validation explicite.",
            file=sys.stderr,
        )
        sys.exit(3)

    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: fichier introuvable : {path}", file=sys.stderr)
        sys.exit(2)

    # Lecture avec fallback d'encodage
    try:
        text = path.read_text(encoding=args.encoding)
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            print(
                f"ERROR: encodage non gere ({args.encoding} et utf-8 echouent) : {e}",
                file=sys.stderr,
            )
            sys.exit(2)

    # Split en lignes (preserve les fins de ligne strippees)
    raw_lines = text.splitlines()
    entries = [parse_line(line, i) for i, line in enumerate(raw_lines, start=1)]

    useful = [e for e in entries if e["type"] not in ("empty", "comment")]
    unknowns = [e for e in entries if e["type"] == "unknown"]

    output = {
        "implicit_file": str(path),
        "total_lines": len(entries),
        "useful_lines": len(useful),
        "entries": entries,
        "summary_by_type": {
            t: sum(1 for e in entries if e["type"] == t)
            for t in ("harmony_path", "windows_path", "sql_url", "comment", "empty", "unknown")
        },
    }

    if unknowns:
        output["warning_pa"] = (
            f"{len(unknowns)} ligne(s) de type 'unknown' detectee(s) -- "
            f"P-A : demander au collaborateur ce que sont ces lignes "
            f"(types non reconnus). Lignes concernees : "
            f"{[u['line'] for u in unknowns]}"
        )

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

    sys.exit(1 if unknowns else 0)


if __name__ == "__main__":
    main()
