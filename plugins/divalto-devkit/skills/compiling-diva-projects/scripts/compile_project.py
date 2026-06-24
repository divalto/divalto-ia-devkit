#!/usr/bin/env python3
"""Compile un projet Divalto reel (`.dhpt`) via xwin7 en contournant le piege
d'encodage des profils avec accent (`developpement` avec `\xe9`).

Probleme adresse (R-005 du batch RETEX 2026-05-27) :
  Passer un profil accentue (`developpement`) en argument direct depuis
  PowerShell echoue silencieusement : la session PowerShell 5.1 stocke les
  chaines en UTF-16 LE, la conversion vers les arguments natifs ne preserve
  pas l'octet 0xe9 attendu par xwin7 (qui compare en ISO-8859-1). Resultat :
  ExitCode=1, log absent, friction ~20 min par tentative.

Solution :
  Generer un script .ps1 **en ISO-8859-1 + CRLF** qui contient le nom de
  profil litteral (`$Profil = "d\xe9veloppement"`), puis l'executer via
  `powershell -ExecutionPolicy Bypass -File <script.ps1>`. xwin7 recoit
  alors le profil en ISO-8859-1 natif et matche correctement.

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

Exit codes :
    0 = compilation reussie (Erreur(s)=0 dans le rapport)
    1 = erreurs de compilation OU erreur utilisateur (input invalide)
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


DEFAULT_XWIN7_PATH = r"C:\divalto\sys\xwin7.exe"
VALID_ACTIONS = ("build", "buildall")


def write_iso(path: Path, content: str) -> None:
    """Ecrit un fichier en ISO-8859-1 + CRLF.

    Critique pour le `.ps1` : sans cette discipline, le nom de profil accentue
    passe en argument echoue (cf. R-005).
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    if content and not content.endswith("\r\n"):
        content += "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("iso-8859-1"))


def resolve_user(cli_user: str | None) -> str | None:
    """Reproduit le fallback de `generate_harness.py` (R-008 batch precedent) :
    --user XX > X_USER non-vide > USERNAME Windows.

    Si tout est vide, retourne None et alerte sur stderr (xwin7 risque le crash
    ExitCode -805306369 avec corruption des objets compiles).
    """
    if cli_user:
        return cli_user
    env_user = os.environ.get("X_USER", "").strip()
    if env_user:
        return None  # xwin7 lira X_USER directement, ne pas passer -user
    fallback = os.environ.get("USERNAME", "").strip() or None
    if fallback:
        print(
            f"  INFO: X_USER vide/absente, fallback sur USERNAME={fallback}",
            file=sys.stderr,
        )
        return fallback
    print(
        "  WARN: ni --user, ni X_USER, ni USERNAME -- xwin7 risque de crasher (ExitCode -805306369).",
        file=sys.stderr,
    )
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

    Pieces critiques pour R-005 :
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

    ps1_lines = [
        "$ErrorActionPreference = 'Continue'",
        "Set-Location 'C:\\divalto\\sys'   # cwd obligatoire (cf. SKILL.md)",
        f"$proc = Start-Process -FilePath '{xwin7_path}' "
        f"-ArgumentList '{args_str}' "
        "-Wait -PassThru -NoNewWindow "
        f"-RedirectStandardOutput '{stdout_path}' "
        f"-RedirectStandardError '{stderr_path}'",
        "Write-Host \"ExitCode: $($proc.ExitCode)\"",
        "exit $proc.ExitCode",
    ]
    return "\n".join(ps1_lines)


# Ligne de RESUME : contient "Erreur(s)=" (a ne pas confondre avec une ligne de
# DETAIL d'erreur commencant par "Erreur ..." -- source du faux negatif #61).
SUMMARY_ERR_RE = re.compile(r"erreur\(s\)\s*=", re.IGNORECASE)
# "Le projet est a jour, aucune compilation a effectuer" (#27) -- pas un echec.
UP_TO_DATE_RE = re.compile(r"aucune compilation", re.IGNORECASE)


def parse_summary_line(log_path: Path) -> dict | None:
    """Lit la LIGNE DE RESUME du rapport xwin7 (celle qui contient 'Erreur(s)=').

    On cible specifiquement 'Erreur(s)=' (et pas une ligne de detail commencant
    par 'Erreur ...'), sinon faux negatif -- cf. #61 (exit 1 alors que Erreur(s)=0).
    """
    if not log_path.is_file():
        return None
    try:
        text = log_path.read_text(encoding="iso-8859-1", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if SUMMARY_ERR_RE.search(line):
            summary: dict = {}
            for token in line.split():
                if "=" in token:
                    key, _, value = token.partition("=")
                    summary[key.rstrip("(s)").lower()] = value
            if summary:
                return summary
    return None


def wait_for_summary(log_path: Path, attempts: int = 12, delay: float = 0.5) -> dict | None:
    """Attend l'apparition de la ligne de resume.

    Le log peut etre visible avec un leger retard apres la fin de xwin7 (flush /
    antivirus) -- d'ou de faux 'log absent' (#16). On retente quelques fois.
    """
    summary = parse_summary_line(log_path)
    for _ in range(attempts):
        if summary is not None:
            return summary
        time.sleep(delay)
        summary = parse_summary_line(log_path)
    return summary


def is_up_to_date(log_path: Path) -> bool:
    """Detecte 'Le projet est a jour, aucune compilation a effectuer' (#27) :
    build incremental sans rien a recompiler -- ce n'est PAS un echec."""
    if not log_path.is_file():
        return False
    try:
        text = log_path.read_text(encoding="iso-8859-1", errors="replace")
    except OSError:
        return False
    return bool(UP_TO_DATE_RE.search(text))


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
    parser = argparse.ArgumentParser(
        description=(
            "Compile un projet Divalto reel (.dhpt) via xwin7 en contournant le "
            "piege d'encodage des profils accentues (R-005)."
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

    user = resolve_user(args.user)

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

    # Execution reelle
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", str(ps1_path),
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

    summary = wait_for_summary(log_path)
    if summary is not None:
        result["summary"] = summary
        erreurs_str = summary.get("erreur", "0")
        try:
            erreurs = int(erreurs_str)
        except ValueError:
            erreurs = -1
        result["success"] = (erreurs == 0)
    elif is_up_to_date(log_path):
        # "Le projet est a jour, aucune compilation a effectuer" : pas un echec (#27)
        result["summary"] = None
        result["up_to_date"] = True
        result["success"] = True
    else:
        # Log absent ou sans ligne de resume apres attente -- xwin7 n'a pas
        # demarre/termine normalement (profil introuvable, .dhpt invalide...).
        result["summary"] = None
        result["success"] = False
        result["error_hint"] = (
            "Le fichier de log est absent ou ne contient pas de ligne de resume "
            "'Erreur(s)=' apres attente. Verifier le stdout/stderr capture, le "
            "profil (--list-profiles) et la validite du .dhpt."
        )

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
