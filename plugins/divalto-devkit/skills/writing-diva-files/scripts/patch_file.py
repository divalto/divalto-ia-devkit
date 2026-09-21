#!/usr/bin/env python3
"""patch_file.py -- Edition chirurgicale d'un fichier texte Divalto (ISO-8859-1 + CRLF).

Modifie un fichier EXISTANT ligne a ligne SANS toucher au reste, en preservant
l'encodage ISO-8859-1 et les fins de ligne CRLF. C'est la voie recommandee pour
MODIFIER un fichier (write_file.py, lui, CREE ou reecrit le fichier en entier).

Operations (--op) :
  insert   : insere du contenu (par --line N + --position, ou par --anchor)
  prepend  : insere en tete de fichier
  append   : insere en fin de fichier
  replace  : remplace la/les ligne(s) ciblee(s) (--anchor, ou --line N / --line-range A:B + --expect-content)
  delete   : supprime la/les ligne(s) (--anchor, ou --line N / --line-range A:B + --expect-content)

Ancrage :
  --anchor "texte"          sous-chaine litterale cherchee dans une ligne (regex si --regex)
  --line N                  numero de ligne 1-based (insert ; ou ligne unique en replace/delete)
  --line-range A:B          plage 1-based inclusive (replace/delete)
  --position before|after   cote de l'insertion (insert ; defaut after)
  --expect N                nb de lignes que l'ancre DOIT matcher (defaut 1). Sinon -> refus, rien ecrit.

Garde-fou anti-numero perime (#303) -- OBLIGATOIRE pour tout ciblage par NUMERO (--line/--line-range) en replace/delete :
  --expect-content "..."         contenu ACTUEL attendu aux lignes visees (match EXACT du bloc entier)
  --expect-content-file <utf8>   idem depuis un fichier UTF-8 (multi-ligne, sans quoting)
    Contenu reel != attendu (fichier modifie depuis la lecture -- mon edition ou xwin en parallele)
    -> REFUS, rien ecrit. L'ancre (--anchor) se verifie deja par son texte -> non concernee.

Securite :
  - Refuse les fichiers STRUCTURES (.dhsd .dhsf .dhsi) : positions/offsets, l'edition
    ligne-a-ligne y est dangereuse. Utiliser le skill dedie (managing-diva-dictionaries
    pour .dhsd ; manipulating-dhsf-screens pour .dhsf/.dhsi). Override : --force-structured.
  - Backup `.bak` (cache sous Windows, glissant : un seul par fichier) avant ecriture, sauf --no-backup.
    NB : l'attribut cache Windows masque le fichier dans l'Explorateur ; il NE garantit PAS
    qu'un VCS (SVN/Git...) l'ignore -- ajouter une regle d'ignore cote partenaire si besoin.
  - --dry-run : montre le resultat sans rien ecrire.
  - Re-verifie l'encodage ISO-8859-1 + CRLF apres ecriture (restaure depuis backup si KO).

Contenu : --content "..."  ou  --content-file <fichier UTF-8>  ou  --stdin  (requis sauf pour delete).

Sortie : JSON sur stdout. Exit 0 = succes, 1 = erreur applicative, 2 = erreur d'usage.
"""

import argparse
import json
import os
import re
import shutil
import sys

STRUCTURED_EXT = {'.dhsd', '.dhsf', '.dhsi'}

# XWin refuse d'OUVRIR un source des qu'une ligne physique depasse cette longueur.
MAX_LINE = 251


def _utf8_residue_count(data):
    """Compte les sequences UTF-8 residuelles dans des octets censes etre ISO-8859-1
    (signature d'un mojibake : Latin-1 double-encode). Copie autonome de la meme
    heuristique que verify_encoding.find_utf8_residue / write_file._utf8_residue_count
    (vendoring intra-skill : chaque script reste executable seul)."""
    n = 0
    i = 0
    total = len(data)
    while i < total:
        b = data[i]
        if b in (0xC2, 0xC3) and i + 1 < total and 0x80 <= data[i + 1] <= 0xBF:
            n += 1
            i += 2
            continue
        if b == 0xEF and i + 2 < total and data[i + 1] == 0xBF and data[i + 2] == 0xBD:
            n += 1
            i += 3
            continue
        i += 1
    return n


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


