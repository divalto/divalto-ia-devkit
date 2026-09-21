#!/usr/bin/env python3
"""Valide la structure d'un fichier .dhpt ou .dhps Divalto.

Verifie les regles PROJ01-PROJ17 (anti-patterns projet).

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

# Regles HORS du jeu par defaut : elles auditent une CONVENTION, pas un defaut.
# Leur constat n'est ni une erreur de compilation ni un dysfonctionnement.
# Activation explicite : --with-rules PROJ09[,...]
#
# NB -- semantique VOLONTAIREMENT differente du `--rules` de linting-diva-code, qui
# FILTRE (n'execute que les regles nommees). Ici `--with-rules` AJOUTE au jeu normal :
# un validateur structurel prive de ses controles de structure n'aurait aucun sens.
# Deux sens differents -> deux noms d'option differents.
REGLES_HORS_DEFAUT = {"PROJ09"}


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


def type_attendu(file_path):
    """Type deduit de l'EXTENSION du fichier : "dhpt", "dhps", ou None.

    C'est l'extension -- et non l'en-tete -- qui dit ce que le fichier DOIT etre.
    Router sur l'en-tete rendait PROJ04/PROJ05 structurellement inatteignables : le type
    etait deduit de la ligne meme qu'il fallait valider, donc un melange
    en-tete/extension etait invisible par construction (un .dhps portant
    `xwin-projet` etait valide comme un .dhpt et repondait valid=true).
    """
    ext = os.path.splitext(file_path)[1].lower()
    return {".dhpt": "dhpt", ".dhps": "dhps"}.get(ext)


def regle_active(rule_id, en_plus):
    """Une regle hors defaut ne s'execute que si --with-rules la nomme."""
    if rule_id not in REGLES_HORS_DEFAUT:
        return True
    return bool(en_plus) and rule_id in en_plus


# NB : fonction volontairement DUPLIQUEE dans add_to_project.py. Les deux scripts
# sont des CLI autonomes -- un import croise casserait celui qu'on copie seul.
def entete_est_surcharge_dhps(nom_dhps, dhpt_path):
    """True si la .dhps referencee porte l'en-tete de surcharge `xwin-s-sprojet`.

    Detection par l'EN-TETE, jamais par le suffixe `u` du nom de fichier. Le
    suffixe est une convention de nommage, pas un marqueur : sur un corpus reel
    de 2513 entrees `[sousprojets]`, le test `stem.endswith("u")` produisait
    **31 faux positifs et zero vrai positif** -- il flaguait `gt_menu.dhps`,
    `a5_menu.dhps`, `rc_cpt_bordereau.dhps`, `pp_zoom individu.dhps`,
    `...lieu.dhps`, `...fou.dhps`... c'est-a-dire tout mot finissant par `u`.

    Retourne False quand le fichier est introuvable : on ne peut pas savoir, et
    affirmer a tort coute plus cher que se taire (xwin7 signalera de toute facon
    une surcharge reellement declaree, au compile, de facon recuperable).
    """
    if not dhpt_path:
        return False
    cible = os.path.join(os.path.dirname(os.path.abspath(dhpt_path)),
                         os.path.basename(nom_dhps))
    if not os.path.isfile(cible):
        return False
    try:
        with open(cible, "r", encoding="iso-8859-1") as fh:
            entete = fh.readline().strip().lower()
    except OSError:
        return False
    return entete.startswith("xwin-s-sprojet")


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
                "rule": "PROJ01",
                "severity": "error",
                "message": f"Encodage UTF-8 detecte (attendu ISO-8859-1) : {output}"
            })
    except Exception:
        warnings.append({
            "rule": "PROJ16",
            "severity": "warning",
            "message": "Impossible de verifier l'encodage avec file --mime-encoding"
        })

    # Verifier CRLF
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        if b"\r\n" not in raw and b"\n" in raw:
            errors.append({
                "rule": "PROJ02",
                "severity": "error",
                "message": "Fins de ligne LF detectees (attendu CRLF)"
            })
    except Exception:
        pass

    return errors, warnings


def _diagnostic_entete(header, header_type, attendu_court, attendu_surcharge):
    """Message PROJ04/PROJ05 : nomme ce qu'on a trouve, pas seulement ce qu'on attendait."""
    if header_type is None:
        trouve = "en-tete non reconnu" if header else "premiere ligne vide"
    else:
        quoi = "PROJET" if header_type == "dhpt" else "SOUS-PROJET"
        if is_surcharge_header(header):
            quoi += " de surcharge"
        trouve = "en-tete de %s" % quoi
    return ("%s : %r (attendu %r, ou %r pour une surcharge)"
            % (trouve, header, attendu_court, attendu_surcharge))


