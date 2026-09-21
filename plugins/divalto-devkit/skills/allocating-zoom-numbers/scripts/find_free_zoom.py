#!/usr/bin/env python3
"""Trouve un numero de zoom libre, en cross-checkant les sources enregistrees
puis en verifiant le candidat dans les sources specifiques/surcharge.

Sources du used-set (numeros a eviter) :
  1. a5tczoom.dhsp      : declarations standard `C_ZOOM_<Name>_<Num> = <Num>`
  2. a5f.dhfi           : zooms STANDARD enregistres (M4, cle A4, champ ZoomNum)
  3. a5f.dhfi versionx9 : (optionnel) zooms standard d'une version anterieure
  4. a5fu.dhfi          : zooms SPECIFIQUES / surcharge enregistres (overlay de a5f,
                          meme structure M4). `a5f` est STANDARD et n'est jamais
                          modifie : les zooms partenaire vivent dans `a5fu`.

Verification phase 2 (recherche large) :
  Le(s) numero(s) candidat(s) est/sont recherche(s) DANS LES SOURCES
  SPECIFIQUES / SURCHARGE uniquement (jamais le standard). Toute occurrence est
  remontee avec son contexte (fichier:ligne + extrait) et etiquetee via un
  registre de patterns EXTENSIBLE (cf. reference/zoom-number-patterns.md) :
    - pattern connu (fort) : Zoom_Call / Tnt_Zoom_Call, binding touche masque fN=<num>
    - affectation (faible) : = <num>
    - non reconnu          : signal d'apprentissage (pattern potentiellement nouveau)
  AUCUNE decision automatique : les occurrences sont remontees pour jugement humain.
  0 occurrence -> candidat considere disponible.

Convention : un nouveau zoom specifique partenaire demarre a 90000 (plage par
defaut). Mais des zooms specifiques < 90000 existent -> la DETECTION du used-set
est globale (toutes plages) ; 90000 ne borne que la RECHERCHE d'un numero libre.

Usage :
    # Allocation partenaire (plage 90000+ par defaut) + verif sources specifiques
    py find_free_zoom.py --a5tczoom a5tczoom.dhsp \\
        --a5f-local a5f.dhfi --a5fu a5fu.dhfi \\
        --read-isam-script .claude/skills/reading-isam-files/scripts/read_isam.py \\
        --structure .claude/skills/reading-isam-files/scripts/structures/structure_a5f_m4.json \\
        --specifs-root "C:/.../specifs" --count 3

Sortie JSON. Exit codes : 0 = au moins un libre confirme, 1 = aucun, 2 = erreur.
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

# Convention : un nouveau zoom specifique partenaire demarre a 90000.
# Plafond 99999 : ZoomNum = 5 caracteres dans la structure M4 de a5f/a5fu.
# C'est la plage de DEFAUT pour ALLOUER ; la detection du used-set reste globale.
PARTNER_DEFAULT_RANGE = (90000, 99999)

# Registre EXTENSIBLE des patterns d'usage d'un numero de zoom dans les sources.
# Sert a ETIQUETER les occurrences de la recherche large (phase 2). Chaque entree
# est tracee a un RETEX dans reference/zoom-number-patterns.md. Etendre ce registre
# au fil des RETEX : une occurrence "non_reconnu" est un candidat-pattern a confirmer.
# {N} est remplace par le numero candidat (deja echappe) lors de la compilation.
ZOOM_USAGE_PATTERNS = [
    {
        "id": "zoom_call",
        "exts": (".dhsp",),
        "regex": r"(?i)\b(?:Tnt_)?Zoom_Call\s*\(",
        "confidence": "fort",
        "desc": "Appel Zoom_Call / Tnt_Zoom_Call",
        "retex": "#29",
    },
    {
        "id": "touche_masque",
        "exts": (".dhsf",),
        "regex": r"(?i)(?:shift_|ctrl_)?f\d+\s*=\s*{N}\b",
        "confidence": "fort",
        "desc": "Binding touche de masque ([touches] fN=<num>)",
        "retex": "#29",
    },
    {
        "id": "affectation",
        "exts": (".dhsp", ".dhsf"),
        # Lookbehind negatif : exclut les comparateurs >= <= == != := (le '=' n'est
        # pas precede de < > = ! :). Decouvert sur sources reelles (sss) : `case vsw >= 9000`
        # etait etiquete a tort. Un '=' simple (assignation/egalite DIVA) reste ambigu -> faible.
        "regex": r"(?<![<>=!:])=\s*{N}\b",
        "confidence": "faible",
        "desc": "Affectation '= <num>' (constante ou autre, a juger ; hors comparateurs)",
        "retex": "#29",
    },
]

# Extensions scannees en phase 2 (extensible).
SPECIFS_SCAN_EXTS = (".dhsp", ".dhsf")


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
    """Invoque read_isam.py pour extraire les ZoomNum depuis a5f/a5fu.dhfi (cle A4).

    Retourne un set de numeros entiers. Meme structure M4 pour a5f et a5fu.
    """
    if not os.path.isfile(dhfi_path):
        print(f"Warning : fichier .dhfi introuvable : {dhfi_path}", file=sys.stderr)
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


def _compile_patterns(num):
    """Compile le registre pour un numero donne. Retourne [(meta, regex_compilee), ...]."""
    compiled = []
    n = re.escape(str(num))
    for p in ZOOM_USAGE_PATTERNS:
        rx = p["regex"].replace("{N}", n)
        compiled.append((p, re.compile(rx)))
    return compiled


def label_occurrence(line, ext, compiled_patterns):
    """Etiquette une ligne (contenant le numero) selon le registre.

    Retourne (label, confidence). ("non_reconnu", "inconnu") si aucun pattern
    connu ne matche -> signal d'apprentissage (pattern potentiellement nouveau).
    """
    best = None
    for meta, rx in compiled_patterns:
        if ext not in meta["exts"]:
            continue
        if rx.search(line):
            conf = meta["confidence"]
            if best is None or (conf == "fort" and best[1] != "fort"):
                best = (meta["id"], conf)
    return best if best else ("non_reconnu", "inconnu")


def broad_search(candidates, specifs_roots, exts, max_files):
    """Recherche large des numeros candidats dans les sources specifiques uniquement.

    UNE passe sur les fichiers (alternation regex des candidats). Retourne
    (occ_by_num, files_scanned, truncated) ou occ_by_num = {num: [occurrences]}.
    """
    occ_by_num = {c: [] for c in candidates}
    if not candidates or not specifs_roots:
        return occ_by_num, 0, False
    num_alt = re.compile(r"\b(" + "|".join(re.escape(str(c)) for c in candidates) + r")\b")
    compiled_by_num = {c: _compile_patterns(c) for c in candidates}
    files_scanned = 0
    truncated = False
    for root in specifs_roots:
        if not os.path.isdir(root):
            print(f"Warning : --specifs-root introuvable : {root}", file=sys.stderr)
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in exts:
                    continue
                if files_scanned >= max_files:
                    truncated = True
                    break
                fpath = os.path.join(dirpath, fn)
                files_scanned += 1
                try:
                    with open(fpath, "r", encoding="iso-8859-1", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            seen_on_line = set()
                            for m in num_alt.finditer(line):
                                num = int(m.group(1))
                                if num in seen_on_line:
                                    continue
                                seen_on_line.add(num)
                                label, conf = label_occurrence(line, ext, compiled_by_num[num])
                                occ_by_num[num].append({
                                    "file": fpath,
                                    "line": lineno,
                                    "text": line.strip()[:200],
                                    "label": label,
                                    "confidence": conf,
                                })
                except Exception as e:
                    print(f"Warning : lecture echouee {fpath} : {e}", file=sys.stderr)
            if truncated:
                break
        if truncated:
            break
    if truncated:
        print(f"Warning : recherche large tronquee a --max-files={max_files} fichiers",
              file=sys.stderr)
    return occ_by_num, files_scanned, truncated


def main():
    parser = argparse.ArgumentParser(
        description="Trouve un numero de zoom libre (a5f + a5fu) puis verifie le "
                    "candidat dans les sources specifiques (recherche large etiquetee).",
    )
    parser.add_argument("--a5tczoom", required=True,
                        help="Chemin de a5tczoom.dhsp (constantes zoom standard)")
    parser.add_argument("--a5f-local", default=None,
                        help="Chemin de a5f.dhfi STANDARD local (optionnel)")
    parser.add_argument("--a5f-versionx9", default=None,
                        help="Chemin de a5f.dhfi STANDARD de versionx9 (optionnel)")
    parser.add_argument("--a5fu", default=None,
                        help="Chemin de a5fu.dhfi (zooms SPECIFIQUES/surcharge, overlay a5f)")
    parser.add_argument("--domain", default=None,
                        help=f"Code domaine standard ({', '.join(sorted(DOMAIN_RANGES.keys()))})")
    parser.add_argument("--range", default=None,
                        help="Plage personnalisee au format START-END (ex: 9900-9999)")
    parser.add_argument("--count", type=int, default=1,
                        help="Nombre de numeros libres confirmes a retourner (defaut: 1)")
    parser.add_argument("--read-isam-script", default=None,
                        help="Chemin de reading-isam-files/scripts/read_isam.py "
                             "(requis si --a5f-local / --a5f-versionx9 / --a5fu)")
    parser.add_argument("--structure", default=None,
                        help="Chemin structure_a5f_m4.json "
                             "(requis si --a5f-local / --a5f-versionx9 / --a5fu)")
    parser.add_argument("--specifs-root", action="append", default=None, metavar="DIR",
                        help="Repertoire de sources SPECIFIQUES/surcharge a scanner en "
                             "phase 2 (repetable). Le standard n'est JAMAIS scanne.")
    parser.add_argument("--max-files", type=int, default=20000,
                        help="Borne de fichiers scannes en phase 2 (defaut: 20000)")
    args = parser.parse_args()

    # Resoudre la plage cible d'ALLOCATION (le used-set, lui, reste global)
    if args.range:
        m = re.match(r'^(\d+)-(\d+)$', args.range.strip())
        if not m:
            print(f"Erreur : --range invalide '{args.range}'. Format attendu : START-END", file=sys.stderr)
            sys.exit(2)
        start, end = int(m.group(1)), int(m.group(2))
        # Garde-fou : ZoomNum = 5 chars dans la structure M4 (99999 max). La plage
        # >= 100000 est valide pour allocating-menu-enrno (EnrNo menu M2, 6 chars), pas ici.
        if end > 99999 or start > 99999:
            print(
                f"Erreur : --range {args.range} depasse 99999. La structure M4 de "
                f"a5f/a5fu limite ZoomNum a 5 caracteres (max 99999).",
                file=sys.stderr,
            )
            sys.exit(2)
        if start > end:
            print(f"Erreur : --range {args.range} : borne basse > borne haute", file=sys.stderr)
            sys.exit(2)
        ranges = [(start, end)]
        alloc_origin = f"range={args.range}"
    elif args.domain:
        ranges = DOMAIN_RANGES.get(args.domain.upper())
        if not ranges:
            print(f"Erreur : domaine inconnu '{args.domain}'. Valides : "
                  f"{sorted(DOMAIN_RANGES.keys())}", file=sys.stderr)
            sys.exit(2)
        alloc_origin = f"domain={args.domain.upper()}"
    else:
        # Defaut : convention partenaire (nouveau zoom specifique demarre a 90000)
        ranges = [PARTNER_DEFAULT_RANGE]
        alloc_origin = "partenaire 90000+ (convention par defaut)"

    # --- Used-set : a5tczoom (standard) + a5f (standard) + a5fu (specifique) ---
    consts = parse_a5tczoom(args.a5tczoom)

    a5f_local_nums = set()
    a5f_v9_nums = set()
    a5fu_nums = set()
    needs_isam = args.a5f_local or args.a5f_versionx9 or args.a5fu
    if needs_isam and (not args.read_isam_script or not args.structure):
        print("Erreur : --a5f-local/--a5f-versionx9/--a5fu requierent --read-isam-script ET --structure",
              file=sys.stderr)
        sys.exit(2)
    if args.a5f_local:
        a5f_local_nums = parse_a5f_zooms(args.a5f_local, args.read_isam_script, args.structure)
    if args.a5f_versionx9:
        a5f_v9_nums = parse_a5f_zooms(args.a5f_versionx9, args.read_isam_script, args.structure)
    if args.a5fu:
        a5fu_nums = parse_a5f_zooms(args.a5fu, args.read_isam_script, args.structure)

    used = set(consts.keys()) | a5f_local_nums | a5f_v9_nums | a5fu_nums

    # --- Phase 1 : pool de candidats libres d'apres le used-set ---
    specifs_roots = args.specifs_root or []
    # Si phase 2 active, on prend un pool plus large pour absorber les "suspects".
    pool_count = args.count if not specifs_roots else (args.count * 5 + 5)
    pool = find_free(used, ranges, pool_count)

    # --- Phase 2 : recherche large dans les sources SPECIFIQUES uniquement ---
    occ_by_num, files_scanned, truncated = broad_search(
        pool, specifs_roots, SPECIFS_SCAN_EXTS, args.max_files
    )

    clean = [n for n in pool if not occ_by_num.get(n)]
    suspects = [
        {"num": n, "occurrences": occ_by_num[n]}
        for n in pool if occ_by_num.get(n)
    ]
    free = clean[:args.count]

    result = {
        "free": free,
        "allocation_origin": alloc_origin,
        "ranges_considered": [[s, e] for (s, e) in ranges],
        "sources": {
            "a5tczoom_count": len(consts),
            "a5f_local_count": len(a5f_local_nums),
            "a5f_versionx9_count": len(a5f_v9_nums),
            "a5fu_count": len(a5fu_nums),
            "union_used_count": len(used),
        },
        "specifs_search": {
            "enabled": bool(specifs_roots),
            "roots": specifs_roots,
            "exts": list(SPECIFS_SCAN_EXTS),
            "files_scanned": files_scanned,
            "truncated": truncated,
            "candidates_examined": pool,
            "suspects": suspects,
        },
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    sys.exit(0 if free else 1)


if __name__ == "__main__":
    main()