def clear_hidden_windows(path):
    """Retire l'attribut 'cache' Windows (no-op hors Windows ; jamais bloquant).

    Indispensable apres une restauration depuis le `.bak` : ce dernier est volontairement
    cache, et une copie qui preserve les metadonnees rendrait le SOURCE restaure invisible
    dans l'Explorateur -- et surtout non reinscriptible (`open(path,'wb')` -> PermissionError
    sur un fichier cache sous Windows), donc impatchable par les scripts du skill.
    """
    if os.name != 'nt':
        return
    try:
        import ctypes
        FILE_ATTRIBUTE_HIDDEN = 0x02
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs != -1 and (attrs & FILE_ATTRIBUTE_HIDDEN):
            ctypes.windll.kernel32.SetFileAttributesW(str(path), attrs & ~FILE_ATTRIBUTE_HIDDEN)
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
    """Reecrit en ISO-8859-1 + CRLF, avec CRLF final garanti.

    Encode AVANT d'ouvrir la cible : si un caractere n'est pas encodable en ISO-8859-1
    (BOM residuel, guillemet typographique, emoji...), l'erreur est levee AVANT l'ouverture
    en ecriture -> la cible reste intacte (pas de troncature). Cf. #262."""
    content = '\r\n'.join(lines)
    if content:
        content += '\r\n'
    data = content.encode('iso-8859-1')  # peut lever UnicodeEncodeError -- cible pas encore ouverte
    with open(path, 'wb') as f:
        f.write(data)


def get_content_lines(args):
    if args.content_file is not None:
        # Fichier UTF-8 (utf-8-sig -> BOM supprime) : evite le quoting PowerShell + le
        # decodage console. Voie privilegiee sous PowerShell.
        try:
            with open(args.content_file, 'r', encoding='utf-8-sig') as _cf:
                c = _cf.read()
        except OSError as e:
            fail(f"--content-file illisible : {e}", 1)
        except UnicodeDecodeError as e:
            fail(f"--content-file n'est pas de l'UTF-8 valide : {e}", 1)
    elif args.stdin:
        # Octets bruts + decodage UTF-8 explicite : sys.stdin.read() decoderait avec
        # l'encodage console (cp1252 sur poste Windows) -> mojibake silencieux sur un
        # contenu UTF-8 pipe. Non-UTF-8 -> echec BRUYANT, pas de corruption.
        try:
            c = sys.stdin.buffer.read().decode('utf-8-sig')  # -sig : strippe un BOM de tete pipe (cf. #262)
        except UnicodeDecodeError as e:
            fail(f"stdin n'est pas de l'UTF-8 valide (offset {e.start}) : {e}. "
                 f"Piper de l'UTF-8, ou passer le contenu via --content-file.", 1)
    elif args.content is not None:
        c = args.content
    else:
        fail("--content, --content-file ou --stdin requis pour cette operation", 2)
    c = c.replace('\r\n', '\n').replace('\r', '\n')
    if c.endswith('\n'):
        c = c[:-1]
    return c.split('\n')


def get_expect_lines(args):
    """Contenu ACTUEL attendu aux lignes visees (--expect-content / --expect-content-file),
    normalise en liste de lignes logiques. Retourne None si aucun des deux n'est fourni."""
    if args.expect_content_file is not None:
        try:
            with open(args.expect_content_file, 'r', encoding='utf-8-sig') as _ef:
                c = _ef.read()
        except OSError as e:
            fail(f"--expect-content-file illisible : {e}", 1)
        except UnicodeDecodeError as e:
            fail(f"--expect-content-file n'est pas de l'UTF-8 valide : {e}", 1)
    elif args.expect_content is not None:
        c = args.expect_content
    else:
        return None
    c = c.replace('\r\n', '\n').replace('\r', '\n')
    if c.endswith('\n'):
        c = c[:-1]
    return c.split('\n')


