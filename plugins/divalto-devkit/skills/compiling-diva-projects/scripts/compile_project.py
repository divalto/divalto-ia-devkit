#!/usr/bin/env python3
"""Compile un projet Divalto reel (`.dhpt`) via xwin7 en contournant le piege
d'encodage des profils avec accent (`developpement` avec `\xe9`).

Probleme adresse (2026-05-27) :
  Passer un profil accentue (`developpement`) en argument direct depuis
  PowerShell echoue silencieusement : la session PowerShell 5.1 stocke les
  chaines en UTF-16 LE, la conversion vers les arguments natifs ne preserve
  pas l'octet 0xe9 attendu par xwin7 (qui compare en ISO-8859-1). Resultat :
  ExitCode=1, log absent, friction ~20 min par tentative.

Solution :
  Generer un script .ps1 **en ISO-8859-1 + CRLF** qui contient le nom de
  profil litteral (`-profile "d\xe9veloppement"`), puis l'executer via
  l'operateur d'appel `powershell -NoProfile -Command "& '<script.ps1>'"`
  (PAS `-ExecutionPolicy Bypass -File`, bloque/signale sur poste verrouille --
  cf. #217 dans le corps). xwin7 recoit alors le profil en ISO-8859-1 natif
  et matche correctement.

Equivalent fonctionnel de `generate_harness.py` mais pour des projets
**reels** (pas des harnesses standalone) : le `.dhpt` cible existe deja,
on ne genere pas de structure mini-projet, on se contente d'orchestrer
l'appel xwin7 et le parsing du rapport.

Usage :
    py compile_project.py --project "<dhpt>" --profile "developpement" \\
        --log-path "<log.txt>"
    py compile_project.py --project "<dhpt>" --profile "developpement" \\
        --log-path "<log.txt>" --action buildall
    py compile_project.py --project "<dhpt>" --profile "developpement" \\
        --log-path "<log.txt>" --sousproject "<dhps>"
    py compile_project.py --project "<dhpt>" --profile "developpement" \\
        --log-path "<log.txt>" --sousproject "<dhps>" --source "<file.dhsf>"
    py compile_project.py --project "<dhpt>" --profile "developpement" \\
        --log-path "<log.txt>" --no-execute   # debug : genere le .ps1 sans le lancer

Sortie JSON (stdout) :
    {
        "ps1_script": "<chemin>",
        "log_file": "<chemin>",
        "action": "build|buildall",
        "executed": true|false,
        "exit_code": <int>,                  # si executed
        "success": true|false,               # si executed
        "summary": {erreurs, warnings, ...}, # si parsable
        "errors": [...],                     # si parsable
        "stdout_path": "<chemin>",           # capture stdout xwin7
        "stderr_path": "<chemin>"            # capture stderr xwin7
    }

Verdict : DELEGUE a parse_compilation.parse_report (regle unique --).
Ne fait plus le faux positif #310 (mauvais implicite : "a jour" + "N ERREUR(S) autre(s)"),
detecte les builds interrompus/abandonnes (#236), traite [TOTAL_ERRORS] en 1re classe.

Exit codes :
    0 = compilation reussie (0 erreur, aucune anomalie -- verdict parse_compilation)
    1 = erreurs de compilation / build incomplet OU erreur utilisateur (input invalide)
    2 = erreur interne (parsing rapport echoue, etc.)
    3 = .ps1 genere mais non execute (--no-execute)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Module frere (meme skill, meme dossier scripts/) : compile_project DELEGUE le verdict
# (success/errors/build_incomplet) a la regle UNIQUE de parse_compilation.
# Evite la logique inline divergente qui reproduisait le faux positif #310.
import parse_compilation


DEFAULT_XWIN7_PATH = r"C:\divalto\sys\xwin7.exe"
VALID_ACTIONS = ("build", "buildall")


def write_iso(path: Path, content: str) -> None:
    """Ecrit un fichier en ISO-8859-1 + CRLF.

    Critique pour le `.ps1` : sans cette discipline, le nom de profil accentue
    passe en argument echoue.
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    if content and not content.endswith("\r\n"):
        content += "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("iso-8859-1"))


