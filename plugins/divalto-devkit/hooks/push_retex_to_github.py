"""
Hook PostToolUse : pousse les nouvelles entrees RETEX vers GitHub en arriere-plan.

Declenche apres tout Edit / Write / MultiEdit ciblant un fichier dont le nom finit par
`RETEX-skills.md`. Lance `push_new_entries.py` en arriere-plan (non bloquant) :
l'edition rend la main immediatement, le push se fait en parallele.

Mode degrade silencieux : si `gh` est absent ou non authentifie, push_new_entries.py
log l'erreur dans .retex-push.log mais sort en code 0. Le hook lui-meme exit 0 dans
tous les cas pour ne jamais bloquer l'utilisateur.

Usage (automatique via hooks Claude Code) :
    Recoit le JSON du tool call sur stdin, exit 0 systematiquement.

Enregistrement dans `.claude/settings.json` :

    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [
              {"type": "command", "command": "py \\"<chemin absolu>/push_retex_to_github.py\\""}
            ]
          }
        ]
      }
    }
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def find_skill_script() -> Path | None:
    """Tente de localiser push_new_entries.py.

    Strategie : remonter de l'emplacement du hook (.../plugin/hooks/ ou .../plugins/divalto-devkit/hooks/)
    jusqu'a trouver un repertoire contenant `skills/pushing-retex-to-github/scripts/push_new_entries.py`.
    """
    here = Path(__file__).resolve()
    # Cote workspace : plugin/hooks/ -> plugin/skills/pushing-retex-to-github/scripts/...
    # Cote plugin distribue : plugins/divalto-devkit/hooks/ -> plugins/divalto-devkit/skills/...
    candidates = [
        here.parent.parent / "skills" / "pushing-retex-to-github" / "scripts" / "push_new_entries.py",
        here.parent.parent / "plugin" / "skills" / "pushing-retex-to-github" / "scripts" / "push_new_entries.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    normalized = file_path.replace("\\", "/").lower()
    if not normalized.endswith("retex-skills.md"):
        sys.exit(0)

    script = find_skill_script()
    if script is None:
        # Skill non installe a cote du hook : on log dans le repertoire courant si possible
        try:
            log_path = Path(file_path).parent / ".retex-push.log"
            log_path.write_text(
                f"[push_retex_to_github hook] skill pushing-retex-to-github introuvable a cote du hook ({Path(__file__).parent})\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        sys.exit(0)

    # Lance en arriere-plan, non bloquant. Sur Windows, DETACHED_PROCESS = 0x00000008.
    creationflags = 0
    if os.name == "nt":
        creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

    try:
        subprocess.Popen(
            ["py", str(script), "--retex-file", file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
    except Exception:
        # Jamais bloquer l'utilisateur sur une erreur de hook
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
