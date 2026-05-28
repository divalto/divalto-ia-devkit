"""
generate_surcharge_field.py -- Prototype

Ajoute un champ a une table standard DIVA via surcharge dictionnaire.

Operation deterministe : a partir de (dictionnaire standard, nom de table,
nom de champ, Nature, libelle, user, prefixe poste), le script :
  1. Parse le .dhsd standard pour extraire les metadonnees [TABLE] et [BASE]
     correspondantes (Version, DateM, libelle) -- garantit D14.
  2. Verifie que le U-container `U<NomTable>` existe et lit sa Nature
     (capacite octets) -- garantit D15.
  3. Si mode --append-to : parse le .dhsd surcharge existant, identifie les
     champs deja ancres sur le U-container cible, calcule l'offset cumule
     atteint.
  4. Verifie que la capacite residuelle >= taille du nouveau champ.
  5. Calcule un FILETIME courant (little-endian hex).
  6. Genere le bloc de surcharge (header [Dictionnaire] + [CHAMP] global
     + [CHAMPR]/[CHAMPL] + [TABLEU] + [BASEU]) ou enrichit l'existant.
  7. Ecrit en ISO-8859-1 + CRLF.
  8. Retourne un JSON detaillant l'operation, l'offset retenu, la capacite
     residuelle, et un pointeur vers les lignes source du standard utilisees
     (tracabilite D14).

Usage :
    py generate_surcharge_field.py \
        --dhsd-standard "C:/divalto/.../gtfdd.dhsd" \
        --table T143 \
        --field-name dgsTrajetKmMax \
        --nature 5,0 \
        --label "Plafond km deplacement" \
        --user rootDGS \
        --prefix dgs \
        (--output "C:/.../fichiers/gtfddu.dhsd"
         | --append-to "C:/.../fichiers/gtfddu.dhsd")

Sortie :
    JSON sur stdout. Exit 0 = succes, 1 = validation echoue, 2 = erreur.

Note prefixe poste : il n'existe AUCUNE regle universelle pour identifier
un champ specifique depuis son nom. Selon les postes, le prefixe peut etre
1, 2 ou 3 caracteres (`m*`, `mi*`, `dgs*`, `eco*`), ou meme absent (champ
en PascalCase pur, identique en surface au standard). Le script ne fait
donc AUCUNE validation de forme sur le prefixe. Si `--prefix` est passe,
le script verifie juste que le nom du champ commence par cette chaine
(garde-fou anti-typo de frappe). Si `--prefix` est absent, n'importe quel
nom est accepte. La doctrine est : le caller (humain ou LLM) DOIT
connaitre la convention de poste OU son absence.
"""

import argparse
import datetime
import json
import re
import struct
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Nature -> taille en octets
# ---------------------------------------------------------------------------

def nature_size(nature: str) -> int:
    """Calcule la taille en octets d'une Nature DIVA."""
    n = nature.strip()
    if not n:
        raise ValueError("Nature vide")
    # Nature numerique "N,M" ou "N,DM"
    if ',' in n:
        size_part = n.split(',', 1)[0].strip()
        if not size_part.isdigit():
            raise ValueError(f"Nature numerique invalide : '{nature}' (partie avant virgule non numerique)")
        return int(size_part)
    # Nature speciale Date+Heure
    if n == 'DH':
        return 14
    # Nature Date "D8" ou Heure "H6"
    m = re.match(r'^([DH])(\d+)$', n)
    if m:
        return int(m.group(2))
    # Nature simple entier
    if n.isdigit():
        return int(n)
    raise ValueError(f"Nature non supportee par ce prototype : '{nature}' (etendre nature_size si besoin)")


# ---------------------------------------------------------------------------
# FILETIME courant en hex little-endian
# ---------------------------------------------------------------------------

def now_filetime_hex_le() -> str:
    """Genere un FILETIME Windows (100ns ticks depuis 1601-01-01 UTC) en hex little-endian 16 chars."""
    now = datetime.datetime.now(datetime.timezone.utc)
    epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
    ticks = int((now - epoch).total_seconds() * 10_000_000)
    return struct.pack('<Q', ticks).hex().upper()


