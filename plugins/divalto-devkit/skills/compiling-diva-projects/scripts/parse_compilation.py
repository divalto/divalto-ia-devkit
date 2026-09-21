#!/usr/bin/env python3
"""Parse un rapport de compilation xwin7 buildall.

Extrait la ligne de resume, les erreurs avec contexte, et les warnings.

Usage :
    py parse_compilation.py --path rapport.txt
    py parse_compilation.py --path rapport.txt --errors-only

Deux formats de rapport reels (cf. les fixtures) :
  - build incremental : entete "[TOTAL_ERRORS]N" + lignes "[INFO]/[WARNING]/[ERROR]"
    (PAS de ligne francaise "Erreur(s)=" -- seul le buildall en produit une).
  - buildall complet   : idem + resume final "Erreur(s)=N Warning(s)=M Diva=.. ...".

Regle de verdict (success=true SEULEMENT si TOUT) : un resume dit 0 erreur (via
[TOTAL_ERRORS]0 ou Erreur(s)=0), ET aucune ligne [ERROR], ET aucune erreur HORS
compilation ("N ERREUR(S) autre(s)" / "absent ou inaccessible. Code=" -- souvent un
mauvais implicite, #310), ET pas d'interruption/abandon ("Compilation interrompue" /
"Construction du projet arretee" / "Fin anormale", #236). Un build interrompu affiche
"Erreur(s) 0" mais les objets ne sont PAS a jour -> jamais un succes.

Sortie JSON :
    {
        "file": "rapport.txt",
        "success": true,
        "summary": {"errors": 0, "warnings": 0, "diva": 42, ..., "duree": "0:01:23"},
        "errors": [],
        "warnings": [],
        "build_incomplet": true,     # present si build interrompu/abandonne (#236)
        "other_errors": [...],       # present si erreurs hors-compilation (#310)
        "up_to_date": true,          # present si "Le projet est a jour"
        "log_vide": true,            # present si le log est VIDE (xwin7 n'a rien produit) --
                                     # SEUL etat ou --check-outputs peut rattraper le verdict
        "summary_absent": true       # present si AUCUN resume reconnu ; summary.errors vaut
                                     # alors -1 = compteur INCONNU (jamais un marqueur d'etat)
    }

Exit codes :
    0 = compilation reussie (0 erreur, aucune anomalie)
    1 = compilation echouee / incomplete (erreurs, erreurs hors-compilation, interruption)
    2 = erreur interne (rapport illisible : ni [TOTAL_ERRORS] ni Erreur(s)=)
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
    """Extrait les erreurs avec contexte et fichier source.

    Le fichier source est cherche dans un ORDRE DE PRIORITE calque sur les formats
    reels de xwin7 (observes sur des rapports captures) :
      1. la ligne d'erreur ELLE-MEME  -- `[ERROR]/chemin/monentite.dhsp (7) Erreur 99 : ...`
      2. la ligne SUIVANTE si c'est la continuation `Fichier:... Ligne:N` de xwin7 --
         `[ERROR]Parametre manquant` / ` Fichier:.../harness.dhpt Ligne:16 Erreur numero 8`
      3. a defaut seulement, la ligne PRECEDENTE (`[INFO]<...monentite.dhsp> version : ...`)
    La ligne precedente est IGNOREE si c'est elle-meme une continuation `Fichier:` : elle
    appartient alors a l'erreur d'AVANT, et la reprendre attribuait silencieusement la 2e
    erreur au fichier de la 1re (mauvaise attribution sur erreurs consecutives).

    Returns:
        list of dict: [{line: N, message: "...", context: "...", source_file: "..."}]
    """
    errors = []
    error_pattern = re.compile(r'(^| |\])Erreur|\[ERROR\]', re.IGNORECASE)
    # Les lignes [WARNING]/[INFO]/[TOTAL_ERRORS] ne sont PAS des erreurs, meme si leur
    # texte contient le mot "erreur" (ex: un warning "Attention ! risque d'erreur") --
    # sinon faux positif qui casse le verdict.
    skip_pattern = re.compile(r'^\s*\[(WARNING|INFO|TOTAL_ERRORS)\]', re.IGNORECASE)
    # Un nom DIVA contient couramment des ESPACES ("gt_piece nouvellepiece.dhps",
    # "divalto achat-venteu.dhpt"). On tente donc d'abord la forme CHEMIN : ce qui suit le
    # dernier separateur, espaces compris. A defaut SEULEMENT, un nom nu (motif conservateur
    # sans espace -- sinon on avalerait la prose autour du nom).
    _EXT = r'(?:dhsp|dhsq|dhsd|dhsf|dhsi|dhpt|dhps)'
    file_path_re = re.compile(r'[/\\]([^/\\<>:"|*?]*\.' + _EXT + r')', re.IGNORECASE)
    file_bare_re = re.compile(r'[-\w]+\.' + _EXT, re.IGNORECASE)
    fichier_cont_re = re.compile(r'^\s*Fichier\s*:', re.IGNORECASE)

    def first_file(text):
        text = text or ""
        m = file_path_re.search(text)
        if m:
            return m.group(1).strip()
        m = file_bare_re.search(text)
        return m.group(0) if m else ""

    # Une ligne de CONTINUATION xwin7 (" Fichier:... Ligne:N Erreur numero 8") DECRIT
    # l'erreur precedente : ce n'est pas une erreur de plus. Sans ce filtre, une erreur
    # reelle en affichait 2 a 3 -> compteur gonfle pour l'agent (le verdict, lui, vient
    # du compteur du resume et n'etait pas affecte).
    prev_was_error = False
    for i, line in enumerate(lines):
        if skip_pattern.match(line):
            prev_was_error = False
            continue
        if prev_was_error and fichier_cont_re.match(line):
            continue          # continuation de l'erreur precedente, deja comptee
        if error_pattern.search(line):
            context = lines[i - 1].strip() if i > 0 else ""
            next_line = lines[i + 1] if i + 1 < len(lines) else ""

            source_file = first_file(line)                      # 1) la ligne d'erreur
            if not source_file and fichier_cont_re.match(next_line):
                source_file = first_file(next_line)             # 2) continuation "Fichier:"
            if not source_file and not fichier_cont_re.match(context):
                source_file = first_file(context)               # 3) contexte precedent

            errors.append({
                "line": i + 1,
                "message": line.strip(),
                "context": context,
                "source_file": source_file
            })
            prev_was_error = True
        else:
            prev_was_error = False

    return errors


# ---------------------------------------------------------------------------
# Diagnostic "Objet en dehors de la clip grille" (2026-04-23)
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
    Convention : position=Y,X et taille=H,L (cf. manipulating-dhsf-screens, reference/normes-graphiques.md).

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
    warning_pattern = re.compile(r'(^| |\])Warning|\[WARNING\]', re.IGNORECASE)

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


# --- Signaux de verdict (formats reels xwin7, cf. les fixtures) ---
# [TOTAL_ERRORS]N : resume "crochet", present sur build incremental ET buildall (1re classe).
TOTAL_ERRORS_RE = re.compile(r'\[TOTAL_ERRORS\](\d+)')
# "N ERREUR(S) autre(s) que des erreurs de compilation" : erreurs HORS compilation (#310).
OTHER_ERRORS_RE = re.compile(r'\d+\s+ERREUR\(S\)\s+autre', re.IGNORECASE)
# "... absent ou inaccessible. Code=0x14" : source/objet non resolu (mauvais implicite, #310).
ABSENT_RE = re.compile(r'absent ou inaccessible', re.IGNORECASE)
# Build INTERROMPU / abandonne : objets pas a jour -> jamais un succes, meme avec 0 erreur.
INTERRUPTED_RE = re.compile(
    r'compilation interrompue|construction du projet arr[e\xea]t|fin anormale|abandon de la compilation',
    re.IGNORECASE,
)
# "Le projet est a jour, aucune compilation a effectuer".
UP_TO_DATE_RE = re.compile(r'projet est\b.*\bjour', re.IGNORECASE)


def parse_report(file_path, errors_only=False, dhsf_base_dir=None):
    """Parse un rapport de compilation complet.

    Args:
        file_path: chemin du fichier rapport
        errors_only: si True, ne retourne que les erreurs
        dhsf_base_dir: si fourni, utilise pour localiser les .dhsf mentionnes dans
            les erreurs "clip grille" et enrichir avec un diagnostic X/Y.

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
            # Drapeau EXPLICITE : seul etat ou `--check-outputs` peut rattraper un verdict
            # (cf. main()). NE PAS se fier a `summary.errors == -1` pour le detecter : cette
            # sentinelle vaut AUSSI "aucun resume reconnu mais des signaux d'echec presents"
            # (cf. le repli plus bas), ce qui melangeait un log vide avec un build interrompu.
            "log_vide": True,
            "summary": {"errors": -1, "warnings": -1,
                         "message": "Log vide -- xwin7 n'a pas produit de resume. "
                                    "Verifier que la compilation a reellement eu lieu "
                                    "(profil correct, projet accessible)."},
            "errors": [],
            "warnings": []
        }

    lines = content.split("\n")

    # --- Signaux extraits du rapport (cf. regex de module ci-dessus) ---
    # 1) Resume "crochet" [TOTAL_ERRORS]N : source de 1re classe (le build incremental
    #    n'a PAS de ligne francaise "Erreur(s)=" -- seul le buildall en produit une).
    total_errors = None
    for line in lines:
        m = TOTAL_ERRORS_RE.search(line)
        if m:
            total_errors = int(m.group(1))
            break

    # 2) Resume francais "Erreur(s)=N Warning(s)=M ..." : buildall uniquement (fin normale).
    summary = None
    duration = None
    for line in reversed(lines):
        if duration is None:
            duration = parse_duration_line(line)
        if summary is None:
            summary = parse_summary_line(line)
        if summary and duration:
            break

    # 3) Interruption / abandon : un build interrompu affiche "Erreur(s) 0" mais les objets
    #    ne sont PAS a jour -> jamais un succes (capture reelle "Compilation interrompue"
    #    + #236 "Construction du projet arretee / Fin anormale").
    interrupted = any(INTERRUPTED_RE.search(line) for line in lines)

    # 4) Erreurs HORS compilation (#310) : "N ERREUR(S) autre(s)" + "absent ou inaccessible.
    #    Code=0x14". [TOTAL_ERRORS]0 les ignore -> faux positif de succes a bloquer.
    # Une ligne "[ERROR]" est une vraie erreur de COMPILATION (meme si elle mentionne
    # "absent" -- ex. include fatal) -> elle va dans `errors`, pas dans `other_errors`.
    other_errors = [line.strip() for line in lines
                    if (OTHER_ERRORS_RE.search(line) or ABSENT_RE.search(line))
                    and not line.lstrip().upper().startswith("[ERROR]")]

    up_to_date = any(UP_TO_DATE_RE.search(line) for line in lines)

    # 5) Erreurs de compilation detaillees ([ERROR]... / "Erreur NN : ..."), en excluant
    #    la ligne de resume, les erreurs hors-compilation et la ligne d'interruption
    #    (comptees a part).
    errors = extract_errors(lines)
    errors = [e for e in errors
              if "Erreur(s)=" not in e["message"]
              and not INTERRUPTED_RE.search(e["message"])
              and not ((OTHER_ERRORS_RE.search(e["message"]) or ABSENT_RE.search(e["message"]))
                       and not e["message"].lstrip().upper().startswith("[ERROR]"))]

    # --- Compte d'erreurs : priorite au resume francais, sinon [TOTAL_ERRORS] ---
    has_summary = (summary is not None) or (total_errors is not None)
    summary_absent = False
    if summary is not None:
        if duration:
            summary["duree"] = duration
        errors_count = summary.get("errors", -1)
    elif total_errors is not None:
        summary = {"errors": total_errors, "warnings": len(extract_warnings(lines))}
        if duration:
            summary["duree"] = duration
        errors_count = total_errors
    else:
        # `-1` = compteur INCONNU (aucun resume reconnu), PAS un marqueur d'etat.
        # NE JAMAIS tester `summary["errors"] == -1` pour deduire un etat : utiliser les
        # drapeaux explicites `log_vide` (log vraiment vide) et `summary_absent` (ici).
        # C'est ce raccourci qui rendait `--check-outputs` capable d'ecraser le verdict.
        summary = {"errors": -1, "warnings": -1}
        errors_count = None
        summary_absent = True

    # Aucun resume reconnu ET aucun signal d'erreur/interruption : rapport illisible.
    if not has_summary and not interrupted and not other_errors and not errors:
        return {
            "error": "Ligne de resume introuvable ([TOTAL_ERRORS] ni Erreur(s)=). "
                     "Verifier que le rapport est bien un fichier de compilation xwin7."
        }

    # --- Regle de verdict (validee + affinee sur des fixtures reelles) ---
    # Succes SEULEMENT si : un resume dit 0 erreur, AUCUNE erreur detaillee, AUCUNE erreur
    # hors-compilation (#310), PAS d'interruption/abandon.
    success = (
        has_summary
        and errors_count == 0
        and not errors
        and not other_errors
        and not interrupted
    )

    # Messages explicatifs
    msgs = []
    if interrupted:
        msgs.append("compilation INTERROMPUE/abandonnee : build INCOMPLET, les objets ne sont "
                    "pas tous a jour -- ne PAS considerer comme un succes malgre un compteur a 0")
    if other_errors:
        msgs.append(f"{len(other_errors)} erreur(s) HORS compilation (fichier/objet absent ou "
                    "inaccessible) -- souvent un mauvais implicite actif : verifier que "
                    "l'environnement charge correspond au workspace du .dhpt (#310/#161)")
    if up_to_date and success:
        msgs.append("Le projet est a jour, aucune compilation a effectuer")

    # Enrichir les erreurs "clip grille" avec un diagnostic X/Y. Non bloquant.
    for err in errors:
        diag = diagnose_clip_grille(err, base_dir=dhsf_base_dir)
        if diag is not None:
            err["diagnosis"] = diag

    result = {
        "file": file_path,
        "success": success,
        "summary": summary,
        "errors": errors,
    }
    if interrupted:
        result["build_incomplet"] = True
    if summary_absent:
        # Aucun resume reconnu : summary.errors vaut -1 (compteur INCONNU). Ce drapeau
        # evite a l'appelant de deduire l'etat depuis la valeur -1 (cf. commentaire plus haut).
        result["summary_absent"] = True
    if other_errors:
        result["other_errors"] = other_errors
    # up_to_date n'est emis que sur un vrai succes (a jour ET propre) : un "a jour"
    # accompagne d'erreurs hors-compilation (#310) est un FAUX a-jour -> pas d'emission.
    if up_to_date and success:
        result["up_to_date"] = True
    if msgs:
        result["summary"]["message"] = " | ".join(msgs)

    if not errors_only:
        result["warnings"] = extract_warnings(lines)

    return result