def find_anchor(lines, anchor, is_regex):
    if is_regex:
        rx = re.compile(anchor)
        return [i for i, ln in enumerate(lines) if rx.search(ln)]
    return [i for i, ln in enumerate(lines) if anchor in ln]


def measure_file(raw):
    """Mesure les criteres de validite d'un contenu DIVA, ALIGNES sur verify_encoding.py
    (vendoring intra-skill).

    Retourne un dict de MESURES (pas de messages) pour pouvoir comparer l'etat AVANT et
    APRES l'ecriture : patch_file doit repondre de ce qu'il ECRIT, pas de la salete
    preexistante -- sinon reparer un fichier deja corrompu devient impossible, alors que
    c'est precisement l'usage recommande (cf. le hint de convert_file.py).
    """
    absolus = []
    try:
        raw.decode('iso-8859-1')
    except Exception:
        absolus.append('octets non decodables en ISO-8859-1')
    if raw.startswith(b'\xef\xbb\xbf'):          # BOM UTF-8
        absolus.append('BOM UTF-8 en tete')
    if raw.replace(b'\r\n', b'').count(b'\n'):   # LF nu (non precede de CR)
        absolus.append('LF nu (fins de ligne non CRLF)')
    if raw and not raw.endswith(b'\r\n'):        # CRLF final manquant
        absolus.append('CRLF final manquant (Erreur 135 a la compilation)')
    physical = raw.decode('iso-8859-1', errors='replace').replace('\r\n', '\n').split('\n')
    return {
        # Criteres ABSOLUS : entierement sous le controle de l'ecrivain -> jamais tolerés.
        'absolus': absolus,
        # Criteres CUMULATIFS : compares avant/apres pour n'imputer que ce que l'on introduit.
        'residue': _utf8_residue_count(raw),
        'longs': [k + 1 for k, ln in enumerate(physical) if len(ln) > MAX_LINE],
    }


def issues_from(m):
    """Messages lisibles a partir d'une mesure."""
    out = list(m['absolus'])
    if m['residue']:
        out.append('%d sequence(s) UTF-8 residuelle(s) (mojibake probable)' % m['residue'])
    if m['longs']:
        out.append("%d ligne(s) > %d caracteres (XWin refuse d'ouvrir) : ligne(s) %s"
                   % (len(m['longs']), MAX_LINE, ', '.join(str(x) for x in m['longs'][:5])))
    return out