def now_aaaammjjhhmmss() -> str:
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')


# ---------------------------------------------------------------------------
# Parser .dhsd minimaliste (section-based)
# ---------------------------------------------------------------------------

class DhsdDoc:
    """Vue parsee d'un .dhsd : tables, bases, champs globaux."""

    def __init__(self, path: Path, lines: list):
        self.path = path
        self.lines = lines  # liste de lignes sans CRLF
        self.tables = []  # [{name, label, version_line, datem_line, nomodbc, fields_lines: [...], start_line, end_line}]
        self.bases = []   # [{name, label, version_line, datem_line, fichier, datemindex, tables: [name], start_line, end_line}]
        self.global_champs = {}  # name_lower -> {name, label, version_line, gel, nature, flags, nomodbc, line_index}


def parse_dhsd(path: Path) -> DhsdDoc:
    """Parse un .dhsd en structures Python exploitables."""
    with path.open('r', encoding='iso-8859-1', newline='') as f:
        raw = f.read()
    # Normaliser fins de ligne pour le parsing (on conserve raw pour reecriture si besoin)
    lines = raw.replace('\r\n', '\n').split('\n')
    doc = DhsdDoc(path, lines)

    section = None       # 'TABLE' | 'BASE' | 'CHAMP' | None
    current = None       # dict en cours
    in_champs = False    # inside [CHAMPS]/[/CHAMPS] of a TABLE
    in_tables = False    # inside [TABLES]/[/TABLES] of a BASE

    def close_section():
        nonlocal current, section
        if current is None:
            return
        current['end_line'] = i  # ligne actuelle
        if section == 'TABLE':
            doc.tables.append(current)
        elif section == 'BASE':
            doc.bases.append(current)
        elif section == 'CHAMP':
            name = current.get('name')
            if name:
                doc.global_champs[name.lower()] = current
        current = None
        section = None

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        ls = line.strip()
        if not ls:
            continue
        # En-tete de section
        if ls.startswith('[') and ls.endswith(']'):
            tag = ls[1:-1]
            if tag in ('TABLE', 'BASE', 'CHAMP'):
                close_section()
                section = tag
                current = {'start_line': i + 1, 'fields_lines': []}
                in_champs = False
                in_tables = False
                continue
            if tag == 'CHAMPS':
                # CHAMPS apparait dans [TABLE] (standard). Si current est None
                # (on n'est pas dans un [TABLE] track), on ignore.
                if current is not None and section == 'TABLE':
                    in_champs = True
                continue
            if tag == '/CHAMPS':
                in_champs = False
                continue
            if tag == 'TABLES':
                # TABLES apparait dans [BASE] (standard) ET dans [BASEU] (surcharge,
                # generalement vide). Si current=None (section non-track), ignorer.
                if current is not None and section == 'BASE':
                    in_tables = True
                    current.setdefault('tables', [])
                continue
            if tag == '/TABLES':
                in_tables = False
                continue
            # Autre section ([PROPLOC], [INDEX], [TABLEU], [BASEU], [CHAMPR], [CHAMPL], ...) :
            # on ferme la section active. Les sections de surcharge ne sont pas trackees
            # par ce parser (le calcul d'offset cumule consomme directement le fichier
            # via consumed_offset_in_container).
            close_section()
            continue
        if current is None:
            continue
        # Lignes a l'interieur d'un [CHAMPS] de table
        if in_champs and section == 'TABLE':
            if ls.startswith('Nom='):
                current['fields_lines'].append((i + 1, ls))
            continue
        # Lignes a l'interieur d'un [TABLES] de base
        if in_tables and section == 'BASE':
            if ls.startswith('Nom='):
                # "Nom=T143,0"
                rest = ls[4:]
                tname = rest.split(',', 1)[0]
                current['tables'].append(tname)
            continue
        # Cles=valeurs de la section
        if '=' in ls:
            key, _, value = ls.partition('=')
            key = key.strip()
            value = value.strip()
            # Stockage brut
            current.setdefault('raw_kv', []).append((i + 1, ls))
            if key == 'Nom':
                # "Nom=T143,Code Garantie,1"
                parts = value.split(',', 2)
                current['name'] = parts[0]
                if len(parts) > 1:
                    current['label'] = parts[1]
                if len(parts) > 2:
                    current['label_kind'] = parts[2]
            elif key == 'Version':
                current['version_value'] = value
            elif key == 'DateM':
                current['datem_value'] = value
            elif key == 'NomOdbc':
                current['nomodbc'] = value
            elif key == 'Gel':
                current['gel'] = value
            elif key == 'Nature':
                current['nature'] = value
            elif key == 'Flags':
                current['flags'] = value
            elif key == 'Fichier':
                current['fichier'] = value
            elif key == 'DateMIndex':
                current['datemindex'] = value
            elif key == 'Versionbase':
                current['versionbase'] = value
    # Fin de fichier : fermer la derniere section
    i = len(lines)
    close_section()
    return doc


