"""
Pousse toutes les entrees RETEX nouvelles ou modifiees vers GitHub.

Pipeline :
  1. Parse RETEX-skills.md (via parse_retex_entries.py vendore inline)
  2. Lit le tracking .retex-pushed.json
  3. Pour chaque entree :
     - Si absente du tracking -> create
     - Si presente + hash inchange -> skip
     - Si presente + hash modifie -> comment sur l'issue
  4. Met a jour le tracking
  5. Ecrit le log

Sortie JSON sur stdout :

    {
      "pushed":  [{"id": "R-028", "issue": 42, "action": "created", "url": "..."}, ...],
      "skipped": [{"id": "R-001", "reason": "unchanged"}, ...],
      "errors":  [{"id": "R-029", "error": "..."}, ...]
    }

Mode --backfill : ignore le tracking, pousse TOUT (avec confirmation explicite via
--yes-i-want-to-push-everything pour eviter les accidents).

Exit codes : 0 succes (meme partiel), 1 erreur applicative bloquante, 2 erreur d'usage.
"""

import argparse
import atexit
import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Verrou : un seul push a la fois par workspace. Le hook PostToolUse lance un process
# DETACHE a chaque Edit/Write sur RETEX-skills.md ; ecrire une entree en deux editions
# successives lancait donc deux pushes concurrents, qui lisaient le meme tracking vide
# et creaient chacun leur issue. Mesure sur le depot partenaire : 19 paires de doublons
# sur 19 avaient ce profil -- meme ID, meme hash, quelques secondes d'ecart.
VERROU_NOM = ".retex-push.lock"
VERROU_PERIME_S = 300  # au-dela, on considere le verrou abandonne (process tue)

# En-tete d'entree dans le fichier RETEX, pour la renumerotation des doublons.
# Doit rester aligne sur HEADER_RE de parse_retex_entries.py.
HEADER_FICHIER_RE = re.compile(
    r"^(?P<diese>#{1,3})(?P<sep1>\s*)(?P<id>R-\d+)(?P<reste>\s*--\s*\d{4}-\d{2}-\d{2}\s*--\s*.+?)[ \t]*$",
    re.MULTILINE,
)

# Memes regles que parse_retex_entries.py : un commentaire n'est structurel que si son
# ouvrant demarre une ligne. Sert ici a ignorer les en-tetes R-NNN qui vivent DANS un
# bloc commente (le gabarit livre en contient un) : ils ne sont pas des entrees, donc
# ils ne doivent ni compter ni etre renumerotes.
HTML_COMMENT_BLOC_RE = re.compile(r"^[ \t]*<!--.*?-->[ \t]*\n?", re.DOTALL | re.MULTILINE)
HTML_COMMENT_OUVERT_RE = re.compile(r"^[ \t]*<!--.*\Z", re.DOTALL | re.MULTILINE)


def detect_pushed_by() -> str:
    """Detecte l'identite a citer dans le footer de l'issue.

    Ordre de resolution :
      1. env var USER_EMAIL (override explicite)
      2. git config user.name + user.email -> "Nom <email>"
      3. gh api user .login + .email -> "GitHub-login <email>" ou juste "GitHub-login"
      4. fallback generique
    """
    if os.environ.get("USER_EMAIL"):
        return os.environ["USER_EMAIL"]

    git_name = _safe_run(["git", "config", "--get", "user.name"])
    git_email = _safe_run(["git", "config", "--get", "user.email"])
    if git_name and git_email:
        return f"{git_name} <{git_email}>"
    if git_email:
        return git_email

    gh_login = _safe_run(["gh", "api", "user", "--jq", ".login"])
    gh_email = _safe_run(["gh", "api", "user", "--jq", ".email"])
    if gh_login and gh_email and gh_email != "null":
        return f"{gh_login} <{gh_email}>"
    if gh_login:
        return f"{gh_login} (GitHub)"

    return "partenaire (identite non detectee)"