def validate_dhps(lines, sections, file_path=None, header_type=None, en_plus=None):
    """Valide un fichier .dhps. Retourne (errors, warnings)."""
    errors = []
    warnings = []

    # PROJ04 : l'en-tete doit annoncer un SOUS-projet. Le type attendu vient de
    # l'extension (.dhps), pas de l'en-tete -- sinon le controle est tautologique.
    header = lines[0].strip() if lines else ""
    if header_type != "dhps":
        errors.append({
            "rule": "PROJ04",
            "severity": "error",
            "message": _diagnostic_entete(header, header_type,
                                          "xwin-sprojet", "xwin-s-sprojet")
                       + " -- fichier .dhps"
        })

    # PROJ12 : section [autres] obligatoire
    if "autres" not in sections:
        errors.append({
            "rule": "PROJ12",
            "severity": "error",
            "message": "Section [autres] absente (obligatoire meme vide)"
        })

    # Sections obligatoires
    for sect in DHPS_REQUIRED_SECTIONS:
        if sect not in sections and sect != "autres":  # autres deja verifie
            errors.append({
                "rule": "PROJ12",
                "severity": "error",
                "message": f"Section [{sect}] absente"
            })

    # PROJ07 : syntaxe fic dans [fichiers] -- doit avoir ," "
    if "fichiers" in sections:
        for lineno, line in sections["fichiers"]:
            if line.startswith("fic="):
                if not re.match(r'^fic="[^"]+"(," "|,"<priv>\d+")', line):
                    errors.append({
                        "rule": "PROJ07",
                        "severity": "error",
                        "message": f"Ligne {lineno} : syntaxe invalide dans [fichiers], "
                                   f'attendu fic="nom"," " : {line}'
                    })

    # PROJ06 : syntaxe fic dans [includes] -- ne doit PAS avoir ," "
    if "includes" in sections:
        for lineno, line in sections["includes"]:
            if line.startswith("fic="):
                if '," "' in line or ',"<priv>' in line:
                    errors.append({
                        "rule": "PROJ06",
                        "severity": "error",
                        "message": f"Ligne {lineno} : syntaxe invalide dans [includes], "
                                   f'fic="nom" sans virgule attendu : {line}'
                    })

    # PROJ09 : zdiva.dhsp dans [includes] -- CONVENTION, hors jeu par defaut.
    # Le standard X.13 livre ne le fait JAMAIS (0 / 2304 .dhps) alors qu'un
    # specifique le fait a 80-98 % : ce n'est pas une obligation. Activee par
    # defaut et en `error`, la regle rendait `valid:false` sur 100 % des
    # sous-projets du standard -- que l'on linte couramment comme modele.
    if "includes" in sections and regle_active("PROJ09", en_plus):
        has_zdiva = False
        for _, line in sections["includes"]:
            if "zdiva.dhsp" in line.lower():
                has_zdiva = True
                break
        if not has_zdiva:
            warnings.append({
                "rule": "PROJ09",
                "severity": "info",
                "message": ("zdiva.dhsp absent de [includes] -- convention de"
                            " projet : jamais present dans le standard livre"
                            " (0/2304 .dhps), usuel en specifique")
            })

    # PROJ10 : verification groupes communs (warning seulement)
    if "communs" not in sections or not sections["communs"]:
        warnings.append({
            "rule": "PROJ10",
            "severity": "warning",
            "message": "Aucun groupe commun dans [communs] (verifier si des groupes sont necessaires)"
        })

    return errors, warnings


def validate_dhpt(lines, sections, file_path=None, header_type=None, en_plus=None):
    """Valide un fichier .dhpt. Retourne (errors, warnings)."""
    errors = []
    warnings = []

    # PROJ05 : l'en-tete doit annoncer un PROJET (meme raisonnement que PROJ04).
    header = lines[0].strip() if lines else ""
    if header_type != "dhpt":
        errors.append({
            "rule": "PROJ05",
            "severity": "error",
            "message": _diagnostic_entete(header, header_type,
                                          "xwin-projet", "xwin-s-projet")
                       + " -- fichier .dhpt"
        })

    # PROJ13 : sections obligatoires meme vides
    for sect in ["projetsfusion", "fabricationmere", "autres"]:
        if sect not in sections:
            errors.append({
                "rule": "PROJ13",
                "severity": "error",
                "message": f"Section [{sect}] absente dans .dhpt (obligatoire meme vide)"
            })

    # Verifier [sousprojets]
    if "sousprojets" not in sections:
        errors.append({
            "rule": "PROJ13",
            "severity": "error",
            "message": "Section [sousprojets] absente dans .dhpt"
        })
    else:
        # PROJ07 : syntaxe fic dans [sousprojets]
        # PROJ17 : aucune .dhps de surcharge (suffixe 'u') dans [sousprojets]
        for lineno, line in sections["sousprojets"]:
            if line.startswith("fic="):
                if not re.match(r'^fic="[^"]+"(," "|,"<priv>\d+")', line):
                    errors.append({
                        "rule": "PROJ07",
                        "severity": "error",
                        "message": f"Ligne {lineno} : syntaxe invalide dans [sousprojets] : {line}"
                    })
                # PROJ17 : detection par l'EN-TETE de la .dhps referencee, pas par son nom.
                m = re.match(r'^fic="([^"]+)"', line)
                if m and entete_est_surcharge_dhps(m.group(1), file_path):
                    errors.append({
                        "rule": "PROJ17",
                        "severity": "error",
                        "message": (
                            f"Ligne {lineno} : .dhps de surcharge '{m.group(1)}' "
                            f"(en-tete 'xwin-s-sprojet') listee dans [sousprojets]. "
                            f"xwin7 la detecte automatiquement via cheminbases et "
                            f"leve 'ne peut etre charge directement' si elle est "
                            f"declaree. Retirer cette ligne."
                        )
                    })

    # PROJ14/PROJ15 : verification accent dans profil (si profil present)
    if "profil" in sections:
        for lineno, line in sections["profil"]:
            if line.startswith("nom="):
                if "developpement" in line.lower() and "\xe9" not in line and "é" not in line:
                    warnings.append({
                        "rule": "PROJ14",
                        "severity": "warning",  # warning car on ne peut pas verifier l'octet exact en UTF-8
                        "message": f"Ligne {lineno} : 'developpement' sans accent (verifier encodage ISO-8859-1)"
                    })
            if line.startswith("implicites="):
                if "developpement" in line.lower() and "\xe9" not in line and "é" not in line:
                    warnings.append({
                        "rule": "PROJ15",
                        "severity": "warning",
                        "message": f"Ligne {lineno} : nom implicites sans accent (verifier encodage ISO-8859-1)"
                    })

    return errors, warnings


