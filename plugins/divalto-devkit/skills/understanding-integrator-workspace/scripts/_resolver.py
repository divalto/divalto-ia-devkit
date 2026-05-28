#!/usr/bin/env python3
"""
Module utilitaire de resolution des chemins harmony pour le skill
understanding-integrator-workspace. Implemente R-3 (divaltopath.cfg),
R-4 (fconfig cle E, fallback heuristique sur le `.dhfd` brut) et R-5
(registre Windows pour DIVA_ROOT + chemin fconfig). Implemente egalement
R-7 (divaltoserver.cfg pour les serveurs SQL) et stub R-8 (fconfig cle B,
fallback non encore implemente faute de spec byte-precise).

Utilise par `find_canonical_file.py` et `check_workspace_coherence.py`.

API publique :
- discover_diva_root() -> dict avec "diva_root", "fconfig_dhfd", "source" ou erreur
- parse_divaltopath_cfg(path) -> dict[alias] = path  (R-3)
- fconfig_alias_lookup(dhfd_path, alias) -> path | None (heuristique raw bytes, R-4)
- resolve_harmony_path(harmony_path, cfg_aliases, dhfd_path, diva_root) -> dict
- parse_divaltoserver_cfg(path) -> dict[server_name] = {sqlpath, address, type, ...} (R-7)
- resolve_sql_url(sql_url, server_cfg, dhfd_path, diva_root) -> dict (R-7 -> R-8)
- parse_bconnect_from_fhsql(fhsql_dhfd_path) -> dict (R-9, BCONNECT raw parse)
- read_odbc_dsn(dsn_name) -> dict 32-bit + 64-bit (R-10)
- parse_implicit_xml_companion(implicit_path) -> dict (R-11 partie 1, alias->connexion)
- parse_connexions_xml(connexions_path) -> dict (R-11 partie 2, connexion->chaine)
- compute_effective_databases(...) -> dict avec base_effective_* + findings cross-portes

Notes :
- L'acces registre n'est disponible que sous Windows (winreg). Sur autre OS,
  discover_diva_root() retourne une erreur exploitable par l'appelant (P-A).
- La lecture fconfig en raw bytes est une heuristique en attendant un
  structure_fconfig.json pour le skill reading-isam-files.

DISCIPLINE REGISTRE -- principe P-C du skill (liste blanche stricte) :
- discover_diva_root() (R-5) : lit UNIQUEMENT `CheminUl1` et `CheminFpartd`
  sous `HKLM\\SOFTWARE\\[WOW6432Node\\]Divalto\\divalto.ini\\System`.
  Aucune enumeration des sous-cles, aucune lecture des autres valeurs.
- read_odbc_dsn() (R-10) : lit UNIQUEMENT les valeurs sous la cle DSN ciblee
  `\\ODBC\\ODBC.INI\\<DSN>` (4 vues HKLM/HKCU x 32/64). N'enumere PAS les autres
  branches de `\\ODBC\\` (drivers, ODBCINST.INI, autres DSN non cibles).
- Tout futur ajout d'acces registre doit (a) etre documente comme regle R-NN
  dans le skill et (b) etre restreint a une cle / liste de valeurs explicite.
  Pas de `reg query /s`, pas d'exploration "au cas ou", pas de lecture de
  cles voisines. Voir SKILL.md section "Principes transverses -- P-C".
"""
import re
import sys
from pathlib import Path

# winreg n'est dispo que sous Windows
try:
    import winreg  # type: ignore
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False


REGISTRY_PATHS = [
    # (root_key, subkey) -- a essayer dans l'ordre
    ("HKLM", r"SOFTWARE\WOW6432Node\Divalto\divalto.ini\System"),
    ("HKLM", r"SOFTWARE\Divalto\divalto.ini\System"),
]


