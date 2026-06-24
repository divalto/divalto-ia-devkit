"""
Localise le `.mcp.json` du plugin divalto-devkit chez le partenaire.

Strategie de recherche (premier match gagne) :

1. Argument explicite `--mcp-path` (override manuel, toujours prioritaire)
2. Variable d'env `CLAUDE_PLUGIN_ROOT` -> `${CLAUDE_PLUGIN_ROOT}/.mcp.json`
3. Remontee depuis le repertoire courant a la recherche d'un `plugins/divalto-devkit/.mcp.json` ou d'un `.mcp.json` adjacent
4. Install marketplace (emplacement reellement charge par Claude Code) :
   - cache versionne : `~/.claude/plugins/cache/<owner>/divalto-devkit/<version>/.mcp.json`
   - source marketplace : `~/.claude/plugins/marketplaces/<owner>/plugins/divalto-devkit/.mcp.json`
   - + variantes `~/.config/claude/...` (Mac / Linux), version la plus recente d'abord
5. Chemins par defaut Windows / Mac / Linux :
   - `~/.claude/plugins/divalto-devkit/.mcp.json`
   - `~/.claude/plugins/divalto@divalto/plugins/divalto-devkit/.mcp.json`
   - `~/.config/claude/plugins/divalto-devkit/.mcp.json`

Sortie JSON sur stdout : {"path": "<chemin>", "exists": bool, "found_via": "<methode>"}.

Exit codes : 0 si trouve, 1 si introuvable, 2 si erreur d'usage.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def _version_key(name: str):
    """Cle de tri d'un nom de repertoire de version ('0.0.10' > '0.0.2')."""
    parts = []
    for chunk in re.split(r"[._-]", name):
        parts.append((0, int(chunk)) if chunk.isdigit() else (1, chunk))
    return parts


def _marketplace_candidates(home: Path) -> list:
    """Decouvre les `.mcp.json` poses par la marketplace Claude Code.

    Couvre les emplacements reellement charges au demarrage, absents des
    chemins par defaut historiques :
      - cache d'install (versionne) :
        ~/.claude/plugins/cache/<owner>/divalto-devkit/<version>/.mcp.json
      - source marketplace :
        ~/.claude/plugins/marketplaces/<owner>/plugins/divalto-devkit/.mcp.json
    + variantes ~/.config/claude (Mac/Linux). Version la plus recente en premier.
    """
    found = []
    for base in (home / ".claude" / "plugins", home / ".config" / "claude" / "plugins"):
        if not base.is_dir():
            continue
        cache = base / "cache"
        if cache.is_dir():
            for p in sorted(cache.glob("*/divalto-devkit/*/.mcp.json"),
                            key=lambda q: _version_key(q.parent.name), reverse=True):
                owner = p.parent.parent.parent.name
                candidates_via = f"cache marketplace ({owner}/{p.parent.name})"
                found.append((p, candidates_via))
        markets = base / "marketplaces"
        if markets.is_dir():
            for p in sorted(markets.glob("*/plugins/divalto-devkit/.mcp.json")):
                found.append((p, "source marketplace"))
    return found


def candidate_paths(cwd: Path) -> list:
    """Retourne la liste ordonnee des chemins candidats."""
    candidates = []

    # 1. CLAUDE_PLUGIN_ROOT
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidates.append((Path(plugin_root) / ".mcp.json", "CLAUDE_PLUGIN_ROOT"))

    # 1b. Install marketplace (cache + source) — emplacement reel chez le partenaire
    candidates.extend(_marketplace_candidates(Path.home()))

    # 2. Remontee depuis cwd
    for parent in [cwd, *cwd.parents]:
        # Le repertoire courant pourrait deja etre la racine du plugin
        adjacent = parent / ".mcp.json"
        if adjacent != (Path(plugin_root) / ".mcp.json" if plugin_root else None):
            candidates.append((adjacent, f"adjacent au cwd ({parent.name})"))
        # Ou bien le plugin est imbrique
        nested = parent / "plugins" / "divalto-devkit" / ".mcp.json"
        candidates.append((nested, f"plugins/divalto-devkit sous {parent.name}"))
        nested2 = parent / "plugin" / ".mcp.json"  # cote workspace
        candidates.append((nested2, f"plugin/ sous {parent.name}"))

    # 3. Chemins Claude Code par defaut
    home = Path.home()
    defaults = [
        home / ".claude" / "plugins" / "divalto-devkit" / ".mcp.json",
        home / ".claude" / "plugins" / "divalto@divalto" / "plugins" / "divalto-devkit" / ".mcp.json",
        home / ".config" / "claude" / "plugins" / "divalto-devkit" / ".mcp.json",
    ]
    for d in defaults:
        candidates.append((d, "Claude Code defaut"))

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-path", help="Chemin explicite (override). Renvoye tel quel si fourni.")
    parser.add_argument("--cwd", default=str(Path.cwd()), help="Repertoire de depart pour la remontee")
    parser.add_argument("--dry-run-show-candidates", action="store_true", help="Affiche tous les candidats sans verifier l'existence")
    args = parser.parse_args()

    if args.mcp_path:
        p = Path(args.mcp_path)
        print(json.dumps({"path": str(p), "exists": p.exists(), "found_via": "--mcp-path explicite"}, ensure_ascii=False))
        return 0 if p.exists() else 1

    cwd = Path(args.cwd).resolve()
    candidates = candidate_paths(cwd)

    if args.dry_run_show_candidates:
        out = [{"path": str(p), "via": via, "exists": p.exists()} for p, via in candidates]
        print(json.dumps({"candidates": out}, ensure_ascii=False, indent=2))
        return 0

    for path, via in candidates:
        if path.exists():
            print(json.dumps({"path": str(path), "exists": True, "found_via": via}, ensure_ascii=False))
            return 0

    print(
        json.dumps(
            {
                "path": None,
                "exists": False,
                "found_via": None,
                "tried": [{"path": str(p), "via": via} for p, via in candidates],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
