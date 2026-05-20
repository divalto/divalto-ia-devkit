#!/usr/bin/env python3
"""Trouve un numero de zoom libre pour une plage donnee, en cross-checkant 3 sources.

Sources verifiees :
  1. a5tczoom.dhsp : declarations `C_ZOOM_<Name>_<Num> = <Num>`
  2. a5f.dhfi local : enregistrements M4 (cle A4, champ ZoomNum) via read_isam.py en sous-process
  3. a5f.dhfi de versionx9 (optionnel)

Usage :
    # Cross-check minimal (a5tczoom seul)
    py find_free_zoom.py --a5tczoom a5tczoom.dhsp --domain DAV

    # Cross-check complet (3 sources)
    py find_free_zoom.py --a5tczoom a5tczoom.dhsp \\
        --a5f-local a5f.dhfi \\
        --read-isam-script .claude/skills/reading-isam-files/scripts/read_isam.py \\
        --structure .claude/skills/reading-isam-files/scripts/structures/structure_a5f_m4.json \\
        --domain DAV --count 5

Sortie JSON : {"free": [...], "sources": {...}, "collisions_...": [...]}
Exit codes : 0 = au moins un libre, 1 = aucun libre, 2 = erreur argument/fichier
"""

import argparse
import json
import os
import re
import subprocess
import sys


# Mapping domaine -> plages principales (source : moulinette 58, Outils/source/outm058.dhsp)
DOMAIN_RANGES = {
    "DAV":    [(9000, 9999), (21000, 21999), (22000, 22999),
               (39000, 39999), (46000, 46999), (47000, 47999)],
    "DAFF":   [(31000, 31999), (12592, 12593)],
    "DRT":    [(30000, 30999)],
    "DCPT":   [(19000, 19999)],
    "DPAIE":  [(25000, 29999)],
    "DSP":    [(32000, 32999)],
    "DQUAL":  [(40000, 40999)],
    "DDOC":   [(41000, 41999)],
    "DCONT":  [(44000, 44999)],
    "DGRM":   [(22039, 22040), (45000, 45999)],
    "DREG":   [(49000, 49999)],
    "COMMUN": [(11000, 18999)],
    "ZOOM":   [(99050, 99060)],
}


def parse_a5tczoom(path):
    """Parse a5tczoom.dhsp et extrait tous les numeros de zoom declares.

    Retourne un dict {num: ligne_source} des constantes `C_ZOOM_<Name>_<Num> = <Num>`.
    Ne garde que les lignes ou suffixe numero et valeur sont identiques (sanity).
    """
    if not os.path.isfile(path):
        print(f"Warning : a5tczoom introuvable : {path}", file=sys.stderr)
        return {}
    pattern = re.compile(r'C_ZOOM_\w+_(\d+)\s*=\s*(\d+)')
    result = {}
    with open(path, "r", encoding="iso-8859-1", errors="replace") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                suffix_num = int(m.group(1))
                val_num = int(m.group(2))
                if suffix_num == val_num:
                    result[val_num] = line.strip()
    return result


