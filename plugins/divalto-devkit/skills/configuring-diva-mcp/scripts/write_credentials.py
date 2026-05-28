"""
Patche un `.mcp.json` pour injecter le header X-Api-Key dans la config de diva-mcp.

Construit le header au format documente :

    X-Api-Key: <site>-<env>@<apikey>

Atomic write : ecrit dans un fichier `.tmp` adjacent puis rename. Backup `.bak` cree
avant ecriture (s'il n'existait pas deja).

Sortie JSON sur stdout :

    {
      "status":   "ok" | "error",
      "mcp_path": "<chemin>",
      "backup":   "<chemin .bak>" | null,
      "header":   "X-Api-Key: <site>-<env>@<masque>",
      "error":    "<message si status=error>"
    }

L'apikey est **masquee** dans la sortie (10 premiers chars + "..." + 4 derniers) pour
ne pas la logger en clair. Le fichier `.mcp.json` lui contient la cle complete.

Exit codes : 0 succes, 1 erreur applicative, 2 erreur d'usage.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def mask_apikey(apikey: str) -> str:
    if len(apikey) <= 14:
        return "*" * len(apikey)
    return f"{apikey[:10]}...{apikey[-4:]}"


def validate_inputs(site: str, env: str, apikey: str) -> str | None:
    """Renvoie un message d'erreur si validation echoue, None sinon."""
    if not site or not re.match(r"^[A-Za-z0-9_-]+$", site):
        return f"site invalide : '{site}'. Attendu : alphanumerique / tirets / underscores."
    if not env or not re.match(r"^[A-Za-z0-9_-]+$", env):
        return f"env invalide : '{env}'. Attendu : alphanumerique / tirets / underscores."
    if not apikey or len(apikey) < 8:
        return f"apikey invalide : longueur {len(apikey)}. Attendu : >= 8 caracteres."
    return None


def patch_mcp_json(mcp_path: Path, site: str, env: str, apikey: str) -> dict:
    """Patche le .mcp.json en injectant le bloc headers dans la config diva-mcp.

    Supporte les deux formats Claude Code :
      - Plugin root (sans wrapper) : { "diva-mcp": {...} }
      - Project scope (avec wrapper mcpServers) : { "mcpServers": { "diva-mcp": {...} } }

    Le plugin marketplace utilise le format sans wrapper (cf. doc plugins).
    """
    text = mcp_path.read_text(encoding="utf-8")
    data = json.loads(text)

    # Determine le format
    if "mcpServers" in data and isinstance(data["mcpServers"], dict):
        servers = data["mcpServers"]
        format_used = "wrapped"
    else:
        servers = data
        format_used = "flat"

    if "diva-mcp" not in servers:
        raise RuntimeError(
            f"Section 'diva-mcp' absente du .mcp.json ({mcp_path}, format {format_used}). "
            f"Le fichier doit declarer diva-mcp avant que ce skill puisse injecter les headers."
        )

    diva = servers["diva-mcp"]
    if "headers" not in diva or not isinstance(diva["headers"], dict):
        diva["headers"] = {}
    diva["headers"]["X-Api-Key"] = f"{site}-{env}@{apikey}"

    return data


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-path", required=True, help="Chemin absolu vers le .mcp.json a patcher")
    parser.add_argument("--site", required=True, help="Code site (ex: GENEVE)")
    parser.add_argument("--env", required=True, help="Environnement (ex: PROD)")
    parser.add_argument("--apikey", required=True, help="API key diva-mcp")
    parser.add_argument("--no-backup", action="store_true", help="Ne cree pas de .bak avant ecriture")
    args = parser.parse_args()

    mcp_path = Path(args.mcp_path)
    if not mcp_path.exists():
        print(
            json.dumps({"status": "error", "error": f".mcp.json introuvable : {mcp_path}", "mcp_path": str(mcp_path), "backup": None, "header": None}),
            file=sys.stdout,
        )
        return 1

    err = validate_inputs(args.site, args.env, args.apikey)
    if err:
        print(json.dumps({"status": "error", "error": err, "mcp_path": str(mcp_path), "backup": None, "header": None}))
        return 2

    # Backup
    backup_path = None
    if not args.no_backup:
        backup_path = mcp_path.with_suffix(mcp_path.suffix + ".bak")
        if not backup_path.exists():
            backup_path.write_text(mcp_path.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        data = patch_mcp_json(mcp_path, args.site, args.env, args.apikey)
    except (json.JSONDecodeError, RuntimeError) as e:
        print(json.dumps({"status": "error", "error": str(e), "mcp_path": str(mcp_path), "backup": str(backup_path) if backup_path else None, "header": None}))
        return 1

    new_content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write(mcp_path, new_content)

    masked_header = f"X-Api-Key: {args.site}-{args.env}@{mask_apikey(args.apikey)}"
    print(
        json.dumps(
            {
                "status":   "ok",
                "mcp_path": str(mcp_path),
                "backup":   str(backup_path) if backup_path else None,
                "header":   masked_header,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
