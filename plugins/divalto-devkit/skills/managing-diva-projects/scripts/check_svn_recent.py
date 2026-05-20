#!/usr/bin/env py
"""check_svn_recent.py -- Check SVN pre-modification (S-16).

Verifie si un fichier (.dhsd / .dhsf / .dhsp) a ete modifie recemment dans SVN
avant qu'un collaborateur ne le modifie. Permet de detecter un refactor en cours
qui pourrait entrer en collision avec la modification en preparation.

Usage :
    py scripts/check_svn_recent.py --path "<chemin>" [--limit 5] [--days 30]

Sortie JSON (stdout) :
    {
        "path": "...",
        "svn_available": bool,
        "commits": [{revision, author, date, message_excerpt}, ...],  # N derniers
        "recent_count": int,       # nb de commits < days jours
        "latest_author": str,
        "latest_date": str,
        "warning": str | null,     # non-null si activite recente detectee
    }

Principe : lecture seule. Rate-limite a 1 appel (via svn_consult timeout=15s).
Degradation gracieuse si SVN indispo (retourne svn_available=false, pas d'erreur).

Voir docs/SVN-CONSULTATION.md pour la policy complete.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Vendored svn_consult
sys.path.insert(0, str(Path(__file__).parent))
try:
    from svn_consult import svn_log, svn_diff_local
except ImportError:
    svn_log = None
    svn_diff_local = None


def _parse_svn_date(s: str) -> datetime | None:
    """Parse un timestamp SVN XML (ex: '2026-04-10T18:18:18.999088Z')."""
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _compute_local_diff(path: Path) -> dict:
    """Appelle svn_diff_local et resume les modifs locales non committees.

    Retourne {has_changes, lines_added, lines_removed, diff_excerpt, error}.
    Silencieux (error=None) si fichier propre OU binaire non comparable.
    """
    out = {
        "has_changes": False,
        "lines_added": 0,
        "lines_removed": 0,
        "diff_excerpt": "",
        "error": None,
    }
    if svn_diff_local is None:
        out["error"] = "svn_diff_local non disponible"
        return out
    r = svn_diff_local(str(path))
    if not r.get("available"):
        out["error"] = f"SVN indisponible : {r.get('error', 'inconnu')[:100]}"
        return out
    if not r.get("ok"):
        err = r.get("error", "")
        # Cas binaire refuse en amont par svn_diff_local (BINARY_EXTENSIONS)
        if "binaire" in err.lower():
            out["error"] = err[:100]
            return out
        out["error"] = f"svn diff a echoue : {err[:100]}"
        return out

    diff_text = r.get("data") or ""
    if not diff_text.strip():
        # Pas de modifs locales
        return out

    # Parse diff unifie : lignes commencant par + (hors +++) = added, - (hors ---) = removed
    added = 0
    removed = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1

    out["has_changes"] = True
    out["lines_added"] = added
    out["lines_removed"] = removed
    # Extrait : premieres 30 lignes max (preserver debut du diff pour context)
    excerpt_lines = diff_text.splitlines()[:30]
    out["diff_excerpt"] = "\n".join(excerpt_lines)
    return out


def check_file(path: Path, limit: int = 5, days_threshold: int = 30,
                include_local_diff: bool = True) -> dict:
    result = {
        "path": str(path),
        "svn_available": False,
        "commits": [],
        "recent_count": 0,
        "latest_author": "",
        "latest_date": "",
        "local_changes": None,
        "warning": None,
    }
    if svn_log is None:
        result["warning"] = "svn_consult module introuvable (verifier vendoring)"
        return result

    r = svn_log(str(path), limit=limit)
    if not r.get("available", False):
        result["warning"] = f"SVN indisponible : {r.get('error', 'inconnu')[:120]}"
        return result

    result["svn_available"] = True
    if not r.get("ok"):
        result["warning"] = f"svn log a echoue : {r.get('error', 'inconnu')[:120]}"
        return result

    entries = r.get("data") or []
    threshold = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    recent = 0
    for e in entries:
        dt = _parse_svn_date(e.get("date", ""))
        msg = (e.get("message") or "").splitlines()
        result["commits"].append({
            "revision": e.get("revision"),
            "author": e.get("author", ""),
            "date": (e.get("date") or "")[:10],
            "message_excerpt": (msg[0][:100] if msg else ""),
            "recent": bool(dt and dt >= threshold),
        })
        if dt and dt >= threshold:
            recent += 1

    if entries:
        result["latest_author"] = entries[0].get("author", "")
        result["latest_date"] = (entries[0].get("date") or "")[:10]
    result["recent_count"] = recent

    # Volet S-16bis : check modifs locales non committees (svn diff WC vs BASE)
    if include_local_diff:
        result["local_changes"] = _compute_local_diff(path)

    # Warning : priorite aux modifs locales (signal plus fort que commits distants)
    lc = result["local_changes"] or {}
    if lc.get("has_changes"):
        result["warning"] = (
            f"MODIFS LOCALES NON COMMITTEES detectees (+{lc['lines_added']}/-{lc['lines_removed']} lignes). "
            f"Quelqu'un travaille deja sur ce fichier. Ne PAS modifier sans clarification : "
            f"risque d'ecraser un travail en cours."
        )
    elif recent >= 2:
        result["warning"] = (
            f"{recent} commits dans les {days_threshold} derniers jours -- refactor en cours "
            f"possible. Verifier avec l'auteur (latest: {result['latest_author']}) "
            f"avant toute modification."
        )
    elif recent == 1:
        result["warning"] = (
            f"1 commit recent (auteur: {result['latest_author']}, date: {result['latest_date']}). "
            f"Coordination recommandee."
        )
    return result


def main() -> int:
    # Windows : stdout par defaut cp1252 -> corrompt les accents DIVA dans le JSON.
    # On force UTF-8 pour coherence avec les downstream skills.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Check SVN pre-modification. Affiche les N derniers commits sur un fichier "
                    "pour detecter un refactor en cours avant modification."
    )
    ap.add_argument("--path", required=True, help="Chemin du fichier a verifier (.dhsd/.dhsf/.dhsp).")
    ap.add_argument("--limit", type=int, default=5, help="Nombre de commits a recuperer (defaut 5).")
    ap.add_argument("--days", type=int, default=30, help="Seuil 'recent' en jours (defaut 30).")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Erreur : path '{args.path}' introuvable (pas de verification SVN possible).",
              file=sys.stderr)
        return 2
    result = check_file(path, limit=args.limit, days_threshold=args.days)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
