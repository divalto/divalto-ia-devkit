"""
Initialise la configuration locale pour pushing-retex-to-github :

1. Cree .retex-github.json (config repo cible + mapping labels)
2. Cree .retex-pushed.json en marquant TOUTES les entrees existantes du RETEX
   comme "deja poussees" (issue=null, hash=actuel). Cela evite le backfill accidentel
   au premier hook : seules les futures entrees R-NNN seront poussees.

Sortie JSON sur stdout : {"config": "<path>", "tracking": "<path>", "entries_marked": N}.

Exit codes : 0 succes, 1 erreur applicative, 2 erreur d'usage.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

DEFAULT_CONFIG = {
    "repo": "",
    "labels_default": ["retex"],
    "labels_categorie": {
        "BUG-SKILL":    "bug-skill",
        "BUG-DOC":      "bug-doc",
        "SUGGESTION":   "suggestion",
        "ENV":          "env",
        "CLAUDE-TOOL":  "claude-tool",
    },
    "labels_severite": {
        "CRITIQUE": "severite:critique",
        "HAUTE":    "severite:haute",
        "MOYENNE":  "severite:moyenne",
        "BASSE":    "severite:basse",
        "INFO":     "severite:info",
    },
}


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retex-file", required=True, help="Chemin vers RETEX-skills.md")
    parser.add_argument("--repo", required=True, help="Repo GitHub cible (owner/name)")
    parser.add_argument("--force", action="store_true", help="Overwrite config existante")
    parser.add_argument("--reset-tracking", action="store_true", help="Reinitialise le tracking (efface l'existant)")
    args = parser.parse_args()

    retex_file = Path(args.retex_file).resolve()
    if not retex_file.exists():
        print(f"ERROR: RETEX introuvable : {retex_file}", file=sys.stderr)
        return 1

    retex_dir = retex_file.parent
    config_path = retex_dir / ".retex-github.json"
    tracking_path = retex_dir / ".retex-pushed.json"

    # Config
    if config_path.exists() and not args.force:
        print(f"ERROR: config existe deja : {config_path}. Utiliser --force pour overwrite.", file=sys.stderr)
        return 1
    config = dict(DEFAULT_CONFIG)
    config["repo"] = args.repo
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    # Tracking : marquer toutes les entrees existantes comme deja poussees (sans issue)
    if tracking_path.exists() and not args.reset_tracking:
        print(f"WARN: tracking existe deja : {tracking_path}. Non touche. Utiliser --reset-tracking pour reinitialiser.", file=sys.stderr)
        entries_marked = 0
    else:
        try:
            entries = parse_entries(retex_file)
        except Exception as e:
            print(f"ERROR: parsing RETEX : {e}", file=sys.stderr)
            return 1
        tracking = {}
        now = datetime.now().isoformat(timespec="seconds")
        for entry in entries:
            tracking[entry["id"]] = {
                "issue":     None,
                "hash":      entry["hash"],
                "url":       None,
                "last_push": None,
                "skipped_at_init": now,
            }
        tracking_path.write_text(
            json.dumps(tracking, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        entries_marked = len(tracking)

    print(
        json.dumps(
            {
                "config":         str(config_path),
                "tracking":       str(tracking_path),
                "entries_marked": entries_marked,
                "repo":           args.repo,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
