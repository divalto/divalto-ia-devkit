#!/usr/bin/env python3
"""patch_file.py -- Edition chirurgicale d'un fichier texte Divalto (ISO-8859-1 + CRLF).

Modifie un fichier EXISTANT ligne a ligne SANS toucher au reste, en preservant
l'encodage ISO-8859-1 et les fins de ligne CRLF. C'est la voie recommandee pour
MODIFIER un fichier (write_file.py, lui, CREE ou reecrit le fichier en entier).

Operations (--op) :
  insert   : insere du contenu (par --line N + --position, ou par --anchor)
  prepend  : insere en tete de fichier
  append   : insere en fin de fichier
  replace  : remplace la/les ligne(s) ciblee(s) (--anchor ou --line-range A:B)
  delete   : supprime la/les ligne(s) (--anchor ou --line-range A:B)

Ancrage :
  --anchor "texte"          sous-chaine litterale cherchee dans une ligne (regex si --regex)
  --line N                  numero de ligne 1-based (insert)
  --line-range A:B          plage 1-based inclusive (replace/delete)
  --position before|after   cote de l'insertion (insert ; defaut after)
  --expect N                nb de lignes que l'ancre DOIT matcher (defaut 1). Sinon -> refus, rien ecrit.

Securite :
  - Refuse les fichiers STRUCTURES (.dhsd .dhsf .dhsi) : positions/offsets, l'edition
    ligne-a-ligne y est dangereuse. Utiliser le skill dedie (managing-diva-dictionaries
    pour .dhsd ; manipulating-dhsf-screens pour .dhsf/.dhsi). Override : --force-structured.
  - Backup `.bak` (cache sous Windows, glissant : un seul par fichier) avant ecriture, sauf --no-backup.
    NB : l'attribut cache Windows masque le fichier dans l'Explorateur ; il NE garantit PAS
    qu'un VCS (SVN/Git...) l'ignore -- ajouter une regle d'ignore cote partenaire si besoin.
  - --dry-run : montre le resultat sans rien ecrire.
  - Re-verifie l'encodage ISO-8859-1 + CRLF apres ecriture (restaure depuis backup si KO).

Contenu : --content "..."  ou  --stdin  (requis sauf pour delete).

Sortie : JSON sur stdout. Exit 0 = succes, 1 = erreur applicative, 2 = erreur d'usage.
"""

import argparse
import json
import os
import re
import shutil
import sys

STRUCTURED_EXT = {'.dhsd', '.dhsf', '.dhsi'}


def fail(msg, code=1, **extra):
    print(json.dumps({"status": "error", "error": msg, **extra}, ensure_ascii=False, indent=2),
          file=sys.stderr)
    sys.exit(code)


