#!/usr/bin/env python3
"""Scaffolde une surcharge masque .dhsf depuis le fichier standard.

A partir d'un .dhsf standard livre, ce script :
1. Lit le timestamp de l'en-tete (`;>xwin4obj 7.0 <TIMESTAMP>`)
2. Cree dans le repertoire de sortie deux fichiers :
   - `<base>u.dhsf` : copie du standard avec les 5 proprietes `[masque]` modifiees
     pour declarer la surcharge (cf. reference/dhsf-overwrite-pattern.md),
     PLUS la migration `[diva]` -> `[diva_base]` + derivation `[diva]` user
     depuis `[enregistrements]` (cf. reference/dhsf-overwrite-pattern.md section
     "Sections [diva] / [diva_base]")
   - `<base>_base.dhsf` : copie EXACTE du standard (compagnon, ne pas editer)
3. Preserve l'encodage ISO-8859-1 + CRLF

Modifications appliquees a `<base>u.dhsf` dans la section `[masque]` :
- AJOUTE   `surcharge=oui`
- AJOUTE   `date_modif_base="<TIMESTAMP_STANDARD>"`
- AJOUTE   `niveau_surcharge=1`
- REMPLACE `dernier_id=<N>` par `dernier_id=1000000`
- REMPLACE `dernier_id_page=<N>` par `dernier_id_page=100000`

Si une propriete existe deja avec une valeur differente (cas surcharge
preexistante), elle est mise a jour. Si elle est absente, elle est ajoutee
en tete du bloc `[masque]` (apres la ligne `[masque]`).

Migration `[diva]` -> `[diva_base]` (R-002 du batch 2026-05-27) :
- L'ancien bloc `[diva]...[/diva]` du standard est renomme en `[diva_base]...[/diva]`
- Un nouveau bloc `[diva]...[/diva]` est insere AVANT, contenant la **derivation
  lowercase** des records depuis la section `[enregistrements]` du masque
  (extensions `.dhsd` -> `Public Record`, `.dhoq`/`.dhsq` -> `Public RecordSql`).
- Sans cette migration, la compilation echoue avec erreur 210 sur les
  `Public Procedure` du `[diva]` standard preserve dans le masque user
  (cf. RETEX R-002 + biais R-031 invalide par R-033).

Ergonomie sortie AGL -- aspects cosmetiques DIFFERES (R-002 validation empirique) :
La comparaison bit-a-bit avec la sortie AGL revele 5 divergences cosmetiques,
fonctionnellement equivalentes mais source de bruit SVN au premier `Save` AGL :
1. `;>xwin4obj <ver> <timestamp>` -- la sortie AGL met la date de la modif vs
   la date du standard (le script copie la valeur standard tel quel)
2. `utilisateur` -- la sortie AGL met le user de la session vs le user du standard
3. `date_modification` -- la sortie AGL met la date courante vs la date du standard
4. Ordre des 3 proprietes surcharge dans `[masque]` -- AGL disperse (apres
   `dernier_id` / `dernier_id_page`) ; ce script les groupe en tete
5. Indentation -- AGL met un espace de tete devant `dernier_id` / `dernier_id_page`
Ces 5 points sont REPORTES a un SC futur cible -- le partenaire a confirme
qu'ils sont cosmetiques (le compilateur s'en moque). Quand l'AGL re-ouvre le
fichier produit par ce script, il re-normalise sans erreur.

Usage :
    py surcharge_mask.py --standard <chemin_standard.dhsf> --output-dir <dest>
    py surcharge_mask.py --standard <chemin>.dhsf --output-dir <dest> --niveau 2
    py surcharge_mask.py --standard <chemin>.dhsf --output-dir <dest> --user EBX13

Sortie JSON (stdout) :
    {
        "standard": "<chemin>",
        "user_mask": "<dest>/<base>u.dhsf",
        "base_mask": "<dest>/<base>_base.dhsf",
        "date_modif_base": "20211115165338",
        "niveau_surcharge": 1,
        "proprietes_modifiees": [...],
        "diva_migration": {
            "migrated": true,
            "derived_records_count": <N>,
            "derived_records": ["Public Record ...", ...]
        },
        "rappels": [...]
    }

Exit codes :
    0 = succes
    1 = erreur utilisateur (standard introuvable, nom invalide, ...)
    2 = erreur interne
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# En-tete xwin4obj : ;>xwin4obj   7.0   <TIMESTAMP>
HEADER_REGEX = re.compile(r"^;>xwin4obj\s+\S+\s+(\d{14})", re.IGNORECASE)

# Proprietes [masque] que l'on cherche / remplace (cle = nom propriete)
PROP_REGEX = {
    "dernier_id":      re.compile(r"^(dernier_id\s*=\s*)\d+", re.IGNORECASE),
    "dernier_id_page": re.compile(r"^(dernier_id_page\s*=\s*)\d+", re.IGNORECASE),
    "surcharge":       re.compile(r"^(surcharge\s*=\s*)\S+", re.IGNORECASE),
    "date_modif_base": re.compile(r'^(date_modif_base\s*=\s*)"[^"]*"', re.IGNORECASE),
    "niveau_surcharge":re.compile(r"^(niveau_surcharge\s*=\s*)\d+", re.IGNORECASE),
}

# Valeurs cibles pour la surcharge
TARGET_DERNIER_ID = 1000000
TARGET_DERNIER_ID_PAGE = 100000


def read_dhsf(path: Path) -> bytes:
    return path.read_bytes()


def write_dhsf(path: Path, raw: bytes) -> None:
    path.write_bytes(raw)


def extract_standard_timestamp(content: str) -> str | None:
    """Lit le timestamp du standard depuis l'en-tete `;>xwin4obj 7.0 <TS>`."""
    for line in content.splitlines():
        m = HEADER_REGEX.match(line.strip())
        if m:
            return m.group(1)
    return None


