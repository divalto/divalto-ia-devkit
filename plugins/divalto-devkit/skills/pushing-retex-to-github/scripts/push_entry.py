"""
Pousse UNE entree RETEX vers GitHub via `gh` CLI.

Cree une issue (ou commente une issue existante si --update --issue N).
Lit l'entree au format JSON (cf. parse_retex_entries.py) sur stdin ou --entry-json.
Lit la config (.retex-github.json) pour determiner repo + labels.

Sortie JSON sur stdout :

    {
      "action": "created" | "updated" | "skipped" | "error",
      "issue":  <int ou null>,
      "url":    "<url>",
      "labels": [...],
      "error":  "<message si action=error>"
    }

Exit codes : 0 succes, 1 erreur applicative, 2 erreur d'usage.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def load_config(path: Path) -> dict:
    if not path.exists():
        return {
            "labels_default":    ["retex"],
            "labels_categorie":  {},
            "labels_severite":   {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def derive_labels(entry: dict, config: dict) -> list:
    labels = list(config.get("labels_default", ["retex"]))
    categorie = (entry.get("categorie") or "").strip()
    severite = (entry.get("severite") or "").strip()

    # categorie peut contenir plusieurs valeurs separees par + / ,
    # On retire D'ABORD toute note entre parentheses : elle peut contenir une virgule
    # (ex "BUG-SKILL (au depart, c'etait SUGGESTION)") qui serait sinon prise pour un
    # separateur et produirait un label parasite ("c'etait suggestion)").
    if categorie:
        cat_map = config.get("labels_categorie", {})
        cat_clean = re.sub(r"\([^)]*\)", "", categorie)
        for tok in [t.strip() for t in re.split(r"[+,]", cat_clean)]:
            tok_clean = tok.strip().upper()
            if not tok_clean:
                continue
            label = cat_map.get(tok_clean)
            if label:
                labels.append(label)
            else:
                labels.append(f"categorie:{tok_clean.lower()}")

    if severite:
        sev_map = config.get("labels_severite", {})
        sev_clean = re.sub(r"\([^)]*\)", "", severite).strip().upper()
        label = sev_map.get(sev_clean)
        if label:
            labels.append(label)
        else:
            labels.append(f"severite:{sev_clean.lower()}")

    # dedup en preservant l'ordre
    seen = set()
    out = []
    for lbl in labels:
        if lbl and lbl not in seen:
            seen.add(lbl)
            out.append(lbl)
    return out


def format_body(entry: dict, source_file: str, user_email: str) -> str:
    parts = [
        f"> RETEX pousse automatiquement depuis le poste de {user_email} via le skill",
        f"> `pushing-retex-to-github`. Source : `{source_file}`.",
        "",
        "## Resultat",
        "",
        entry.get("resultat") or "_(non renseigne)_",
        "",
        "## Skill(s) concerne(s)",
        "",
        entry.get("skills") or "_(non renseigne)_",
        "",
        "## Description",
        "",
        entry.get("description") or "_(non renseigne)_",
        "",
        "## Reproduction",
        "",
        entry.get("reproduction") or "_(non renseigne)_",
        "",
        "## Contournement",
        "",
        entry.get("contournement") or "_(non renseigne)_",
        "",
        "## Suggestion",
        "",
        entry.get("suggestion") or "_(non renseigne)_",
        "",
        "---",
        "",
        f"_Date d'origine : {entry.get('date')}_  ",
        f"_ID local : {entry.get('id')}_  ",
        # Hash COMPLET (40 car.) et non tronque : ce marqueur est lu par le push pour
        # arbitrer un conflit de numerotation -- quand deux entrees portent le meme
        # R-NNN, celle dont le hash correspond au corps de l'issue deja creee garde son
        # numero. Un hash tronque a 8 restait exploitable, mais la comparaison exacte
        # ne coute rien ici. Le hash ne depend que des 8 champs du RETEX : allonger ce
        # pied de page ne modifie aucun hash et ne declenche donc aucun faux "modifie".
        f"_Hash : {entry.get('hash', '')}_",
    ]
    body = "\n".join(parts)
    # Tronquer si > 60k chars (limite GitHub ~65k)
    if len(body) > 60000:
        body = body[:59000] + "\n\n_[Tronque -- corps original > 60k chars]_"
    return body


def gh_available() -> bool:
    try:
        r = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def gh_authenticated() -> bool:
    try:
        r = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_gh_with_body(cmd_base: list, body: str):
    """Lance `gh` en passant le corps via un fichier temporaire UTF-8 (`--body-file`).

    Evite tout re-encodage du corps par le codepage de la ligne de commande Windows
    (cause de mojibake constatee, cf. issues #279/#338/#347). Fichier ecrit en UTF-8,
    fins de ligne \\n (rendu markdown identique), supprime dans tous les cas.
    """
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8", newline="\n"
        ) as tf:
            tf.write(body)
            tmp = tf.name
        cmd = cmd_base + ["--body-file", tmp]
        return subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
        )
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def read_issue_labels(repo: str, issue_number: int) -> list:
    """Relit les labels REELLEMENT poses sur l'issue.

    GitHub ignore silencieusement les labels passes a la creation si le compte n'a
    pas le droit triage/push (cf. #351) : `gh issue create --label X` sort en code 0
    sans avertissement. On relit donc l'etat reel pour ne pas affirmer un effet non obtenu.
    """
    try:
        r = subprocess.run(
            ["gh", "issue", "view", str(issue_number), "--repo", repo,
             "--json", "labels", "--jq", ".labels[].name"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        if r.returncode == 0:
            return [x.strip() for x in r.stdout.splitlines() if x.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return []


def create_issue(repo: str, title: str, body: str, labels: list) -> tuple:
    """Cree une issue GitHub via `gh`. Retourne (issue_number, url) ou leve."""
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title]
    for lbl in labels:
        cmd.extend(["--label", lbl])
    r = _run_gh_with_body(cmd, body)
    if r.returncode != 0:
        raise RuntimeError(f"gh issue create echec : {r.stderr.strip()}")
    # Sortie attendue : URL de l'issue sur la derniere ligne
    url = r.stdout.strip().splitlines()[-1]
    # Extraire le numero
    try:
        issue_number = int(url.rsplit("/", 1)[-1])
    except ValueError:
        issue_number = None
    return issue_number, url


def comment_issue(repo: str, issue_number: int, body: str) -> str:
    cmd = ["gh", "issue", "comment", str(issue_number), "--repo", repo]
    r = _run_gh_with_body(cmd, body)
    if r.returncode != 0:
        raise RuntimeError(f"gh issue comment echec : {r.stderr.strip()}")
    return r.stdout.strip()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Chemin vers .retex-github.json")
    parser.add_argument("--source-file", required=True, help="Chemin du RETEX-skills.md source (pour le body)")
    parser.add_argument("--user-email", default="aschmitt@divalto.com", help="Email a citer dans le footer")
    parser.add_argument("--entry-json", help="JSON inline de l'entree. Sinon stdin ou --entry-file.")
    parser.add_argument("--entry-file", help="Chemin d'un fichier JSON contenant l'entree (alternative a --entry-json et stdin, utile sous PowerShell qui mangle les pipes binaires)")
    parser.add_argument("--update", action="store_true", help="Mode commentaire d'issue existante")
    parser.add_argument("--issue", type=int, help="Numero d'issue a commenter (avec --update)")
    args = parser.parse_args()

    if not gh_available():
        print(json.dumps({"action": "error", "error": "gh CLI absent", "issue": None, "url": None, "labels": []}))
        return 1
    if not gh_authenticated():
        print(json.dumps({"action": "error", "error": "gh non authentifie", "issue": None, "url": None, "labels": []}))
        return 1

    config = load_config(Path(args.config))
    repo = config.get("repo")
    if not repo:
        print(json.dumps({"action": "error", "error": "repo absent de la config", "issue": None, "url": None, "labels": []}))
        return 1

    if args.entry_json:
        entry = json.loads(args.entry_json)
    elif args.entry_file:
        entry = json.loads(Path(args.entry_file).read_text(encoding="utf-8"))
    else:
        entry = json.loads(sys.stdin.read())

    labels = derive_labels(entry, config)
    title = f"[{entry.get('id')}] {entry.get('titre')}"
    body = format_body(entry, args.source_file, args.user_email)

    try:
        if args.update:
            if not args.issue:
                print(json.dumps({"action": "error", "error": "--update requiert --issue N", "issue": None, "url": None, "labels": labels}))
                return 2
            comment_body = f"**Mise a jour de l'entree RETEX (nouveau hash : `{entry.get('hash', '')[:8]}`)**\n\n---\n\n{body}"
            comment_issue(repo, args.issue, comment_body)
            print(json.dumps({"action": "updated", "issue": args.issue, "url": None, "labels": labels}))
        else:
            issue_number, url = create_issue(repo, title, body, labels)
            applied = read_issue_labels(repo, issue_number) if issue_number else []
            out = {"action": "created", "issue": issue_number, "url": url,
                   "labels": applied, "labels_requested": labels}
            missing = [lbl for lbl in labels if lbl not in applied]
            if missing:
                out["warning"] = (
                    "labels demandes non appliques (compte sans droit triage/push ?) : "
                    + ", ".join(missing)
                )
            print(json.dumps(out, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"action": "error", "error": str(e), "issue": None, "url": None, "labels": labels}))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
