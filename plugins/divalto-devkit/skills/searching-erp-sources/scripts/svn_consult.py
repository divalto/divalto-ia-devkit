#!/usr/bin/env py
"""Wrapper SVN en lecture seule pour les skills DIVA.

Source canonique : .claude/skills/searching-erp-sources/scripts/svn_consult.py
Vendoring prevu (S-13) vers : analyzing-diva-request, building-preaction-report, modifying-diva-entity.

**Principe premier** : SVN est consulte, jamais ecrit. Voir docs/SVN-CONSULTATION.md.

Expose 6 fonctions publiques :
    svn_info(path, timeout=None) -> dict
    svn_log(path, limit=10, revision_range=None, search=None, verbose=False, timeout=None) -> dict
    svn_blame(file_path, revision='HEAD', line_start=None, line_end=None, timeout=None) -> dict
    svn_diff(path, rev_from, rev_to='HEAD', timeout=None) -> dict
    svn_cat(path, revision='HEAD', timeout=None) -> dict
    svn_list(path, depth='immediates', timeout=None) -> dict

Toutes retournent un dict standardise :
    {
        'subcommand': str,      # nom de la primitive invoquee
        'ok': bool,             # succes de l'operation
        'available': bool,      # SVN disponible (binary + reseau)
        'data': Any,            # donnees parsees si ok (forme depend de la primitive)
        'error': str | None,    # message d'erreur si !ok
        'duration_s': float,    # duree d'execution
    }

Whitelist enforcement : toute sous-commande hors {log, blame, diff, cat, info, list}
leve SvnWriteAttempted (sous-classe de NotImplementedError).

Dry-run : definir SVN_DRY_RUN=1 dans l'environnement pour obtenir des stubs sans
appeler le binaire svn (utile pour tests unitaires skills).
"""

import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# -----------------------------------------------------------------
# Constantes (cf docs/SVN-CONSULTATION.md section 6.2)
# -----------------------------------------------------------------

ALLOWED = {"log", "blame", "diff", "cat", "info", "list"}

BLACKLISTED = {
    "commit", "ci", "merge", "mergeinfo", "resolve", "resolved",
    "update", "switch", "copy", "move", "rename", "delete", "rm",
    "mkdir", "lock", "unlock", "propset", "propdel", "propedit",
    "revert", "import", "cleanup", "export",
}

TIMEOUTS = {
    "info": 5,
    "list": 5,
    "log": 15,
    "cat": 10,
    "blame": 60,
    "diff": 30,
}

MAX_TIMEOUT = 120
BINARY_EXTENSIONS = {".dhfi"}  # ISAM : svn log OK, blame/diff non pertinents


# -----------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------

class SvnWriteAttempted(NotImplementedError):
    """Tentative d'execution d'une sous-commande SVN ecrivante ou inconnue."""


# -----------------------------------------------------------------
# Internals
# -----------------------------------------------------------------

def _validate_subcommand(subcmd):
    if subcmd in BLACKLISTED:
        raise SvnWriteAttempted(
            f"Sous-commande '{subcmd}' blacklistee. SVN est en lecture seule. "
            f"Voir docs/SVN-CONSULTATION.md section 1.2."
        )
    if subcmd not in ALLOWED:
        raise SvnWriteAttempted(
            f"Sous-commande '{subcmd}' non whitelistee. "
            f"Autorisees : {sorted(ALLOWED)}."
        )


def _svn_binary_available():
    return shutil.which("svn") is not None


def _make_result(subcommand, ok=False, available=True, data=None, error=None, duration_s=0.0, raw=""):
    return {
        "subcommand": subcommand,
        "ok": ok,
        "available": available,
        "data": data,
        "error": error,
        "duration_s": duration_s,
        "raw": raw,
    }


