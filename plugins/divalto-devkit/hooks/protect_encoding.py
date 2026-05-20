"""
Hook PreToolUse : empeche la corruption d'encodage des fichiers DIVA.

Bloque les appels Edit/Write ciblant les fichiers texte Divalto
(.dhsp, .dhsq, .dhsd, .dhsf, .dhpt, .dhps) car l'outil Edit de Claude
convertit silencieusement ISO-8859-1 en UTF-8, corrompant les accents.

Redirige vers le skill writing-diva-files qui preserve l'encodage.

Usage (automatique via hooks Claude Code) :
    Recoit le JSON du tool call sur stdin, exit 2 pour bloquer.
"""

import json
import sys

DIVA_EXTENSIONS = (".dhsp", ".dhsq", ".dhsd", ".dhsf", ".dhpt", ".dhps")


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Normaliser et verifier l'extension
    normalized = file_path.replace("\\", "/").lower()

    if normalized.endswith(DIVA_EXTENSIONS):
        tool = data.get("tool_name", "?")
        ext = "." + normalized.rsplit(".", 1)[-1]
        print(
            f"BLOQUE : les fichiers Divalto ({ext}) doivent etre ecrits via le skill writing-diva-files.\n"
            f"\n"
            f"  Fichier : {file_path}\n"
            f"  Outil   : {tool}\n"
            f"\n"
            f"Pourquoi : l'outil {tool} de Claude convertit silencieusement ISO-8859-1 en UTF-8,\n"
            f"ce qui corrompt les accents (e accent -> FFFD). Le compilateur xwin7 refuse ensuite\n"
            f"le fichier (ex: 'Profil absent du projet' car 'developpement' est illisible).\n"
            f"\n"
            f"Solution : utiliser le skill writing-diva-files qui preserve l'encodage ISO-8859-1 + CRLF.\n"
            f"Exemple : Skill(\"writing-diva-files\") puis scripts/write_file.py --path ... --content ...",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