def find_table(doc: DhsdDoc, table_name: str) -> dict:
    target = table_name.upper()
    for t in doc.tables:
        if t.get('name', '').upper() == target:
            return t
    return None


def find_bases_for_table(doc: DhsdDoc, table_name: str) -> list:
    """Retourne TOUTES les bases dont la section [TABLES] reference la table cible.

    Une table peut etre repliquee dans plusieurs bases physiques (cas frequent
    dans le standard, ex: ccfdd.dhsd c3 -> CcfJCA + Ccfm). Chaque base concernee
    doit recevoir son propre bloc [BASEU] dans la surcharge.
    """
    target = table_name.upper()
    return [b for b in doc.bases if target in [n.upper() for n in b.get('tables', [])]]


def parse_champs_for_u_container(table: dict, container_name: str):
    """Retourne (offset, taille, position_in_table_bytes) ou None si absent.

    Format attendu d'une ligne CHAMPS: 'Nom=<champ>,<position>,<enjambee>,<flag>,<nbDim>,<dim>,<flag2>,<niveau>'
    Le 2e nombre est la position 1-based dans la table.
    """
    target = container_name.upper()
    for lineno, line in table.get('fields_lines', []):
        # Nom=UT143,401,2,N,0,0,N,3
        if not line.startswith('Nom='):
            continue
        body = line[4:]
        parts = body.split(',')
        if len(parts) < 2:
            continue
        if parts[0].upper() == target:
            return {'lineno': lineno, 'raw': line, 'position_in_table': int(parts[1])}
    return None


# ---------------------------------------------------------------------------
# Parser surcharge existante : calcul offset cumule deja consomme dans un U-container
# ---------------------------------------------------------------------------

def consumed_offset_in_container(surcharge_path: Path, container_name: str, global_champs_surcharge: dict) -> int:
    """Parcourt le .dhsd surcharge, identifie les `[CHAMPR] nom=U<table>` actifs,
    pour chaque ligne `[CHAMPL] Nom=<champ>,<offset>,...` calcule l'offset+taille,
    retourne le max(offset_fin) trouve dans le container demande.

    Si aucun champ surcharge n'ancre le container, retourne 0 (le 1er champ partira a offset 1).
    """
    if not surcharge_path.exists():
        return 0
    with surcharge_path.open('r', encoding='iso-8859-1', newline='') as f:
        lines = f.read().replace('\r\n', '\n').split('\n')

    target = container_name.upper()
    in_champr = False
    active_container = None
    max_end = 0  # offset 1-based + taille - 1 du dernier champ ancre
    in_champl = False

    # On a besoin de la Nature de chaque champ ancre -> reparser les [CHAMP] globaux
    # de la surcharge (passes en argument).
    for line in lines:
        ls = line.strip()
        if not ls:
            continue
        if ls == '[CHAMPR]':
            in_champr = True
            active_container = None
            continue
        if ls == '[/CHAMPR]':
            in_champr = False
            active_container = None
            continue
        if not in_champr:
            continue
        # A l'interieur de [CHAMPR]
        if ls == '[CHAMPL]':
            in_champl = True
            continue
        if ls == '[/CHAMPL]':
            in_champl = False
            continue
        if ls.lower().startswith('nom='):
            # Soit "nom=UT143" (declarateur de container actif)
            # soit "Nom=<champ>,<offset>,..." si in_champl
            body = ls[4:]
            parts = body.split(',')
            if not in_champl:
                # declarateur de container
                active_container = parts[0].upper()
            else:
                if active_container != target:
                    continue
                if len(parts) < 2:
                    continue
                field_name = parts[0]
                try:
                    offset = int(parts[1])
                except ValueError:
                    continue
                # Recuperer la Nature depuis les [CHAMP] globaux
                champ = global_champs_surcharge.get(field_name.lower())
                if champ and 'nature' in champ:
                    try:
                        size = nature_size(champ['nature'])
                    except ValueError:
                        size = 0
                else:
                    size = 0
                end = offset + size - 1
                if end > max_end:
                    max_end = end
    return max_end


