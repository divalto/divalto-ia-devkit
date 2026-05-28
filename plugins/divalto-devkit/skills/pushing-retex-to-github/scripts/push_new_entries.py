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
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


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
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
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


def parse_entries(retex_file: Path) -> list:
    r = subprocess.run(
        ["py", str(SCRIPT_DIR / "parse_retex_entries.py"), "--retex-file", str(retex_file)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"parse_retex_entries.py echec : {r.stderr}")
    return json.loads(r.stdout)["entries"]


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
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout) if r.stdout else {"action": "error", "error": r.stderr.strip()}
    except json.JSONDecodeError:
        return {"action": "error", "error": f"sortie non-JSON : {r.stdout[:200]}"}


def main() -> int:
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
    args = parser.parse_args()

    retex_file = Path(args.retex_file).resolve()
    if not retex_file.exists():
        print(json.dumps({"errors": [{"error": f"RETEX file introuvable : {retex_file}"}]}, ensure_ascii=False))
        return 1

    retex_dir = retex_file.parent
    config_path = Path(args.config) if args.config else retex_dir / ".retex-github.json"
    tracking_path = Path(args.tracking) if args.tracking else retex_dir / ".retex-pushed.json"
    log_path = Path(args.log) if args.log else retex_dir / ".retex-push.log"

    if not config_path.exists():
        print(
            json.dumps(
                {
                    "errors": [
                        {
                            "error": (
                                f"Config absente : {config_path}. "
                                f"Lancer init_config.py d'abord."
                            )
                        }
                    ]
                },
                ensure_ascii=False,
            )
        )
        log(log_path, f"Abort: config absente ({config_path})")
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

    # Charger tracking
    tracking = {}
    if tracking_path.exists() and not args.backfill:
        try:
            tracking = json.loads(tracking_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log(log_path, f"WARN: tracking illisible, repart de zero ({tracking_path})")

    try:
        entries = parse_entries(retex_file)
    except Exception as e:
        log(log_path, f"ERROR: parse_entries : {e}")
        print(json.dumps({"errors": [{"error": str(e)}]}, ensure_ascii=False))
        return 1

    # Resolution de l'identite (auto-detection si non specifie)
    pushed_by = args.user_email or detect_pushed_by()
    log(log_path, f"INFO pushed_by={pushed_by}")

    pushed = []
    skipped = []
    errors = []

    for entry in entries:
        eid = entry["id"]
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

    print(json.dumps({"pushed": pushed, "skipped": skipped, "errors": errors}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