def validate_cross_reference(dhps_name, dhpt_path):
    """Verifie qu'un .dhps est reference dans le [sousprojets] d'un .dhpt (PROJ08)."""
    errors = []

    try:
        with open(dhpt_path, "r", encoding="iso-8859-1") as f:
            content = f.read()
    except Exception as e:
        return [{"rule": "PROJ08", "severity": "error",
                 "message": f"Impossible de lire le .dhpt : {e}"}]

    lines = content.split("\n")
    sections = parse_sections(lines)

    if "sousprojets" not in sections:
        errors.append({
            "rule": "PROJ08",
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
            "rule": "PROJ08",
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
        help="Chemin du .dhpt parent (pour validation croisee PROJ08)"
    )
    parser.add_argument(
        "--with-rules", dest="with_rules", default=None,
        help=("Active EN PLUS du jeu normal des regles hors defaut "
              "(virgule, ex: PROJ09). A ne pas confondre avec le --rules de "
              "linting-diva-code, qui FILTRE au lieu d'ajouter.")
    )
    args = parser.parse_args()

    en_plus = set()
    if args.with_rules:
        en_plus = {r.strip().upper() for r in args.with_rules.split(",") if r.strip()}
        inconnues = en_plus - REGLES_HORS_DEFAUT
        if inconnues:
            print("Attention : regles ignorees par --with-rules (deja actives ou"
                  " inexistantes) : %s" % ", ".join(sorted(inconnues)),
                  file=sys.stderr)
            en_plus -= inconnues

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
    # Le type vient de l'EXTENSION. `detect_file_type` ne sert plus qu'a savoir ce
    # que l'en-tete ANNONCE, pour que PROJ04/PROJ05 puissent comparer les deux. Router sur
    # l'en-tete les rendait inatteignables (cf. type_attendu).
    file_type = type_attendu(args.path)
    header_type = detect_file_type(lines)

    if file_type is None:
        print("Erreur : extension non geree : %s (attendu .dhpt ou .dhps)"
              % os.path.splitext(args.path)[1], file=sys.stderr)
        sys.exit(2)

    sections = parse_sections(lines)

    # Validation structurelle
    if file_type == "dhps":
        errors, warnings = validate_dhps(lines, sections, args.path,
                                         header_type, en_plus)
    else:
        errors, warnings = validate_dhpt(lines, sections, args.path,
                                         header_type, en_plus)

    # Validation encodage
    enc_errors, enc_warnings = check_encoding(args.path)
    errors.extend(enc_errors)
    warnings.extend(enc_warnings)

    # Validation croisee si .dhpt fourni et fichier est .dhps
    # PROJ08 EXEMPTEE pour une .dhps de SURCHARGE (en-tete xwin-s-sprojet) : une surcharge
    # ne DOIT PAS figurer dans [sousprojets] (PROJ17 -- xwin7 l'auto-detecte via cheminbases).
    # Sans cette exemption, PROJ08 et PROJ17 se contredisent -> validation verte impossible sur
    # une surcharge pourtant correcte (issues #306 / #340). Detection par en-tete (autoritaire),
    # pas par suffixe 'u' (qui produirait des faux positifs : menu.dhps, bureau.dhps...).
    if args.dhpt and file_type == "dhps":
        dhps_header = lines[0].strip() if lines else ""
        # Test PRECIS : une .dhps de surcharge a l'en-tete 'xwin-s-sprojet'.
        # (is_surcharge_header() matcherait aussi 'xwin-s-projet' = en-tete de .dhpt,
        # sans interet ici -> on teste directement la variante .dhps.)
        if not dhps_header.startswith("xwin-s-sprojet"):
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
        "type_annonce_par_entete": header_type,
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