def discover_diva_root() -> dict:
    """R-5 : decouvre DIVA_ROOT et le chemin fconfig.dhfd via la base de registre Windows.

    Conformite P-C (discipline registre, liste blanche) : lit UNIQUEMENT
    les valeurs `CheminUl1` et `CheminFpartd` sous l'une des deux cles
    Divalto autorisees (cf. REGISTRY_PATHS). N'enumere pas les sous-cles,
    ne lit pas d'autres valeurs, ne fait aucune exploration au-dela.

    Retourne :
      {"diva_root": str, "fconfig_dhfd": str, "source": "registry:<path>"}
      ou {"error": str} si introuvable / inaccessible.
    """
    if not _HAS_WINREG:
        return {
            "error": (
                "Module winreg non disponible (OS non-Windows ou environnement sandboxe). "
                "P-A : demander au collaborateur la racine d'installation Divalto et "
                "le chemin de fconfig.dhfd."
            )
        }

    for root_name, subkey in REGISTRY_PATHS:
        root = winreg.HKEY_LOCAL_MACHINE if root_name == "HKLM" else winreg.HKEY_CURRENT_USER
        try:
            with winreg.OpenKey(root, subkey) as key:
                # CheminUl1 (l minuscule) -> DIVA_ROOT
                # CheminFpartd -> chemin fconfig.dhfd
                try:
                    diva_root, _ = winreg.QueryValueEx(key, "CheminUl1")
                except FileNotFoundError:
                    continue
                try:
                    fconfig_dhfd, _ = winreg.QueryValueEx(key, "CheminFpartd")
                except FileNotFoundError:
                    fconfig_dhfd = None

                return {
                    "diva_root": diva_root,
                    "fconfig_dhfd": fconfig_dhfd,
                    "source": f"{root_name}\\{subkey}",
                }
        except (FileNotFoundError, OSError):
            continue

    return {
        "error": (
            "Cle de registre Divalto introuvable (essaye sous HKLM/WOW6432Node et "
            "HKLM racine). P-A : Divalto peut-etre non installe via le standard "
            "installer, ou install portable. Demander au collaborateur."
        )
    }


def parse_divaltopath_cfg(cfg_path: Path) -> dict:
    """R-3 : parse `<DIVA_ROOT>/sys/divaltopath.cfg`.

    Grammaire d'une ligne :
        <NAME>nom_alias<PATH>chemin_absolu<MULTIBASE>...<SHARENAME>...

    Retourne un dict[alias_lower] = chemin_absolu. La casse de l'alias est conservee
    sous une cle 'aliases_case' pour reference, mais le lookup est case-insensitive.
    """
    if not cfg_path.is_file():
        return {"error": f"divaltopath.cfg introuvable : {cfg_path}"}

    # divaltopath.cfg semble etre en encoding cp1252 / iso-8859-1 (Windows fr-FR)
    text = cfg_path.read_text(encoding="iso-8859-1", errors="replace")

    aliases = {}
    aliases_case = {}
    pattern = re.compile(r"<NAME>([^<]*)<PATH>([^<]*)<MULTIBASE>", re.IGNORECASE)
    for line in text.splitlines():
        m = pattern.search(line)
        if not m:
            continue
        name = m.group(1).strip()
        path = m.group(2).strip()
        if not name:
            continue
        aliases[name.lower()] = path
        aliases_case[name] = path

    return {"aliases": aliases, "aliases_case": aliases_case, "source": str(cfg_path)}