def _run(subcommand, args, timeout=None):
    _validate_subcommand(subcommand)

    if os.environ.get("SVN_DRY_RUN") == "1":
        return _make_result(subcommand, ok=True, data={"dry_run": True, "args": args})

    if not _svn_binary_available():
        return _make_result(subcommand, ok=False, available=False,
                            error="svn binary not found in PATH")

    if timeout is None:
        timeout = TIMEOUTS[subcommand]
    if timeout > MAX_TIMEOUT:
        raise ValueError(f"Timeout {timeout}s > MAX_TIMEOUT={MAX_TIMEOUT}s")

    cmd = ["svn", subcommand] + list(args)
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return _make_result(subcommand, ok=False, available=True,
                            error=f"Timeout {timeout}s depasse",
                            duration_s=time.time() - t0)
    except FileNotFoundError:
        return _make_result(subcommand, ok=False, available=False,
                            error="svn binary not found")

    duration = time.time() - t0

    try:
        stdout = proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        stdout = proc.stdout.decode("iso-8859-1", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        available = not any(m in stderr for m in ("Unable to connect", "Unknown hostname"))
        return _make_result(subcommand, ok=False, available=available,
                            error=stderr.strip(), duration_s=duration, raw=stdout)

    return _make_result(subcommand, ok=True, duration_s=duration, raw=stdout)


# -----------------------------------------------------------------
# Primitives publiques
# -----------------------------------------------------------------

def svn_info(path, timeout=None):
    """Retourne {url, revision, last_author, last_revision, last_date, wc_root}."""
    r = _run("info", [str(path), "--xml"], timeout=timeout)
    if not r["ok"] or r["data"] is not None:  # dry-run: data deja populated
        return r
    try:
        root = ET.fromstring(r["raw"])
        entry = root.find("entry")
        if entry is None:
            r["ok"] = False
            r["error"] = "No <entry> in svn info output"
            return r
        url = entry.findtext("url") or ""
        rev = int(entry.get("revision") or 0)
        commit = entry.find("commit")
        wc = entry.find("wc-info")
        r["data"] = {
            "url": url,
            "revision": rev,
            "last_author": (commit.findtext("author") if commit is not None else "") or "",
            "last_revision": int(commit.get("revision") or 0) if commit is not None else 0,
            "last_date": (commit.findtext("date") if commit is not None else "") or "",
            "wc_root": (wc.findtext("wcroot-abspath") if wc is not None else None),
        }
    except ET.ParseError as e:
        r["ok"] = False
        r["error"] = f"XML parse error: {e}"
    return r


def svn_log(path, limit=10, revision_range=None, search=None, verbose=False, timeout=None):
    """Retourne une liste d'entries [{revision, author, date, message}]."""
    args = [str(path), "--xml", f"--limit={limit}"]
    if revision_range:
        args.extend(["-r", revision_range])
    if search:
        args.extend(["--search", search])
    if verbose:
        args.append("-v")
    r = _run("log", args, timeout=timeout)
    if not r["ok"] or r["data"] is not None:  # dry-run: data deja populated
        return r
    try:
        root = ET.fromstring(r["raw"])
        entries = []
        for e in root.findall("logentry"):
            entries.append({
                "revision": int(e.get("revision") or 0),
                "author": (e.findtext("author") or ""),
                "date": (e.findtext("date") or ""),
                "message": (e.findtext("msg") or ""),
            })
        r["data"] = entries
    except ET.ParseError as e:
        r["ok"] = False
        r["error"] = f"XML parse error: {e}"
    return r


def svn_blame(file_path, revision="HEAD", line_start=None, line_end=None,
              use_merge_history=True, timeout=None):
    """Retourne une liste [{line, revision, author, date}]. Refuse binaires .dhfi.

    Note : SVN 1.8 ne supporte pas d'option native pour limiter aux lignes N,M.
    Si line_start/line_end sont fournis, le blame complet est recupere puis filtre cote Python.
    Pour gros fichiers, preferer un timeout plus long (cf docs/SVN-CONSULTATION.md 6.2).
    """
    ext = Path(str(file_path)).suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return _make_result("blame", ok=False, available=True,
                            error=f"{ext} est binaire (ISAM). Utiliser svn_log pour l'historique.")
    args = [str(file_path), "-r", revision, "--xml"]
    if use_merge_history:
        args.append("-g")
    r = _run("blame", args, timeout=timeout)
    if not r["ok"] or r["data"] is not None:  # dry-run: data deja populated
        return r
    try:
        root = ET.fromstring(r["raw"])
        entries = []
        target = root.find("target")
        if target is not None:
            for e in target.findall("entry"):
                commit = e.find("commit")
                line = int(e.get("line-number") or 0)
                if line_start is not None and line < line_start:
                    continue
                if line_end is not None and line > line_end:
                    continue
                entries.append({
                    "line": line,
                    "revision": int(commit.get("revision") or 0) if commit is not None else 0,
                    "author": (commit.findtext("author") if commit is not None else "") or "",
                    "date": (commit.findtext("date") if commit is not None else "") or "",
                })
        r["data"] = entries
    except ET.ParseError as e:
        r["ok"] = False
        r["error"] = f"XML parse error: {e}"
    return r


def svn_diff(path, rev_from, rev_to="HEAD", timeout=None):
    """Retourne le diff brut (texte unifie) entre deux revisions."""
    ext = Path(str(path)).suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return _make_result("diff", ok=False, available=True,
                            error=f"{ext} est binaire (ISAM). Utiliser svn_log pour l'historique.")
    r = _run("diff", [str(path), "-r", f"{rev_from}:{rev_to}"], timeout=timeout)
    if r["ok"] and r["data"] is None:  # dry-run: preserver data
        r["data"] = r["raw"]
    return r


def svn_diff_local(path, timeout=None):
    """Retourne le diff entre le Working Copy et la revision BASE (modifs locales non committees).

    Cas d'usage principal : avant de modifier un fichier, detecter si quelqu'un a deja
    des modifs locales en cours (fichier en etat 'M' dans svn status). Distinct de
    svn_log qui ne voit que les commits pousses au depot.

    Sortie data (si ok) : texte diff unifie. Vide si pas de modif locale.
    Refuse les binaires ISAM (.dhfi) comme svn_diff.
    """
    ext = Path(str(path)).suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return _make_result("diff", ok=False, available=True,
                            error=f"{ext} est binaire (ISAM). svn diff non exploitable.")
    # Pas de -r = compare WC au BASE local (modifs non committees)
    r = _run("diff", [str(path)], timeout=timeout)
    if r["ok"] and r["data"] is None:  # dry-run: preserver data
        r["data"] = r["raw"]
    return r


def svn_cat(path, revision="HEAD", timeout=None):
    """Retourne le contenu d'un fichier a une revision."""
    r = _run("cat", [str(path), "-r", revision], timeout=timeout)
    if r["ok"] and r["data"] is None:
        r["data"] = r["raw"]
    return r


def svn_list(path, depth="immediates", timeout=None):
    """Retourne une liste de noms d'entrees."""
    r = _run("list", [str(path), f"--depth={depth}"], timeout=timeout)
    if r["ok"] and r["data"] is None:
        r["data"] = [line.strip() for line in r["raw"].splitlines() if line.strip()]
    return r


# -----------------------------------------------------------------
# Self-test (execute en CLI)
# -----------------------------------------------------------------

def _self_test(wc_path):
    """Test minimaliste des 6 primitives. Lecture seule uniquement."""
    print(f"Self-test svn_consult sur : {wc_path}")
    print(f"  SVN binary available : {_svn_binary_available()}")
    print(f"  SVN_DRY_RUN : {os.environ.get('SVN_DRY_RUN', '0')}")
    print()

    tests = [
        ("info",   lambda: svn_info(wc_path)),
        ("list",   lambda: svn_list(wc_path)),
        ("log",    lambda: svn_log(wc_path, limit=3)),
    ]
    # cat/blame/diff necessitent un fichier specifique
    # Chercher un .dhsp de taille raisonnable (<500 lignes) pour tester blame rapidement
    for candidate in ("A5/source/a5ep.dhsp", "A5/source/a5sp.dhsp", "A5/fichier/a5dd.dhsd"):
        f = Path(wc_path) / candidate
        if f.exists() and f.stat().st_size < 50_000:
            tests.append((f"cat[{candidate.split('/')[-1]}]",
                          lambda fp=str(f): svn_cat(fp, revision="HEAD")))
            tests.append((f"log_file[{candidate.split('/')[-1]}]",
                          lambda fp=str(f): svn_log(fp, limit=2)))
            break
    dhfi = Path(wc_path) / "A5" / "fichier" / "a5f.dhfi"
    if dhfi.exists():
        tests.append(("blame_binary_rejected", lambda: svn_blame(str(dhfi))))
        tests.append(("diff_binary_rejected", lambda: svn_diff(str(dhfi), "1000", "HEAD")))

    results = {}
    for name, fn in tests:
        try:
            r = fn()
            results[name] = r
            status = "OK" if r["ok"] else ("UNAVAIL" if not r["available"] else "FAIL")
            err = f" | err={r['error'][:80]}" if r["error"] else ""
            print(f"  {name:25} [{status}] dur={r['duration_s']:.2f}s{err}")
        except Exception as e:
            print(f"  {name:25} [EXCEPTION] {type(e).__name__}: {e}")
            results[name] = {"exception": str(e)}

    # Test blacklist
    print()
    print("  Blacklist enforcement :")
    for bad in ["commit", "merge", "update", "revert"]:
        try:
            _validate_subcommand(bad)
            print(f"    {bad:10} [FAIL] -- should have raised")
        except SvnWriteAttempted:
            print(f"    {bad:10} [OK] rejected")

    # Test whitelist
    print()
    print("  Whitelist accept :")
    for good in ALLOWED:
        try:
            _validate_subcommand(good)
            print(f"    {good:10} [OK] accepted")
        except SvnWriteAttempted:
            print(f"    {good:10} [FAIL] -- should have passed")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Self-test du module svn_consult (lib vendore).")
    parser.add_argument("wc", nargs="?", default=r"{CHEMIN_ERP_STANDARD}",
                        help="Working copy SVN a utiliser pour le self-test.")
    args = parser.parse_args()
    _self_test(args.wc)
