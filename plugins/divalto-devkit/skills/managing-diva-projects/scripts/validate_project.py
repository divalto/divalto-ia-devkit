#!/usr/bin/env python3
"""Valide la structure d'un fichier .dhpt ou .dhps Divalto.

Verifie les regles P01-P16 (anti-patterns projet).

Usage :
    py validate_project.py --path fichier.dhps
    py validate_project.py --path fichier.dhpt
    py validate_project.py --path fichier.dhps --dhpt parent.dhpt

Sortie JSON :
    {
        "file": "fichier.dhps",
        "type": "dhps",
        "valid": true,
        "errors": [],
        "warnings": [],
        "summary": {"sections": 5, "fichiers": 3, "includes": 5}
    }

Exit codes :
    0 = valide (0 erreur)
    1 = invalide (erreurs trouvees)
    2 = erreur interne
"""

import argparse
import json
import os
import re
import subprocess
import sys


# Sections obligatoires par type de fichier
DHPS_REQUIRED_SECTIONS = {"general", "fichiers", "includes", "autres"}
DHPT_REQUIRED_SECTIONS = {
    "general", "profildefaut", "sousprojets",
    "projetsfusion", "fabricationmere", "autres"
}


def detect_file_type(lines):
    """Detecte si le fichier est un .dhpt ou .dhps d'apres l'en-tete.

    Reconnait les 4 en-tetes valides :
    - `xwin-projet`    -> .dhpt standard
    - `xwin-s-projet`  -> .dhpt de surcharge
    - `xwin-sprojet`   -> .dhps standard
    - `xwin-s-sprojet` -> .dhps de surcharge
    """
    if not lines:
        return None
    header = lines[0].strip()
    # Ordre important : tester les variantes longues en premier
    if header.startswith("xwin-s-sprojet"):
        return "dhps"
    if header.startswith("xwin-sprojet"):
        return "dhps"
    if header.startswith("xwin-s-projet"):
        return "dhpt"
    if header.startswith("xwin-projet"):
        return "dhpt"
    return None


def is_surcharge_header(header):
    """True si l'en-tete designe une variante de surcharge (xwin-s-*)."""
    return header.startswith("xwin-s-projet") or header.startswith("xwin-s-sprojet")


def parse_sections(lines):
    """Parse les sections du fichier. Retourne {nom_section: [lignes]}."""
    sections = {}
    current = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r'^\[(\w+)\]$', stripped)
        if match:
            current = match.group(1)
            if current not in sections:
                sections[current] = []
        elif current is not None:
            sections.setdefault(current, []).append((i + 1, stripped))

    return sections