def derive_user_mask_name(standard_basename: str) -> str:
    """Calcule le nom du masque user : `<base>u.dhsf`.

    Exemple : `gtez000_sql.dhsf` -> `gtez000_sqlu.dhsf`
    """
    stem, ext = os.path.splitext(standard_basename)
    return f"{stem}u{ext}"


def derive_base_mask_name(standard_basename: str) -> str:
    """Calcule le nom du compagnon : `<base>_base.dhsf`.

    Exemple : `gtez000_sql.dhsf` -> `gtez000_sql_base.dhsf`
    """
    stem, ext = os.path.splitext(standard_basename)
    return f"{stem}_base{ext}"


# Pattern d'une ligne de [enregistrements] :
#   "<file.ext>",,<rec>,<alias>,<size>,<flag>
# (indentation tolere, guillemets autour de file uniquement, ',,' double virgule
#  signifie un champ vide intermediaire)
_ENR_LINE_RE = re.compile(
    r'^\s*"([^"]+)"\s*,\s*,\s*([^,\s]+)\s*,\s*([^,\s]+)\s*,',
    re.IGNORECASE,
)


def derive_diva_from_enregistrements(content: str) -> list[str]:
    """R-002 / R-033 -- derive le bloc `[diva]` user depuis `[enregistrements]`.

    Pour chaque ligne valide de `[enregistrements]` :
      - Extension `.dhsd` -> `Public Record "<file>" <rec> <alias>`
      - Extension `.dhoq` / `.dhsq` -> `Public RecordSql "<file>" <rec> <alias>`
      - Autres extensions ignorees (typiquement non observees)

    Tous les noms (file, rec, alias) sont mis en lowercase (datapoint canonique
    AGL : `[diva]` user en lowercase, cf. dhsf-overwrite-pattern.md section
    "Pattern [diva] user").

    Lignes commentaires (`;...`) et lignes vides ignorees.

    Retourne la liste ordonnee des lignes derivees (sans `[diva]` / `[/diva]`).
    """
    lines = content.split("\r\n")
    in_enr = False
    derived: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower() == "[enregistrements]":
            in_enr = True
            continue
        if in_enr and stripped.startswith("[") and stripped.endswith("]"):
            # Section [enregistrements] terminee
            break
        if not in_enr:
            continue
        if not stripped or stripped.startswith(";"):
            continue
        m = _ENR_LINE_RE.match(line)
        if not m:
            continue
        file_raw, rec, alias = m.group(1), m.group(2), m.group(3)
        ext = os.path.splitext(file_raw)[1].lower()
        if ext == ".dhsd":
            kind = "Record"
        elif ext in (".dhoq", ".dhsq"):
            kind = "RecordSql"
        else:
            # Extension inattendue -- on ignore (le linter du skill alertera)
            continue
        derived.append(
            f'Public {kind} "{file_raw.lower()}" {rec.lower()} {alias.lower()}'
        )
    return derived