def resolve_user(cli_user: str | None, dhpt_util: str | None = None) -> str | None:
    """Ordre de fallback (#235) : --user > util= du .dhpt > X_USER > USERNAME.

    #235 : l'ancien ordre ignorait le champ `util="..."` declare dans le .dhpt et
    tombait directement sur USERNAME Windows -> 1re compilation sous le mauvais
    utilisateur Harmony. Le `util=` du projet passe donc AVANT les fallbacks poste.
    Avertit si le user retenu differe du util= declare. Si tout est vide, retourne
    None et alerte (xwin7 risque le crash ExitCode -805306369, corruption des objets).
    """
    if cli_user:
        if dhpt_util and cli_user.strip().lower() != dhpt_util.strip().lower():
            print(f"  WARN: --user={cli_user} differe de util=\"{dhpt_util}\" declare dans le .dhpt (#235).",
                  file=sys.stderr)
        return cli_user
    if dhpt_util:
        return dhpt_util  # voie declarative du projet, avant les fallbacks poste
    env_user = os.environ.get("X_USER", "").strip()
    if env_user:
        return None  # xwin7 lira X_USER directement, ne pas passer -user
    fallback = os.environ.get("USERNAME", "").strip() or None
    if fallback:
        print(
            f"  INFO: ni --user, ni util= du .dhpt, ni X_USER -- fallback sur USERNAME={fallback}. "
            f"Verifier que c'est bien l'utilisateur Harmony attendu (#235).",
            file=sys.stderr,
        )
        return fallback
    print(
        "  WARN: ni --user, ni util=, ni X_USER, ni USERNAME -- xwin7 risque de crasher (ExitCode -805306369).",
        file=sys.stderr,
    )
    return None


def parse_util(dhpt_path: Path) -> str | None:
    """Lit le champ `util="..."` du .dhpt (utilisateur Harmony declare du projet). #235."""
    try:
        text = dhpt_path.read_text(encoding="iso-8859-1", errors="replace")
    except OSError:
        return None
    for raw in text.splitlines():
        s = raw.strip()
        if s.lower().startswith("util="):
            val = s[5:].split(",", 1)[0].strip().strip('"')
            if val:
                return val
    return None


def generate_ps1(
    xwin7_path: str,
    action: str,
    project: str,
    profile: str,
    log_path: str,
    stdout_path: str,
    stderr_path: str,
    user: str | None = None,
    sousproject: str | None = None,
    source_basename: str | None = None,
) -> str:
    """Construit le contenu PowerShell qui lance xwin7 avec le profil accentue.

    Pieces critiques :
    - Le `.ps1` doit etre ecrit en ISO-8859-1 (cf. write_iso) -- xwin7 compare
      le nom du profil sur les octets bruts en ISO-8859-1.
    - Working directory force a `C:\\divalto\\sys` (regle partagee avec
      `syncing-diva-sql`, cf. SKILL.md "Working directory obligatoire").
    - Capture stdout/stderr via `Start-Process -RedirectStandardOutput/Error`
      pour traces post-mortem.
    """
    user_arg = f"-user {user} " if user else ""

    # Construction de l'ArgumentList xwin7 (les arguments incluent les chemins
    # avec espaces, donc passage en chaine unique a Start-Process via ' '.join).
    args_parts = [
        f"-action {action}",
        user_arg.strip() if user_arg else "",
        f'-project "{project}"',
    ]
    if sousproject:
        args_parts.append(f'-sousproject "{sousproject}"')
    if source_basename:
        args_parts.append(f'-source "{source_basename}"')
    args_parts.append(f'-profile "{profile}"')
    args_parts.append(f'-output "{log_path}"')
    args_parts.append("-outputall")
    args_str = " ".join(a for a in args_parts if a)

    # cwd = dossier de xwin7.exe, DERIVE de --xwin7-path. #301 : ne PAS coder
    # "C:\divalto\sys" en dur -- sur un poste ou Divalto est ailleurs (ex. K:\Divalto\Sys),
    # un Set-Location vers un chemin inexistant fait avorter tout le .ps1 (Start-Process
    # jamais atteint) ou masque un faux "a jour".
    cwd = os.path.dirname(xwin7_path) or "C:\\divalto\\sys"
    ps1_lines = [
        "$ErrorActionPreference = 'Continue'",
        f"Set-Location '{cwd}'   # cwd = dossier de xwin7 (derive de --xwin7-path, #301)",
        f"$proc = Start-Process -FilePath '{xwin7_path}' "
        f"-ArgumentList '{args_str}' "
        "-Wait -PassThru -NoNewWindow "
        f"-RedirectStandardOutput '{stdout_path}' "
        f"-RedirectStandardError '{stderr_path}'",
        "Write-Host \"ExitCode: $($proc.ExitCode)\"",
        "exit $proc.ExitCode",
    ]
    return "\n".join(ps1_lines)