def check_encoding(file_path):
    """Verifie l'encodage du fichier avec file --mime-encoding."""
    errors = []
    warnings = []

    try:
        result = subprocess.run(
            ["file", "--mime-encoding", file_path],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip().lower()

        if "utf-8" in output:
            errors.append({
                "rule": "P01",
                "severity": "error",
                "message": f"Encodage UTF-8 detecte (attendu ISO-8859-1) : {output}"
            })
    except Exception:
        warnings.append({
            "rule": "P16",
            "severity": "warning",
            "message": "Impossible de verifier l'encodage avec file --mime-encoding"
        })

    # Verifier CRLF
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        if b"\r\n" not in raw and b"\n" in raw:
            errors.append({
                "rule": "P02",
                "severity": "error",
                "message": "Fins de ligne LF detectees (attendu CRLF)"
            })
    except Exception:
        pass

    return errors, warnings


def validate_dhps(lines, sections, file_path=None):
    """Valide un fichier .dhps. Retourne (errors, warnings)."""
    errors = []
    warnings = []

    # P04 : en-tete correct
    header = lines[0].strip() if lines else ""
    if header.startswith("xwin-projet") and not header.startswith("xwin-sprojet"):
        errors.append({
            "rule": "P04",
            "severity": "error",
            "message": "En-tete 'xwin-projet' dans un .dhps (attendu 'xwin-sprojet')"
        })

    # P12 : section [autres] obligatoire
    if "autres" not in sections:
        errors.append({
            "rule": "P12",
            "severity": "error",
            "message": "Section [autres] absente (obligatoire meme vide)"
        })

    # Sections obligatoires
    for sect in DHPS_REQUIRED_SECTIONS:
        if sect not in sections and sect != "autres":  # autres deja verifie
            errors.append({
                "rule": "P12",
                "severity": "error",
                "message": f"Section [{sect}] absente"
            })

    # P07 : syntaxe fic dans [fichiers] -- doit avoir ," "
    if "fichiers" in sections:
        for lineno, line in sections["fichiers"]:
            if line.startswith("fic="):
                if not re.match(r'^fic="[^"]+"(," "|,"<priv>\d+")', line):
                    errors.append({
                        "rule": "P07",
                        "severity": "error",
                        "message": f"Ligne {lineno} : syntaxe invalide dans [fichiers], "
                                   f'attendu fic="nom"," " : {line}'
                    })

    # P06 : syntaxe fic dans [includes] -- ne doit PAS avoir ," "
    if "includes" in sections:
        for lineno, line in sections["includes"]:
            if line.startswith("fic="):
                if '," "' in line or ',"<priv>' in line:
                    errors.append({
                        "rule": "P06",
                        "severity": "error",
                        "message": f"Ligne {lineno} : syntaxe invalide dans [includes], "
                                   f'fic="nom" sans virgule attendu : {line}'
                    })

    # P09 : zdiva.dhsp dans [includes]
    if "includes" in sections:
        has_zdiva = False
        for _, line in sections["includes"]:
            if "zdiva.dhsp" in line.lower():
                has_zdiva = True
                break
        if not has_zdiva:
            errors.append({
                "rule": "P09",
                "severity": "error",
                "message": "zdiva.dhsp absent de [includes] (obligatoire)"
            })

    # P10 : verification groupes communs (warning seulement)
    if "communs" not in sections or not sections["communs"]:
        warnings.append({
            "rule": "P10",
            "severity": "warning",
            "message": "Aucun groupe commun dans [communs] (verifier si des groupes sont necessaires)"
        })

    return errors, warnings


def validate_dhpt(lines, sections, file_path=None):
    """Valide un fichier .dhpt. Retourne (errors, warnings)."""
    errors = []
    warnings = []

    # P05 : en-tete correct
    header = lines[0].strip() if lines else ""
    if header.startswith("xwin-sprojet"):
        errors.append({
            "rule": "P05",
            "severity": "error",
            "message": "En-tete 'xwin-sprojet' dans un .dhpt (attendu 'xwin-projet')"
        })

    # P13 : sections obligatoires meme vides
    for sect in ["projetsfusion", "fabricationmere", "autres"]:
        if sect not in sections:
            errors.append({
                "rule": "P13",
                "severity": "error",
                "message": f"Section [{sect}] absente dans .dhpt (obligatoire meme vide)"
            })

    # Verifier [sousprojets]
    if "sousprojets" not in sections:
        errors.append({
            "rule": "P13",
            "severity": "error",
            "message": "Section [sousprojets] absente dans .dhpt"
        })
    else:
        # P07 : syntaxe fic dans [sousprojets]
        # P17 : aucune .dhps de surcharge (suffixe 'u') dans [sousprojets]
        for lineno, line in sections["sousprojets"]:
            if line.startswith("fic="):
                if not re.match(r'^fic="[^"]+"(," "|,"<priv>\d+")', line):
                    errors.append({
                        "rule": "P07",
                        "severity": "error",
                        "message": f"Ligne {lineno} : syntaxe invalide dans [sousprojets] : {line}"
                    })
                # P17 : detection nom xxxu.dhps
                m = re.match(r'^fic="([^"]+)"', line)
                if m:
                    fname = m.group(1)
                    stem, ext = os.path.splitext(fname)
                    if ext.lower() == ".dhps" and stem.endswith("u"):
                        errors.append({
                            "rule": "P17",
                            "severity": "error",
                            "message": (
                                f"Ligne {lineno} : .dhps de surcharge '{fname}' "
                                f"listee dans [sousprojets]. xwin7 la detecte "
                                f"automatiquement via cheminbases et leve 'ne "
                                f"peut etre charge directement' si elle est "
                                f"declaree. Retirer cette ligne."
                            )
                        })

    # P14/P15 : verification accent dans profil (si profil present)
    if "profil" in sections:
        for lineno, line in sections["profil"]:
            if line.startswith("nom="):
                if "developpement" in line.lower() and "\xe9" not in line and "é" not in line:
                    warnings.append({
                        "rule": "P14",
                        "severity": "warning",  # warning car on ne peut pas verifier l'octet exact en UTF-8
                        "message": f"Ligne {lineno} : 'developpement' sans accent (verifier encodage ISO-8859-1)"
                    })
            if line.startswith("implicites="):
                if "developpement" in line.lower() and "\xe9" not in line and "é" not in line:
                    warnings.append({
                        "rule": "P15",
                        "severity": "warning",
                        "message": f"Ligne {lineno} : nom implicites sans accent (verifier encodage ISO-8859-1)"
                    })

    return errors, warnings


def validate_cross_reference(dhps_name, dhpt_path):
    """Verifie qu'un .dhps est reference dans le [sousprojets] d'un .dhpt (P08)."""
    errors = []

    try:
        with open(dhpt_path, "r", encoding="iso-8859-1") as f:
            content = f.read()
    except Exception as e:
        return [{"rule": "P08", "severity": "error",
                 "message": f"Impossible de lire le .dhpt : {e}"}]

    lines = content.split("\n")
    sections = parse_sections(lines)

    if "sousprojets" not in sections:
        errors.append({
            "rule": "P08",
            "severity": "error",
            "message": f"{dhps_name} : section [sousprojets] absente du .dhpt"
        })
        return errors

    found = False
    for _, line in sections["sousprojets"]:
        if dhps_name in line:
            found = True
            break

    if not found:
        errors.append({
            "rule": "P08",
            "severity": "error",
            "message": f"{dhps_name} non reference dans [sousprojets] du .dhpt"
        })

    return errors


def count_entries(sections, section_name):
    """Compte les entrees fic= ou incl= dans une section."""
    if section_name not in sections:
        return 0
    count = 0
    for _, line in sections[section_name]:
        if line.startswith(("fic=", "incl=")):
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Valide la structure d'un fichier .dhpt ou .dhps"
    )
    parser.add_argument(
        "--path", required=True,
        help="Chemin du fichier .dhpt ou .dhps a valider"
    )
    parser.add_argument(
        "--dhpt", default=None,
        help="Chemin du .dhpt parent (pour validation croisee P08)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Erreur : fichier introuvable : {args.path}", file=sys.stderr)
        sys.exit(1)

    # Lire le fichier
    try:
        with open(args.path, "r", encoding="iso-8859-1") as f:
            content = f.read()
    except Exception as e:
        print(f"Erreur lecture : {e}", file=sys.stderr)
        sys.exit(2)

    lines = content.split("\n")
    file_type = detect_file_type(lines)

    if file_type is None:
        print("Erreur : en-tete non reconnu (ni xwin-projet ni xwin-sprojet)",
              file=sys.stderr)
        sys.exit(1)

    sections = parse_sections(lines)

    # Validation structurelle
    if file_type == "dhps":
        errors, warnings = validate_dhps(lines, sections, args.path)
    else:
        errors, warnings = validate_dhpt(lines, sections, args.path)

    # Validation encodage
    enc_errors, enc_warnings = check_encoding(args.path)
    errors.extend(enc_errors)
    warnings.extend(enc_warnings)

    # Validation croisee si .dhpt fourni et fichier est .dhps
    if args.dhpt and file_type == "dhps":
        dhps_name = os.path.basename(args.path)
        cross_errors = validate_cross_reference(dhps_name, args.dhpt)
        errors.extend(cross_errors)

    # Construire le resultat
    summary = {"sections": len(sections)}
    if file_type == "dhps":
        summary["fichiers"] = count_entries(sections, "fichiers")
        summary["includes"] = count_entries(sections, "includes")
        summary["communs"] = count_entries(sections, "communs")
    elif file_type == "dhpt":
        summary["sousprojets"] = count_entries(sections, "sousprojets")
        summary["communs_groups"] = sum(
            1 for _, line in sections.get("communs", [])
            if line.startswith("nom=")
        )
        summary["profils"] = sum(
            1 for _, line in sections.get("profil", [])
            if line.startswith("nom=")
        )

    result = {
        "file": args.path,
        "type": file_type,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": summary
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