def migrate_diva_to_base(content: str, derived_block: list[str]) -> tuple[str, dict]:
    """R-002 / R-033 -- migre `[diva]` -> `[diva_base]` et insere un nouveau `[diva]`.

    Mecanique :
    1. Repere le bloc `[diva]...[/diva]` existant (= standard preserve par la copie)
    2. Renomme la balise d'ouverture `[diva]` en `[diva_base]`
    3. Insere AVANT cet ancien bloc un nouveau bloc `[diva]\\n<derived>\\n[/diva]`

    Resultat attendu (cf. dhsf-overwrite-pattern.md) :
        [diva]
        Public Record "..." ...      ; derives lowercase depuis [enregistrements]
        ...
        [/diva]
        [diva_base]
        ;; Copie EXACTE du [diva] standard
        Public Record ...
        Public Procedure ...
        ...
        [/diva]

    Args :
        content        : contenu du fichier user a transformer
        derived_block  : sortie de derive_diva_from_enregistrements()

    Retourne (content_modifie, stats_dict). Si `[diva]` introuvable, retourne
    content inchange + stats avec `migrated=false`.
    """
    lines = content.split("\r\n")
    diva_open = None
    diva_close = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.lower() == "[diva]" and diva_open is None:
            diva_open = i
            continue
        if diva_open is not None and s.lower() == "[/diva]":
            diva_close = i
            break

    if diva_open is None or diva_close is None:
        return content, {
            "migrated": False,
            "reason": "Section [diva]...[/diva] introuvable dans le masque",
            "derived_records_count": 0,
            "derived_records": [],
        }

    # Renommer la balise d'ouverture du bloc existant en [diva_base]
    lines[diva_open] = "[diva_base]"

    # Construire le nouveau bloc [diva] (avec ligne vide finale avant [/diva]
    # pour preserver la convention de mise en forme observee dans la doc)
    new_diva_block = ["[diva]"] + derived_block + [""] + ["[/diva]"]

    # Inserer juste avant l'ancien bloc (devenu [diva_base])
    lines = lines[:diva_open] + new_diva_block + lines[diva_open:]

    return "\r\n".join(lines), {
        "migrated": True,
        "derived_records_count": len(derived_block),
        "derived_records": derived_block,
    }