def parse_profiles(dhpt_path: Path) -> list[str]:
    """Extrait les noms de profils des sections [profil] du .dhpt (lignes 'nom=').

    Sert a valider --profile AVANT de lancer xwin7 (evite l'echec tardif
    'Profil X inexistant') et a repondre a --list-profiles -- cf. #26, #71.
    """
    try:
        text = dhpt_path.read_text(encoding="iso-8859-1", errors="replace")
    except OSError:
        return []
    profiles: list[str] = []
    in_profil = False
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("["):
            in_profil = (s.lower() == "[profil]")
            continue
        if in_profil and s.lower().startswith("nom="):
            val = s[4:].split(",", 1)[0].strip().strip('"')
            if val:
                profiles.append(val)
    return profiles


def main() -> None:
    # Sortie UTF-8 (stdout + stderr) : le verdict inclut desormais des messages
    # [ERROR]/[WARNING] accentues (via parse_compilation) ; sans ca, cp1252 casserait
    # un json.loads(utf-8) cote appelant. Meme garde-fou que parse_compilation.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
            _stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description=(
            "Compile un projet Divalto reel (.dhpt) via xwin7 en contournant le "
            "piege d'encodage des profils accentues."
        )
    )
    parser.add_argument("--project", required=True, help="Chemin absolu du .dhpt cible")
    parser.add_argument(
        "--profile",
        help='Nom du profil (peut contenir accent, ex: "developpement" avec e accent aigu). Requis sauf avec --list-profiles.',
    )
    parser.add_argument(
        "--log-path",
        help="Chemin absolu du fichier de log que xwin7 doit produire (-output). Requis sauf avec --list-profiles.",
    )
    parser.add_argument(
        "--list-profiles", action="store_true",
        help="Liste les profils declares dans le .dhpt (lecture seule) puis sort, sans compiler.",
    )
    parser.add_argument(
        "--action", default="build", choices=VALID_ACTIONS,
        help='Type de compilation. Defaut: "build" (incremental). Utiliser "buildall" pour complet.',
    )
    parser.add_argument(
        "--user",
        help="Utilisateur xwin7. Fallback: X_USER env non-vide, sinon USERNAME Windows.",
    )
    parser.add_argument(
        "--sousproject",
        help='Limite la compilation aux fichiers d\'un sous-projet ".dhps" (basename).',
    )
    parser.add_argument(
        "--source",
        help=(
            'Basename d\'un fichier source unique a compiler (ex: "gtez183_sql.dhsf"). '
            "Couplage obligatoire avec --sousproject (cf. SKILL.md piege couplage source/sousproject)."
        ),
    )
    parser.add_argument(
        "--xwin7-path", default=DEFAULT_XWIN7_PATH,
        help=f"Chemin de xwin7.exe. Defaut: {DEFAULT_XWIN7_PATH}",
    )
    parser.add_argument(
        "--ps1-dir",
        help=(
            "Repertoire ou ecrire le .ps1 genere. Defaut: meme dossier que --log-path. "
            "Utile pour separer logs/scripts."
        ),
    )
    parser.add_argument(
        "--no-execute", action="store_true",
        help="Genere uniquement le .ps1 (debug), ne lance pas xwin7. Exit code 3.",
    )

    args = parser.parse_args()

    project_path = Path(args.project).resolve()

    if not project_path.is_file():
        print(f"ERREUR: --project introuvable : {project_path}", file=sys.stderr)
        sys.exit(1)
    if not project_path.suffix.lower() == ".dhpt":
        print(
            f"ERREUR: --project doit avoir l'extension .dhpt (recu: {project_path.suffix})",
            file=sys.stderr,
        )
        sys.exit(1)

    profiles = parse_profiles(project_path)

    # --list-profiles : lecture seule, pas de compilation
    if args.list_profiles:
        json.dump({"project": str(project_path), "profiles": profiles},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.exit(0)

    if not args.profile or not args.log_path:
        print("ERREUR: --profile et --log-path sont requis (sauf avec --list-profiles).", file=sys.stderr)
        sys.exit(1)

    # Validation du profil contre les [profil] du .dhpt : evite l'echec tardif
    # "Profil X inexistant" apres demarrage de xwin7 (#26, #71). Si aucun profil
    # n'a pu etre lu (liste vide), on ne bloque pas.
    if profiles and args.profile not in profiles:
        print(json.dumps({
            "status": "error",
            "error": f"Profil '{args.profile}' absent du projet {project_path.name}.",
            "available_profiles": profiles,
            "hint": "Choisir un profil de la liste ci-dessus (ou inspecter via --list-profiles).",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

    log_path = Path(args.log_path).resolve()

    if args.source and not args.sousproject:
        print(
            "ERREUR: --source requiert --sousproject (couplage xwin7 obligatoire). "
            "Cf. SKILL.md section 'Cas avec un seul source'.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Repertoire d'accueil du .ps1 + des fichiers de capture stdout/stderr
    ps1_dir = Path(args.ps1_dir).resolve() if args.ps1_dir else log_path.parent
    ps1_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ps1_path = ps1_dir / f"compile_project_{ts}.ps1"
    stdout_path = ps1_dir / f"compile_project_{ts}_stdout.txt"
    stderr_path = ps1_dir / f"compile_project_{ts}_stderr.txt"

    user = resolve_user(args.user, parse_util(project_path))

    ps1_content = generate_ps1(
        xwin7_path=args.xwin7_path,
        action=args.action,
        project=str(project_path),
        profile=args.profile,
        log_path=str(log_path),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        user=user,
        sousproject=args.sousproject,
        source_basename=args.source,
    )
    write_iso(ps1_path, ps1_content)

    result: dict = {
        "ps1_script": str(ps1_path),
        "log_file": str(log_path),
        "action": args.action,
        "executed": False,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }

    if args.no_execute:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.exit(3)

    # Execution reelle.
    # #217 : NE PAS lancer via `powershell -ExecutionPolicy Bypass -File`. Sur un poste
    # integrateur verrouille, `-ExecutionPolicy Bypass` en ligne de commande est soit
    # SURCHARGE par une GPO MachinePolicy (le .ps1 est alors refuse : "running scripts is
    # disabled"), soit SIGNALE comme IOC par l'antivirus/EDR (process tue). On invoque donc
    # le script LOCAL fraichement genere via l'operateur d'appel `& '<ps1>'`, sans drapeau
    # de bypass : sous la policy usuelle RemoteSigned, un script LOCAL (sans marque
    # Zone.Identifier "telecharge") s'execute sans bypass. La lecture du .ps1 (donc le
    # profil accentue ISO-8859-1) est identique a `-File`.
    ps1_quoted = str(ps1_path).replace("'", "''")  # echappe une eventuelle apostrophe
    try:
        # `; exit $LASTEXITCODE` : SANS lui, `-Command "& '<ps1>'"` renvoie toujours
        # returncode 1 sur tout `exit N` non nul du .ps1 (PowerShell 5.1) -> le champ
        # `exit_code` du JSON perdrait le vrai code xwin7 (dont le crash -805306369).
        # Avec, le code est propage fidelement (verifie), sans revenir a `-File` (#217).
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command", f"& '{ps1_quoted}'; exit $LASTEXITCODE",
            ],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError as e:
        print(f"ERREUR: powershell introuvable : {e}", file=sys.stderr)
        sys.exit(2)

    result["executed"] = True
    result["exit_code"] = proc.returncode
    result["powershell_stdout"] = (proc.stdout or "").strip()
    result["powershell_stderr"] = (proc.stderr or "").strip()

    # Verdict DELEGUE a parse_compilation.parse_report (source unique --).
    # On attend d'abord que le log soit lisible (race de flush / antivirus #16). xwin7 a
    # deja quitte (Start-Process -Wait), donc le fichier est complet une fois apparu.
    for _ in range(12):
        if log_path.is_file() and log_path.stat().st_size > 0:
            break
        time.sleep(0.5)

    verdict = parse_compilation.parse_report(str(log_path)) if log_path.is_file() else {"error": "log absent"}

    if "error" not in verdict:
        result["success"] = bool(verdict.get("success"))
        result["summary"] = verdict.get("summary")
        if verdict.get("errors"):
            result["errors"] = verdict["errors"]
        # Champs de diagnostic remontes tels quels (#310 / #236).
        for _k in ("build_incomplet", "other_errors", "up_to_date", "summary_absent"):
            if _k in verdict:
                result[_k] = verdict[_k]
    else:
        # Log absent/illisible apres attente -- xwin7 n'a pas demarre/termine normalement
        # (profil introuvable, .dhpt invalide...).
        result["summary"] = None
        result["success"] = False
        result["error_hint"] = (
            "Le fichier de log est absent ou non parsable (ni [TOTAL_ERRORS] ni 'Erreur(s)=' "
            "apres attente). Verifier le stdout/stderr capture, le profil (--list-profiles) "
            "et la validite du .dhpt."
        )

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