# ---------------------------------------------------------------------------
# Generation des blocs surcharge
# ---------------------------------------------------------------------------

def pad_user(user: str, width: int = 20) -> str:
    """Padding user a 20 caracteres avec espaces (convention DIVA)."""
    if len(user) > width:
        raise ValueError(f"User '{user}' trop long (>{width} chars)")
    return user + (' ' * (width - len(user)))


def build_header(user_padded: str, ts_aaaa: str, dico_internal_name: str) -> list:
    """Genere les premieres lignes du fichier (en-tete + [Dictionnaire]).

    `dico_internal_name` = nom du fichier .dhsd standard (ex: gtfdd.dhsd, ccfdd.dhsd).
    Le nom interne du dictionnaire est TOUJOURS celui du standard, jamais le nom physique
    du fichier de surcharge (cf doc canonique reference/dhsd-surcharge-pattern.md).
    """
    return [
        ';>xwinobj      dictionnaire',
        '[Dictionnaire]',
        f'Version=1,,,{ts_aaaa},{user_padded}',
        f'Nom={dico_internal_name},{dico_internal_name},1',
    ]


def build_champ_block(field_name: str, label: str, nature: str, user_padded: str, ts_aaaa: str) -> list:
    return [
        '[CHAMP]',
        f'Version=1,{ts_aaaa},{user_padded},{ts_aaaa},{user_padded}',
        f'Nom={field_name},{label},1',
        'Gel=1',
        f'Nature={nature}',
        'Flags=n,1,n,n,n,n,n,n,n',
    ]


def build_champr_block(container: str, field_name: str, offset: int) -> list:
    return [
        '[CHAMPR]',
        f'nom={container}',
        '[CHAMPL]',
        f'Nom={field_name},{offset},0,0,N,1',
        '[/CHAMPL]',
        '[/CHAMPR]',
    ]


def build_tableu_block(table: dict, ft_hex_le: str) -> list:
    return [
        '[TABLEU]',
        f"Version={table['version_value']}",
        f"Nom={table['name']},{table.get('label', '')},{table.get('label_kind', '1')}",
        f"DateM={table['datem_value']},{ft_hex_le}",
    ]


def build_baseu_block(base: dict, ft_hex_le: str) -> list:
    return [
        '[BASEU]',
        f"Version={base['version_value']}",
        f"Nom={base['name']},{base.get('label', '')},{base.get('label_kind', '1')}",
        f"DateM={base['datem_value']}",
        f"DateMIndex={ft_hex_le}",
        '[TABLES]',
        '[/TABLES]',
    ]


# ---------------------------------------------------------------------------
# Ecriture ISO-8859-1 + CRLF
# ---------------------------------------------------------------------------

def write_iso_crlf(path: Path, lines: list):
    content = '\r\n'.join(lines) + '\r\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='iso-8859-1', newline='') as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Mode --output (creation) vs --append-to (ajout dans surcharge existante)
# ---------------------------------------------------------------------------

def mode_output(args, table, bases, user_padded, ts_aaaa, ft_hex_le, offset, field_name, dico_internal_name):
    lines = []
    lines.extend(build_header(user_padded, ts_aaaa, dico_internal_name))
    lines.extend(build_champ_block(field_name, args.label, args.nature, user_padded, ts_aaaa))
    lines.extend(build_champr_block(f'U{args.table.upper()}', field_name, offset))
    lines.extend(build_tableu_block(table, ft_hex_le))
    for base in bases:
        lines.extend(build_baseu_block(base, ft_hex_le))
    out_path = Path(args.output)
    if out_path.exists():
        raise FileExistsError(f"Le fichier existe deja : {out_path}. Utiliser --append-to pour ajouter dans une surcharge existante.")
    write_iso_crlf(out_path, lines)
    return out_path


