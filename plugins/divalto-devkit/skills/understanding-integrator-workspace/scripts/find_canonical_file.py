#!/usr/bin/env python3
"""
Trouve la version canonique d'un fichier pour un workspace integrateur Divalto
(R-13 du skill understanding-integrator-workspace).

A partir d'un fichier implicite et d'un nom de fichier, parcourt les chemins
declares dans le search path **dans l'ordre** et retourne le premier hit.
Ne tombe JAMAIS sur un find aveugle dans un tree "Standard generique".

Usage:
    py find_canonical_file.py --implicit <chemin_implicite> --file <nom_fichier> --confirmed-by-user
    py find_canonical_file.py --implicit <chemin> --file <nom> --recursive --confirmed-by-user

Le flag `--confirmed-by-user` est OBLIGATOIRE : il materialise la confirmation
R-1/P-B (le collaborateur a explicitement valide le fichier implicite). Sans le
flag : warning sur stderr et exit code 3.

Output JSON:
    {
      "file": "<nom_fichier>",
      "implicit_file": "<chemin>",
      "diva_root": "<chemin>",
      "search_path": [
        {"line": N, "harmony": "...", "resolved": "...", "source": "cfg|fconfig|registry"},
        ...
      ],
      "found": true|false,
      "canonical_path": "<chemin_absolu>" | null,
      "hit_in_line": N | null,
      "hit_source": "cfg|fconfig|registry" | null
    }

Exit codes :
    0 = fichier trouve
    1 = fichier introuvable dans le search path (P-A : signaler, ne pas chercher ailleurs)
    2 = erreur (implicite introuvable, resolution impossible)
    3 = --confirmed-by-user absent (R-1/P-B viole)
"""
import argparse
import json
import sys
from pathlib import Path

# Import du module utilitaire frere
sys.path.insert(0, str(Path(__file__).parent))
from _resolver import discover_diva_root, parse_divaltopath_cfg, resolve_harmony_path  # noqa: E402


def parse_implicit_lines(path: Path, encoding: str = "iso-8859-1") -> list:
    """Parse le fichier implicite et retourne la liste des entrees non-comment/empty."""
    try:
        text = path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8")

    entries = []
    for i, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith(";"):
            continue
        # SQL URL : ignore pour la recherche filesystem
        if stripped.startswith("//"):
            continue
        entries.append({"line": i, "raw": stripped})
    return entries


def search_file_in_dir(directory: Path, filename: str, recursive: bool) -> Path | None:
    """Cherche un fichier par nom dans un dossier (recursif si demande)."""
    if not directory.is_dir():
        return None
    if recursive:
        for found in directory.rglob(filename):
            if found.is_file():
                return found
        return None
    else:
        candidate = directory / filename
        return candidate if candidate.is_file() else None


def main():
    parser = argparse.ArgumentParser(
        description="Trouve la version canonique d'un fichier pour un workspace "
        "integrateur (R-13).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--implicit", required=True, help="Chemin du fichier implicite confirme")
    parser.add_argument("--file", required=True, help="Nom du fichier a chercher (sans chemin)")
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Cherche recursivement sous chaque chemin du search path (defaut: True)",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Desactive la recherche recursive",
    )
    parser.add_argument(
        "--confirmed-by-user",
        action="store_true",
        help=(
            "OBLIGATOIRE : confirme que le collaborateur a explicitement valide le "
            "fichier implicite passe en --implicit (R-1/P-B). Sans ce flag, le script "
            "refuse de demarrer (exit 3)."
        ),
    )
    args = parser.parse_args()

    # Garde-fou R-1/P-B : refuser la recherche sans confirmation explicite du fichier implicite
    if not args.confirmed_by_user:
        print(
            f"WARNING: Selection du fichier implicite '{args.implicit}' non confirmee "
            f"par l'utilisateur (R-1/P-B). Le skill understanding-integrator-workspace "
            f"exige que le fichier implicite soit confirme par le collaborateur avant "
            f"toute resolution de fichier canonique. Relancer avec --confirmed-by-user "
            f"apres validation explicite.",
            file=sys.stderr,
        )
        sys.exit(3)

    implicit_path = Path(args.implicit)
    if not implicit_path.is_file():
        print(f"ERROR: fichier implicite introuvable : {implicit_path}", file=sys.stderr)
        sys.exit(2)

    # R-5 : decouvrir DIVA_ROOT
    info = discover_diva_root()
    if "error" in info:
        print(f"ERROR R-5 : {info['error']}", file=sys.stderr)
        sys.exit(2)
    diva_root = info["diva_root"]
    fconfig_dhfd = Path(info["fconfig_dhfd"]) if info.get("fconfig_dhfd") else None

    # R-3 : parse divaltopath.cfg
    cfg_path = Path(diva_root) / "sys" / "divaltopath.cfg"
    cfg = parse_divaltopath_cfg(cfg_path)
    if "error" in cfg:
        print(f"WARNING R-3 : {cfg['error']} (poursuite avec R-4 seul)", file=sys.stderr)
        cfg_aliases = {}
    else:
        cfg_aliases = cfg["aliases"]

    # R-2 : parse implicit
    entries = parse_implicit_lines(implicit_path)

    # Resoudre chaque ligne -> liste search path ordonnee
    search_path = []
    for entry in entries:
        raw = entry["raw"]
        # Chemin Windows absolu : utilise tel quel
        if raw[:2].lower() in ("c:", "d:", "e:", "f:", "g:", "h:") and (raw[2] in "\\/"):
            search_path.append(
                {"line": entry["line"], "harmony": raw, "resolved": raw, "source": "absolute"}
            )
            continue
        # Chemin harmony
        if raw.startswith("/"):
            res = resolve_harmony_path(raw, cfg_aliases, fconfig_dhfd, diva_root)
            if "resolved" in res:
                search_path.append(
                    {
                        "line": entry["line"],
                        "harmony": raw,
                        "resolved": res["resolved"],
                        "source": res["source"],
                    }
                )
            else:
                search_path.append(
                    {
                        "line": entry["line"],
                        "harmony": raw,
                        "resolved": None,
                        "error": res.get("error", "resolution failed"),
                    }
                )

    # Recherche du fichier dans l'ordre
    hit = None
    for sp_entry in search_path:
        resolved = sp_entry.get("resolved")
        if not resolved:
            continue
        found = search_file_in_dir(Path(resolved), args.file, args.recursive)
        if found:
            hit = {
                "canonical_path": str(found),
                "hit_in_line": sp_entry["line"],
                "hit_harmony": sp_entry["harmony"],
                "hit_source": sp_entry.get("source"),
            }
            break

    output = {
        "file": args.file,
        "implicit_file": str(implicit_path),
        "diva_root": diva_root,
        "search_path": search_path,
        "found": hit is not None,
    }
    if hit:
        output.update(hit)
    else:
        output["canonical_path"] = None
        output["warning_pa"] = (
            f"Fichier '{args.file}' introuvable dans le search path du workspace. "
            f"P-A : NE PAS chercher dans un dossier 'Standard generique' hors search path. "
            f"Demander au collaborateur."
        )

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

    sys.exit(0 if hit else 1)


if __name__ == "__main__":
    main()
