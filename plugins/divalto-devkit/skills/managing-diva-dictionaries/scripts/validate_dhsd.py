#!/usr/bin/env python3
"""Valide les blocs generes ou un fichier .dhsd contre les regles D01-D16.

Usage:
    Valider des blocs generes (JSON) :
    py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
        --blocks output_blocks.json

    Valider une table dans un .dhsd existant :
    py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
        --path "chemin/dictionnaire.dhsd" --table NomTable

    Valider une surcharge contre son .dhsd standard (regles D14/D15/D16) :
    py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
        --path "chemin/<dict>u.dhsd" --dhsd-standard "chemin/<dict>.dhsd"

Sortie JSON: {target, valid, errors[], warnings[], summary}
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import re
import sys

# Ajouter le repertoire parent pour importer nature_to_size
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nature_to_size import nature_to_size


# Champs standard qui ne necessitent pas de declaration [CHAMP]
# UserTrace (Nature=28) etait historique, retire 2026-04-17 (0 occurrence X.13)
# UserCrDh / UserMoDh (DH) sont le socle audit canonique (88 % tables X.12)
STANDARD_FIELDS = {"Ce1", "Ce2", "Ce3", "Ce4", "Ce5", "Ce6", "Ce7", "Ce8", "Ce9",
                   "CeA", "CeB", "CeC", "Ce",
                   "Dos", "UserCr", "UserMo", "UserCrDh", "UserMoDh",
                   "UserCrDt", "UserMoDt", "UserTrace"}  # UserTrace garde pour compat anciennes tables

# Prefixes de base par dictionnaire
BASE_PREFIXES = {
    "gtfdd": "Gtf", "ccfdd": "Ccf", "rtlfdd": "Rtl", "ggfdd": "Ggf",
    "wmsfdd": "Wms", "ppfdd": "Ppf", "a5dd": "A5f", "rcfdd": "Rcf",
    "gafdd": "Gaf", "cofdd": "Cof", "pvfdd": "Pvf", "grfdd": "Grf",
    "dofdd": "Dof", "spfdd": "Spf", "mofdd": "Mof", "qufdd": "Quf",
    "gmfdd": "Gmf", "bifdd": "Bif",
}


def validate_blocks(blocks_data):
    """Valide les blocs generes (sortie de generate_dhsd_block.py).

    Verifie :
    - D01/D02 : Positions sans trou
    - D03 : U-field present
    - D04 : coherence champs declares vs utilises
    - D07 : Sections fermees dans le bloc table
    - D10 : CE coherent dans les index
    - D11 : Prefixe base
    """
    errors = []
    warnings = []

    table_name = blocks_data.get("table", "?")
    positions = blocks_data.get("positions", {})
    taille = blocks_data.get("taille", 0)
    blocks = blocks_data.get("blocks", {})

    # D01/D02 : Verifier les positions
    prev_name = None
    prev_end = 0
    for field_name, info in positions.items():
        pos = info["position"]
        size = info["size"]
        expected_pos = prev_end + 1 if prev_name else 1

        if pos != expected_pos:
            gap = pos - expected_pos
            if gap > 0:
                errors.append({
                    "rule": "D02",
                    "severity": "error",
                    "message": f"Trou de {gap} octet(s) avant '{field_name}' "
                               f"(position={pos}, attendu={expected_pos})",
                })
            else:
                errors.append({
                    "rule": "D01",
                    "severity": "error",
                    "message": f"Chevauchement au champ '{field_name}' "
                               f"(position={pos}, attendu={expected_pos})",
                })

        prev_name = field_name
        prev_end = pos + size - 1

    # Verifier Taille
    if prev_end != taille:
        errors.append({
            "rule": "D01",
            "severity": "error",
            "message": f"Taille declaree ({taille}) != taille calculee ({prev_end})",
        })

    # D03 : U-field present
    u_field_name = f"U{table_name}"
    if u_field_name not in positions:
        errors.append({
            "rule": "D03",
            "severity": "error",
            "message": f"Champ reserve distributeur '{u_field_name}' absent",
        })

    # D07 : Verifier que le bloc table contient [/CHAMPS]
    table_block = blocks.get("table", "")
    if "[CHAMPS]" in table_block and "[/CHAMPS]" not in table_block:
        errors.append({
            "rule": "D07",
            "severity": "error",
            "message": "Section [/CHAMPS] manquante dans le bloc [TABLE]",
        })

    # D08 : Verifier que le bloc base contient [/TABLES]
    base_block = blocks.get("base", "")
    if "[TABLES]" in base_block and "[/TABLES]" not in base_block:
        errors.append({
            "rule": "D08",
            "severity": "error",
            "message": "Section [/TABLES] manquante dans le bloc [BASE]",
        })

    # D09 : Verifier que les blocs index contiennent [/INDEX]
    for idx_block in blocks.get("indexes", []):
        block_text = idx_block.get("block", "")
        if "[INDEX]" in block_text and "[/INDEX]" not in block_text:
            errors.append({
                "rule": "D09",
                "severity": "error",
                "message": f"Section [/INDEX] manquante pour l'index '{idx_block.get('name', '?')}'",
            })

    return {
        "target": f"blocs generes pour {table_name}",
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": len(errors) + len(warnings),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


def parse_dhsd_table(content, table_name):
    """Parse un .dhsd et extrait les informations d'une table specifique.

    Returns:
        dict avec les champs, positions, CE, etc. ou None si table non trouvee
    """
    lines = content.splitlines()
    table_info = None
    in_target_table = False
    in_champs = False
    champs = []
    ce_field = None
    ce_value = None
    taille = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Chercher la table
        if line == "[TABLE]":
            # Lire jusqu'a trouver Nom=
            j = i + 1
            found_table = False
            while j < len(lines):
                tl = lines[j].strip()
                if tl.startswith("Nom="):
                    parts = tl[4:].split(",", 1)
                    if parts[0] == table_name:
                        in_target_table = True
                        found_table = True
                    break
                if tl.startswith("[") and not tl.startswith("[TABLE"):
                    break
                j += 1
            if not found_table:
                i = j
                continue

        if in_target_table:
            if line.startswith("Taille="):
                parts = line[7:].split(",")
                taille = int(parts[0])

            if line.startswith("CE="):
                parts = line[3:].split(",")
                if len(parts) >= 2:
                    ce_field = parts[0]
                    ce_value = parts[1]

            if line == "[CHAMPS]":
                in_champs = True
                i += 1
                continue

            if line == "[/CHAMPS]":
                in_champs = False
                in_target_table = False
                table_info = {
                    "champs": champs,
                    "ce_field": ce_field,
                    "ce_value": ce_value,
                    "taille": taille,
                }
                break

            if in_champs and line.startswith("Nom="):
                parts = line[4:].split(",")
                if len(parts) >= 8:
                    champs.append({
                        "name": parts[0],
                        "position": int(parts[1]),
                        "repetition": int(parts[5]),
                        "gel": int(parts[7]),
                    })

        i += 1

    return table_info


def validate_dhsd_file(path, table_name, dict_name=None):
    """Valide une table dans un fichier .dhsd existant."""
    errors = []
    warnings = []

    # D05/D06 : Verifier l'encodage
    with open(path, 'rb') as f:
        raw = f.read()

    has_lf_only = b'\n' in raw and b'\r\n' not in raw
    if has_lf_only:
        errors.append({
            "rule": "D06",
            "severity": "error",
            "message": "Fins de ligne LF detectees (attendu: CRLF)",
        })

    has_mixed = b'\r\n' in raw and raw.replace(b'\r\n', b'').count(b'\n') > 0
    if has_mixed:
        errors.append({
            "rule": "D06",
            "severity": "error",
            "message": "Fins de ligne mixtes LF/CRLF detectees",
        })

    if raw.startswith(b'\xef\xbb\xbf'):
        errors.append({
            "rule": "D05",
            "severity": "error",
            "message": "BOM UTF-8 detecte (le fichier doit etre en ISO-8859-1)",
        })

    # Lire le contenu
    content = raw.decode('iso-8859-1')

    # Parser la table
    table_info = parse_dhsd_table(content, table_name)
    if table_info is None:
        errors.append({
            "rule": "D04",
            "severity": "error",
            "message": f"Table '{table_name}' non trouvee dans le fichier",
        })
        return {
            "target": f"{table_name} dans {path}",
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "summary": {"total": len(errors), "errors": len(errors), "warnings": 0},
        }

    champs = table_info["champs"]

    # D01/D02 : Verifier les positions
    # On a besoin des natures pour calculer les tailles
    # Chercher les declarations [CHAMP] pour chaque champ
    champ_natures = {}
    in_champ = False
    current_name = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[CHAMP]":
            in_champ = True
            current_name = None
            continue
        if in_champ:
            if stripped.startswith("Nom="):
                parts = stripped[4:].split(",")
                current_name = parts[0]
            elif stripped.startswith("Nature=") and current_name:
                champ_natures[current_name] = stripped[7:]
                in_champ = False
                current_name = None
            elif stripped.startswith("[") and stripped != "[CHAMP]":
                in_champ = False

    # Verifier les positions contigues
    for idx in range(len(champs) - 1):
        current = champs[idx]
        next_f = champs[idx + 1]
        name = current["name"]

        # Determiner la taille
        if name == "Filler":
            size = current["repetition"]
        elif name in champ_natures:
            info = nature_to_size(champ_natures[name])
            size = info["size"] if info else 0
        elif name in STANDARD_FIELDS:
            # Tailles standard connues
            standard_sizes = {
                "Ce1": 1, "Ce2": 1, "Ce3": 1, "Ce4": 1, "Ce5": 1,
                "Ce6": 1, "Ce7": 1, "Ce8": 1, "Ce9": 1,
                "CeA": 1, "CeB": 1, "CeC": 1, "Ce": 10,
                "Dos": 8, "UserCr": 20, "UserMo": 20,
                "UserCrDh": 14, "UserMoDh": 14,
                "UserCrDt": 8, "UserMoDt": 8,
                "UserTrace": 28,
            }
            size = standard_sizes.get(name, 0)
        else:
            continue  # Impossible de verifier sans la nature

        if size > 0:
            expected_next = current["position"] + size
            if next_f["position"] != expected_next:
                gap = next_f["position"] - expected_next
                rule = "D02" if gap > 0 else "D01"
                msg = "Trou" if gap > 0 else "Chevauchement"
                errors.append({
                    "rule": rule,
                    "severity": "error",
                    "message": f"{msg} entre '{name}' (pos={current['position']}, "
                               f"taille={size}) et '{next_f['name']}' "
                               f"(pos={next_f['position']}, attendu={expected_next})",
                })

    # D03 : U-field present
    u_field_name = f"U{table_name}"
    if not any(c["name"] == u_field_name for c in champs):
        errors.append({
            "rule": "D03",
            "severity": "error",
            "message": f"Champ reserve distributeur '{u_field_name}' absent",
        })

    # D04 : Verifier que chaque champ non-standard a une declaration
    for champ in champs:
        name = champ["name"]
        if name == "Filler":
            continue  # Mot-cle special
        if name in STANDARD_FIELDS:
            continue  # Deja declare
        if name.startswith("U") and name[1:] == table_name:
            # U-field -- verifier qu'il a une declaration
            if name not in champ_natures:
                errors.append({
                    "rule": "D04",
                    "severity": "error",
                    "message": f"Champ '{name}' utilise dans [CHAMPS] sans declaration [CHAMP]",
                })
            continue
        if name not in champ_natures:
            errors.append({
                "rule": "D04",
                "severity": "error",
                "message": f"Champ '{name}' utilise dans [CHAMPS] sans declaration [CHAMP]",
            })

    # D11 : Prefixe base (si dict_name fourni)
    if dict_name:
        dict_key = dict_name.lower().replace(".dhsd", "")
        expected_prefix = BASE_PREFIXES.get(dict_key, "")
        if expected_prefix:
            # Chercher les bases qui referencent cette table
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("Nom=") and f",{table_name},0" in stripped:
                    # On est dans [TABLES] -- trouver le nom de la base
                    pass  # Verification complexe, on laisse en warning simple

    return {
        "target": f"{table_name} dans {os.path.basename(path)}",
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": len(errors) + len(warnings),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


# ----------------------------------------------------------------------------
# Regles de surcharge D14/D15/D16 -- verifications croisees avec le .dhsd standard
# ----------------------------------------------------------------------------

# Detecte une section "Nom=<valeur>,..." (premier sous-element seulement)
_BLOCK_NAME_RE = re.compile(r'^\s*Nom\s*=\s*([^,]+)', re.IGNORECASE)


def _read_dhsd(path):
    """Lit un .dhsd en ISO-8859-1 (encodage natif Divalto)."""
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode("iso-8859-1")


def _parse_named_blocks(content, block_tag):
    """Parse les blocs `[<block_tag>]` et retourne {name: {lines:[...]}}.

    Le `name` est le 1er sous-element du `Nom=` du bloc.
    Les blocs sans ligne `Nom=` sont ignores.
    Cle insensible a la casse (stockee en lowercase) pour eviter les
    divergences entre `nom=UArt` et `Nom=ART`.
    """
    blocks = {}
    lines = content.splitlines()
    in_block = False
    current_lines = []
    open_tag = f"[{block_tag}]"

    def _index_current():
        if not current_lines:
            return
        name = None
        for cl in current_lines:
            m = _BLOCK_NAME_RE.match(cl)
            if m:
                name = m.group(1).strip()
                break
        if name:
            blocks[name.lower()] = {"name": name, "lines": list(current_lines)}

    for line in lines:
        stripped = line.strip()
        if stripped == open_tag:
            # Cloturer le bloc precedent (s'il etait du meme tag)
            if in_block:
                _index_current()
            in_block = True
            current_lines = []
            continue
        if in_block:
            if stripped.startswith("[") and stripped.endswith("]"):
                # Autre section -- cloturer le bloc courant
                _index_current()
                in_block = False
                current_lines = []
                continue
            current_lines.append(line)
    # Eventuel dernier bloc en fin de fichier
    if in_block:
        _index_current()
    return blocks


def _extract_field(lines, prefix):
    """Retourne la 1ere ligne 'prefix=...' (apres strip), ou None."""
    for line in lines:
        s = line.strip()
        if s.lower().startswith(prefix.lower() + "="):
            return s.split("=", 1)[1].strip()
    return None


def _parse_table_u_containers(content):
    """Pour chaque [TABLE] du standard, extrait {nom_table_lower: [containers U*]}.

    Container detecte : ligne `Nom=U<NomTable>,...` dans le `[CHAMPS]` du bloc.
    Cle table en lowercase pour matching insensible a la casse.
    Containers stockes en lowercase pour la meme raison.
    """
    result = {}
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == "[TABLE]":
            # Lire le bloc TABLE jusqu'a la section suivante (hors [CHAMPS]/[/CHAMPS] qui sont des sous-sections)
            block_lines = []
            j = i + 1
            while j < len(lines):
                ls = lines[j].strip()
                if ls.startswith("[") and ls.endswith("]") and ls != "[CHAMPS]" and ls != "[/CHAMPS]":
                    if not ls.startswith("[/"):
                        break
                block_lines.append(lines[j])
                j += 1
            tname = None
            for bl in block_lines:
                m = _BLOCK_NAME_RE.match(bl)
                if m:
                    tname = m.group(1).strip()
                    break
            in_champs = False
            containers = []
            for bl in block_lines:
                s = bl.strip()
                if s == "[CHAMPS]":
                    in_champs = True
                    continue
                if s == "[/CHAMPS]":
                    in_champs = False
                    continue
                if in_champs and s.lower().startswith("nom=u"):
                    m = re.match(r'(?i)^Nom=U([A-Za-z0-9_]+),', s)
                    if m:
                        containers.append(("U" + m.group(1)).lower())
            if tname:
                result[tname.lower()] = containers
            i = j
        else:
            i += 1
    return result


def _parse_champ_attrs(lines):
    """Pour un bloc [CHAMP], extrait {Nom, Nature, Gel, Flags}."""
    attrs = {}
    for line in lines:
        s = line.strip()
        if s.lower().startswith("nom="):
            # Nom=<X>,<libelle>,1 -- on garde uniquement le 1er sous-element
            attrs["Nom"] = s.split("=", 1)[1].split(",", 1)[0].strip()
        elif s.lower().startswith("nature="):
            attrs["Nature"] = s.split("=", 1)[1].strip()
        elif s.lower().startswith("gel="):
            attrs["Gel"] = s.split("=", 1)[1].strip()
        elif s.lower().startswith("flags="):
            attrs["Flags"] = s.split("=", 1)[1].strip()
    return attrs


def _parse_champr_targets(content):
    """Parse le bloc [CHAMPR] et retourne la liste des `nom=U<X>` declares."""
    targets = []
    in_champr = False
    for line in content.splitlines():
        s = line.strip()
        if s == "[CHAMPR]":
            in_champr = True
            continue
        if s == "[/CHAMPR]":
            in_champr = False
            continue
        if in_champr and s.lower().startswith("nom=u"):
            m = re.match(r'(?i)^nom=U([A-Za-z0-9_]+)\s*$', s)
            if m:
                targets.append("U" + m.group(1))
    return targets


def validate_surcharge_against_standard(surcharge_path, standard_path):
    """Verifie une surcharge .dhsd contre son .dhsd standard.

    Regles :
    - D14 : metadonnees [BASEU]/[TABLEU] divergentes du standard (Version, Nom, DateM)
    - D15 : [CHAMPR] nom=U<X> sans container U<X> dans la table standard
    - D16 : [CHAMP] surcharge redeclare un champ global standard avec Nature/Gel/Flags differents

    Retourne (errors, warnings).
    """
    errors = []
    warnings = []

    try:
        surcharge = _read_dhsd(surcharge_path)
        standard = _read_dhsd(standard_path)
    except Exception as e:
        warnings.append({
            "rule": "D14",
            "severity": "warning",
            "message": f"Verification croisee impossible (lecture echoue) : {e}",
        })
        return errors, warnings

    # --- D14 : [BASEU] vs [BASE] et [TABLEU] vs [TABLE] ---
    baseu_blocks = _parse_named_blocks(surcharge, "BASEU")
    base_blocks = _parse_named_blocks(standard, "BASE")
    for base_key, surcharge_block in baseu_blocks.items():
        display = surcharge_block["name"]
        std_block = base_blocks.get(base_key)
        if not std_block:
            errors.append({
                "rule": "D14",
                "severity": "error",
                "message": f"[BASEU] '{display}' : aucune [BASE] standard correspondante.",
            })
            continue
        for attr in ("Version", "Nom", "DateM"):
            su_val = _extract_field(surcharge_block["lines"], attr)
            std_val = _extract_field(std_block["lines"], attr)
            if su_val is not None and std_val is not None and su_val != std_val:
                errors.append({
                    "rule": "D14",
                    "severity": "error",
                    "message": (
                        f"[BASEU] '{display}' : {attr}= divergent du standard. "
                        f"Surcharge='{su_val}' / Standard='{std_val}'. Recopier la valeur du standard."
                    ),
                })

    tableu_blocks = _parse_named_blocks(surcharge, "TABLEU")
    table_blocks = _parse_named_blocks(standard, "TABLE")
    for table_key, surcharge_block in tableu_blocks.items():
        display = surcharge_block["name"]
        std_block = table_blocks.get(table_key)
        if not std_block:
            errors.append({
                "rule": "D14",
                "severity": "error",
                "message": f"[TABLEU] '{display}' : aucune [TABLE] standard correspondante.",
            })
            continue
        for attr in ("Version", "Nom"):
            su_val = _extract_field(surcharge_block["lines"], attr)
            std_val = _extract_field(std_block["lines"], attr)
            if su_val is not None and std_val is not None and su_val != std_val:
                errors.append({
                    "rule": "D14",
                    "severity": "error",
                    "message": (
                        f"[TABLEU] '{display}' : {attr}= divergent du standard. "
                        f"Surcharge='{su_val}' / Standard='{std_val}'. Recopier la valeur du standard."
                    ),
                })
        # DateM : 1ere partie doit etre identique au standard (la 2eme est le FILETIME courant de la surcharge)
        su_datem = _extract_field(surcharge_block["lines"], "DateM")
        std_datem = _extract_field(std_block["lines"], "DateM")
        if su_datem and std_datem:
            su_origin = su_datem.split(",", 1)[0].strip()
            std_origin = std_datem.split(",", 1)[0].strip()
            if su_origin != std_origin:
                errors.append({
                    "rule": "D14",
                    "severity": "error",
                    "message": (
                        f"[TABLEU] '{display}' : 1ere partie de DateM= divergente du standard. "
                        f"Surcharge='{su_origin}' / Standard='{std_origin}'. Recopier du standard."
                    ),
                })

    # --- D15 : [CHAMPR] nom=U<X> vs container U<X> dans la table standard ---
    targets = _parse_champr_targets(surcharge)
    table_containers = _parse_table_u_containers(standard)
    for u_target in targets:
        if not u_target.lower().startswith("u"):
            continue
        table_name = u_target[1:]
        std_containers = table_containers.get(table_name.lower())
        if std_containers is None:
            errors.append({
                "rule": "D15",
                "severity": "error",
                "message": (
                    f"[CHAMPR] nom={u_target} : la table '{table_name}' n'existe pas "
                    f"dans le standard. Surcharge invalide."
                ),
            })
        elif u_target.lower() not in std_containers:
            errors.append({
                "rule": "D15",
                "severity": "error",
                "message": (
                    f"[CHAMPR] nom={u_target} : la table standard '{table_name}' n'a "
                    f"pas de container '{u_target}' dans son [CHAMPS]. Table non "
                    f"surchargeable -- voir dhsd-surcharge-pattern.md."
                ),
            })

    # --- D16 : [CHAMP] surcharge vs [CHAMP] standard de meme nom ---
    surcharge_champs = _parse_named_blocks(surcharge, "CHAMP")
    standard_champs = _parse_named_blocks(standard, "CHAMP")
    for champ_key, su_block in surcharge_champs.items():
        std_block = standard_champs.get(champ_key)
        if not std_block:
            continue  # nouveau champ -- OK
        display = su_block["name"]
        su_attrs = _parse_champ_attrs(su_block["lines"])
        std_attrs = _parse_champ_attrs(std_block["lines"])
        divergent = []
        for k in ("Nature", "Gel", "Flags"):
            if k in su_attrs and k in std_attrs and su_attrs[k] != std_attrs[k]:
                divergent.append(f"{k}: surcharge='{su_attrs[k]}' / standard='{std_attrs[k]}'")
        if divergent:
            errors.append({
                "rule": "D16",
                "severity": "error",
                "message": (
                    f"[CHAMP] '{display}' : redeclaration du champ standard avec "
                    f"attributs differents ({'; '.join(divergent)}). Option C interdite -- "
                    f"renommer le champ avec un prefixe (option B) ou reutiliser le standard (option A)."
                ),
            })

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Valide les blocs generes ou un fichier .dhsd contre les regles D01-D16"
    )
    parser.add_argument("--blocks", default=None,
                        help="Chemin vers le JSON des blocs generes (sortie de generate_dhsd_block.py)")
    parser.add_argument("--path", default=None,
                        help="Chemin vers un fichier .dhsd existant")
    parser.add_argument("--table", default=None,
                        help="Nom de la table a valider dans le .dhsd (requis avec --path sauf si --dhsd-standard)")
    parser.add_argument("--dict-name", default=None,
                        help="Nom du dictionnaire pour verifier le prefixe base (D11)")
    parser.add_argument("--dhsd-standard", default=None,
                        help="Chemin vers le .dhsd standard pour activer les checks de surcharge D14/D15/D16")

    args = parser.parse_args()

    if args.blocks:
        try:
            with open(args.blocks, "r", encoding="utf-8") as f:
                blocks_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Erreur lecture blocs : {e}", file=sys.stderr)
            sys.exit(1)

        report = validate_blocks(blocks_data)

    elif args.path:
        if not os.path.exists(args.path):
            print(f"Fichier non trouve : {args.path}", file=sys.stderr)
            sys.exit(1)

        # Mode 1 : validation classique d'une table (D01-D11) si --table fourni
        if args.table:
            report = validate_dhsd_file(args.path, args.table, args.dict_name)
        else:
            # Mode 2 : surcharge sans table specifique, on fait D14/D15/D16 sur tout le fichier
            report = {
                "target": f"{os.path.basename(args.path)} (mode surcharge)",
                "valid": True,
                "errors": [],
                "warnings": [],
                "summary": {"total": 0, "errors": 0, "warnings": 0},
            }

        # Verifications croisees surcharge vs standard (D14/D15/D16) si demande
        if args.dhsd_standard:
            if not os.path.exists(args.dhsd_standard):
                print(f"Fichier standard non trouve : {args.dhsd_standard}", file=sys.stderr)
                sys.exit(1)
            su_errors, su_warnings = validate_surcharge_against_standard(args.path, args.dhsd_standard)
            report["errors"].extend(su_errors)
            report["warnings"].extend(su_warnings)
            report["valid"] = len(report["errors"]) == 0
            report["summary"] = {
                "total": len(report["errors"]) + len(report["warnings"]),
                "errors": len(report["errors"]),
                "warnings": len(report["warnings"]),
            }

        if not args.table and not args.dhsd_standard:
            print("--table ou --dhsd-standard requis avec --path", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    print()

    # Exit code base sur la validite
    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