def mode_append_to(args, table, bases, user_padded, ts_aaaa, ft_hex_le, offset, field_name, dico_internal_name):
    """Mode minimaliste : ajoute le bloc [CHAMP] global + une entree dans le [CHAMPR] existant
    (ou cree un nouveau [CHAMPR] si le container cible n'est pas deja ancre).
    Si le [TABLEU] correspondant existe deja, on n'ajoute pas de doublon.
    Si pas, on ajoute aussi [TABLEU] (et [BASEU] manquants pour chacune des bases concernees).
    """
    src_path = Path(args.append_to)
    if not src_path.exists():
        raise FileNotFoundError(f"Surcharge introuvable pour --append-to : {src_path}")
    raw = src_path.read_text(encoding='iso-8859-1')
    body = raw.replace('\r\n', '\n').rstrip('\n')
    src_lines = body.split('\n')

    container = f'U{args.table.upper()}'

    # Localiser le bloc [CHAMPR] et le sous-bloc nom=<container> ; sinon, en ajouter un.
    # Pour simplifier le prototype, on parse en zones.
    out_lines = list(src_lines)

    # Etape 1 : ajouter le [CHAMP] global juste avant le 1er [CHAMPR]
    champ_lines = build_champ_block(field_name, args.label, args.nature, user_padded, ts_aaaa)
    inserted_champ = False
    for idx, l in enumerate(out_lines):
        if l.strip() == '[CHAMPR]':
            out_lines = out_lines[:idx] + champ_lines + out_lines[idx:]
            inserted_champ = True
            break
    if not inserted_champ:
        # Pas de [CHAMPR] -> ajouter [CHAMP] et le [CHAMPR] complet a la fin (avant [TABLEU])
        # Cas simple : on append apres le header
        # Pour le prototype, on echoue plutot que d'inventer.
        raise NotImplementedError("Surcharge sans [CHAMPR] existant : cas non gere par le prototype.")

    # Etape 2 : ajouter une ligne [CHAMPL] dans le [CHAMPR] correct
    # Strategie : trouver le 'nom=<container>' actif, et inserer juste apres son [CHAMPL] existant (avant son [/CHAMPL]).
    new_champl_line = f'Nom={field_name},{offset},0,0,N,1'
    in_champr = False
    active_container = None
    inserted_champl = False
    for idx, l in enumerate(out_lines):
        ls = l.strip()
        if ls == '[CHAMPR]':
            in_champr = True
            active_container = None
            continue
        if ls == '[/CHAMPR]' and in_champr:
            if active_container == container.upper() and not inserted_champl:
                # Fin du bloc CHAMPR alors que notre container etait actif sans [CHAMPL] precedent
                # -> on insere juste avant ce [/CHAMPR]
                out_lines.insert(idx, '[/CHAMPL]')
                out_lines.insert(idx, new_champl_line)
                out_lines.insert(idx, '[CHAMPL]')
                out_lines.insert(idx, f'nom={container}')
                inserted_champl = True
                in_champr = False
                active_container = None
                continue
            in_champr = False
            active_container = None
            continue
        if not in_champr:
            continue
        if ls.lower().startswith('nom=') and not ls.startswith('Nom='):
            # declarateur de container
            active_container = ls[4:].split(',')[0].upper()
            continue
        if ls == '[/CHAMPL]' and active_container == container.upper() and not inserted_champl:
            # Inserer la nouvelle ligne juste avant [/CHAMPL]
            out_lines.insert(idx, new_champl_line)
            inserted_champl = True
            in_champr = False
            active_container = None
            continue

    if not inserted_champl:
        # Container pas du tout reference -> creer un nouveau sous-bloc juste avant [/CHAMPR] du 1er [CHAMPR]
        for idx, l in enumerate(out_lines):
            if l.strip() == '[/CHAMPR]':
                out_lines.insert(idx, '[/CHAMPL]')
                out_lines.insert(idx, new_champl_line)
                out_lines.insert(idx, '[CHAMPL]')
                out_lines.insert(idx, f'nom={container}')
                inserted_champl = True
                break

    # Etape 3 : verifier que [TABLEU] pour notre table existe ; sinon ajouter avant le [BASEU]
    tname_token = f"Nom={table['name']},"
    has_tableu = False
    for idx, l in enumerate(out_lines):
        if l.strip().startswith(tname_token):
            # check section
            # Remonter pour voir si on est dans un [TABLEU]
            for k in range(idx, -1, -1):
                if out_lines[k].strip().startswith('['):
                    if out_lines[k].strip() == '[TABLEU]':
                        has_tableu = True
                    break
            if has_tableu:
                break
    if not has_tableu:
        tableu_lines = build_tableu_block(table, ft_hex_le)
        # Inserer avant le 1er [BASEU]
        inserted = False
        for idx, l in enumerate(out_lines):
            if l.strip() == '[BASEU]':
                out_lines = out_lines[:idx] + tableu_lines + out_lines[idx:]
                inserted = True
                break
        if not inserted:
            # Pas de [BASEU] -> ajouter a la fin
            out_lines.extend(tableu_lines)

    # Etape 4 : pour CHAQUE base concernee, verifier que [BASEU] existe ; sinon ajouter a la fin
    for base in bases:
        bname_token = f"Nom={base['name']},"
        has_baseu = False
        for idx, l in enumerate(out_lines):
            if l.strip().startswith(bname_token):
                for k in range(idx, -1, -1):
                    if out_lines[k].strip().startswith('['):
                        if out_lines[k].strip() == '[BASEU]':
                            has_baseu = True
                        break
                if has_baseu:
                    break
        if not has_baseu:
            out_lines.extend(build_baseu_block(base, ft_hex_le))

    write_iso_crlf(src_path, out_lines)
    return src_path