def fconfig_alias_lookup(dhfd_path: Path, alias: str) -> dict:
    """R-4 fallback : cherche l'alias dans `fconfig.dhfd` (lecture brute des bytes).

    Heuristique observee empiriquement (a remplacer par une lecture ISAM propre via
    le skill reading-isam-files quand `structure_fconfig.json` sera disponible) :

    Les enregistrements de type "alias de chemin" dans fconfig.dhfd sont prefixes par
    le **literal `^Y` (bytes 0x5E 0x59)**, PAS par le control char 0x19 comme
    on pourrait le croire en lisant un dump cat. Apres le marqueur, le nom de l'alias
    est sur 32 chars (padde avec des espaces) puis le chemin absolu Windows commence
    immediatement (lui aussi padde par des espaces pour atteindre la taille fixe du
    record).

    Retourne {"path": str, "source": str} ou {"error": str} si non trouve.
    """
    if not dhfd_path.is_file():
        return {"error": f"fconfig.dhfd introuvable : {dhfd_path}"}

    data = dhfd_path.read_bytes()
    marker = b"\x5E\x59"  # litteral ^Y, PAS 0x19
    alias_lc = alias.lower()

    # Trouver toutes les positions du marqueur
    positions = []
    start = 0
    while True:
        idx = data.find(marker, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1

    for pos in positions:
        # Apres le marqueur ^Y (2 bytes), 32 chars d'alias-padde puis chemin
        record_start = pos + 2
        if record_start + 32 > len(data):
            continue
        alias_field = data[record_start : record_start + 32].decode(
            "iso-8859-1", errors="replace"
        )
        record_alias = alias_field.strip()
        if not record_alias:
            continue
        if record_alias.lower() != alias_lc:
            continue
        # Le chemin commence immediatement apres les 32 chars d'alias
        # Il est lui aussi padde par des espaces -- prendre jusqu'au premier groupe
        # de >= 8 espaces (fin de champ) ou jusqu'au prochain marqueur
        path_chunk = data[record_start + 32 : record_start + 32 + 256].decode(
            "iso-8859-1", errors="replace"
        )
        # Decoupe au premier run de 8+ espaces consecutifs (fin du champ path)
        m = re.match(r"^(.*?)(?=\s{8,}|\x00|$)", path_chunk, re.DOTALL)
        if m:
            record_path = m.group(1).rstrip()
            if record_path:
                return {"path": record_path, "source": f"{dhfd_path} (offset {pos})"}

    return {"error": f"Alias '{alias}' non trouve dans fconfig.dhfd"}


def resolve_harmony_path(
    harmony_path: str,
    cfg_aliases: dict,
    dhfd_path: Path | None = None,
    diva_root: str | None = None,
) -> dict:
    """Resout un chemin harmony (R-3 -> R-4 -> R-5 pour /divalto/).

    Args :
        harmony_path  : ex. "/specifs/<X>/fichiers/"
        cfg_aliases   : dict alias_lower -> path absolu (sortie de parse_divaltopath_cfg)
        dhfd_path     : chemin de fconfig.dhfd (pour R-4 fallback)
        diva_root     : DIVA_ROOT (pour /divalto/ via R-5)

    Retourne :
        {"resolved": str, "source": "cfg|fconfig|registry"}
        ou {"error": str, "alias": str} si non resoluble.
    """
    m = re.match(r"^/([^/]+)/?(.*)$", harmony_path.strip())
    if not m:
        return {"error": f"Pas un chemin harmony valide : {harmony_path}"}

    alias = m.group(1)
    rest = m.group(2)

    # Cas special /divalto/ -> R-5 (registre)
    if alias.lower() == "divalto":
        if diva_root:
            resolved = str(Path(diva_root) / rest) if rest else diva_root
            return {"resolved": resolved, "alias": alias, "source": "registry"}
        return {
            "error": (
                "Alias 'divalto' ne resout pas via divaltopath.cfg ni fconfig (toujours absent). "
                "Necessite DIVA_ROOT du registre (R-5). P-A : DIVA_ROOT non disponible."
            ),
            "alias": alias,
        }

    # R-3 : divaltopath.cfg
    if alias.lower() in cfg_aliases:
        base = cfg_aliases[alias.lower()]
        resolved = str(Path(base) / rest) if rest else base
        return {"resolved": resolved, "alias": alias, "source": "cfg"}

    # R-4 : fconfig (fallback)
    if dhfd_path is not None:
        lookup = fconfig_alias_lookup(dhfd_path, alias)
        if "path" in lookup:
            base = lookup["path"]
            resolved = str(Path(base) / rest) if rest else base
            return {"resolved": resolved, "alias": alias, "source": "fconfig"}

    return {
        "error": f"Alias '{alias}' non trouve dans divaltopath.cfg ni fconfig. P-A : demander.",
        "alias": alias,
    }


# ----------------------------------------------------------------------------
# R-7 / R-8 -- Resolution SQL via divaltoserver.cfg puis fconfig cle B
# ----------------------------------------------------------------------------


def parse_divaltoserver_cfg(cfg_path: Path) -> dict:
    """R-7 : parse `<DIVA_ROOT>/sys/divaltoserver.cfg`.

    Grammaire d'une ligne (parallele de divaltopath.cfg) :
        <NAME>nom_serveur<ADDRESS>adresse<SQLPATH>chemin<COMMENT>libelle<TYPE>type<OS>os<PORT>port

    `<TYPE>` observes : `WINDOWS`, `SQL`, `XLAN`. `<SQLPATH>` peut etre vide.

    Retourne :
        {
          "servers": dict[name_lower -> {sqlpath, address, comment, type, os, port}],
          "servers_case": dict[name -> ...],   # casse preservee
          "source": str
        }
        ou {"error": str}
    """
    if not cfg_path.is_file():
        return {"error": f"divaltoserver.cfg introuvable : {cfg_path}"}

    text = cfg_path.read_text(encoding="iso-8859-1", errors="replace")

    pattern = re.compile(
        r"<NAME>([^<]*)<ADDRESS>([^<]*)<SQLPATH>([^<]*)<COMMENT>([^<]*)<TYPE>([^<]*)<OS>([^<]*)<PORT>([^<\r\n]*)",
        re.IGNORECASE,
    )

    servers = {}
    servers_case = {}
    for line in text.splitlines():
        m = pattern.search(line)
        if not m:
            continue
        name = m.group(1).strip()
        if not name:
            continue
        record = {
            "sqlpath": m.group(3).strip(),
            "address": m.group(2).strip(),
            "comment": m.group(4).strip(),
            "type": m.group(5).strip(),
            "os": m.group(6).strip(),
            "port": m.group(7).strip(),
        }
        servers[name.lower()] = record
        servers_case[name] = record

    return {"servers": servers, "servers_case": servers_case, "source": str(cfg_path)}


def fconfig_sql_lookup(dhfd_path: Path, server_name: str) -> dict:
    """R-8 stub : cherche un serveur SQL dans `fconfig.dhfd` (table cle B).

    **Non implemente** -- la doc du skill mentionne un prefixe `C 5XX` pour
    les enregistrements serveur mais la grammaire byte-precise n'a pas ete
    formellement specifiee. Tant que `structure_fconfig.json` n'existe pas
    pour `reading-isam-files`, on retourne une erreur exploitable par
    l'appelant (P-A : demander au collaborateur si R-7 a echoue).

    Sera implemente quand soit :
    - `structure_fconfig.json` sera fourni pour `reading-isam-files`, OU
    - le pattern byte-precis du marqueur de la table B sera documente
      par un RETEX terrain comme R-4 l'a ete pour la table E.

    Retourne {"error": "..."} systematiquement.
    """
    return {
        "error": (
            f"R-8 non implemente (fallback fconfig cle B pour '{server_name}'). "
            f"Le marqueur byte de la table serveurs dans fconfig.dhfd n'est pas "
            f"specifie. P-A : demander au collaborateur le chemin SQL effectif "
            f"pour ce serveur, ou inscrire le serveur dans divaltoserver.cfg "
            f"(qui est la source primaire R-7)."
        )
    }


_SQL_URL_RE = re.compile(r"^//([^/]+)/(.+?)/?$")


def resolve_sql_url(
    sql_url: str,
    server_cfg: dict,
    dhfd_path: Path | None = None,
    diva_root: str | None = None,
) -> dict:
    """R-7 -> R-8 : resout une ligne URL SQL `//host/db` du fichier implicite
    en chemin SQL absolu (dossier qui doit contenir `fhsql.dhfi/.dhfd`).

    Args :
        sql_url     : ex. `//localhost/DIVALTO_CLIENT_VX13`
        server_cfg  : dict server_name_lower -> {sqlpath, ...} (sortie de parse_divaltoserver_cfg)
        dhfd_path   : chemin de fconfig.dhfd (pour R-8 fallback, non implemente)
        diva_root   : DIVA_ROOT (pour le fallback SQLPATH vide -> <DIVA_ROOT>/<db>/)

    Retourne :
        {
          "resolved": str,             # chemin SQL absolu
          "source": "cfg|fconfig|fallback_diva_root",
          "host": str,
          "db": str,
          "sqlpath_raw": str           # valeur brute de SQLPATH (peut etre vide)
        }
        ou {"error": str, "host": str|None, "db": str|None}
    """
    m = _SQL_URL_RE.match(sql_url.strip())
    if not m:
        return {
            "error": f"URL SQL malformee : '{sql_url}' (forme attendue : //host/db)",
            "host": None,
            "db": None,
        }
    host = m.group(1).strip()
    db = m.group(2).strip()

    # R-7 : lookup dans server_cfg sur <db>
    record = server_cfg.get(db.lower()) if server_cfg else None
    if record:
        sqlpath_raw = record.get("sqlpath", "")
        if sqlpath_raw:
            return {
                "resolved": sqlpath_raw,
                "source": "cfg",
                "host": host,
                "db": db,
                "sqlpath_raw": sqlpath_raw,
            }
        # Cas particulier : SQLPATH vide -> fallback <DIVA_ROOT>/<db>/
        if diva_root:
            fallback = str(Path(diva_root) / db)
            return {
                "resolved": fallback,
                "source": "fallback_diva_root",
                "host": host,
                "db": db,
                "sqlpath_raw": "",
            }
        return {
            "error": (
                f"R-7 a trouve '{db}' dans divaltoserver.cfg mais SQLPATH vide "
                f"et DIVA_ROOT non disponible pour le fallback <DIVA_ROOT>/{db}/."
            ),
            "host": host,
            "db": db,
        }

    # R-8 : fallback fconfig (non implemente)
    if dhfd_path is not None:
        r8 = fconfig_sql_lookup(dhfd_path, db)
        if "path" in r8:
            return {
                "resolved": r8["path"],
                "source": "fconfig",
                "host": host,
                "db": db,
                "sqlpath_raw": r8["path"],
            }
        # Sinon : continuer en P-A

    return {
        "error": (
            f"Serveur '{db}' non trouve dans divaltoserver.cfg (R-7) et R-8 (fallback "
            f"fconfig cle B) non implemente. P-A : verifier que le serveur est "
            f"declare dans divaltoserver.cfg, ou demander au collaborateur le chemin SQL."
        ),
        "host": host,
        "db": db,
    }


# ----------------------------------------------------------------------------
# R-9 -- Extraction BCONNECT depuis fhsql.dhfd (raw bytes)
# ----------------------------------------------------------------------------

# Pattern de la chaine BCONNECT : commence par "CONNECT DSN=" ou "BCONNECT DSN="
# suivie d'une serie de cles=valeur separees par ;
_BCONNECT_RE = re.compile(rb"B?CONNECT\s+([A-Za-z][\x20-\x7E]+)")


def parse_bconnect_from_fhsql(fhsql_dhfd_path: Path) -> dict:
    """R-9 : extrait la chaine BCONNECT de `fhsql.dhfd` en lecture brute des bytes.

    Le pattern observe est :
      BCONNECT DSN=<nom>;Description=<desc>;Trusted_Connection=<Yes|No>;
        APP=<app>;WSID=<host>;DATABASE=<base>;Encrypt=<Yes|No>;TrustServerCertificate=<Yes|No>;

    Heuristique : recherche du pattern `B?CONNECT DSN=...;...;` dans les bytes
    du `.dhfd`. A remplacer par une lecture ISAM propre (cle C) via le skill
    `reading-isam-files` quand `structure_fhsql.json` sera disponible.

    Retourne :
      {
        "raw_string": str,            # chaine BCONNECT complete
        "pairs": dict[str, str],      # dict des cles=valeur
        "dsn": str | None,            # raccourci sur DSN
        "database": str | None,       # raccourci sur DATABASE (override Harmony)
        "source": str
      }
      ou {"error": str} si non trouve / inaccessible.
    """
    if not fhsql_dhfd_path.is_file():
        return {"error": f"fhsql.dhfd introuvable : {fhsql_dhfd_path}"}

    try:
        data = fhsql_dhfd_path.read_bytes()
    except OSError as e:
        return {"error": f"Lecture fhsql.dhfd echoue : {e}"}

    m = _BCONNECT_RE.search(data)
    if not m:
        return {
            "error": (
                f"Pattern 'BCONNECT' ou 'CONNECT DSN=' introuvable dans "
                f"{fhsql_dhfd_path}. P-A : verifier que ce fichier est bien un "
                f"fhsql.dhfd Divalto, ou demander au collaborateur."
            )
        }

    # Decode le segment trouve, strip les bytes de fin (espaces, control chars)
    raw = m.group(1).decode("iso-8859-1", errors="replace").strip()
    # Tronquer apres le dernier ';' visible (apres c'est typiquement du padding)
    if ";" in raw:
        # Garder jusqu'au dernier ';' inclus
        last_semi = raw.rfind(";")
        # Verifier qu'on n'inclut pas trop -- si apres le dernier ';' il y a moins de 5 chars
        # et pas de '=', tronquer
        tail = raw[last_semi + 1:].strip()
        if tail and "=" not in tail:
            raw = raw[: last_semi + 1]

    # Parser les paires cle=valeur (separateur ';')
    pairs = {}
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, value = part.partition("=")
        pairs[key.strip()] = value.strip()

    return {
        "raw_string": raw,
        "pairs": pairs,
        "dsn": pairs.get("DSN"),
        "database": pairs.get("DATABASE"),
        "source": str(fhsql_dhfd_path),
    }


# ----------------------------------------------------------------------------
# R-10 -- Lecture DSN ODBC dans le registre Windows
# ----------------------------------------------------------------------------

# Cles registre ODBC, dans l'ordre d'essai
_ODBC_REGISTRY_PATHS = [
    # (root_key, subkey_template, bitness, scope)
    ("HKLM", r"SOFTWARE\WOW6432Node\ODBC\ODBC.INI\{}", "32-bit", "system"),
    ("HKLM", r"SOFTWARE\ODBC\ODBC.INI\{}", "64-bit", "system"),
    ("HKCU", r"SOFTWARE\WOW6432Node\ODBC\ODBC.INI\{}", "32-bit", "user"),
    ("HKCU", r"SOFTWARE\ODBC\ODBC.INI\{}", "64-bit", "user"),
]


def read_odbc_dsn(dsn_name: str) -> dict:
    """R-10 : lit la configuration d'un DSN ODBC dans le registre Windows.

    Essaye les 4 emplacements possibles (System/User x 32/64 bit) et retourne
    les valeurs trouvees, en separant 32-bit et 64-bit. Tolere les DSN absents
    sur l'un des deux bitness.

    Conformite P-C (discipline registre, liste blanche) : enumere les valeurs
    UNIQUEMENT sous la cle DSN ciblee `\\ODBC\\ODBC.INI\\<DSN>` (4 vues).
    N'explore PAS les autres branches de `\\ODBC\\` (drivers, ODBCINST.INI,
    autres DSN non cibles). L'enumeration locale via `winreg.EnumValue` reste
    dans le perimetre admis -- toutes les valeurs sous la cle DSN font partie
    de la configuration ODBC standard.

    Retourne :
      {
        "dsn": str,
        "32bit": dict | None,    # {Driver, Server, Database, Trusted_Connection, Encrypt, ...} ou None
        "64bit": dict | None,
        "sources": list[str]     # cles registre effectivement trouvees
      }
      ou {"error": str} si winreg non dispo OU DSN introuvable dans les 4 cles.

    Hygiene credentials : si `PWD` est present dans une entree, sa valeur est
    redactee dans le retour (`<REDACTED>`).
    """
    if not _HAS_WINREG:
        return {
            "error": (
                "Module winreg non disponible (OS non-Windows). P-A : demander "
                "au collaborateur les valeurs du DSN ODBC."
            )
        }

    result = {"dsn": dsn_name, "32bit": None, "64bit": None, "sources": []}

    for root_name, subkey_tmpl, bitness, scope in _ODBC_REGISTRY_PATHS:
        root = winreg.HKEY_LOCAL_MACHINE if root_name == "HKLM" else winreg.HKEY_CURRENT_USER
        subkey = subkey_tmpl.format(dsn_name)
        try:
            with winreg.OpenKey(root, subkey) as key:
                values = {}
                i = 0
                while True:
                    try:
                        name, value, _vtype = winreg.EnumValue(key, i)
                    except OSError:
                        break
                    # Redaction credentials
                    if name.upper() in ("PWD", "PASSWORD"):
                        value = "<REDACTED>"
                    values[name] = value
                    i += 1
                # Garder la 1ere occurrence par bitness (System prime sur User)
                if result[bitness] is None:
                    result[bitness] = values
                    result["sources"].append(f"{root_name}\\{subkey} ({scope}, {bitness})")
        except FileNotFoundError:
            continue
        except OSError:
            continue

    if result["32bit"] is None and result["64bit"] is None:
        return {
            "error": (
                f"DSN '{dsn_name}' introuvable dans le registre (4 emplacements "
                f"testes : HKLM/HKCU x 32/64). P-A : verifier que le DSN existe."
            )
        }

    return result


# ----------------------------------------------------------------------------
# R-11 -- Parsing implicite.xml + connexions.xml (porte ADO.NET)
# ----------------------------------------------------------------------------


def parse_implicit_xml_companion(implicit_path: Path) -> dict:
    """R-11 partie 1 : parse le compagnon XML du fichier implicite.

    Le compagnon est `<implicite>.xml` (meme repertoire, meme basename, ext .xml).
    Contient le mapping alias_applicatif -> nom_connexion_logique.

    Forme attendue (xml namespace `urn:implicites-schema`) :
      <implicites xmlns="urn:implicites-schema">
        <implicite nom="<alias>" connexion="<nom_connexion>" />
      </implicites>

    Retourne :
      {
        "xml_path": str,
        "mappings": dict[alias -> connexion_logique],
        "source": str
      }
      ou {"error": str} si absent ou malforme.
    """
    xml_path = implicit_path.with_suffix(".xml")
    if not xml_path.is_file():
        return {
            "error": (
                f"Compagnon XML '{xml_path.name}' introuvable a cote du fichier "
                f"implicite. Porte ADO.NET non resolue. P-A : verifier."
            )
        }

    try:
        text = xml_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        try:
            text = xml_path.read_text(encoding="iso-8859-1")
        except OSError as e:
            return {"error": f"Lecture {xml_path} echoue : {e}"}

    # Parse XML naive (regex) -- evite import xml.etree pour rester leger
    mappings = {}
    pattern = re.compile(
        r'<implicite\s+nom="([^"]+)"\s+connexion="([^"]+)"\s*/?>',
        re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        mappings[m.group(1)] = m.group(2)

    if not mappings:
        return {
            "error": (
                f"Aucun mapping <implicite nom=... connexion=... /> trouve dans "
                f"{xml_path}. Format inattendu ou fichier vide. P-A."
            ),
            "xml_path": str(xml_path),
        }

    return {"xml_path": str(xml_path), "mappings": mappings, "source": str(xml_path)}


def parse_connexions_xml(connexions_path: Path, target_connexion: str = None) -> dict:
    """R-11 partie 2 : parse `<DIVA_ROOT>/sys/connexions.xml` et extrait les
    connexions logiques avec leur chaine ADO.NET.

    Args :
        connexions_path  : chemin de `connexions.xml`
        target_connexion : (optionnel) nom de connexion specifique a extraire ;
                           si fourni, retourne uniquement cette connexion

    Retourne :
      {
        "connexions": dict[nom_connexion -> {type, nomBase, chaineDeConnexion, ...}],
        "source": str
      }
      ou (avec target_connexion) :
      {
        "connexion": {type, nomBase, chaineDeConnexion, ...} | None,
        "source": str
      }
      ou {"error": str} si fichier absent ou aucune connexion trouvee.

    Hygiene credentials : `Password=`, `pwd=` redactes en `<REDACTED>` dans
    le champ `chaineDeConnexion`.
    """
    if not connexions_path.is_file():
        return {"error": f"connexions.xml introuvable : {connexions_path}"}

    try:
        text = connexions_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        try:
            text = connexions_path.read_text(encoding="iso-8859-1")
        except OSError as e:
            return {"error": f"Lecture {connexions_path} echoue : {e}"}

    connexions = {}
    # Pattern d'un bloc <connexion nom="X">...</connexion>
    block_re = re.compile(
        r'<connexion\s+nom="([^"]+)"\s*>(.*?)</connexion>',
        re.DOTALL | re.IGNORECASE,
    )

    def _extract_tag(body: str, tag: str) -> str | None:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", body, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _redact(s: str | None) -> str | None:
        if not s:
            return s
        # Redaction simple : Password=...; / pwd=...; (case insensitive)
        s = re.sub(r"(?i)(Password|pwd)\s*=\s*[^;]+", r"\1=<REDACTED>", s)
        return s

    for m in block_re.finditer(text):
        nom = m.group(1)
        body = m.group(2)
        chaine = _extract_tag(body, "chaineDeConnexion")
        # Tente d'extraire la "Database" de la chaine ADO.NET
        database = None
        if chaine:
            db_m = re.search(
                r"(?i)(?:Initial\s+Catalog|Database)\s*=\s*([^;]+)", chaine
            )
            if db_m:
                database = db_m.group(1).strip()
        connexions[nom] = {
            "type": _extract_tag(body, "type"),
            "nomBase": _extract_tag(body, "nomBase"),
            "chaineDeConnexion": _redact(chaine),
            "database": database,
            "harmonyShareServer": _extract_tag(body, "harmonyShareServer"),
            "logSql": _extract_tag(body, "logSql"),
        }

    if not connexions:
        return {
            "error": (
                f"Aucune <connexion nom=... > trouvee dans {connexions_path}. "
                f"Format inattendu ou fichier vide. P-A."
            ),
            "source": str(connexions_path),
        }

    if target_connexion:
        # Lookup case-insensitive
        match = next(
            (v for k, v in connexions.items() if k.lower() == target_connexion.lower()),
            None,
        )
        return {"connexion": match, "source": str(connexions_path)}

    return {"connexions": connexions, "source": str(connexions_path)}


# ----------------------------------------------------------------------------
# Cross-check : base_effective Harmony vs ADO.NET (synthese R-9, R-10, R-11)
# ----------------------------------------------------------------------------


def compute_effective_databases(
    bconnect: dict | None,
    odbc: dict | None,
    ado_net: dict | None,
) -> dict:
    """Synthese cross-portes pour produire les findings de coherence transverse.

    Applique la regle d'override BCONNECT : `base_effective_Harmony` =
    `BCONNECT[DATABASE]` si present, sinon `ODBC_registry[Database]`. Compare
    avec `base_effective_ADO_NET` (chaine ADO.NET de connexions.xml) et produit
    les findings Cas A (warning) vs Cas B (error).

    Args :
        bconnect : sortie de parse_bconnect_from_fhsql() ou None / {"error":...}
        odbc     : sortie de read_odbc_dsn() ou None / {"error":...}
        ado_net  : dict de la connexion ADO.NET (sortie de
                   parse_connexions_xml(..., target_connexion=...)) ou None

    Retourne :
      {
        "base_effective_Harmony_32": str | None,
        "base_effective_Harmony_64": str | None,
        "base_effective_ADO_NET":     str | None,
        "harmony_uses_override":      bool,    # True si BCONNECT DATABASE override le registre
        "findings": list[dict]                  # [{severity, rule, message, ...}, ...]
      }
    """
    findings = []
    bconnect_db = None
    odbc_32_db = None
    odbc_64_db = None
    ado_db = None

    if bconnect and "pairs" in bconnect:
        bconnect_db = bconnect.get("database")
    if odbc and not odbc.get("error"):
        if odbc.get("32bit"):
            odbc_32_db = odbc["32bit"].get("Database")
        if odbc.get("64bit"):
            odbc_64_db = odbc["64bit"].get("Database")
    if ado_net and "connexion" in ado_net and ado_net["connexion"]:
        ado_db = ado_net["connexion"].get("database")

    harmony_uses_override = bconnect_db is not None

    # base_effective_Harmony : override BCONNECT prime, sinon registre par bitness
    effective_32 = bconnect_db if bconnect_db else odbc_32_db
    effective_64 = bconnect_db if bconnect_db else odbc_64_db

    # Cas A -- registre 32/64 divergent mais override identique
    if (
        odbc_32_db is not None
        and odbc_64_db is not None
        and odbc_32_db != odbc_64_db
    ):
        if bconnect_db is not None:
            # Override identique -> warning (cas A)
            findings.append({
                "severity": "warning",
                "rule": "coherence-bitness-bconnect-override",
                "message": (
                    f"Registre ODBC divergent 32-bit/64-bit sur Database "
                    f"(32-bit='{odbc_32_db}', 64-bit='{odbc_64_db}') mais BCONNECT "
                    f"override les deux a '{bconnect_db}'. Configuration fonctionnelle "
                    f"mais inhabituelle -- le registre 64-bit est ignore au runtime."
                ),
                "odbc_32bit_database": odbc_32_db,
                "odbc_64bit_database": odbc_64_db,
                "bconnect_database": bconnect_db,
            })
        else:
            # Pas d'override -> les 2 bitness vraiment divergent (Harmony 32 vs 64)
            findings.append({
                "severity": "error",
                "rule": "coherence-bitness-no-override",
                "message": (
                    f"Registre ODBC divergent 32-bit/64-bit sur Database "
                    f"(32-bit='{odbc_32_db}', 64-bit='{odbc_64_db}') et BCONNECT ne "
                    f"contient pas de DATABASE override. Harmony 32 vs 64 pointent "
                    f"sur des bases differentes -- bug latent selon le bitness de l'outil."
                ),
                "odbc_32bit_database": odbc_32_db,
                "odbc_64bit_database": odbc_64_db,
            })

    # Cas B -- Harmony vs ADO.NET divergent
    if effective_32 is not None and ado_db is not None and effective_32 != ado_db:
        findings.append({
            "severity": "error",
            "rule": "coherence-harmony-adonet",
            "message": (
                f"Vraie incoherence cross-portes : base_effective_Harmony (32-bit)="
                f"'{effective_32}' != base_effective_ADO_NET='{ado_db}'. Les deux "
                f"portes pointent sur des bases differentes -- toute operation qui "
                f"utilise les deux portes en sequence cassera (typique : creation via "
                f"Harmony puis lecture via RecordSql)."
            ),
            "base_effective_Harmony_32": effective_32,
            "base_effective_ADO_NET": ado_db,
        })
    if (
        effective_64 is not None
        and ado_db is not None
        and effective_64 != ado_db
        and effective_64 != effective_32  # eviter doublon avec ligne precedente
    ):
        findings.append({
            "severity": "error",
            "rule": "coherence-harmony-adonet",
            "message": (
                f"Vraie incoherence cross-portes : base_effective_Harmony (64-bit)="
                f"'{effective_64}' != base_effective_ADO_NET='{ado_db}'."
            ),
            "base_effective_Harmony_64": effective_64,
            "base_effective_ADO_NET": ado_db,
        })

    return {
        "base_effective_Harmony_32": effective_32,
        "base_effective_Harmony_64": effective_64,
        "base_effective_ADO_NET": ado_db,
        "harmony_uses_override": harmony_uses_override,
        "findings": findings,
    }


# Mini-CLI de test/debug
if __name__ == "__main__":
    import argparse
    import json

    p = argparse.ArgumentParser(description="Test du module de resolution harmony (debug)")
    p.add_argument("--harmony-path", help="Chemin harmony a resoudre (ex: /specifs/X/fichiers/)")
    p.add_argument("--discover", action="store_true", help="Decouvrir DIVA_ROOT via R-5")
    args = p.parse_args()

    if args.discover:
        json.dump(discover_diva_root(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    elif args.harmony_path:
        info = discover_diva_root()
        if "error" in info:
            print(json.dumps(info, indent=2, ensure_ascii=False))
            sys.exit(2)
        diva_root = info["diva_root"]
        cfg_path = Path(diva_root) / "sys" / "divaltopath.cfg"
        cfg = parse_divaltopath_cfg(cfg_path)
        if "error" in cfg:
            print(json.dumps(cfg, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(2)
        dhfd_path = Path(info["fconfig_dhfd"]) if info.get("fconfig_dhfd") else None
        result = resolve_harmony_path(args.harmony_path, cfg["aliases"], dhfd_path, diva_root)
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        p.print_help()
