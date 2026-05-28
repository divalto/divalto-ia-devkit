#!/usr/bin/env python3
"""
Audit de coherence d'un workspace integrateur Divalto.

Combine R-1, R-2, R-3/R-4/R-5, R-13 et R-15 du skill understanding-integrator-workspace
pour produire un rapport d'audit complet :
- Resolution physique de chaque ligne du fichier implicite (existence, lisibilite)
- Lecture des [profil] de tous les `.dhpt` de surcharge du workspace
- Cross-check coherence implicite <-> profil (paths references vs paths declares)
- Cross-check coherence inter-`.dhpt` (cheminbases, versioncible, repobjet*, repbrowse*)
- Findings classes par severite (error / warning / info)

Usage:
    py check_workspace_coherence.py --workspace <chemin_workspace> --implicit <chemin_implicite> --confirmed-by-user

Le flag `--confirmed-by-user` est OBLIGATOIRE pour que le script execute son audit.
Il materialise la confirmation R-1/P-B : le collaborateur doit avoir explicitement
valide le fichier implicite avant que l'audit puisse tourner. Sans le flag : warning
sur stderr et exit code 3.

Output JSON: rapport structure (voir exemple dans la doc du skill).

Exit codes :
    0 = audit OK (0 error)
    1 = audit avec findings (warnings ou errors) -- a presenter au collaborateur
    2 = erreur d'execution (workspace ou implicite introuvable)
    3 = --confirmed-by-user absent (R-1/P-B viole)
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _resolver import (  # noqa: E402
    compute_effective_databases,
    discover_diva_root,
    parse_bconnect_from_fhsql,
    parse_connexions_xml,
    parse_divaltopath_cfg,
    parse_divaltoserver_cfg,
    parse_implicit_xml_companion,
    read_odbc_dsn,
    resolve_harmony_path,
    resolve_sql_url,
)


def parse_dhpt_profiles(dhpt_path: Path) -> dict:
    """Parse un `.dhpt` et extrait son header + tous ses [profil].

    Retourne :
        {
          "path": str,
          "header": "xwin-projet" | "xwin-s-projet" | str,
          "name": str | None,
          "cheminbases": str | None,
          "filtres": str | None,
          "profiles": [
              {"nom": str, "repobjet": str|None, "repbrowse": str|None,
               "repobjetsurcharge": str|None, "repbrowsesurcharge": str|None,
               "implicites": str|None, "versioncible": str|None}
          ]
        }
    """
    try:
        text = dhpt_path.read_text(encoding="iso-8859-1", errors="replace")
    except OSError as e:
        return {"path": str(dhpt_path), "error": f"lecture impossible : {e}"}

    lines = text.splitlines()

    # Header = premiere ligne non vide
    header = ""
    for line in lines:
        s = line.strip()
        if s:
            header = s
            break

    # Champs au niveau [general]
    name = None
    cheminbases = None
    filtres = None
    for line in lines:
        s = line.strip()
        if s.startswith("nom=") and name is None:
            m = re.match(r'^nom=(?:"([^"]*)"|([^\s]+))', s)
            if m:
                name = m.group(1) or m.group(2)
        if s.startswith("cheminbases=") and cheminbases is None:
            m = re.match(r'^cheminbases=(?:"([^"]*)"|([^\s]+))', s)
            if m:
                cheminbases = m.group(1) or m.group(2)
        if s.startswith("filtres=") and filtres is None:
            m = re.match(r'^filtres=(?:"([^"]*)"|([^\s]+))', s)
            if m:
                filtres = m.group(1) or m.group(2)

    # Extraction des [profil] (un .dhpt peut en contenir plusieurs)
    profiles = []
    in_profil = False
    current = None
    for line in lines:
        s = line.strip()
        if s == "[profil]":
            if current is not None:
                profiles.append(current)
            current = {
                "nom": None,
                "repobjet": None,
                "repbrowse": None,
                "repobjetsurcharge": None,
                "repbrowsesurcharge": None,
                "implicites": None,
                "versioncible": None,
            }
            in_profil = True
            continue
        if s.startswith("["):
            # Nouvelle section quelconque -> sort du profil
            if current is not None:
                profiles.append(current)
                current = None
            in_profil = False
            continue
        if not in_profil or current is None:
            continue
        # Champs du profil
        for field in ("nom", "repobjet", "repbrowse", "repobjetsurcharge",
                      "repbrowsesurcharge", "implicites", "versioncible"):
            if s.startswith(field + "="):
                m = re.match(rf'^{field}=(?:"([^"]*)"|([^\s]+))', s)
                if m:
                    current[field] = m.group(1) or m.group(2)
                break

    if current is not None:
        profiles.append(current)

    return {
        "path": str(dhpt_path),
        "header": header,
        "name": name,
        "cheminbases": cheminbases,
        "filtres": filtres,
        "profiles": profiles,
    }


def add_finding(findings: list, severity: str, rule: str, message: str, **extra):
    findings.append({"severity": severity, "rule": rule, "message": message, **extra})


def main():
    parser = argparse.ArgumentParser(
        description="Audit de coherence d'un workspace integrateur Divalto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--workspace", required=True, help="Chemin racine du workspace")
    parser.add_argument(
        "--implicit",
        required=True,
        help="Chemin du fichier implicite confirme (R-1)",
    )
    parser.add_argument(
        "--confirmed-by-user",
        action="store_true",
        help=(
            "OBLIGATOIRE : confirme que le collaborateur a explicitement valide le "
            "fichier implicite passe en --implicit (R-1/P-B). Sans ce flag, le script "
            "refuse de demarrer (exit 3)."
        ),
    )
    args = parser.parse_args()

    # Garde-fou R-1/P-B : refuser l'audit sans confirmation explicite du fichier implicite
    if not args.confirmed_by_user:
        print(
            f"WARNING: Selection du fichier implicite '{args.implicit}' non confirmee "
            f"par l'utilisateur (R-1/P-B). Le skill understanding-integrator-workspace "
            f"exige que le fichier implicite soit confirme par le collaborateur avant "
            f"tout audit. Relancer avec --confirmed-by-user apres validation explicite.",
            file=sys.stderr,
        )
        sys.exit(3)

    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"ERROR: workspace introuvable : {workspace}", file=sys.stderr)
        sys.exit(2)

    implicit_path = Path(args.implicit)
    if not implicit_path.is_file():
        print(f"ERROR: fichier implicite introuvable : {implicit_path}", file=sys.stderr)
        sys.exit(2)

    findings = []

    # R-5 : DIVA_ROOT + fconfig
    diva_info = discover_diva_root()
    if "error" in diva_info:
        add_finding(findings, "error", "R-5",
                    f"Impossible de decouvrir DIVA_ROOT via le registre : {diva_info['error']}")
        # On poursuit quand meme avec resolution degradee
        diva_root = None
        fconfig_dhfd = None
    else:
        diva_root = diva_info["diva_root"]
        fconfig_dhfd = Path(diva_info["fconfig_dhfd"]) if diva_info.get("fconfig_dhfd") else None

    # R-3 : divaltopath.cfg
    cfg_aliases = {}
    if diva_root:
        cfg_path = Path(diva_root) / "sys" / "divaltopath.cfg"
        cfg = parse_divaltopath_cfg(cfg_path)
        if "error" in cfg:
            add_finding(findings, "warning", "R-3", cfg["error"])
        else:
            cfg_aliases = cfg["aliases"]

    # R-7 : divaltoserver.cfg (parallele de R-3 pour les serveurs SQL)
    server_cfg = {}
    if diva_root:
        server_cfg_path = Path(diva_root) / "sys" / "divaltoserver.cfg"
        scfg = parse_divaltoserver_cfg(server_cfg_path)
        if "error" in scfg:
            add_finding(findings, "warning", "R-7", scfg["error"])
        else:
            server_cfg = scfg["servers"]

    # R-2 : parse implicit
    try:
        text = implicit_path.read_text(encoding="iso-8859-1")
    except UnicodeDecodeError:
        text = implicit_path.read_text(encoding="utf-8")

    implicit_lines = []
    for i, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith(";"):
            continue
        entry = {"line": i, "raw": stripped, "type": None, "resolved": None, "exists": None}

        if stripped.startswith("//"):
            entry["type"] = "sql_url"
            res = resolve_sql_url(stripped, server_cfg, fconfig_dhfd, diva_root)
            if "resolved" in res:
                entry["resolved"] = res["resolved"]
                entry["source"] = res["source"]
                entry["host"] = res.get("host")
                entry["db"] = res.get("db")
                entry["sqlpath_raw"] = res.get("sqlpath_raw")
            else:
                entry["host"] = res.get("host")
                entry["db"] = res.get("db")
                add_finding(findings, "warning", "R-7/R-8",
                            f"Ligne {i} : URL SQL non resolue -- {res.get('error')}",
                            sql_url=stripped)
        elif re.match(r"^[A-Za-z]:[\\/]", stripped):
            entry["type"] = "windows_path"
            entry["resolved"] = stripped
        elif stripped.startswith("/"):
            entry["type"] = "harmony_path"
            res = resolve_harmony_path(stripped, cfg_aliases, fconfig_dhfd, diva_root)
            if "resolved" in res:
                entry["resolved"] = res["resolved"]
                entry["source"] = res["source"]
            else:
                add_finding(findings, "warning", "R-3/R-4",
                            f"Ligne {i} : alias non resolu -- {res.get('error')}",
                            harmony=stripped)
        else:
            entry["type"] = "unknown"
            add_finding(findings, "error", "R-6",
                        f"Ligne {i} : type non reconnu -- ne matche aucune grammaire valide",
                        raw=stripped)

        # Verification d'existence physique
        if entry["resolved"]:
            p = Path(entry["resolved"])
            entry["exists"] = p.exists()
            if p.exists() and p.is_dir():
                try:
                    entry["entry_count"] = sum(1 for _ in p.iterdir())
                except OSError:
                    entry["entry_count"] = None
                # Pour les URL SQL, verifier la presence de fhsql.dhfi + .dhfd (R-9 prerequis)
                if entry["type"] == "sql_url":
                    fhsql_dhfi = p / "fhsql.dhfi"
                    fhsql_dhfd = p / "fhsql.dhfd"
                    entry["fhsql_dhfi_present"] = fhsql_dhfi.is_file()
                    entry["fhsql_dhfd_present"] = fhsql_dhfd.is_file()
                    if not fhsql_dhfi.is_file() or not fhsql_dhfd.is_file():
                        add_finding(findings, "warning", "R-9",
                                    f"Ligne {i} : chemin SQL '{entry['resolved']}' resolu mais "
                                    f"fhsql.dhfi/.dhfd manquant -- R-9 (extraction DSN ODBC) "
                                    f"impossible.",
                                    sql_url=stripped, resolved=entry["resolved"])
            if not p.exists():
                rule = "R-7/R-8" if entry["type"] == "sql_url" else "R-2"
                key = "sql_url" if entry["type"] == "sql_url" else "harmony"
                add_finding(findings, "warning", rule,
                            f"Ligne {i} : chemin resolu n'existe pas sur disque",
                            **{key: stripped, "resolved": entry["resolved"]})

        implicit_lines.append(entry)

    # R-15 : trouver les .dhpt et lire leurs profils
    dhpt_files = sorted(workspace.rglob("*.dhpt"))
    dhpts_parsed = []
    for dhpt in dhpt_files:
        info = parse_dhpt_profiles(dhpt)
        dhpts_parsed.append(info)

    # Cross-checks inter-`.dhpt`
    surcharge_dhpts = [d for d in dhpts_parsed if d.get("header", "").startswith("xwin-s-projet")]

    # Coherence en-tete vs nom (suffixe u)
    for d in dhpts_parsed:
        if "error" in d:
            continue
        path_name = Path(d["path"]).stem  # nom sans extension
        ends_with_u = path_name.endswith("u")
        header = d.get("header", "")
        is_surcharge_header = header.startswith("xwin-s-projet")
        if ends_with_u and not is_surcharge_header:
            add_finding(findings, "error", "convention-naming",
                        f".dhpt '{path_name}.dhpt' suffixe 'u' (indique une surcharge) mais "
                        f"en-tete '{header}' (projet standard). Devrait etre 'xwin-s-projet 2.0'.",
                        dhpt=d["path"])

    # cheminbases coherent entre .dhpt de surcharge
    cheminbases_set = set()
    for d in surcharge_dhpts:
        if d.get("cheminbases"):
            cheminbases_set.add(d["cheminbases"])
    if len(cheminbases_set) > 1:
        add_finding(findings, "warning", "coherence-cheminbases",
                    f"{len(cheminbases_set)} valeurs distinctes de cheminbases entre les .dhpt "
                    f"de surcharge -- possible incoherence",
                    values=list(cheminbases_set))

    # versioncible coherent entre profils homonymes
    versioncibles_by_profile = {}  # profile_name -> set(versioncible)
    for d in surcharge_dhpts:
        for p in d.get("profiles", []):
            if p.get("nom") and p.get("versioncible"):
                versioncibles_by_profile.setdefault(p["nom"], set()).add(p["versioncible"])
    for prof_name, versions in versioncibles_by_profile.items():
        if len(versions) > 1:
            add_finding(findings, "error", "coherence-versioncible",
                        f"Profil '{prof_name}' a des versioncible divergents entre .dhpt : "
                        f"{sorted(versions)}. Probable typo de configuration.")

    # Coherence implicite <-> profils : chaque path du profil doit etre dans l'implicite
    implicit_harmony_lines = {e["raw"].rstrip("/") for e in implicit_lines
                              if e["type"] == "harmony_path"}
    for d in surcharge_dhpts:
        for p in d.get("profiles", []):
            for field in ("repobjet", "repobjetsurcharge", "repbrowse", "repbrowsesurcharge"):
                val = p.get(field)
                if not val:
                    continue
                # Normalise : strip slash final + comparer en lowercase
                val_norm = val.rstrip("/").lower()
                # Vrai match : la valeur du profil DOIT etre une ligne de l'implicite OU un sous-segment
                match_found = any(
                    val_norm == h.lower() or val_norm.startswith(h.lower() + "/")
                    for h in implicit_harmony_lines
                )
                if not match_found:
                    add_finding(findings, "warning", "coherence-profil-implicite",
                                f".dhpt '{Path(d['path']).name}' profil '{p.get('nom')}' "
                                f"{field}='{val}' n'a aucune correspondance dans l'implicite. "
                                f"Configuration suspecte.",
                                dhpt=d["path"])

    # Cross-check inter-portes Harmony vs ADO.NET (R-9, R-10, R-11)
    # Sur la 1ere ligne sql_url resolue et accessible, on tente la chaine R-9..R-11
    cross_portes_report = {
        "skipped": True,
        "reason": "Aucune ligne sql_url resolue + accessible + fhsql present",
    }
    for entry in implicit_lines:
        if entry["type"] != "sql_url":
            continue
        if not entry.get("resolved") or not entry.get("exists"):
            continue
        if not entry.get("fhsql_dhfd_present"):
            continue

        sql_path = Path(entry["resolved"])
        cross_portes_report = {"sql_path": str(sql_path), "skipped": False}

        # R-9 : parse BCONNECT dans fhsql.dhfd
        bconnect = parse_bconnect_from_fhsql(sql_path / "fhsql.dhfd")
        cross_portes_report["bconnect"] = bconnect
        if "error" in bconnect:
            add_finding(findings, "warning", "R-9",
                        f"BCONNECT non extrait depuis fhsql.dhfd : {bconnect['error']}",
                        sql_path=str(sql_path))

        # R-10 : registre ODBC du DSN trouve
        odbc = None
        if bconnect.get("dsn"):
            odbc = read_odbc_dsn(bconnect["dsn"])
            cross_portes_report["odbc"] = odbc
            if "error" in odbc:
                add_finding(findings, "warning", "R-10",
                            f"DSN '{bconnect['dsn']}' non lu dans le registre : {odbc['error']}",
                            dsn=bconnect["dsn"])

        # R-11 : compagnon implicite.xml + connexions.xml
        ado_net_connexion = None
        xml_companion = parse_implicit_xml_companion(implicit_path)
        cross_portes_report["implicit_xml"] = xml_companion
        if "error" not in xml_companion and xml_companion.get("mappings"):
            # Prendre la 1ere connexion mappee (typiquement "Default")
            first_alias = next(iter(xml_companion["mappings"].keys()))
            connexion_logique = xml_companion["mappings"][first_alias]
            cross_portes_report["alias_used"] = first_alias
            cross_portes_report["connexion_logique"] = connexion_logique

            if diva_root:
                connexions_path = Path(diva_root) / "sys" / "connexions.xml"
                ado_net_connexion = parse_connexions_xml(connexions_path, target_connexion=connexion_logique)
                cross_portes_report["ado_net"] = ado_net_connexion
                if "error" in ado_net_connexion:
                    add_finding(findings, "warning", "R-11",
                                f"connexions.xml non parsable : {ado_net_connexion['error']}",
                                connexion=connexion_logique)
                elif not ado_net_connexion.get("connexion"):
                    add_finding(findings, "warning", "R-11",
                                f"Connexion logique '{connexion_logique}' non trouvee dans "
                                f"connexions.xml. Mapping invalide ?",
                                connexion=connexion_logique)
        else:
            add_finding(findings, "warning", "R-11",
                        f"Compagnon implicite.xml absent ou vide : "
                        f"{xml_companion.get('error', 'unknown')}. Porte ADO.NET non resolue.",
                        implicit=str(implicit_path))

        # Synthese cross-portes : applique override BCONNECT + produit findings
        synthesis = compute_effective_databases(
            bconnect if "error" not in bconnect else None,
            odbc if odbc and "error" not in odbc else None,
            ado_net_connexion if ado_net_connexion and "error" not in ado_net_connexion else None,
        )
        cross_portes_report["synthesis"] = synthesis
        # Ajouter les findings de la synthese
        for f in synthesis.get("findings", []):
            findings.append(f)

        # On ne traite que la 1ere ligne sql_url eligible
        break

    # Sortie
    summary = {
        "errors": sum(1 for f in findings if f["severity"] == "error"),
        "warnings": sum(1 for f in findings if f["severity"] == "warning"),
        "infos": sum(1 for f in findings if f["severity"] == "info"),
    }

    output = {
        "workspace": str(workspace),
        "implicit_file": str(implicit_path),
        "diva_root": diva_root,
        "fconfig_dhfd": str(fconfig_dhfd) if fconfig_dhfd else None,
        "implicit_lines": implicit_lines,
        "dhpts": dhpts_parsed,
        "cross_portes": cross_portes_report,
        "summary": summary,
        "findings": findings,
    }

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

    sys.exit(0 if (summary["errors"] + summary["warnings"]) == 0 else 1)


if __name__ == "__main__":
    main()
