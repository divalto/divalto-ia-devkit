"""
Hook PreToolUse : garde-fou de version pour les outils MCP diva-mcp.

Verifie trois choses pour tout outil dont le nom matche `mcp__*diva-mcp*__*` :

  1. L'argument 'version' (str) ou 'versions' (list[str]) est present dans
     tool_input.
  2. Les versions fournies sont valides (X.7 a X.13).
  3. Les versions ciblees sont effectivement mentionnees par l'utilisateur
     dans le transcript JSONL (lecture en streaming de la totalite du
     fichier, filtree sur la voix user uniquement — outputs LLM, system
     reminders et bodies de tool_result sont ignores). Les reponses via
     AskUserQuestion sont reconnues (champ structure toolUseResult.answers
     OU body tool_result avec signature "User has answered your
     questions:" / "Your questions have been answered:").

Exemptions : outils listes dans EXEMPT_TOOLS (ne necessitent pas de version).

Recoit le JSON du tool call sur stdin.
Exit 0 = laisser passer.
Exit 2 = bloquer (message d'erreur sur stderr, visible par le LLM Claude).
"""

import json
import os
import re
import sys


VALID_VERSIONS = {"X.7", "X.8", "X.9", "X.10", "X.11", "X.12", "X.13"}

# Outils diva-mcp qui n'ont PAS besoin de version (probe / introspection
# pure, ne dependant d'aucune base ERP precise). Vide pour l'instant.
EXEMPT_TOOLS = set()

# Detecte une mention X.<N> dans le transcript user (case-insensitive)
USER_VERSION_RE = re.compile(r"\bX\.(7|8|9|10|11|12|13)\b", re.IGNORECASE)

# Detecte les tools du serveur diva-mcp (suffixe __<basename> apres le
# prefix mcp__<...>diva-mcp<...>__). Suffisamment large pour couvrir les
# variantes plugin (mcp__plugin_<plugin>_diva-mcp__) et direct
# (mcp__diva-mcp__).
TOOL_NAME_RE = re.compile(r"mcp__.*diva-mcp(?:[^_]|_(?!_))*__(.+)$")


def deny(msg: str) -> None:
    print(f"BLOQUE : {msg}", file=sys.stderr)
    sys.exit(2)


def _extract_user_messages_from_path(path: str) -> list[str]:
    """Stream a JSONL transcript file, returning texts typed by the human user.

    Filters to entries where type=='user', isMeta is falsy, and message.role
    is 'user' — so we ignore assistant outputs, system reminders, skill
    descriptions, tool results, and meta inputs (like local-command
    caveats). This is the *real* user voice.

    Reads the whole file line-by-line instead of a fixed byte tail: user
    text is small compared to tool outputs, so reading everything is cheap
    and large MCP responses no longer push earlier user authorizations out
    of a sliding window. The hook stays purely user-driven — only text
    the user explicitly typed is considered.
    """
    texts: list[str] = []
    try:
        with open(path, "rb") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if obj.get("type") != "user":
                    continue
                if obj.get("isMeta"):
                    continue

                # AskUserQuestion answers are stored in a structured field
                # on the user entry: toolUseResult.answers is a dict
                # {question: answer}. Read this first — it survives wording
                # changes in the tool_result text body.
                tur = obj.get("toolUseResult")
                if isinstance(tur, dict):
                    answers = tur.get("answers")
                    if isinstance(answers, dict):
                        for v in answers.values():
                            if isinstance(v, str):
                                texts.append(v)

                msg = obj.get("message") or {}
                if msg.get("role") != "user":
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        itype = item.get("type")
                        if itype == "text":
                            texts.append(item.get("text") or "")
                        elif itype == "tool_result":
                            # tool_result entries are typically generic tool
                            # outputs (Bash stdout, etc.) — we skip those.
                            # EXCEPT replies to AskUserQuestion: the body
                            # starts with a signature line and contains the
                            # user's pick(s). The wording has changed across
                            # harness versions, so accept both known forms.
                            body = item.get("content")
                            if isinstance(body, str) and (
                                body.startswith("User has answered your questions:")
                                or body.startswith("Your questions have been answered:")
                            ):
                                texts.append(body)
    except OSError:
        return []
    return texts


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    m = TOOL_NAME_RE.match(tool_name)
    if not m:
        sys.exit(0)

    basename = m.group(1)
    if basename in EXEMPT_TOOLS:
        sys.exit(0)

    tool_input = data.get("tool_input") or {}
    raw_version = tool_input.get("version")
    raw_versions = tool_input.get("versions")

    if not raw_version and not raw_versions:
        deny(
            f"L'appel a {basename} ne specifie pas de 'version'. "
            f"Demande explicitement a l'utilisateur la version ERP cible "
            f"(une parmi {sorted(VALID_VERSIONS)}) avant de relancer cet outil."
        )

    if raw_version is not None and raw_versions:
        deny(
            f"L'appel a {basename} specifie a la fois 'version' et 'versions'. "
            f"Choisis l'un OU l'autre : 'version' (str) pour une seule version, "
            f"'versions' (list) pour comparer plusieurs versions."
        )

    if raw_version is not None:
        if not isinstance(raw_version, str):
            deny(f"'version' doit etre une string, recu {type(raw_version).__name__}.")
        wanted = {raw_version}
    else:
        if not isinstance(raw_versions, list) or not raw_versions:
            deny("'versions' doit etre une liste non vide.")
        wanted = {str(v) for v in raw_versions}

    bad = wanted - VALID_VERSIONS
    if bad:
        deny(
            f"Versions invalides : {sorted(bad)}. "
            f"Valides : {sorted(VALID_VERSIONS, key=lambda v: int(v.split('.')[1]))}."
        )

    transcript_path = (
        data.get("transcript_path")
        or os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    )
    if not transcript_path or not os.path.exists(transcript_path):
        sys.exit(0)

    user_texts = _extract_user_messages_from_path(transcript_path)
    haystack = "\n".join(user_texts)
    mentioned = {f"X.{n}" for n in USER_VERSION_RE.findall(haystack)}

    if not mentioned:
        deny(
            f"L'appel cible {sorted(wanted)} mais aucune version ERP n'a ete "
            f"explicitement mentionnee par l'utilisateur dans la conversation recente. "
            f"Demande-lui la/les version(s) cibles avant de relancer l'outil."
        )

    unaligned = wanted - mentioned
    if unaligned:
        deny(
            f"L'appel cible {sorted(wanted)} mais l'utilisateur a mentionne "
            f"{sorted(mentioned)}. Realigne avec ce qu'il a demande, ou demande "
            f"confirmation s'il veut comparer plusieurs versions."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
