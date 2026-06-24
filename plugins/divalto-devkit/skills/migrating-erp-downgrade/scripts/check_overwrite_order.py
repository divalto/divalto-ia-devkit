#!/usr/bin/env python3
"""Verifie l'integrite des surcharges overWrite apres une migration / rebase de pack.

Bug cible (R-035) : un module `OverWrite base.dhop` fusionne ses procedures DANS
`base.dhop` a la compilation. Si on recompile le STANDARD `base` APRES sa surcharge
(rebase mal ordonne), `base.dhop` est regenere PROPRE et perd les procedures de
surcharge (symptome runtime : comportement standard / boucle infinie).

Deux signaux de detection :
  (a) DATE   : l'objet de base est plus recent que son overlay -> inversion d'ordre suspecte
               (le base a ete (re)compile apres l'overlay).
  (b) SYMBOLE: une procedure presente dans l'overlay est ABSENTE de l'objet de base
               -> la fusion overWrite a ete effacee.

Regle de migration : compiler les bases standard d'abord, les surcharges overWrite
ENSUITE. Ce script verifie l'etat resultant.

Modes :
  Paire explicite (fiable) :
    py check_overwrite_order.py --base B.dhop --overlay O.dhop [--symbols Proc1,Proc2]
  Scan d'un repertoire d'objets (heuristique de nommage) :
    py check_overwrite_order.py --objets <dir>

Couplage overlay/base : a defaut de declaration `OverWrite` (cote source), le couplage
repose sur le nommage -- position 3 (index 2) `u` <-> `t` (ex. `gtuz099` <-> `gttz099`).
En mode `--objets`, ce nommage est une heuristique : confirmer cote source en cas de doute.

Symboles : en mode explicite, fournir `--symbols` (les procedures de surcharge a controler)
donne un resultat fiable. Sans `--symbols`, le script extrait des candidats proc-like de
l'overlay absents du base (a relire -- heuristique).

Sortie JSON. Exit codes : 0 = aucune anomalie, 1 = anomalie detectee, 2 = erreur.
"""

import argparse
import json
import os
import re
import sys

# Token proc-like : commence par lettre/_ , >= 4 chars
_TOKEN = re.compile(rb'[A-Za-z_][A-Za-z0-9_]{3,63}')


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def symbol_in(raw, sym):
    return sym.encode("iso-8859-1") in raw


def extract_proc_candidates(raw):
    """Tokens proc-like : minuscule presente ET (majuscule OU '_').

    Filtre le bruit ALLCAPS (noms de records/tables) en exigeant une minuscule.
    Heuristique -- destinee au mode auto (candidats a relire), pas a une preuve.
    """
    out = set()
    for m in _TOKEN.finditer(raw):
        t = m.group().decode("iso-8859-1", "replace")
        if any(c.islower() for c in t) and (any(c.isupper() for c in t) or "_" in t):
            out.add(t)
    return out


def derive_base_name(overlay_name):
    """Derive le nom de base d'un overlay via position 3 (index 2) 'u' -> 't'."""
    if len(overlay_name) >= 3 and overlay_name[2] in ("u", "U"):
        repl = "t" if overlay_name[2] == "u" else "T"
        return overlay_name[:2] + repl + overlay_name[3:]
    return None


def check_pair(base_path, overlay_path, symbols=None):
    raw_base = read_bytes(base_path)
    raw_overlay = read_bytes(overlay_path)
    mt_base = os.path.getmtime(base_path)
    mt_overlay = os.path.getmtime(overlay_path)
    date_inversion = mt_base > mt_overlay

    auto = symbols is None
    if auto:
        symbols = sorted(extract_proc_candidates(raw_overlay) - extract_proc_candidates(raw_base))

    sym_report = []
    lost = []
    for s in symbols:
        in_base = symbol_in(raw_base, s)
        in_overlay = symbol_in(raw_overlay, s)
        is_lost = in_overlay and not in_base
        sym_report.append({"symbol": s, "in_base": in_base, "in_overlay": in_overlay, "lost": is_lost})
        if is_lost:
            lost.append(s)

    return {
        "base": os.path.basename(base_path),
        "overlay": os.path.basename(overlay_path),
        "base_mtime": round(mt_base, 0),
        "overlay_mtime": round(mt_overlay, 0),
        "date_inversion": date_inversion,
        "auto_symbols": auto,
        "symbols_checked": len(symbols),
        "symbols": sym_report if not auto else sym_report[:50],
        "lost_symbols": lost,
        "anomaly": date_inversion or bool(lost),
    }


def scan_objets(objets_dir):
    pairs = []
    names = {f for f in os.listdir(objets_dir) if f.lower().endswith(".dhop")}
    lower = {f.lower(): f for f in names}
    for f in sorted(names):
        stem = os.path.splitext(f)[0]
        if len(stem) >= 3 and stem[2] in ("u", "U"):
            base_stem = derive_base_name(stem)
            if not base_stem:
                continue
            base_file = base_stem + os.path.splitext(f)[1]
            if base_file.lower() in lower:
                real_base = lower[base_file.lower()]
                pairs.append((os.path.join(objets_dir, real_base), os.path.join(objets_dir, f)))
    return pairs


def main():
    parser = argparse.ArgumentParser(
        description="Verifie l'integrite des surcharges overWrite apres migration (R-035)")
    parser.add_argument("--base", help="Objet de base (.dhop)")
    parser.add_argument("--overlay", help="Objet de surcharge overWrite (.dhop)")
    parser.add_argument("--symbols", help="Procedures de surcharge a controler (separees par des virgules)")
    parser.add_argument("--objets", help="Repertoire d'objets a scanner (paires par nommage t<->u)")
    args = parser.parse_args()

    if args.objets:
        if not os.path.isdir(args.objets):
            print(f"ERREUR : repertoire introuvable : {args.objets}", file=sys.stderr)
            sys.exit(2)
        pairs = scan_objets(args.objets)
        results = [check_pair(b, o) for (b, o) in pairs]
        anomalies = [r for r in results if r["anomaly"]]
        out = {
            "mode": "scan",
            "objets": args.objets,
            "pairs_found": len(pairs),
            "anomalies": len(anomalies),
            "results": results,
            "note": "Couplage par heuristique de nommage (position 3 u<->t) ; symboles auto = candidats a relire.",
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(1 if anomalies else 0)

    if args.base and args.overlay:
        for p in (args.base, args.overlay):
            if not os.path.isfile(p):
                print(f"ERREUR : fichier introuvable : {p}", file=sys.stderr)
                sys.exit(2)
        symbols = None
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        result = check_pair(args.base, args.overlay, symbols)
        result["mode"] = "pair"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1 if result["anomaly"] else 0)

    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