def parse_a5f_zooms(dhfi_path, read_isam_script, structure_path):
    """Invoque read_isam.py pour extraire les ZoomNum depuis a5f.dhfi (cle A4).

    Retourne un set de numeros entiers.
    """
    if not os.path.isfile(dhfi_path):
        print(f"Warning : a5f.dhfi introuvable : {dhfi_path}", file=sys.stderr)
        return set()
    try:
        r = subprocess.run(
            ["py", read_isam_script,
             "--file", dhfi_path,
             "--structure", structure_path,
             "--key", "A4",
             "--max", "100000",
             "--fields", "ZoomNum"],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        # read_isam.py : exit 0 si records trouves, 1 si aucun, 2 si erreur
        if r.returncode not in (0, 1):
            print(f"Warning : read_isam.py exit={r.returncode} sur {dhfi_path}", file=sys.stderr)
            if r.stderr:
                print(f"  stderr : {r.stderr[:500]}", file=sys.stderr)
            return set()
        data = json.loads(r.stdout)
        nums = set()
        for rec in data.get("records", []):
            zn = rec.get("ZoomNum", "").strip()
            if zn.isdigit():
                nums.add(int(zn))
        return nums
    except Exception as e:
        print(f"Warning : parse_a5f_zooms failed sur {dhfi_path} : {e}", file=sys.stderr)
        return set()


def find_free(used_set, ranges, count=1):
    """Trouve les premiers numeros libres dans les plages, dans l'ordre croissant."""
    free = []
    for (start, end) in ranges:
        for num in range(start, end + 1):
            if num not in used_set:
                free.append(num)
                if len(free) >= count:
                    return free
    return free


def main():
    parser = argparse.ArgumentParser(
        description="Trouve un numero de zoom libre via cross-check 3 sources",
    )
    parser.add_argument("--a5tczoom", required=True,
                        help="Chemin de a5tczoom.dhsp (source de verite standard)")
    parser.add_argument("--a5f-local", default=None,
                        help="Chemin de a5f.dhfi local (optionnel)")
    parser.add_argument("--a5f-versionx9", default=None,
                        help="Chemin de a5f.dhfi de versionx9 (optionnel)")
    parser.add_argument("--domain", default=None,
                        help=f"Code domaine ({', '.join(sorted(DOMAIN_RANGES.keys()))})")
    parser.add_argument("--range", default=None,
                        help="Plage personnalisee au format START-END (ex: 9900-9999)")
    parser.add_argument("--count", type=int, default=1,
                        help="Nombre de numeros libres a retourner (defaut: 1)")
    parser.add_argument("--read-isam-script", default=None,
                        help="Chemin de reading-isam-files/scripts/read_isam.py "
                             "(requis si --a5f-local ou --a5f-versionx9)")
    parser.add_argument("--structure", default=None,
                        help="Chemin structure_a5f_m4.json "
                             "(requis si --a5f-local ou --a5f-versionx9)")
    args = parser.parse_args()

    # Resoudre la plage cible
    if args.range:
        m = re.match(r'^(\d+)-(\d+)$', args.range.strip())
        if not m:
            print(f"Erreur : --range invalide '{args.range}'. Format attendu : START-END", file=sys.stderr)
            sys.exit(2)
        start, end = int(m.group(1)), int(m.group(2))
        # Garde-fou : la structure M4 de a5f.dhfi limite ZoomNum a 5 chars (99999 max).
        # La plage "custom >= 100000" est valide pour les EnrNo menu (M2, 6 chars) via
        # allocating-menu-enrno, mais PAS pour les zooms.
        if end > 99999 or start > 99999:
            print(
                f"Erreur : --range {args.range} depasse 99999. La structure M4 de "
                f"a5f.dhfi limite ZoomNum a 5 caracteres (max 99999). Utiliser "
                f"--domain DAV/DAFF/... ou une plage <= 99999. Note : la plage "
                f">= 100000 est valide pour allocating-menu-enrno (EnrNo menu, "
                f"M2 sur 6 chars), pas pour les zooms (M4 sur 5 chars).",
                file=sys.stderr,
            )
            sys.exit(2)
        if start > end:
            print(f"Erreur : --range {args.range} : borne basse > borne haute", file=sys.stderr)
            sys.exit(2)
        ranges = [(start, end)]
    elif args.domain:
        ranges = DOMAIN_RANGES.get(args.domain.upper())
        if not ranges:
            print(f"Erreur : domaine inconnu '{args.domain}'. Valides : "
                  f"{sorted(DOMAIN_RANGES.keys())}", file=sys.stderr)
            sys.exit(2)
    else:
        print("Erreur : fournir --domain OU --range", file=sys.stderr)
        sys.exit(2)

    # Source 1 : a5tczoom.dhsp
    consts = parse_a5tczoom(args.a5tczoom)

    # Sources 2 et 3 : a5f.dhfi (optionnelles)
    a5f_local_nums = set()
    a5f_v9_nums = set()
    needs_isam = args.a5f_local or args.a5f_versionx9
    if needs_isam and (not args.read_isam_script or not args.structure):
        print("Erreur : --a5f-local/--a5f-versionx9 requierent --read-isam-script ET --structure",
              file=sys.stderr)
        sys.exit(2)
    if args.a5f_local:
        a5f_local_nums = parse_a5f_zooms(args.a5f_local, args.read_isam_script, args.structure)
    if args.a5f_versionx9:
        a5f_v9_nums = parse_a5f_zooms(args.a5f_versionx9, args.read_isam_script, args.structure)

    # Union des numeros utilises
    used = set(consts.keys()) | a5f_local_nums | a5f_v9_nums

    # Numeros libres dans la plage consideree
    free = find_free(used, ranges, args.count)

    # Collisions inter-sources limitees a la plage (pour info / diagnostic)
    in_range = lambda n: any(s <= n <= e for (s, e) in ranges)
    collisions_a5f_vs_consts = sorted(
        n for n in a5f_local_nums & set(consts.keys()) if in_range(n)
    )

    result = {
        "free": free,
        "range": args.range or f"domain={args.domain}",
        "ranges_considered": [[s, e] for (s, e) in ranges],
        "sources": {
            "a5tczoom_count": len(consts),
            "a5f_local_count": len(a5f_local_nums),
            "a5f_versionx9_count": len(a5f_v9_nums),
            "union_used_count": len(used),
        },
        "collisions_a5f_local_vs_a5tczoom_in_range": collisions_a5f_vs_consts,
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    sys.exit(0 if free else 1)


if __name__ == "__main__":
    main()
