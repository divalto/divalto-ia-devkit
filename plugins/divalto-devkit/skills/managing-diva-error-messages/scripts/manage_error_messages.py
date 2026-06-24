#!/usr/bin/env python3
"""Lit / compare les messages d'erreur applicatifs DIVA (fichiers XXferr).

Un XXferr.dhfi est un fichier ISAM sequentiel indexe (table XErr : Nivalerte,
Errnum, Errtxt). Ce script NE lit PAS les octets a la main : il **orchestre le
skill reading-isam-files** (invoque `read_isam.py` en sous-process, cle A), ce qui
evite tout sous-comptage (on lit les vrais enregistrements, pas une regex sur octets).

Modes :
    --list                : liste les codes + libelles
    --check <code>        : verifie qu'un code existe + renvoie son libelle
    --diff <autre.dhfi>   : compare les ensembles de codes entre 2 fichiers
                            (ajoutes / retires) -- detection de derive / arbitrage

Usage :
    py manage_error_messages.py --file "<...>/gtferr.dhfi" \\
        --read-isam-script .claude/skills/reading-isam-files/scripts/read_isam.py \\
        --list

La structure d'enregistrement par defaut (`structures/structure_xxferr.json`) couvre
les XXferr standard ET specifiques (meme table XErr). Emplacement du fichier : par
convention `objets/`, mais peut etre ailleurs -> localiser via
`understanding-integrator-workspace`.

Sortie JSON. Exit codes : 0 = ok (resultat), 1 = vide / code absent, 2 = erreur.
"""

import argparse
import json
import os
import subprocess
import sys

DEFAULT_STRUCTURE = os.path.join(os.path.dirname(__file__), "structures", "structure_xxferr.json")


def read_records(dhfi_path, read_isam_script, structure_path):
    """Invoque read_isam.py (cle A) et retourne la liste des enregistrements XErr.

    Retourne (records, error_msg). records = [{Errnum, Errtxt, Nivalerte}, ...].
    """
    if not os.path.isfile(dhfi_path):
        return None, f"fichier introuvable : {dhfi_path}"
    if not os.path.isfile(read_isam_script):
        return None, f"read_isam.py introuvable : {read_isam_script} (fournir --read-isam-script)"
    if not os.path.isfile(structure_path):
        return None, f"structure introuvable : {structure_path}"
    try:
        r = subprocess.run(
            ["py", read_isam_script, "--file", dhfi_path,
             "--structure", structure_path, "--key", "A", "--max", "100000",
             "--fields", "Errnum,Errtxt,Nivalerte"],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        if r.returncode not in (0, 1):
            return None, f"read_isam.py exit={r.returncode} : {r.stderr[:400]}"
        data = json.loads(r.stdout)
        return data.get("records", []), None
    except Exception as e:
        return None, f"lecture echouee : {e}"


def is_code(errnum):
    """Un vrai code erreur : Errnum numerique non nul (Errnum=0 = ligne de commentaire ;*)."""
    s = (errnum or "").strip()
    return s.isdigit() and int(s) != 0


def codes_map(records):
    """{code_int: libelle} pour les enregistrements qui sont de vrais codes."""
    out = {}
    for rec in records:
        if is_code(rec.get("Errnum")):
            out.setdefault(int(rec["Errnum"].strip()), rec.get("Errtxt", "").strip())
    return out


def cmd_list(records):
    cm = codes_map(records)
    items = [{"code": c, "message": cm[c]} for c in sorted(cm)]
    return {"total_codes": len(items), "codes": items}


def cmd_check(records, code):
    try:
        target = int(str(code).strip())
    except ValueError:
        return {"code": code, "found": False, "error": "code non numerique"}
    cm = codes_map(records)
    if target in cm:
        return {"code": target, "found": True, "message": cm[target]}
    return {"code": target, "found": False}


def cmd_diff(records_a, records_b, file_a, file_b):
    a = codes_map(records_a)
    b = codes_map(records_b)
    sa, sb = set(a), set(b)
    only_a = sorted(sa - sb)
    only_b = sorted(sb - sa)
    return {
        "file_a": file_a, "file_b": file_b,
        "count_a": len(sa), "count_b": len(sb),
        "common": len(sa & sb),
        "only_in_a": [{"code": c, "message": a[c]} for c in only_a],
        "only_in_b": [{"code": c, "message": b[c]} for c in only_b],
        "note": "only_in_a = presents dans A absents de B. Pour un arbitrage downgrade : "
                "A=downgrade, B=standard -> only_in_a = candidats CUSTOM a PRESERVER "
                "(jamais d'adoption aveugle du standard). Un code custom dans un fichier "
                "STANDARD = violation de norme (le custom doit vivre dans le XXferr du partenaire).",
    }


def main():
    ap = argparse.ArgumentParser(description="Lit / compare les messages d'erreur applicatifs (XXferr).")
    ap.add_argument("--file", required=True, help="Chemin du XXferr.dhfi")
    ap.add_argument("--read-isam-script", required=True,
                    help="Chemin de reading-isam-files/scripts/read_isam.py")
    ap.add_argument("--structure", default=DEFAULT_STRUCTURE,
                    help="Structure XErr (defaut : structures/structure_xxferr.json embarquee)")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--list", action="store_true", help="Liste codes + libelles")
    grp.add_argument("--check", metavar="CODE", help="Verifie l'existence d'un code")
    grp.add_argument("--diff", metavar="AUTRE_DHFI", help="Compare les codes avec un autre XXferr")
    args = ap.parse_args()

    records, err = read_records(args.file, args.read_isam_script, args.structure)
    if err:
        print(f"Erreur : {err}", file=sys.stderr)
        sys.exit(2)

    if args.list:
        payload = cmd_list(records)
        success = payload["total_codes"] > 0
    elif args.check:
        payload = cmd_check(records, args.check)
        success = payload.get("found", False)
    else:  # diff
        records_b, err_b = read_records(args.diff, args.read_isam_script, args.structure)
        if err_b:
            print(f"Erreur (fichier B) : {err_b}", file=sys.stderr)
            sys.exit(2)
        payload = cmd_diff(records, records_b, args.file, args.diff)
        success = True

    result = {"file": args.file, **payload}
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
