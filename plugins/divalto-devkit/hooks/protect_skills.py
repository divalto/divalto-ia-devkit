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

    # Resoudre un chemin relatif contre le cwd fourni par Claude Code : sinon un
    # Write/Edit a chemin relatif (cwd deja dans .claude/skills/) contourne la
    # protection (la detection par sous-chaine ne verrait pas ".claude/skills/").
    if not os.path.isabs(file_path):
        cwd = data.get("cwd", "")
        if cwd:
            file_path = os.path.join(cwd, file_path)

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
            f"BLOQUE : ecriture refusee sous .claude/skills/{skill_name}/ .\n"
            f"\n"
            f"  Fichier : .claude/skills/{rel}\n"
            f"  Outil   : {tool}\n"
            f"\n"
            f"Sous .claude/skills/, seuls les skills de WORKSPACE (nom prefixe 'workspace-')\n"
            f"sont editables. Les skills DIVA distribues sont en lecture seule (volontaire).\n"
            f"\n"
            f"  - Vous CREEZ un skill a vous (workspace) ? Nommez-le avec le prefixe 'workspace-'.\n"
            f"  - Vous voulez faire EVOLUER un skill distribue ? Passez par le RETEX :\n"
            f"    ajoutez une entree dans RETEX-skills.md (elle sera traitee puis republiee).",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