def main():
    # Sortie en UTF-8 (stdout + stderr) : sinon print() encode avec la console (cp1252 sur
    # Windows) et les caracteres non-ASCII cassent un json.loads(utf-8) cote appelant
    # (fail() emet meme son JSON d'erreur sur stderr). Meme garde-fou que read_isam.py.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
            _stream.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="Edition chirurgicale d'un fichier Divalto (ISO-8859-1 + CRLF).")
    p.add_argument('--path', required=True)
    p.add_argument('--op', required=True, choices=['insert', 'prepend', 'append', 'replace', 'delete'])
    p.add_argument('--content')
    p.add_argument('--content-file', dest='content_file',
                   help="Lire le contenu depuis un fichier UTF-8 (evite le quoting PowerShell et le BOM)")
    p.add_argument('--stdin', action='store_true')
    p.add_argument('--anchor')
    p.add_argument('--regex', action='store_true')
    p.add_argument('--line', type=int)
    p.add_argument('--line-range', dest='line_range')
    p.add_argument('--position', choices=['before', 'after'], default='after')
    p.add_argument('--expect', type=int, default=1)
    p.add_argument('--expect-content',
                   help="Contenu ACTUEL attendu aux lignes visees -- OBLIGATOIRE pour le ciblage par "
                        "numero (--line/--line-range) en replace/delete (garde-fou anti-numero perime #303)")
    p.add_argument('--expect-content-file', dest='expect_content_file',
                   help="Comme --expect-content mais depuis un fichier UTF-8 (multi-ligne, sans quoting)")
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

    # `--expect-content` ne garde QUE le ciblage par numero en replace/delete (decision de
    # perimetre : insert n'est pas gate). L'accepter ailleurs en l'IGNORANT donnait une
    # fausse garantie : l'appelant qui l'ajoutait par prudence croyait etre protege et ne
    # l'etait pas (exit 0, ecriture faite, aucun avertissement). On refuse explicitement.
    _par_numero = args.line is not None or args.line_range is not None
    if (args.expect_content is not None or args.expect_content_file is not None) \
            and not (op in ('replace', 'delete') and _par_numero):
        _pourquoi = ("l'operation %s n'est pas gardee" % op
                     if op not in ('replace', 'delete')
                     else "le ciblage se fait par --anchor, qui se verifie par son propre texte")
        fail(f"--expect-content / --expect-content-file n'a AUCUN effet ici ({_pourquoi}) : "
             f"il ne garde que le ciblage par NUMERO (--line / --line-range) en replace/delete. "
             f"Retirer l'option pour ne pas se croire protege, ou cibler par numero.",
             2, op=op, cible=("numero" if _par_numero else "ancre"))

    # Garde-fou anti-mojibake sur le CONTENU A INJECTER uniquement (symetrie avec le refus
    # de write_file.py). Porte volontairement sur `new` et PAS sur tout le fichier : patcher
    # une cible deja sale AILLEURS (mojibake preexistant sur une ligne non touchee) est une
    # operation legitime -- souvent la reparation elle-meme -- qu'un controle tout-fichier
    # refuserait. Actif aussi en --dry-run, comme --expect-content.
    if new:
        probe = '\r\n'.join(new).encode('iso-8859-1', errors='replace')
        residue = _utf8_residue_count(probe)
        if residue:
            fail("%d sequence(s) UTF-8 residuelle(s) dans le CONTENU A INJECTER "
                 "(mojibake / double-encodage en amont) -- rien ecrit, cible intacte. "
                 "Verifier la source du contenu (le pipe transporte-t-il bien de l'UTF-8 propre ?)."
                 % residue, 1, residues=residue)

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
        # Ciblage numerique : --line N (ligne unique) ou --line-range A:B.
        rng = None
        if args.line_range:
            m = re.match(r'^(\d+):(\d+)$', args.line_range)
            if not m:
                fail("--line-range attend le format A:B (1-based)", 2)
            rng = (int(m.group(1)), int(m.group(2)))
        elif args.line is not None:
            rng = (args.line, args.line)

        if rng is not None:
            a, b = rng
            label = f"--line {a}" if (args.line is not None and not args.line_range) else f"--line-range {a}:{b}"
            if a < 1 or b > n0 or a > b:
                fail(f"{label} hors limites (1..{n0})", 2)
            # Garde-fou OBLIGATOIRE pour le ciblage par NUMERO : sans contenu de reference, un
            # numero perime (fichier modifie depuis la lecture -- ma propre edition anterieure ou
            # le collaborateur dans xwin en parallele) ecrase/supprime la MAUVAISE ligne sans
            # aucune erreur (#303/#263). L'ancre (--anchor), elle, se verifie deja par son texte.
            expected = get_expect_lines(args)
            if expected is None:
                fail(f"{label} (ciblage par numero) exige --expect-content ou --expect-content-file : "
                     f"fournir le contenu ACTUEL attendu aux lignes visees pour verifier que les "
                     f"numeros ne sont pas perimes. Voie sure alternative : --anchor.", 2)
            actual = lines[a - 1:b]
            if actual != expected:
                ln = exp_v = act_v = None
                for k in range(max(len(expected), len(actual))):
                    ev = expected[k] if k < len(expected) else '<absente>'
                    av = actual[k] if k < len(actual) else '<absente>'
                    if ev != av:
                        ln, exp_v, act_v = a + k, ev, av
                        break
                fail(f"--expect-content ne correspond pas au contenu actuel de {label} : la plage a "
                     f"probablement derive (numeros perimes). 1re divergence ligne {ln} -- "
                     f"attendu {exp_v!r}, trouve {act_v!r}. Rien ecrit ; relire le fichier et "
                     f"recalculer les numeros, ou utiliser --anchor.", 1,
                     expected_lines=len(expected), actual_lines=len(actual))
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
            fail(f"{op} requiert --anchor, --line ou --line-range", 2)

    n1 = len(lines)
    changed = (lines != original)

    if args.dry_run:
        print(json.dumps({"status": "ok", "path": os.path.abspath(path), "op": op, "dry_run": True,
                          "matched": matched, "lines_before": n0, "lines_after": n1, "changed": changed},
                         ensure_ascii=False, indent=2))
        return

    # Etat AVANT ecriture : sert a n'imputer a ce patch que les defauts qu'il INTRODUIT
    # (les defauts preexistants ne doivent pas empecher une reparation chirurgicale).
    avant = measure_file(open(path, 'rb').read())

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

    try:
        write_lines(path, lines)
    except UnicodeEncodeError as e:
        # encode leve AVANT ouverture -> cible intacte ; le backup eventuel reste (redondant, inoffensif)
        fail(f"caractere non encodable en ISO-8859-1 (position {e.start}) : {e.reason}. "
             f"Rien ecrit, cible intacte (verifier BOM/guillemet typographique/caractere hors Latin-1).", 1)

    apres = measure_file(open(path, 'rb').read())
    # On n'impute que ce que CE patch a introduit : les criteres absolus (encodage, CRLF,
    # BOM) sont toujours de notre ressort, les criteres cumulatifs (mojibake, lignes > 251)
    # seulement s'ils AUGMENTENT. Sinon patcher un fichier deja sale serait impossible --
    # or c'est justement la voie de reparation recommandee.
    introduits = list(apres['absolus'])
    if apres['residue'] > avant['residue']:
        introduits.append('%d sequence(s) UTF-8 residuelle(s) AJOUTEE(S) par ce patch'
                          % (apres['residue'] - avant['residue']))
    if len(apres['longs']) > len(avant['longs']):
        introduits.append("%d ligne(s) > %d caracteres AJOUTEE(S) par ce patch "
                          "(XWin refuse d'ouvrir le source)"
                          % (len(apres['longs']) - len(avant['longs']), MAX_LINE))
    if introduits:
        detail = ' ; '.join(introduits)
        if backup and os.path.exists(backup):
            # copyfile (et NON copy2) : ne pas propager les metadonnees du `.bak`, qui est
            # cache -- sinon le source restaure devient invisible ET non reinscriptible.
            shutil.copyfile(backup, path)
            clear_hidden_windows(path)
            fail("Verification echouee apres ecriture -- fichier RESTAURE depuis le backup. "
                 "Cause(s) : " + detail,
                 1, backup=os.path.abspath(backup), issues=introduits, restored=True)
        # Sans backup (--no-backup), RIEN n'a ete restaure : ne pas le laisser croire.
        fail("Verification echouee apres ecriture et AUCUN backup disponible (--no-backup) : "
             "l'ecriture est CONSERVEE sur le disque, a corriger manuellement. Cause(s) : " + detail,
             1, backup=None, issues=introduits, restored=False)

    # Le patch est propre. Le fichier peut malgre tout rester invalide a cause de defauts
    # PREEXISTANTS : on le signale au lieu de certifier `verified: true` a tort.
    preexistants = issues_from(apres)

    resultat = {"status": "ok", "path": os.path.abspath(path), "op": op, "matched": matched,
                "lines_before": n0, "lines_after": n1, "changed": changed,
                "backup": (os.path.abspath(backup) if backup else None),
                "verified": not preexistants}
    if preexistants:
        resultat["preexisting_issues"] = preexistants
        resultat["hint"] = ("Le patch lui-meme est propre, mais le fichier reste invalide a "
                            "cause de defauts PREEXISTANTS (non introduits par cette "
                            "operation) : les corriger avant compilation -- cf. "
                            "verify_encoding.py puis convert_file.py.")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
