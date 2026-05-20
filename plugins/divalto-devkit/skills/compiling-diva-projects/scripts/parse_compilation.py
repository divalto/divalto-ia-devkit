#!/usr/bin/env python3
"""Parse un rapport de compilation xwin7 buildall.

Extrait la ligne de resume, les erreurs avec contexte, et les warnings.

Usage :
    py parse_compilation.py --path rapport.txt
    py parse_compilation.py --path rapport.txt --errors-only

Sortie JSON :
    {
        "file": "rapport.txt",
        "success": true,
        "summary": {
            "errors": 0,
            "warnings": 0,
            "diva": 42,
            "masques": 5,
            "dictionnaires": 3,
            "sql": 8,
            "objets_proteges": 0,
            "duree": "0:01:23"
        },
        "errors": [],
        "warnings": []
    }

Exit codes :
    0 = compilation reussie (0 erreur)
    1 = compilation echouee (erreurs trouvees)
    2 = erreur interne (rapport illisible)
"""

import argparse
import json
import os
import re
import sys


def parse_summary_line(line):
    """Parse la ligne de resume du rapport.

    Format attendu :
        Erreur(s)=0   Warning(s)=0   Diva=42   Masques=5   ...

    Returns:
        dict ou None si ligne non reconnue
    """
    summary = {}

    patterns = {
        "errors": r'Erreur\(s\)=(\d+)',
        "warnings": r'Warning\(s\)=(\d+)',
        "diva": r'Diva=(\d+)',
        "masques": r'Masques=(\d+)',
        "dictionnaires": r'Dictionnaires=(\d+)',
        "sql": r'Sql=(\d+)',
        "objets_proteges": r'Objets proteges=(\d+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, line)
        if match:
            summary[key] = int(match.group(1))

    if not summary:
        return None

    return summary


def parse_duration_line(line):
    """Parse la ligne de duree.

    Formats :
        Duree=H:M:S          (gros projet, sans accent)
        Dur\xe9e=H:M:S       (petit projet, avec accent e aigu ISO-8859-1)
        Durée=H:M:S          (petit projet, lu en ISO-8859-1 -> e accent)
    """
    match = re.search(r'Dur[eé\xe9]e=(\d+:\d+:\d+)', line)
    if match:
        return match.group(1)
    return None


def extract_errors(lines):
    """Extrait les erreurs avec contexte (1 ligne avant = fichier source).

    Returns:
        list of dict: [{line: N, message: "...", context: "...", file: "..."}]
    """
    errors = []
    error_pattern = re.compile(r'(^| |\])Erreur', re.IGNORECASE)

    for i, line in enumerate(lines):
        if error_pattern.search(line):
            context = lines[i - 1].strip() if i > 0 else ""
            # Tenter d'extraire le nom de fichier du contexte
            source_file = ""
            file_match = re.search(r'[\w]+\.(dhsp|dhsq|dhsd|dhsf|dhpt|dhps)', context)
            if file_match:
                source_file = file_match.group(0)

            errors.append({
                "line": i + 1,
                "message": line.strip(),
                "context": context,
                "source_file": source_file
            })

    return errors


# ---------------------------------------------------------------------------
# Diagnostic "Objet en dehors de la clip grille" (R-007 2026-04-23)
# ---------------------------------------------------------------------------

# L'erreur xwin7 "Objet en dehors de la clip grille" a deux causes possibles :
#   - max_X > nb_col * 4 (saturation largeur)
#   - max_Y > nb_lig * 14 (saturation hauteur)
# Le message brut ne dit pas laquelle. Ce module parse le .dhsf cible et compare
# les bornes pour emettre une cause probable.

CLIP_GRILLE_PATTERN = re.compile(
    r"(clip\s+grille|en dehors de la clip|hors\s+clip)",
    re.IGNORECASE,
)

_DHSF_PAGE_START = re.compile(r"^\s*\[page\]\s*$", re.IGNORECASE)
_DHSF_ATTR = re.compile(r"^\s*(\w+)\s*=\s*(.+?)\s*$")
_DHSF_PRESENTATION = re.compile(r"^\s*\[presentation\]\s*$", re.IGNORECASE)
_DHSF_NEXT_SEC = re.compile(r"^\s*\[")
_DHSF_POSITION = re.compile(r"position\s*=\s*(\d+)\s*,\s*(\d+)")
_DHSF_TAILLE = re.compile(r"taille\s*=\s*(\d+)\s*,\s*(\d+)")


def compute_dhsf_bounds(dhsf_path):
    """Pour un .dhsf, calcule les bornes max_X / max_Y par page et flags saturation.

    Lit le fichier en regex sans dependance au parseur complet (reste leger).
    Convention : position=Y,X et taille=H,L (cf reference/normes-graphiques.md).

    Returns:
        list[dict] : [{"page": N, "nb_col": int, "nb_lig": int,
                       "max_x": int, "max_y": int,
                       "bound_x": int, "bound_y": int,
                       "saturation_x": bool, "saturation_y": bool}, ...]
        ou None si fichier illisible.
    """
    try:
        with open(dhsf_path, encoding="iso-8859-1") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return None

    pages = []
    current_page = None

    i = 0
    while i < len(lines):
        line = lines[i]
        if _DHSF_PAGE_START.match(line):
            if current_page is not None:
                pages.append(current_page)
            current_page = {
                "page": 0, "nb_col": 0, "nb_lig": 0,
                "max_x": 0, "max_y": 0,
            }
            i += 1
            continue

        if current_page is None:
            i += 1
            continue

        # Attribut de page (numero, nb_col, nb_lig...)
        attr_m = _DHSF_ATTR.match(line)
        if attr_m and not line.lstrip().startswith("["):
            key = attr_m.group(1).lower()
            val = attr_m.group(2).strip().strip('"')
            if key == "numero" and val.isdigit():
                current_page["page"] = int(val)
            elif key == "nb_col" and val.isdigit():
                current_page["nb_col"] = int(val)
            elif key == "nb_lig" and val.isdigit():
                current_page["nb_lig"] = int(val)

        # Dans un [presentation], capturer position + taille
        if _DHSF_PRESENTATION.match(line):
            pos = None
            taille = None
            j = i + 1
            while j < len(lines):
                sub = lines[j]
                if _DHSF_NEXT_SEC.match(sub):
                    break
                pm = _DHSF_POSITION.search(sub)
                if pm:
                    pos = (int(pm.group(1)), int(pm.group(2)))
                tm = _DHSF_TAILLE.search(sub)
                if tm:
                    taille = (int(tm.group(1)), int(tm.group(2)))
                j += 1
            if pos and taille:
                max_y = pos[0] + taille[0]
                max_x = pos[1] + taille[1]
                if max_x > current_page["max_x"]:
                    current_page["max_x"] = max_x
                if max_y > current_page["max_y"]:
                    current_page["max_y"] = max_y
            i = j
            continue

        i += 1

    if current_page is not None:
        pages.append(current_page)

    for p in pages:
        p["bound_x"] = p["nb_col"] * 4 if p["nb_col"] else 0
        p["bound_y"] = p["nb_lig"] * 14 if p["nb_lig"] else 0
        p["saturation_x"] = bool(p["bound_x"]) and p["max_x"] > p["bound_x"]
        p["saturation_y"] = bool(p["bound_y"]) and p["max_y"] > p["bound_y"]

    return pages


def diagnose_clip_grille(error, base_dir=None):
    """Si l'erreur concerne 'clip grille' sur un .dhsf, emet un diagnostic X/Y.

    Args:
        error: dict d'erreur (output extract_errors)
        base_dir: repertoire dans lequel chercher le .dhsf (optionnel, defaut = repertoire courant)

    Returns:
        dict de diagnostic ou None si non applicable.
    """
    if not CLIP_GRILLE_PATTERN.search(error.get("message", "")):
        return None
    source = error.get("source_file", "")
    if not source.lower().endswith(".dhsf"):
        return None

    # Resoudre le chemin absolu : si relatif, tenter base_dir puis repertoire courant
    candidates = []
    if os.path.isabs(source):
        candidates.append(source)
    else:
        if base_dir:
            candidates.append(os.path.join(base_dir, source))
        candidates.append(source)
        candidates.append(os.path.join(os.getcwd(), source))

    dhsf_path = next((p for p in candidates if os.path.isfile(p)), None)
    if not dhsf_path:
        return {
            "issue": "clip_grille",
            "cause": "unknown",
            "detail": f"Fichier .dhsf '{source}' non localise (tente : {candidates}). "
                      "Specifier --dhsf-base-dir pour que le parser trouve le masque.",
        }

    pages = compute_dhsf_bounds(dhsf_path)
    if pages is None:
        return {
            "issue": "clip_grille",
            "cause": "unknown",
            "detail": f"Lecture du .dhsf '{dhsf_path}' a echoue.",
        }

    saturated = [p for p in pages if p["saturation_x"] or p["saturation_y"]]
    if not saturated:
        return {
            "issue": "clip_grille",
            "cause": "unknown",
            "detail": "Aucune saturation X/Y detectee dans les pages du masque. "
                      "Cause possible autre que les bornes de grille (ex : attache_lgx/lgy).",
            "pages": pages,
        }

    causes = set()
    for p in saturated:
        if p["saturation_x"]:
            causes.add("X")
        if p["saturation_y"]:
            causes.add("Y")
    cause = "X" if causes == {"X"} else ("Y" if causes == {"Y"} else "X+Y")

    details = []
    for p in saturated:
        bits = []
        if p["saturation_x"]:
            bits.append(f"max_X={p['max_x']} > nb_col*4={p['bound_x']}")
        if p["saturation_y"]:
            bits.append(f"max_Y={p['max_y']} > nb_lig*14={p['bound_y']}")
        details.append(f"page {p['page']}: " + ", ".join(bits))

    hint = {
        "X": "Reduire la largeur d'un objet (groupbox le plus probable) ou augmenter nb_col de la page.",
        "Y": "Reduire la hauteur d'un objet ou augmenter nb_lig de la page.",
        "X+Y": "Les deux axes depassent : verifier chaque page saturee separement.",
    }[cause]

    return {
        "issue": "clip_grille",
        "cause": cause,
        "detail": f"Saturation {cause} detectee. " + " | ".join(details),
        "hint": hint,
        "pages": saturated,
    }


def extract_warnings(lines):
    """Extrait les warnings du rapport.

    Returns:
        list of dict: [{line: N, message: "..."}]
    """
    warnings = []
    warning_pattern = re.compile(r'(^| |\])Warning', re.IGNORECASE)

    for i, line in enumerate(lines):
        if warning_pattern.search(line):
            # Exclure la ligne de resume (contient "Warning(s)=")
            if 'Warning(s)=' in line:
                continue
            context = lines[i - 1].strip() if i > 0 else ""
            warnings.append({
                "line": i + 1,
                "message": line.strip(),
                "context": context
            })

    return warnings


def parse_report(file_path, errors_only=False, dhsf_base_dir=None):
    """Parse un rapport de compilation complet.

    Args:
        file_path: chemin du fichier rapport
        errors_only: si True, ne retourne que les erreurs
        dhsf_base_dir: si fourni, utilise pour localiser les .dhsf mentionnes dans
            les erreurs "clip grille" et enrichir avec un diagnostic X/Y (R-007).

    Returns:
        dict: resultat structure
    """
    # Lire le fichier (rapport genere par xwin7, potentiellement en ISO-8859-1)
    try:
        with open(file_path, "r", encoding="iso-8859-1") as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Fichier introuvable : {file_path}"}
    except Exception as e:
        return {"error": f"Erreur lecture : {e}"}

    # Log vide = condition anormale. xwin7 ecrit TOUJOURS un resume
    # (Erreur(s)=N Warning(s)=M) quand il termine normalement.
    if not content.strip():
        return {
            "file": file_path,
            "success": False,
            "summary": {"errors": -1, "warnings": -1,
                         "message": "Log vide -- xwin7 n'a pas produit de resume. "
                                    "Verifier que la compilation a reellement eu lieu "
                                    "(profil correct, projet accessible)."},
            "errors": [],
            "warnings": []
        }

    lines = content.split("\n")

    # Chercher la ligne de resume (peut etre sur plusieurs lignes proches de la fin)
    summary = None
    duration = None

    for line in reversed(lines):
        if duration is None:
            duration = parse_duration_line(line)
        if summary is None:
            summary = parse_summary_line(line)
        if summary and duration:
            break

    if summary is None:
        # Verifier le format "abandon de la compilation"
        abandon = any(
            "abandon" in line.lower() and "compilation" in line.lower()
            for line in lines
        )
        if abandon:
            # Extraire le total_errors si present
            total_errors = 0
            for line in lines:
                te_match = re.search(r'\[TOTAL_ERRORS\](\d+)', line)
                if te_match:
                    total_errors = int(te_match.group(1))
                    break
            errors = extract_errors(lines)
            # Ajouter les lignes "Fichier ... absent" comme erreurs
            for i, line in enumerate(lines):
                if "absent ou inaccessible" in line.lower() or "abandon" in line.lower():
                    if not any(e["line"] == i + 1 for e in errors):
                        errors.append({
                            "line": i + 1,
                            "message": line.strip(),
                            "context": lines[i - 1].strip() if i > 0 else "",
                            "source_file": ""
                        })
            return {
                "file": file_path,
                "success": False,
                "summary": {"errors": len(errors), "warnings": 0,
                            "message": "Compilation abandonnee"},
                "errors": errors,
                "warnings": []
            }

        # Verifier le format "rien a compiler"
        up_to_date = any(
            "projet est" in line.lower() and "jour" in line.lower()
            for line in lines
        )
        if up_to_date:
            # Extraire le total_errors si present
            total_errors = 0
            for line in lines:
                te_match = re.search(r'\[TOTAL_ERRORS\](\d+)', line)
                if te_match:
                    total_errors = int(te_match.group(1))
                    break
            return {
                "file": file_path,
                "success": total_errors == 0,
                "summary": {"errors": total_errors, "warnings": 0, "message": "Le projet est a jour, aucune compilation a effectuer"},
                "errors": [],
                "warnings": []
            }

        return {
            "error": "Ligne de resume introuvable dans le rapport. "
                     "Verifier que le rapport est un fichier buildall xwin7."
        }

    if duration:
        summary["duree"] = duration

    # Extraire les erreurs
    errors = extract_errors(lines)

    # Filtrer les erreurs qui font partie de la ligne de resume
    errors = [e for e in errors if "Erreur(s)=" not in e["message"]]

    # Enrichir les erreurs "clip grille" avec un diagnostic X/Y (R-007 2026-04-23).
    # Non bloquant : si le .dhsf n'est pas localise, on ajoute une note explicative.
    for err in errors:
        diag = diagnose_clip_grille(err, base_dir=dhsf_base_dir)
        if diag is not None:
            err["diagnosis"] = diag

    # Extraire les warnings
    warnings = [] if errors_only else extract_warnings(lines)

    result = {
        "file": file_path,
        "success": summary.get("errors", -1) == 0,
        "summary": summary,
        "errors": errors,
    }

    if not errors_only:
        result["warnings"] = warnings

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Parse un rapport de compilation xwin7 buildall"
    )
    parser.add_argument(
        "--path", required=True,
        help="Chemin du fichier rapport de compilation"
    )
    parser.add_argument(
        "--errors-only", action="store_true",
        help="Ne retourner que les erreurs (pas les warnings)"
    )
    parser.add_argument(
        "--check-outputs", nargs="*", default=None,
        help="Fichiers compiles attendus (.dhop, .dhoq). Si log vide mais outputs presents avec timestamp recent, considerer comme succes (warning)."
    )
    parser.add_argument(
        "--dhsf-base-dir", default=None,
        help="Repertoire racine des .dhsf mentionnes par les erreurs. Si fourni, les erreurs 'clip grille' "
             "sont enrichies d'un diagnostic X/Y (comparaison max_X vs nb_col*4 et max_Y vs nb_lig*14)."
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Erreur : fichier introuvable : {args.path}", file=sys.stderr)
        sys.exit(2)

    result = parse_report(args.path, args.errors_only, dhsf_base_dir=args.dhsf_base_dir)

    # Si log vide et --check-outputs fourni, verifier les fichiers compiles
    # Un fichier compile valide fait au moins 2048 octets (1024B = stub vide = echec)
    MIN_COMPILED_SIZE = 2048
    if not result.get("success") and result.get("summary", {}).get("errors") == -1 and args.check_outputs:
        missing = []
        too_small = []
        for f in args.check_outputs:
            if not os.path.isfile(f):
                missing.append(f)
            elif os.path.getsize(f) < MIN_COMPILED_SIZE:
                too_small.append(f"{os.path.basename(f)} ({os.path.getsize(f)}B)")
        if not missing and not too_small:
            result["success"] = True
            result["summary"]["message"] = (
                "Log vide mais tous les fichiers compiles sont presents et valides. "
                "Compilation reussie."
            )
            result["summary"]["errors"] = 0
            result["summary"]["warnings"] = 0
        else:
            details = []
            if missing:
                details.append(f"Absents : {', '.join(os.path.basename(f) for f in missing)}")
            if too_small:
                details.append(f"Trop petits (< {MIN_COMPILED_SIZE}B, stub echec) : {', '.join(too_small)}")
            result["summary"]["message"] += " " + ". ".join(details)

    if "error" in result:
        print(f"Erreur : {result['error']}", file=sys.stderr)
        sys.exit(2)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