def _safe_run(cmd: list) -> str:
    """Lance une commande, renvoie stdout strip ou chaine vide si echec/absent."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        if r.returncode == 0:
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return ""


def log(log_path: Path, msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def _parse_ids(raw: str) -> set:
    """Parse la valeur de --ids en un set d'entiers.

    Accepte plusieurs formes : 'R-021,R-022', 'R-21 R-22', '21,22'. On ne compare
    que la partie numerique -> insensible aux zeros de tete et au prefixe R-.
    """
    out = set()
    for tok in re.split(r"[,\s]+", (raw or "").strip()):
        if not tok:
            continue
        m = re.search(r"(\d+)", tok)
        if m:
            out.add(int(m.group(1)))
    return out


def parse_entries(retex_file: Path) -> list:
    r = subprocess.run(
        ["py", str(SCRIPT_DIR / "parse_retex_entries.py"), "--retex-file", str(retex_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"parse_retex_entries.py echec : {r.stderr}")
    data = json.loads(r.stdout)
    return {"entries": data.get("entries", []), "warnings": data.get("warnings", [])}


def _creer_verrou(chemin: Path) -> bool:
    """Cree le fichier verrou de facon atomique. False s'il existe deja."""
    try:
        fd = os.open(str(chemin), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    except OSError:
        return False
    try:
        os.write(fd, f"{os.getpid()} {datetime.now().isoformat(timespec='seconds')}\n".encode())
    finally:
        os.close(fd)
    return True


def prendre_verrou(chemin: Path, log_path: Path) -> bool:
    """Verrou exclusif inter-process. False si un autre push tourne deja.

    Le hook lance un push DETACHE a chaque ecriture du RETEX ; deux editions rapprochees
    produisent deux pushes simultanes qui lisent le meme tracking et creent chacun leur
    issue. Le second n'a rien a faire : ses entrees seront poussees par le premier, ou au
    prochain appel. Il abandonne donc silencieusement.

    Un verrou plus vieux que VERROU_PERIME_S est considere abandonne (process tue avant
    son nettoyage) et repris : sans ca, un seul crash bloquerait tous les pushes suivants.
    """
    if _creer_verrou(chemin):
        return True
    age = None
    try:
        age = time.time() - chemin.stat().st_mtime
    except OSError:
        pass
    if age is not None and age > VERROU_PERIME_S:
        log(log_path, f"WARN verrou perime ({int(age)}s), repris : {chemin}")
        with contextlib.suppress(OSError):
            chemin.unlink()
        return _creer_verrou(chemin)
    return False


def relacher_verrou(chemin: Path) -> None:
    with contextlib.suppress(OSError):
        chemin.unlink()


def _hash_marque(texte: str) -> str | None:
    m = re.search(r"_Hash\s*:\s*([0-9a-f]{6,})_", texte or "")
    return m.group(1) if m else None


def _gh_lire(chemin: str, jq: str) -> str | None:
    """Appelle `gh api` en lecture. None si l'appel echoue, quelle qu'en soit la cause."""
    try:
        r = subprocess.run(
            ["gh", "api", chemin, "--jq", jq],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    return r.stdout if r.returncode == 0 else None


def hashes_connus_de_l_issue(repo: str, numero: int) -> list:
    """Tous les hash que GitHub connait pour cette issue, du plus faisant foi au moins.

    Sert a arbitrer un conflit de numerotation : l'issue dit ce que GitHub contient
    REELLEMENT, la ou le tracking ne dit que ce que le dernier passage a cru.

    Le corps d'une issue est un INSTANTANE fige a la creation : une mise a jour n'ajoute
    qu'un commentaire, le corps ne bouge jamais. Ne regarder que le corps faisait donc
    echouer l'arbitrage des qu'une entree avait ete modifiee une fois -- mesure en
    conditions reelles : le hash courant etait dans un commentaire, pas dans le corps.

    L'ordre porte la decision quand plusieurs candidats correspondent :
      1. le corps  -- c'est ce que l'issue EST, et c'est ce qui departage une issue
         abimee par le ping-pong, dont les commentaires portent les DEUX contenus ;
      2. les commentaires, du plus recent au plus ancien -- l'etat le plus frais connu.

    Liste vide si la lecture echoue (gh absent, non authentifie, reseau, issue
    supprimee) : l'appelant se rabat alors sur le tracking puis sur l'ordre du fichier.
    """
    corps = _gh_lire(f"repos/{repo}/issues/{numero}", ".body")
    if corps is None:
        return []
    out = []
    h = _hash_marque(corps)
    if h:
        out.append(h)
    # Les commentaires sont un PLUS : leur lecture peut echouer sans invalider le corps.
    bruts = _gh_lire(f"repos/{repo}/issues/{numero}/comments", ".[].body")
    if bruts:
        # `--jq .[].body` rend un corps par ligne ; un corps multiligne est donc eclate.
        # On ne cherche qu'un marqueur par bloc, l'eclatement est sans consequence.
        vus = set(out)
        trouves = [x for x in (_hash_marque(l) for l in bruts.splitlines()) if x]
        for h in reversed(trouves):            # du plus recent au plus ancien
            if h not in vus:
                vus.add(h)
                out.append(h)
    return out


def _zones_commentees(texte: str) -> list:
    """Spans (debut, fin) des blocs de commentaire HTML structurels."""
    spans = [m.span() for m in HTML_COMMENT_BLOC_RE.finditer(texte)]
    reste = HTML_COMMENT_OUVERT_RE.search(texte)
    if reste and not any(d <= reste.start() < f for d, f in spans):
        spans.append(reste.span())
    return spans


def _entetes_vivants(texte: str) -> list:
    """En-tetes R-NNN du fichier, hors blocs commentes, dans l'ordre du fichier.

    Le gabarit livre contient un `### R-001` d'exemple dans un bloc commente : il n'est
    pas une entree, donc il ne doit ni compter ni etre renumerote. On l'ecarte avec les
    memes regles que le parseur, pour que les deux voient exactement les memes entrees.
    """
    zones = _zones_commentees(texte)
    return [
        m for m in HEADER_FICHIER_RE.finditer(texte)
        if not any(d <= m.start() < f for d, f in zones)
    ]


def choisir_qui_garde(groupe: list, eid: str, tracking: dict, repo: str, log_path: Path) -> int:
    """Parmi des entrees partageant un meme R-NNN, renvoie l'index de celle qui le garde.

    Cascade, du plus sur au plus degrade :
      1. une fiche de tracking porte un numero d'issue -> on lit les hash que GitHub
         connait pour elle (corps d'abord, puis commentaires du plus recent au plus
         ancien) et on designe l'entree qui correspond au premier d'entre eux  [exact]
      2. sinon / echec -> l'entree dont le hash est celui du tracking [le tracking peut
         etre incoherent si le ping-pong a eu lieu]
      3. sinon -> la premiere du fichier [aucune n'est poussee : le choix est indifferent,
         mesure -- les deux regles donnent le meme resultat]
    """
    fiche = tracking.get(eid) or {}
    numero = fiche.get("issue")
    if numero and repo:
        connus = hashes_connus_de_l_issue(repo, numero)
        if connus:
            # On parcourt les hash dans l'ordre de confiance, PAS les entrees : sur une
            # issue abimee par le ping-pong, les deux entrees figurent dans l'historique
            # et c'est le corps qui doit trancher.
            for rang, h_issue in enumerate(connus):
                for i, e in enumerate(groupe):
                    h = e.get("hash") or ""
                    if h == h_issue or h.startswith(h_issue) or h_issue.startswith(h):
                        origine = "corps" if rang == 0 else f"commentaire ({rang}e hash connu)"
                        log(log_path, f"INFO conflit {eid} : arbitre par l'issue #{numero}, {origine} (hash {h_issue[:8]})")
                        return i
            log(log_path, f"WARN conflit {eid} : aucun des {len(connus)} hash connus de l'issue "
                          f"#{numero} ne correspond a une entree, repli sur le tracking")
        else:
            log(log_path, f"WARN conflit {eid} : issue #{numero} illisible, repli sur le tracking")
    h_suivi = fiche.get("hash")
    if h_suivi:
        for i, e in enumerate(groupe):
            if e.get("hash") == h_suivi:
                log(log_path, f"INFO conflit {eid} : arbitre par le tracking (hash {h_suivi[:8]})")
                return i
    log(log_path, f"INFO conflit {eid} : aucune entree deja poussee, ordre du fichier")
    return 0


def renumeroter_doublons(retex_file: Path, entries: list, tracking: dict, repo: str,
                         log_path: Path, dry_run: bool) -> tuple:
    """Donne un numero libre aux entrees qui partagent un R-NNN. Renvoie (entries, changements).

    La regle d'unicite existe deja cote partenaire ("Chaque entree porte un identifiant
    unique (R-NNN)") mais rien ne la faisait respecter : le parseur acceptait deux R-024
    sans un mot. Consequence mesuree -- les deux entrees se partagent une seule case de
    tracking, chacune trouve le hash de l'autre, conclut "modifiee" et commente l'issue de
    l'autre. A chaque passage. #557 a accumule 111 commentaires alternes de cette facon.

    On renumerote AVANT tout appel GitHub : les numeros qui partent sont donc uniques, et
    la cle `R-NNN` du tracking redevient fiable.
    """
    par_id = {}
    for e in entries:
        par_id.setdefault(e["id"], []).append(e)
    conflits = {i: g for i, g in par_id.items() if len(g) > 1}
    if not conflits:
        return entries, []

    # `newline=""` DES LA LECTURE : sans lui, `read_text` traduit les CRLF en LF en
    # memoire et la reecriture -- qui, elle, ne traduit pas -- rend un fichier LF.
    # Le journal du partenaire ne doit pas changer de fins de ligne parce qu'on a
    # renumerote une entree.
    with retex_file.open(encoding="utf-8", newline="") as f:
        texte = f.read()
    entetes = _entetes_vivants(texte)
    if len(entetes) != len(entries):
        # Desaccord entre ce que le parseur voit et ce que je vois dans le fichier :
        # je ne sais pas quelle ligne renumeroter, donc je ne touche a rien.
        log(log_path, f"ERROR renumerotation abandonnee : {len(entetes)} en-tetes dans le fichier "
                      f"pour {len(entries)} entrees parsees")
        return entries, []

    utilises = {int(m.group("id").split("-")[1]) for m in entetes}
    libre = max(utilises) + 1
    changements = []
    for eid, groupe in conflits.items():
        garde = choisir_qui_garde(groupe, eid, tracking, repo, log_path)
        for i, e in enumerate(groupe):
            if i == garde:
                continue
            nouveau = f"R-{libre:03d}"
            utilises.add(libre)
            libre += 1
            changements.append({"ancien": eid, "nouveau": nouveau, "titre": e.get("titre", ""),
                                "index": entries.index(e)})
            e["id"] = nouveau

    if dry_run:
        for c in changements:
            log(log_path, f"DRY-RUN renumerotation {c['ancien']} -> {c['nouveau']} ({c['titre'][:50]})")
        return entries, changements

    # Reecriture : on remplace le seul champ `id` de la ligne d'en-tete concernee, de la
    # fin vers le debut pour que les offsets restent valides.
    for c in sorted(changements, key=lambda x: -x["index"]):
        m = entetes[c["index"]]
        ligne = f"{m.group('diese')}{m.group('sep1')}{c['nouveau']}{m.group('reste')}"
        texte = texte[:m.start()] + ligne + texte[m.end():]

    # Ecriture atomique : le fichier du partenaire est son journal, on ne le laisse jamais
    # a moitie ecrit. Encodage et fins de ligne preserves de bout en bout : `newline=""`
    # a la LECTURE comme a l'ECRITURE -- l'un sans l'autre ne suffit pas.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, dir=str(retex_file.parent),
                                         encoding="utf-8", newline="") as tf:
            tf.write(texte)
            tmp = tf.name
        os.replace(tmp, str(retex_file))
        tmp = None
    finally:
        if tmp:
            with contextlib.suppress(OSError):
                os.unlink(tmp)

    for c in changements:
        log(log_path, f"OK renumerotation {c['ancien']} -> {c['nouveau']} ({c['titre'][:50]})")
    return entries, changements


def push_one(entry: dict, config_path: Path, source_file: Path, pushed_by: str, update_issue: int | None) -> dict:
    """Invoque push_entry.py et renvoie son JSON de sortie."""
    cmd = [
        "py",
        str(SCRIPT_DIR / "push_entry.py"),
        "--config",
        str(config_path),
        "--source-file",
        str(source_file),
        "--user-email",
        pushed_by,
        "--entry-json",
        json.dumps(entry, ensure_ascii=False),
    ]
    if update_issue is not None:
        cmd.extend(["--update", "--issue", str(update_issue)])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        return json.loads(r.stdout) if r.stdout else {"action": "error", "error": r.stderr.strip()}
    except json.JSONDecodeError:
        return {"action": "error", "error": f"sortie non-JSON : {r.stdout[:200]}"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retex-file", required=True, help="Chemin vers RETEX-skills.md")
    parser.add_argument("--config", help="Chemin vers .retex-github.json (defaut : a cote du retex-file)")
    parser.add_argument("--tracking", help="Chemin vers .retex-pushed.json (defaut : a cote du retex-file)")
    parser.add_argument("--log", help="Chemin du fichier log (defaut : a cote du retex-file)")
    parser.add_argument(
        "--user-email",
        default=None,
        help="Identite a citer dans le footer. Defaut : detection auto via git config / gh api user.",
    )
    parser.add_argument("--backfill", action="store_true", help="Ignore le tracking, repousse tout")
    parser.add_argument("--yes-i-want-to-push-everything", action="store_true", help="Confirmation pour --backfill")
    parser.add_argument("--dry-run", action="store_true", help="Affiche ce qui serait pousse sans appeler gh")
    parser.add_argument(
        "--ids",
        help="Restreint le push aux seuls IDs listes (ex: R-021,R-022). Les entrees non "
        "listees ne sont ni poussees ni trackees (elles partiront a un prochain appel sans filtre).",
    )
    args = parser.parse_args()

    retex_file = Path(args.retex_file).resolve()
    if not retex_file.exists():
        print(json.dumps({"errors": [{"error": f"RETEX file introuvable : {retex_file}"}]}, ensure_ascii=False))
        return 1

    retex_dir = retex_file.parent
    # Resolution de config en cascade : --config explicite, sinon config LOCALE
    # (a cote du RETEX), sinon config GLOBALE utilisateur (~/.claude/).
    # Le tracking, lui, reste TOUJOURS local : la numerotation R-NNN est propre a
    # chaque workspace, un tracking partage provoquerait des collisions d'ID.
    local_config = retex_dir / ".retex-github.json"
    global_config = Path.home() / ".claude" / ".retex-github.json"
    if args.config:
        config_path = Path(args.config)
    elif local_config.exists():
        config_path = local_config
    else:
        config_path = global_config
    tracking_path = Path(args.tracking) if args.tracking else retex_dir / ".retex-pushed.json"
    log_path = Path(args.log) if args.log else retex_dir / ".retex-push.log"

    if not config_path.exists():
        msg = (
            "RETEX push NON CONFIGURE -- aucune config trouvee "
            f"(ni locale '{local_config}', ni globale '{global_config}'). "
            "Lancer : py .../init_config.py --retex-file <RETEX-skills.md> --repo <owner/name> "
            "(ajouter --global pour une config partagee entre workspaces). "
            f"Aucun RETEX n'est perdu : les entrees restent dans '{retex_file}' et restent "
            "poussables ensuite (--backfill --yes-i-want-to-push-everything si elles ont ete "
            "ecrites avant la configuration)."
        )
        print(json.dumps({"errors": [{"error": msg}]}, ensure_ascii=False))
        log(log_path, "Abort: RETEX push non configure (config locale+globale absentes)")
        return 1

    if args.backfill and not args.yes_i_want_to_push_everything:
        print(
            json.dumps(
                {
                    "errors": [
                        {
                            "error": "--backfill requiert aussi --yes-i-want-to-push-everything (garde-fou)"
                        }
                    ]
                }
            )
        )
        return 2

    # Verrou : un seul push a la fois par workspace. Pris AVANT la lecture du tracking,
    # sinon deux pushes concurrents liraient le meme etat et creeraient chacun leur issue.
    # Relache par atexit : couvre la sortie normale et l'exception ; le delai de peremption
    # couvre le process tue.
    verrou_path = retex_dir / VERROU_NOM
    if not prendre_verrou(verrou_path, log_path):
        log(log_path, "INFO push ignore : un autre push tourne deja (verrou pris)")
        print(json.dumps(
            {"pushed": [], "skipped": [{"reason": "push-concurrent-ignore"}], "errors": []},
            ensure_ascii=False))
        return 0
    atexit.register(relacher_verrou, verrou_path)

    # Charger tracking
    tracking = {}
    if tracking_path.exists() and not args.backfill:
        try:
            tracking = json.loads(tracking_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log(log_path, f"WARN: tracking illisible, repart de zero ({tracking_path})")

    try:
        parsed = parse_entries(retex_file)
    except Exception as e:
        log(log_path, f"ERROR: parse_entries : {e}")
        print(json.dumps({"errors": [{"error": str(e)}]}, ensure_ascii=False))
        relacher_verrou(verrou_path)
        return 1
    entries = parsed["entries"]
    for w in parsed.get("warnings", []):
        log(log_path, f"WARN parsing: {w}")

    # Unicite des R-NNN, AVANT tout appel GitHub : deux entrees sous un meme numero se
    # partagent une seule case de tracking et finissent par commenter l'issue l'une de
    # l'autre, indefiniment. On leur donne un numero libre ici, donc ce qui part vers
    # GitHub est unique et la cle `R-NNN` du tracking redevient fiable.
    try:
        repo_cible = json.loads(config_path.read_text(encoding="utf-8")).get("repo", "")
    except (OSError, json.JSONDecodeError):
        repo_cible = ""
    try:
        entries, renumerotations = renumeroter_doublons(
            retex_file, entries, tracking, repo_cible, log_path, args.dry_run)
    except Exception as e:
        # La renumerotation ne doit jamais empecher un push : au pire on pousse avec les
        # numeros d'origine, ce qui est le comportement d'avant.
        log(log_path, f"ERROR renumerotation ignoree : {e}")
        renumerotations = []

    # Resolution de l'identite (auto-detection si non specifie)
    pushed_by = args.user_email or detect_pushed_by()
    log(log_path, f"INFO pushed_by={pushed_by}")

    ids_filter = _parse_ids(args.ids) if args.ids else None

    pushed = []
    skipped = []
    errors = []

    for entry in entries:
        eid = entry["id"]

        # Filtre --ids : ne traiter que les IDs demandes ; les autres restent non pousses
        # ET non trackes (ils partiront a un prochain appel sans filtre).
        if ids_filter is not None:
            m = re.search(r"\d+", eid)
            if not m or int(m.group()) not in ids_filter:
                skipped.append({"id": eid, "reason": "hors-filtre-ids"})
                continue

        # Categorie=OK : par convention non poussable vers GitHub (cf. reference/issue-format.md).
        # Skip AVANT tout appel gh, sinon gh echoue sur le label absent 'categorie:ok'.
        cat = re.sub(r"\([^)]*\)", "", (entry.get("categorie") or "")).strip().upper()
        if cat == "OK":
            skipped.append({"id": eid, "reason": "categorie-ok-non-poussable"})
            continue

        existing = tracking.get(eid) if not args.backfill else None

        if existing and existing.get("hash") == entry["hash"]:
            skipped.append({"id": eid, "reason": "unchanged"})
            continue

        if args.dry_run:
            action = "would_update" if existing else "would_create"
            pushed.append({"id": eid, "action": action, "issue": existing.get("issue") if existing else None})
            continue

        update_issue = existing.get("issue") if existing else None
        result = push_one(entry, config_path, retex_file, pushed_by, update_issue)
        action = result.get("action")

        if action in ("created", "updated"):
            issue_num = result.get("issue") or (existing.get("issue") if existing else None)
            tracking[eid] = {
                "issue":     issue_num,
                "hash":      entry["hash"],
                "url":       result.get("url") or (existing.get("url") if existing else None),
                "last_push": datetime.now().isoformat(timespec="seconds"),
            }
            pushed.append({"id": eid, "issue": issue_num, "action": action, "url": result.get("url")})
            log(log_path, f"OK {action} {eid} -> issue#{issue_num}")
        else:
            errors.append({"id": eid, "error": result.get("error", "unknown")})
            log(log_path, f"ERROR {eid} : {result.get('error', 'unknown')}")

    # Sauver tracking
    if not args.dry_run:
        tracking_path.write_text(
            json.dumps(tracking, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    sortie = {"pushed": pushed, "skipped": skipped, "errors": errors}
    # Les renumerotations modifient le FICHIER du partenaire : elles doivent etre visibles
    # dans la sortie, pas seulement dans le log. Il a pu citer l'ancien numero ailleurs.
    if renumerotations:
        sortie["renumerotations"] = [
            {"ancien": c["ancien"], "nouveau": c["nouveau"], "titre": c["titre"]}
            for c in renumerotations
        ]
    print(json.dumps(sortie, ensure_ascii=False, indent=2))
    # Relache des la fin du push, sans attendre la sortie du process : le verrou ne doit
    # couvrir que la section critique. atexit reste enregistre comme filet pour le chemin
    # d'exception.
    relacher_verrou(verrou_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