def set_hidden_windows(path):
    """Pose l'attribut 'cache' Windows (no-op hors Windows ; jamais bloquant)."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass


def read_lines(path):
    """Lit en binaire, decode ISO-8859-1, retourne les lignes logiques (sans fin de ligne)."""
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('iso-8859-1').replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines


def write_lines(path, lines):
    """Reecrit en ISO-8859-1 + CRLF, avec CRLF final garanti."""
    content = '\r\n'.join(lines)
    if content:
        content += '\r\n'
    with open(path, 'wb') as f:
        f.write(content.encode('iso-8859-1'))


def get_content_lines(args):
    if args.stdin:
        c = sys.stdin.read()
    elif args.content is not None:
        c = args.content
    else:
        fail("--content ou --stdin requis pour cette operation", 2)
    c = c.replace('\r\n', '\n').replace('\r', '\n')
    if c.endswith('\n'):
        c = c[:-1]
    return c.split('\n')


def find_anchor(lines, anchor, is_regex):
    if is_regex:
        rx = re.compile(anchor)
        return [i for i, ln in enumerate(lines) if rx.search(ln)]
    return [i for i, ln in enumerate(lines) if anchor in ln]


def verify_iso_crlf(path):
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        raw.decode('iso-8859-1')
    except Exception:
        return False
    if raw.startswith(b'\xef\xbb\xbf'):          # BOM UTF-8
        return False
    if raw.replace(b'\r\n', b'').count(b'\n'):   # LF nu (non precede de CR)
        return False
    if raw and not raw.endswith(b'\r\n'):        # CRLF final manquant
        return False
    return True


def main():
    p = argparse.ArgumentParser(description="Edition chirurgicale d'un fichier Divalto (ISO-8859-1 + CRLF).")
    p.add_argument('--path', required=True)
    p.add_argument('--op', required=True, choices=['insert', 'prepend', 'append', 'replace', 'delete'])
    p.add_argument('--content')
    p.add_argument('--stdin', action='store_true')
    p.add_argument('--anchor')
    p.add_argument('--regex', action='store_true')
    p.add_argument('--line', type=int)
    p.add_argument('--line-range', dest='line_range')
    p.add_argument('--position', choices=['before', 'after'], default='after')
    p.add_argument('--expect', type=int, default=1)
    p.add_argument('--no-backup', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--force-structured', action='store_true')
    args = p.parse_args()

    path = args.path
    if not os.path.isfile(path):
        fail(f"Fichier introuvable : {path}. Pour CREER un fichier, utiliser write_file.py.", 1)

    ext = os.path.splitext(path)[1].lower()
    if ext in STRUCTURED_EXT and not args.force_structured:
        fail(f"Fichier structure ({ext}) : edition ligne-a-ligne risquee (positions/offsets). "
             f"Utiliser le skill dedie -- managing-diva-dictionaries (.dhsd) ou "
             f"manipulating-dhsf-screens (.dhsf/.dhsi). Override explicite : --force-structured.",
             1, extension=ext)

    original = read_lines(path)
    lines = list(original)
    n0 = len(lines)
    matched = []

    op = args.op
    new = get_content_lines(args) if op in ('insert', 'prepend', 'append', 'replace') else []

    if op == 'prepend':
        if lines[:len(new)] == new:
            print(json.dumps({"status": "ok", "path": os.path.abspath(path), "op": op, "changed": False,
                              "reason": "contenu deja present en tete", "lines_before": n0,
                              "lines_after": n0, "dry_run": args.dry_run}, ensure_ascii=False, indent=2))
            return
        lines = new + lines

    elif op == 'append':
        if new and lines[len(lines) - len(new):] == new:
            print(json.dumps({"status": "ok", "path": os.path.abspath(path), "op": op, "changed": False,
                              "reason": "contenu deja present en fin", "lines_before": n0,
                              "lines_after": n0, "dry_run": args.dry_run}, ensure_ascii=False, indent=2))
            return
        lines = lines + new

    elif op == 'insert':
        if args.line is not None:
            if args.line < 1 or args.line > n0 + 1:
                fail(f"--line {args.line} hors limites (1..{n0 + 1})", 2)
            at = (args.line - 1) if args.position == 'before' else args.line
            lines = lines[:at] + new + lines[at:]
            matched = [args.line]
        elif args.anchor is not None:
            idx = find_anchor(lines, args.anchor, args.regex)
            if len(idx) != args.expect:
                fail(f"Ancre matchee {len(idx)} fois, attendu {args.expect}. Rien ecrit.", 1, matched=[i + 1 for i in idx])
            for i in sorted(idx, reverse=True):
                at = i if args.position == 'before' else i + 1
                lines = lines[:at] + new + lines[at:]
            matched = [i + 1 for i in idx]
        else:
            fail("insert requiert --line N ou --anchor", 2)

    elif op in ('replace', 'delete'):
        if args.line_range:
            m = re.match(r'^(\d+):(\d+)$', args.line_range)
            if not m:
                fail("--line-range attend le format A:B (1-based)", 2)
            a, b = int(m.group(1)), int(m.group(2))
            if a < 1 or b > n0 or a > b:
                fail(f"--line-range {a}:{b} hors limites (1..{n0})", 2)
            matched = list(range(a, b + 1))
            lines = lines[:a - 1] + (new if op == 'replace' else []) + lines[b:]
        elif args.anchor is not None:
            idx = find_anchor(lines, args.anchor, args.regex)
            if len(idx) != args.expect:
                fail(f"Ancre matchee {len(idx)} fois, attendu {args.expect}. Rien ecrit.", 1, matched=[i + 1 for i in idx])
            matched = [i + 1 for i in idx]
            idxset = set(idx)
            rebuilt = []
            for i, ln in enumerate(lines):
                if i in idxset:
                    if op == 'replace':
                        rebuilt.extend(new)
                else:
                    rebuilt.append(ln)
            lines = rebuilt
        else:
            fail(f"{op} requiert --anchor ou --line-range", 2)

    n1 = len(lines)
    changed = (lines != original)

    if args.dry_run:
        print(json.dumps({"status": "ok", "path": os.path.abspath(path), "op": op, "dry_run": True,
                          "matched": matched, "lines_before": n0, "lines_after": n1, "changed": changed},
                         ensure_ascii=False, indent=2))
        return

    backup = None
    if not args.no_backup:
        backup = path + '.bak'
        try:
            if os.path.exists(backup):
                os.remove(backup)          # backup glissant : on remplace l'ancien (evite le verrou 'hidden' a la reecriture)
            shutil.copy2(path, backup)
            set_hidden_windows(backup)
        except Exception as e:
            fail(f"Echec creation backup : {e}", 1)

    write_lines(path, lines)

    if not verify_iso_crlf(path):
        if backup and os.path.exists(backup):
            shutil.copy2(backup, path)
        fail("Verification ISO-8859-1/CRLF echouee apres ecriture ; fichier restaure depuis le backup.",
             1, backup=(os.path.abspath(backup) if backup else None))

    print(json.dumps({"status": "ok", "path": os.path.abspath(path), "op": op, "matched": matched,
                      "lines_before": n0, "lines_after": n1, "changed": changed,
                      "backup": (os.path.abspath(backup) if backup else None), "verified": True},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