def main():
    # Sortie en UTF-8 (stdout + stderr) : sinon json.dump(ensure_ascii=False) encode avec la
    # console (cp1252 sur Windows) et les accents des messages [ERROR]/[WARNING] cassent un
    # json.loads(utf-8) cote appelant. Meme garde-fou que les scripts writing-diva-files.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
            _stream.reconfigure(encoding="utf-8")

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
        help="Fichiers compiles attendus (.dhop, .dhoq). Rattrapage UNIQUEMENT si le log est VIDE : "
             "si tous les fichiers existent et font >= 2048 octets, le verdict passe a succes. "
             "AUCUN controle de fraicheur (un objet perime d'un build anterieur satisfait le test). "
             "N'a aucun effet sur un log non vide : le verdict lu dans le log reste souverain."
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

    # Si log VIDE et --check-outputs fourni, verifier les fichiers compiles.
    # Un fichier compile valide fait au moins 2048 octets (1024B = stub vide = echec).
    #
    # GARDE-FOU : ce rattrapage est reserve au SEUL cas "log reellement vide"
    # (drapeau `log_vide` pose par parse_report). Il ne doit JAMAIS surcharger le verdict :
    # l'ancien test `summary.errors == -1` attrapait aussi les rapports SANS ligne de resume
    # mais AVEC des signaux d'echec ([ERROR], erreurs hors-compilation #310, build interrompu
    # #236) -> il rendait `success:true` sur un build INTERROMPU (avec `build_incomplet:true`
    # dans le meme JSON), soit exactement le faux positif que la regle de verdict interdit.
    MIN_COMPILED_SIZE = 2048
    if result.get("log_vide") and args.check_outputs:
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
            # .get() defensif : ne jamais transformer un diagnostic en traceback KeyError.
            base_msg = result["summary"].get("message", "")
            result["summary"]["message"] = (base_msg + " " + ". ".join(details)).strip()

    if "error" in result:
        print(f"Erreur : {result['error']}", file=sys.stderr)
        sys.exit(2)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