def apply_surcharge_modifications(
    content: str, timestamp_standard: str, niveau: int
) -> tuple[str, list[dict]]:
    """Modifie la section `[masque]` pour declarer la surcharge.

    Retourne (content_modifie, liste_des_modifications_pour_rapport).
    """
    lines = content.split("\r\n")
    modifications: list[dict] = []

    # Localiser la section [masque] : entre la ligne `[masque]` et la prochaine `[...]` au top-level
    start = None
    end = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.lower() == "[masque]":
            start = i
            continue
        if start is not None and s.startswith("[") and s.endswith("]"):
            end = i
            break
    if start is None:
        raise ValueError("Section [masque] introuvable dans le fichier standard")
    if end is None:
        end = len(lines)

    # Trouver les proprietes existantes et leurs index
    existing: dict[str, int] = {}
    for i in range(start + 1, end):
        for key, pattern in PROP_REGEX.items():
            if pattern.match(lines[i].strip()):
                existing[key] = i
                break

    # Remplacements / ajouts cibles
    targets = {
        "surcharge":        ("surcharge=oui",                        "ajoute"),
        "date_modif_base":  (f'date_modif_base="{timestamp_standard}"', "ajoute"),
        "niveau_surcharge": (f"niveau_surcharge={niveau}",            "ajoute"),
        "dernier_id":       (f"dernier_id={TARGET_DERNIER_ID}",      "remplace"),
        "dernier_id_page":  (f"dernier_id_page={TARGET_DERNIER_ID_PAGE}", "remplace"),
    }

    # Phase 1 : remplacements (proprietes existantes)
    for key, (new_line, _action) in targets.items():
        if key in existing:
            idx = existing[key]
            old = lines[idx]
            lines[idx] = new_line
            modifications.append({
                "propriete": key, "action": "remplace",
                "avant": old.strip(), "apres": new_line,
            })

    # Phase 2 : ajouts (proprietes absentes) -- inseres juste apres [masque]
    insert_offset = start + 1
    for key, (new_line, _action) in targets.items():
        if key not in existing:
            lines.insert(insert_offset, new_line)
            modifications.append({
                "propriete": key, "action": "ajoute",
                "avant": None, "apres": new_line,
            })
            insert_offset += 1

    return "\r\n".join(lines), modifications


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffolde une surcharge masque .dhsf (cf. reference/dhsf-overwrite-pattern.md)"
    )
    parser.add_argument("--standard", required=True, help="Chemin du .dhsf standard a surcharger")
    parser.add_argument("--output-dir", required=True, help="Repertoire de sortie (typiquement <projet>/sources)")
    parser.add_argument("--niveau", type=int, default=1, help="Niveau de surcharge (1 par defaut, 2 = surcharge de surcharge)")
    parser.add_argument("--force", action="store_true", help="Ecraser les fichiers cibles s'ils existent")
    args = parser.parse_args()

    standard_path = Path(args.standard)
    output_dir = Path(args.output_dir)

    if not standard_path.is_file():
        print(f"ERREUR : fichier standard introuvable : {standard_path}", file=sys.stderr)
        sys.exit(1)

    if not output_dir.is_dir():
        print(f"ERREUR : repertoire de sortie introuvable : {output_dir}", file=sys.stderr)
        sys.exit(1)

    # Lecture du standard en mode binaire pour preserver l'encodage
    raw_standard = read_dhsf(standard_path)
    try:
        content_standard = raw_standard.decode("iso-8859-1")
    except UnicodeDecodeError as e:
        print(f"ERREUR : impossible de decoder en ISO-8859-1 : {e}", file=sys.stderr)
        sys.exit(2)

    # Verifier l'extension et la regle pos 3 = 'e'
    if not standard_path.name.lower().endswith(".dhsf"):
        print(f"ERREUR : extension '.dhsf' attendue, recue : '{standard_path.suffix}'", file=sys.stderr)
        sys.exit(1)
    stem = standard_path.stem
    if len(stem) < 4 or stem[2].lower() != "e":
        print(
            f"ERREUR : nom '{standard_path.name}' ne respecte pas la convention masque "
            f"(position 3 = '{stem[2] if len(stem) > 2 else '?'}', attendu 'e' invariant)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extraire le timestamp standard
    timestamp = extract_standard_timestamp(content_standard)
    if not timestamp:
        print(
            "ERREUR : timestamp de l'en-tete ';>xwin4obj 7.0 <TIMESTAMP>' introuvable. "
            "Le fichier standard est-il valide ?",
            file=sys.stderr,
        )
        sys.exit(1)

    # Calculer les noms de sortie
    user_mask_name = derive_user_mask_name(standard_path.name)
    base_mask_name = derive_base_mask_name(standard_path.name)
    user_mask_path = output_dir / user_mask_name
    base_mask_path = output_dir / base_mask_name

    for target in (user_mask_path, base_mask_path):
        if target.exists() and not args.force:
            print(f"ERREUR : fichier cible existe deja (utiliser --force) : {target}", file=sys.stderr)
            sys.exit(1)

    # Compagnon _base.dhsf : copie exacte du standard
    write_dhsf(base_mask_path, raw_standard)

    # Masque user : copie + modifications [masque]
    try:
        content_user, modifications = apply_surcharge_modifications(
            content_standard, timestamp, args.niveau
        )
    except ValueError as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        sys.exit(1)

    # Migration [diva] -> [diva_base] + derivation [diva] user (R-002)
    derived_block = derive_diva_from_enregistrements(content_user)
    content_user, diva_migration = migrate_diva_to_base(content_user, derived_block)

    write_dhsf(user_mask_path, content_user.encode("iso-8859-1"))

    rappels = [
        "Le compagnon _base.dhsf est gere par l'outillage : ne pas l'editer manuellement.",
        "Le masque user doit etre reference dans [fichiers] d'un .dhps de surcharge (xwin-s-sprojet).",
        "NE PAS lister le masque dans [sousprojets] du .dhpt parent (P17 de managing-diva-projects).",
    ]
    # Rappel diva selon resultat de la migration (R-002 + R-006)
    if diva_migration.get("migrated"):
        rappels.append(
            f"[INFO] Migration [diva] -> [diva_base] effectuee et [diva] user derive "
            f"depuis [enregistrements] ({diva_migration['derived_records_count']} record(s) "
            f"declare(s) en lowercase). Conforme au pattern documente dans "
            f"reference/dhsf-overwrite-pattern.md (sections [diva]/[diva_base])."
        )
    else:
        rappels.append(
            "[WARNING] Section [diva] standard non trouvee dans le masque -- migration NON effectuee. "
            "Verifier manuellement la structure [diva]/[diva_base] avant compilation. Cf. RETEX R-002 "
            "(erreur 210 systematique sur Public Procedure si la migration n'est pas faite)."
        )

    result = {
        "standard": str(standard_path),
        "user_mask": str(user_mask_path),
        "base_mask": str(base_mask_path),
        "date_modif_base": timestamp,
        "niveau_surcharge": args.niveau,
        "proprietes_modifiees": modifications,
        "diva_migration": diva_migration,
        "rappels": rappels,
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
