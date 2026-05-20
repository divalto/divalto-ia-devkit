"""
Hook PreToolUse : empeche la modification des skills distribues.

Bloque les appels Edit/Write ciblant .claude/skills/.
Installe par install.py lors de la distribution des skills DIVA.

Usage (automatique via hooks Claude Code) :
    Recoit le JSON du tool call sur stdin, exit 2 pour bloquer.
"""

import json
import os
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Normaliser les separateurs
    normalized = file_path.replace("\\", "/")

    if "/.claude/skills/" in normalized or normalized.startswith(".claude/skills/"):
        rel = normalized.split("/.claude/skills/")[-1] if "/.claude/skills/" in normalized else normalized
        skill_name = rel.split("/", 1)[0] if rel else ""

        # Exception : les skills workspace-only (prefixe workspace-) sont editables
        # par l'architecte du workspace. Ils ne sont jamais distribues chez un
        # collaborateur (double filtre dans dist/build_zip.py + install.py).
        if skill_name.startswith("workspace-"):
            sys.exit(0)

        tool = data.get("tool_name", "?")
        print(
            f"BLOQUE : modification interdite sur les skills distribues.\n"
            f"\n"
            f"  Fichier : .claude/skills/{rel}\n"
            f"  Outil   : {tool}\n"
            f"\n"
            f"Les skills DIVA sont distribues en lecture seule.\n"
            f"Pour toute modification, contactez l'administrateur des skills.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