# ---------------------------------------------------------------------------
# Validation prefixe
# ---------------------------------------------------------------------------

def validate_prefix(field_name: str, prefix: str):
    """Garde-fou anti-typo si --prefix est passe.

    Aucune validation de FORME du prefixe : selon les postes integrateur,
    le prefixe peut etre 1/2/3 caracteres, n'importe quelle casse, ou
    inexistant. Le script accepte donc tout. Le seul controle effectue
    est : si --prefix est non vide, le nom du champ DOIT commencer par
    cette chaine (sinon = erreur de frappe ou incoherence entre
    --field-name et --prefix).
    """
    if not prefix:
        # Pas de prefixe declare -> aucune verification
        return
    if not field_name.startswith(prefix):
        raise ValueError(
            f"Le nom du champ '{field_name}' ne commence pas par le prefixe '{prefix}'. "
            f"Probable erreur de frappe : renommer le champ, ajuster --prefix, ou omettre --prefix."
        )


# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ajoute un champ a une table standard via surcharge dictionnaire DIVA.")
    parser.add_argument('--dhsd-standard', required=True, help="Chemin du .dhsd standard (lecture seule).")
    parser.add_argument('--table', required=True, help="Nom de la table cible (ex: T143).")
    parser.add_argument('--field-name', required=True, help="Nom du champ a ajouter (avec prefixe poste, ex: dgsTrajetKmMax).")
    parser.add_argument('--nature', required=True, help="Nature DIVA du champ (ex: 5,0 ou D8 ou 20).")
    parser.add_argument('--label', required=True, help="Libelle FR du champ (sans accents recommande).")
    parser.add_argument('--user', required=True, help="Identifiant utilisateur (ex: rootDGS), padding 20 chars automatique.")
    parser.add_argument('--prefix', default='', help="Prefixe poste OPTIONNEL (ex: dgs, mi, m, eco, ou rien). Aucune validation de forme. Si fourni, le nom du champ doit commencer par cette chaine (garde-fou anti-typo). Sans valeur, le script accepte n'importe quel nom de champ.")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument('--output', help="Chemin de creation d'un nouveau .dhsd surcharge.")
    grp.add_argument('--append-to', help="Chemin d'un .dhsd surcharge existant a enrichir.")
    args = parser.parse_args()

    try:
        # Validation prefixe
        validate_prefix(args.field_name, args.prefix)

        # Calcul taille
        try:
            field_size = nature_size(args.nature)
        except ValueError as e:
            raise ValueError(f"Nature du champ invalide : {e}")

        # Parse standard
        std_path = Path(args.dhsd_standard)
        if not std_path.exists():
            raise FileNotFoundError(f"Standard introuvable : {std_path}")
        std = parse_dhsd(std_path)

        table = find_table(std, args.table)
        if not table:
            raise ValueError(f"Table '{args.table}' introuvable dans {std_path.name}.")
        bases = find_bases_for_table(std, args.table)
        if not bases:
            raise ValueError(f"Aucune [BASE] ne reference la table '{args.table}' (section [TABLES]).")

        # Verifier U-container
        container_name = f'U{args.table.upper()}'
        u_anchor = parse_champs_for_u_container(table, container_name)
        if not u_anchor:
            raise ValueError(
                f"Container '{container_name}' absent du [CHAMPS] de la table '{args.table}'. "
                f"La table N'EST PAS surchargeable. Demander a Divalto un agrandissement (anti-pattern D15)."
            )
        u_champ_global = std.global_champs.get(container_name.lower())
        if not u_champ_global or 'nature' not in u_champ_global:
            raise ValueError(
                f"Champ global '{container_name}' introuvable ou sans Nature dans le standard. "
                f"Impossible de connaitre la capacite du container."
            )
        container_capacity = nature_size(u_champ_global['nature'])

        # Calcul offset
        if args.append_to:
            surcharge_path = Path(args.append_to)
            # Parser la surcharge existante pour ses [CHAMP] globaux (Nature des champs ancres)
            if surcharge_path.exists():
                surcharge_doc = parse_dhsd(surcharge_path)
                global_surcharge = surcharge_doc.global_champs
            else:
                global_surcharge = {}
            consumed_end = consumed_offset_in_container(surcharge_path, container_name, global_surcharge)
            offset = consumed_end + 1 if consumed_end > 0 else 1
        else:
            offset = 1

        # Verifier capacite
        new_end = offset + field_size - 1
        if new_end > container_capacity:
            raise ValueError(
                f"Capacite du container '{container_name}' depassee : "
                f"offset {offset} + taille {field_size} - 1 = {new_end} > capacite {container_capacity}. "
                f"Demander a Divalto un agrandissement."
            )

        # Generer timestamps
        ts_aaaa = now_aaaammjjhhmmss()
        ft_hex_le = now_filetime_hex_le()
        user_padded = pad_user(args.user)

        # Nom interne du dictionnaire = nom du fichier standard (sans path).
        dico_internal_name = std_path.name.lower()

        # Mode
        if args.output:
            written = mode_output(args, table, bases, user_padded, ts_aaaa, ft_hex_le, offset, args.field_name, dico_internal_name)
        else:
            written = mode_append_to(args, table, bases, user_padded, ts_aaaa, ft_hex_le, offset, args.field_name, dico_internal_name)

        result = {
            "status": "ok",
            "file": str(written),
            "mode": "create" if args.output else "append",
            "field": args.field_name,
            "nature": args.nature,
            "size_bytes": field_size,
            "container": container_name,
            "container_capacity": container_capacity,
            "offset_in_container": offset,
            "capacity_remaining": container_capacity - new_end,
            "table_metadata_source": {
                "dhsd": str(std_path),
                "table_line": table.get('start_line'),
                "table_name": table.get('name'),
                "table_label": table.get('label'),
                "version": table.get('version_value'),
                "datem": table.get('datem_value'),
            },
            "bases_metadata_source": [
                {
                    "base_name": b.get('name'),
                    "base_label": b.get('label'),
                    "version": b.get('version_value'),
                    "datem": b.get('datem_value'),
                }
                for b in bases
            ],
            "filetime_le": ft_hex_le,
            "timestamp_aaaa": ts_aaaa,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        print(json.dumps({"status": "error", "error_type": type(e).__name__, "error": str(e)}, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
