#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertit les anciennes fonctions de lecture DIVA (seek_xxx, Lectab) vers la nouvelle
API objet metier (Give_xxx, Find_T041, Load_gtfdos) lors d'une migration Divalto.

Autonome : n'utilise NI AutoConvertSrc.exe NI diva-MCP. La verification de l'existence
d'une fonction cible se fait par lecture de l'objet metier *tmchk<entite>.dhsp dans le
PACK STD DE DESTINATION fourni en parametre (--std).

Regles (par ligne, casse insensible) :
  seek_soc(x)         -> Load_gtfdos(x)                        (exception directe, sans verif)
  seek_<x>(args)      -> Give_<x>(<INSTANCE>, args)            si Give_<x> existe ; + ;TODO hooks (cf. note seek)
  Lectab(n|nn, [a b]) -> Give_T0nn(T0nn, a, b)                 si Give_T0nn existe (numero sur 1 ou 2 chiffres)
  Lectab(n|nn, a & b) -> Give_T0nn(T0nn, a, b)                 cle concatenee eclatee selon le nb de champs de la signature
  Lectab(n|nn, cle)   -> Give_T0nn(T0nn, cle)                  SANS numero d'erreur : lecture simple, pas d'erreur auto
  Lectab(nn, cle, 11nn) -> Find_T0nn(cle)                      AVEC numero d'erreur (3e arg = 1100+table) : Find_T0nn
                                                               affiche l'erreur automatiquement (GT_GererErreurCheck)
  Lectab(nn, cle, 11nn) -> Find_T0nn(cle, allcolumns = true)   idem MAIS si l'enreg T0nn est lu en aval (T0nn.Champ)
    + ;TODO Get_Record                                         dans le fichier : charge tout + TODO Get_T0nn_Record()

Note : la presence du 3e argument (numero d'erreur 11nn) determine la cible. Sans lui -> Give_T0nn
(remplit l'instance, pas d'affichage d'erreur). Avec lui -> Find_T0nn(<cle>) qui reproduit l'affichage
automatique de l'erreur de l'ancien Lectab. Find_T0nn prend la CLE en 1er argument (pas d'instance).
Enrichissement automatique : si un champ de l'instance (T0nn.Champ) est lu ailleurs dans le fichier,
le Find_ recoit "allcolumns = true" (charge l'enreg complet) et un ';TODO Get_Record' rappelle d'ajouter
"T0nn = Get_T0nn_Record()" apres succes (2e instruction, non inserable de facon sure dans une condition).
Toutes les tables T000..T099 exposent les deux fonctions ; T041 n'est pas un cas special.

Note cle : l'ancien Lectab/Seek recoit la CLE CONCATENEE (champ1 & champ2 & ...) alors que Give_/Find_
attendent les champs de la cle en PARAMETRES SEPARES. Le nombre de champs de cle est lu dans la signature
reelle de l'objet metier (parametres de tete avant 'allcolumns'/'context' pour Find_ ; parametres apres
l'instance pour Give_). Si la cle est concatenee par '&' et que la cible attend N champs, on eclate sur les
'&' de premier niveau en exactement N arguments. Si l'eclatement est ambigu (compte different), la cle est
laissee telle quelle avec un ';TODO cle' a verifier manuellement.

Note seek_ : en X.13, Seek_<ent> survit comme wrapper de compatibilite (gtpmfic.dhsp) faisant l'acces
ISAM legacy + les hooks <Ent>_Seek_Av/_Ap. La conversion seek_<ent> -> Give_<ent> est donc une
MODERNISATION optionnelle ; comme Give_ ne declenche pas ces hooks, chaque conversion recoit un
';TODO hooks ...' invitant a verifier qu'aucune surcharge/standard ne s'y branche.

Tout appel (hors seek_soc) dont la fonction cible est introuvable dans le pack reste
INCHANGE, avec un commentaire ';TODO migration ...' ajoute en fin de ligne, et une entree
au rapport.

Sortie : seuls les fichiers modifies sont ecrits dans --out (en miroir du chemin relatif),
en ISO-8859-1 (latin-1), fins de ligne preservees, sans BOM. Un rapport regExResult.txt
est genere.

Usage :
  py convert_lectures.py --src <sources> --out <sortie> --std <pack_std> [--report <chemin>]
"""

import argparse
import re
import sys
from pathlib import Path

# ISO-8859-1 : bijection parfaite octet <-> caractere (round-trip exact des octets non modifies).
ENCODING = "latin-1"

# Module compile portant Load_gtfdos (fonction framework, livree compilee dans le pack).
LOAD_GTFDOS_OM = "gtpmfdos"

# Detection d'un appel de lecture : seek_<lettre...> ou lectab, suivi d'une parenthese ouvrante.
FIND = re.compile(r"\b(?P<name>seek_[A-Za-z]\w*|lectab)\s*\(", re.IGNORECASE)

# Definition de fonction locale DIVA : 'function <type> <nom>(' ou 'function <nom>('
# (eventuellement prefixee public/private/local). Sert a EXCLURE les seek_xxx qui sont
# en realite des fonctions utilisateur definies dans le fichier (pas des lectures ISAM).
LOCAL_DEF = re.compile(
    r"(?im)^\s*(?:public\s+|private\s+|local\s+)*function\s+(?:\w+\s+)?(?P<name>\w+)\s*\("
)


def collect_local_defs(text: str):
    """Noms (en minuscules) des fonctions definies localement dans le fichier."""
    return {m.group("name").lower() for m in LOCAL_DEF.finditer(text)}


# Declarations d'inclusion en tete de source DIVA.
MODULE_DECL = re.compile(r'(?i)^\s*module\s+"(?P<name>[^"]+)"')
INCLUDE_DECL = re.compile(r'(?i)^\s*include\s+"(?P<name>[^"]+)"')

# Balises de bloc DIVA dans un masque de surcharge (.dhsf / .dhsi) :
#   [diva] ... [/diva]       = code SURCHARGE (modifiable)
#   [diva_base] ... [/diva]  = copie figee du STANDARD (INTOUCHABLE -- la modifier casse le diff)
# Des variantes [diva_xxx] sont possibles -> traitees comme NON modifiables : seul le bloc [diva]
# EXACT (suffixe vide) est du code de surcharge transformable. Tout le reste est laisse verbatim.
DIVA_OPEN = re.compile(r'^\s*\[diva([a-z0-9_]*)\]\s*$', re.IGNORECASE)
DIVA_CLOSE = re.compile(r'^\s*\[/diva[a-z0-9_]*\]\s*$', re.IGNORECASE)
# Extensions soumises par defaut au filtre [diva] (masques de surcharge ecran/imprimante).
FILTER_EXTS = (".dhsf", ".dhsi")


def ensure_modules(lines, om_stems):
    """
    Garantit la presence d'une directive Module "<om>.dhop" pour chaque objet metier utilise
    par les conversions. Insere les manquantes dans le bloc Module existant (sinon apres le
    dernier Include, sinon avant la premiere ligne de code). Idempotent (dedoublonne).
    Retourne (nouvelles_lignes, modules_ajoutes).
    """
    wanted = [s + ".dhop" for s in sorted(om_stems)]
    declared = set()
    module_idxs = []
    include_idxs = []
    for i, line in enumerate(lines):
        m = MODULE_DECL.match(line)
        if m:
            declared.add(m.group("name").lower())
            module_idxs.append(i)
        elif INCLUDE_DECL.match(line):
            include_idxs.append(i)
    missing = [w for w in wanted if w.lower() not in declared]
    if not missing:
        return lines, []

    if module_idxs:
        at = module_idxs[-1] + 1
    elif include_idxs:
        at = include_idxs[-1] + 1
    else:
        at = 0
        for i, line in enumerate(lines):
            body, _ = split_eol(line)
            s = body.strip()
            if s and not s.startswith(";"):
                at = i
                break

    ref = lines[at - 1] if 0 < at <= len(lines) else (lines[0] if lines else "")
    _, eol = split_eol(ref)
    if not eol:
        eol = "\r\n"
    block = [f'Module\t"{name}"{eol}' for name in missing]
    return lines[:at] + block + lines[at:], missing


def split_eol(line: str):
    """Separe le corps de la ligne de sa fin de ligne (preservee a l'identique)."""
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def diva_block_range(lines):
    """Localise le bloc surcharge [diva] (exact) d'un masque, avec validation fail-safe.

    Retourne :
      ("ok", start, end)    : un unique bloc [diva] bien forme. Lignes transformables =
                              indices ]start, end[ (start = ligne [diva], end = ligne [/diva]).
      ("none", None, None)  : aucun bloc [diva] -> rien a transformer.
      ("skip", reason, None): structure inattendue (imbrication, [/diva] orphelin, bloc non
                              ferme, >1 bloc [diva]) -> fichier laisse INTACT par securite.
    """
    depth = 0
    open_idx = None
    open_is_surcharge = False
    diva_blocks = []
    for i, line in enumerate(lines):
        body, _ = split_eol(line)
        mo = DIVA_OPEN.match(body)
        if mo:
            if depth != 0:
                return ("skip", f"balises [diva] imbriquees (ligne {i + 1})", None)
            depth = 1
            open_idx = i
            open_is_surcharge = (mo.group(1) == "")   # [diva] exact = suffixe vide
            continue
        if DIVA_CLOSE.match(body):
            if depth != 1:
                return ("skip", f"[/diva] sans ouverture correspondante (ligne {i + 1})", None)
            depth = 0
            if open_is_surcharge:
                diva_blocks.append((open_idx, i))
            open_idx = None
    if depth != 0:
        return ("skip", "bloc [diva...] non ferme avant la fin du fichier", None)
    if not diva_blocks:
        return ("none", None, None)
    if len(diva_blocks) > 1:
        return ("skip", f"{len(diva_blocks)} blocs [diva] (convention attendue : un seul)", None)
    start, end = diva_blocks[0]
    return ("ok", start, end)


def parse_proto_params(s: str):
    """Liste [(nom, byref)] des parametres d'une signature (texte entre parentheses), casse preservee."""
    out = []
    for raw in s.split(","):
        t = raw.strip()
        if not t:
            continue
        byref = t.startswith("&")
        name = t.lstrip("&").strip()
        name = re.split(r"[\s=]", name, maxsplit=1)[0]  # enleve un eventuel "= defaut"
        if name:
            out.append((name, byref))
    return out


def leading_byref_count(params):
    """Nb de champs de cle = parametres de tete passes par reference (&), avant le 1er parametre par valeur.

    Convention objet metier : dans Find_<ent>(&k1, &k2, ..., option1, option2, allcolumns, context),
    seuls les champs de cle sont en tete et marques '&' ; tout ce qui suit (par valeur) est optionnel
    (nonvide, conf, allcolumns, context, ...). Ex. Find_T018(&depo,&lieu,allcolumns,context) -> 2,
    Find_C3(&cpt,nonvide,...) -> 1, Find_ART(&ref,artind,...) -> 1.
    """
    n = 0
    for _name, byref in params:
        if byref:
            n += 1
        else:
            break
    return n


def split_top_level_amp(expr: str):
    """Eclate sur les '&' de premier niveau (concatenation DIVA), en respectant () et []. Ignore '&&'."""
    parts, depth, cur = [], 0, []
    i, n = 0, len(expr)
    while i < n:
        c = expr[i]
        if c in "([":
            depth += 1
            cur.append(c)
        elif c in ")]":
            depth -= 1
            cur.append(c)
        elif c == "&" and depth == 0 and (i + 1 >= n or expr[i + 1] != "&") and (i == 0 or expr[i - 1] != "&"):
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def has_top_level_comma(expr: str) -> bool:
    """True si une virgule de premier niveau existe (cle deja eclatee par l'appelant)."""
    depth = 0
    for c in expr:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            return True
    return False


def matching_paren(s: str, i: int) -> int:
    """Index de la parenthese fermante correspondant a la '(' en position i, ou -1 si non equilibree."""
    depth = 0
    for j in range(i, len(s)):
        c = s[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
    return -1


class Resolver:
    """Resout, dans le pack Std, l'objet metier *tmchk<ent>.dhsp et la fonction cible."""

    def __init__(self, std_root: Path):
        self.std = std_root
        self.index = {}        # ent_lower -> [Path, ...]
        self.cache = {}        # (ent_lower, kind) -> (fn, inst, stem, key_count) | None
        self._kc_cache = {}    # ent_lower -> nb_champs_cle (depuis Find_<ent>) | None
        self.pack_funcs = set()  # noms (minuscules) de fonctions definies dans les objets metier du pack
        self._build_index()

    def _build_index(self):
        pat = re.compile(r"(?i)tmchk(?P<ent>.+)\.dhsp$")
        for p in self.std.rglob("*.dhsp"):
            m = pat.search(p.name)
            if m:
                self.index.setdefault(m.group("ent").lower(), []).append(p)
                # un appel dont le nom est lui-meme une fonction du pack est deja a l'API moderne
                try:
                    with open(p, "r", encoding=ENCODING, newline="") as fh:
                        self.pack_funcs |= collect_local_defs(fh.read())
                except OSError:
                    continue

    def resolve(self, ent: str, kind: str):
        """kind = 'give' ou 'find'. Retourne (nom_fonction_reel, instance, stem_om, nb_champs_cle, nb_params) ou None.
        nb_params = nombre total de parametres de la signature cible (sert a trim_args, SC-001)."""
        key = (ent.lower(), kind)
        if key in self.cache:
            return self.cache[key]
        prefix = "Find" if kind == "find" else "Give"
        defre = re.compile(
            r"(?im)^\s*public\s+function\s+\w+\s+(?P<fn>" + prefix + r"_" + re.escape(ent) +
            r")\s*\(\s*(?P<params>[^)]*)\)"
        )
        result = None
        for p in self.index.get(ent.lower(), []):
            try:
                txt = p.read_text(encoding=ENCODING)
            except OSError:
                continue
            m = defre.search(txt)
            if m:
                # 1er parametre de Give_ = instance (&T0nn / &ART) ; Find_ n'a pas d'instance.
                params = parse_proto_params(m.group("params"))
                inst = params[0][0] if kind == "give" else None
                # Nb de champs de cle : lu sur la signature Find_<ent> (meme entite, meme cle) pour
                # give comme pour find (Give_ ne distingue pas la cle des params optionnels par valeur).
                # p.stem = nom de l'objet metier (ex. 'gttmchkart') -> module compile 'gttmchkart.dhop'
                result = (m.group("fn"), inst, p.stem, self.key_count(ent), len(params))
                break
        self.cache[key] = result
        return result

    def key_count(self, ent: str):
        """Nb de champs de cle de l'entite, deduit de la serie de '&' en tete de Find_<ent>. None si inconnu."""
        k = ent.lower()
        if k in self._kc_cache:
            return self._kc_cache[k]
        defre = re.compile(
            r"(?im)^\s*public\s+function\s+\w+\s+Find_" + re.escape(ent) + r"\s*\(\s*(?P<params>[^)]*)\)"
        )
        kc = None
        for p in self.index.get(k, []):
            try:
                txt = p.read_text(encoding=ENCODING)
            except OSError:
                continue
            m = defre.search(txt)
            if m:
                n = leading_byref_count(parse_proto_params(m.group("params")))
                kc = n if n > 0 else None
                break
        self._kc_cache[k] = kc
        return kc


def split_top_level_commas(expr: str):
    """Decoupe sur les virgules de premier niveau (depth 0), en respectant ()/[]."""
    parts, depth, cur = [], 0, []
    for c in expr:
        if c in "([":
            depth += 1; cur.append(c)
        elif c in ")]":
            depth -= 1; cur.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(c)
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def trim_args(rendered: str, max_args):
    """Tronque une liste d'args rendue a `max_args` args de 1er niveau (SC-001 / R-001).

    Les Lectab/Seek recopiaient des flags legacy (n d'erreur deja extrait, '0' de non-affichage,
    options) que Give_/Find_ n'acceptent pas -> trop d'arguments -> erreur de compilation. On ne
    coupe QUE le surplus AU-DELA de l'arite (un arg qui rentre est conserve). Retourne
    (rendu_tronque, dropped_nontrivial) ; dropped_nontrivial=True si un arg supprime n'est pas un
    simple '0'/vide (-> ;TODO args)."""
    if max_args is None or max_args < 0:
        return rendered, False
    parts = split_top_level_commas(rendered)
    if len(parts) <= max_args:
        return rendered, False
    nontrivial = any(d.strip() not in ("0", "") for d in parts[max_args:])
    return ", ".join(parts[:max_args]), nontrivial


def build_seek_index(objets_root: Path):
    """Index des symboles seek_* presents (EN CLAIR) dans l'arbre des objets compiles .dhop (SC-004 / R-004).

    Permet de decider, pour un seek_<ent> vif : wrapper SURVIT dans la cible (present -> garder)
    ou a disparu (absent -> convertir vers Give_<ent>). Retourne un set de noms minuscules, ou
    None si l'arbre est introuvable. Frontiere de mot obligatoire (seek_c3 != seek_c3xq)."""
    if not objets_root.is_dir():
        return None
    pat = re.compile(rb"(?i)\bseek_[a-z0-9_]+\b")
    names = set()
    for p in objets_root.rglob("*.dhop"):
        try:
            data = p.read_bytes()
        except OSError:
            continue
        for m in pat.finditer(data):
            names.add(m.group(0).decode("latin-1").lower())
    return names


def build_replacement(name: str, inner: str, resolver: Resolver, skip_names=None, consumed=None, seek_index=None):
    """
    Retourne (replacement, event) :
      - replacement (str) si conversion appliquee ;
      - None + event si fonction cible introuvable (non resolu) ;
      - (None, None) si l'appel n'est pas a traiter (laisse silencieusement).
    event applique : ('applied', titre)
    event non resolu : ('unresolved', ent, fonction_cible)
    consumed : ensemble (minuscules) des instances T0nn dont un champ est lu dans le fichier
               (accès 'T0nn.Champ') -> permet de charger l'enregistrement complet pour un Find_.
    """
    lname = name.lower()
    if consumed is None:
        consumed = set()

    # Eclatement de la cle concatenee selon le nb de champs attendu par la signature cible.
    def render_key(seg, key_count):
        """(rendu, warn, split_n) : eclate la cle concatenee en key_count champs si necessaire.
        warn != None si l'eclatement est incertain ; split_n = nb de champs si un eclatement reel
        (> 1 champ) a ete applique, sinon None."""
        seg = seg.strip()
        # forme explicite [p1 p2] : eclatement sur l'espace
        if seg.startswith("[") and seg.endswith("]"):
            toks = seg[1:-1].split()
            rendered = ", ".join(transform_segment(t, resolver, skip_names=skip_names, consumed=consumed, seek_index=seek_index).strip() for t in toks)
            warn = (f"{key_count} champ(s) cle attendu(s), {len(toks)} fourni(s)"
                    if (key_count and key_count != len(toks)) else None)
            return rendered, warn, (len(toks) if len(toks) > 1 else None)
        # cle deja eclatee par l'appelant (virgules de premier niveau) -> on ne retouche pas
        if has_top_level_comma(seg):
            return transform_segment(seg, resolver, skip_names=skip_names, consumed=consumed, seek_index=seek_index).strip(), None, None
        # cle simple concatenee : eclater sur '&' de 1er niveau si la cible attend > 1 champ
        if key_count and key_count > 1:
            segs = split_top_level_amp(seg)
            if len(segs) == key_count:
                rendered = ", ".join(transform_segment(s, resolver, skip_names=skip_names, consumed=consumed, seek_index=seek_index).strip() for s in segs)
                return rendered, None, len(segs)
            rendered = transform_segment(seg, resolver, skip_names=skip_names, consumed=consumed, seek_index=seek_index).strip()
            return rendered, f"{key_count} champ(s) cle attendu(s), separation '&' ambigue ({len(segs)} segment(s))", None
        return transform_segment(seg, resolver, skip_names=skip_names, consumed=consumed, seek_index=seek_index).strip(), None, None

    # seek_soc -> Load_gtfdos (exception directe, pas de verif objet metier, pas de module a ajouter)
    if lname == "seek_soc":
        newargs = transform_segment(inner, resolver, skip_names=skip_names, consumed=consumed, seek_index=seek_index).strip()
        newargs, dropped = trim_args(newargs, 1)  # Load_gtfdos prend 1 argument (SC-001 / R-001)
        return f"Load_gtfdos({newargs})", ("applied", "Seek_Soc() -> Load_gtfdos()", LOAD_GTFDOS_OM, None, None, dropped)

    # seek_<ent> generiques
    if lname.startswith("seek_"):
        # nom deja defini comme fonction dans le pack -> appel deja a l'API objet metier moderne
        if lname in resolver.pack_funcs:
            return None, ("modern", name)
        ent = name[5:]
        # SC-004 / R-004 : decision 3-voies quand l'index des .dhop (--objets) est disponible.
        # (1) GARDER intact si le wrapper seek_<ent> survit dans la cible (present dans l'index).
        #     La reference garde 79 entites (seek_art, seek_c3, seek_sart...). Sans index : on
        #     conserve le comportement historique (tout convertir).
        if seek_index is not None and lname in seek_index:
            return None, ("kept", name)
        # Resoudre Give_<ent> ; SC-002 / R-002 : recuperer le suffixe de variante _Key.
        res = resolver.resolve(ent, "give")
        if res is None and ent.lower().endswith("_key"):
            # Seek_<ent>_Key : variante d'acces par cle ; l'objet metier reel est <ent>.
            # Si Give_<ent>_Key est absent mais Give_<ent> present -> cibler Give_<ent>
            # (entites a cle MULTI-CHAMPS : render_key + trim_args s'en chargent ci-dessous).
            base = ent[:-4]
            res_base = resolver.resolve(base, "give")
            if res_base is not None:
                ent, res = base, res_base
        if res is None:
            # (3) absent de l'index + du local + du pack -> ;TODO (via "unresolved")
            return None, ("unresolved", ent, f"Give_{ent}")
        # (2) wrapper disparu (ou index absent) mais Give_<ent> existe dans le pack -> CONVERTIR.
        fn, inst, om, kc, npar = res
        key_str, warn, splitn = render_key(inner, kc)
        key_str, dropped = trim_args(key_str, npar - 1)  # arite reelle = params apres l'instance (SC-001)
        # En X.13, Seek_<ent> survit comme wrapper framework (gtpmfic.dhsp) et declenche les hooks
        # <Ent>_Seek_Av/_Ap. Give_<ent> ne les appelle pas -> on convertit (modernisation) MAIS on
        # signale la perte potentielle des hooks via un ;TODO (event "seekhook").
        return f"{fn}({inst}, {key_str})", ("seekhook", f"Seek_{ent} -> {fn}", om, ent, warn, splitn, dropped)

    # lectab
    if lname == "lectab":
        parts = inner.split(",", 1)
        first = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        # Numero de table sur 1 OU 2 chiffres (Lectab(6, ...) comme Lectab(06, ...)).
        # Premier argument non numerique (constante C_TABLE_*, CeBin, CeCout, Valnum...) -> on ne touche pas.
        if not re.fullmatch(r"\d{1,2}", first):
            return (None, None)
        nn = first.zfill(2)  # normalise sur 2 chiffres : 6 -> "06" -> t006 / Give_T006
        ent = "t0" + nn

        # 3e argument = NUMERO D'ERREUR (convention 11nn = 1100 + numero de table ; ex. Lectab(40, x, 1140)).
        # Sa presence determine la cible : l'ancien Lectab affichait l'erreur si non trouve, et c'est
        # Find_T0nn (et non Give_T0nn) qui reproduit cet affichage automatique (appel interne a
        # GT_GererErreurCheck(11nn, ...)). On route donc vers Find_T0nn(<cle>) - SANS instance en 1er
        # argument : Find_T0nn prend directement la cle (cf. signature reelle de l'objet metier).
        errno = None
        mflag = re.search(r",\s*(11\d{2})\s*$", rest)
        if mflag and int(mflag.group(1)) == 1100 + int(nn):
            errno = mflag.group(1)
            rest = rest[:mflag.start()].rstrip()

        if errno is not None:
            # avec numero d'erreur -> Find_T0nn(cle) : affichage auto de l'erreur 11nn
            res = resolver.resolve(ent, "find")
            if res is None:
                return None, ("unresolved", ent, f"Find_T0{nn}")
            fn, _inst, om, kc, _npar = res
            inst_name = "T0" + nn  # nom conventionnel de l'instance/enregistrement de la table
            key, warn, splitn = render_key(rest, kc)
            # Find_T0nn ne prend que les champs de cle (l'instance n'est PAS passee) : tronquer
            # les flags legacy surnumeraires a l'arite de la cle (SC-001 / R-001).
            key, dropped = (trim_args(key, kc) if kc else (key, False))
            if inst_name.lower() in consumed:
                # l'enregistrement T0nn est lu en aval -> charger toutes les colonnes ;
                # le "T0nn = Get_T0nn_Record()" (2e instruction) ne peut pas etre insere de
                # facon sure quand le Find_ est dans une condition -> signale par TODO localise.
                return (f"{fn}({key}, allcolumns = true)",
                        ("findfull", f"Lectab({nn}, ..., {errno}) -> {fn}(..., allcolumns = true)", om, nn, warn, splitn, dropped))
            return f"{fn}({key})", ("applied", f"Lectab({nn}, ..., {errno}) -> {fn}(...)", om, warn, splitn, dropped)

        # sans numero d'erreur -> Give_T0nn(T0nn, ...)  (y compris nn == 41 : preuve X2->X4 = Give_T041)
        res = resolver.resolve(ent, "give")
        if res is None:
            return None, ("unresolved", ent, f"Give_T0{nn}")
        fn, inst, om, kc, npar = res
        key, warn, splitn = render_key(rest, kc)
        key, dropped = trim_args(key, npar - 1)  # arite reelle = params apres l'instance (SC-001 / R-001)
        return f"{fn}({inst}, {key})", ("applied", f"Lectab({nn}, ...) -> {fn}(...)", om, warn, splitn, dropped)

    return (None, None)


def transform_segment(body: str, resolver: Resolver, events=None, unresolved=None, skip_names=None, consumed=None, seek_index=None) -> str:
    """
    Transforme un segment (ligne ou sous-expression d'arguments) en convertissant tous
    les appels de lecture detectes. Recurse dans les arguments (appels imbriques).
    events / unresolved sont alimentes si fournis (sinon ignores pour les sous-segments).
    skip_names : noms (minuscules) a laisser intacts (fonctions locales du fichier).
    consumed : instances T0nn (minuscules) dont un champ est lu dans le fichier.
    seek_index : index des seek_* presents dans l'arbre Objets .dhop (--objets), ou None (SC-004).
    """
    if events is None:
        events = []
    if unresolved is None:
        unresolved = []
    if skip_names is None:
        skip_names = set()
    if consumed is None:
        consumed = set()
    out = []
    pos = 0
    while True:
        m = FIND.search(body, pos)
        if not m:
            out.append(body[pos:])
            break
        open_idx = m.end() - 1
        close_idx = matching_paren(body, open_idx)
        if close_idx == -1:
            # appel non referme sur cette ligne : traitement ligne-a-ligne -> on laisse
            out.append(body[pos:m.end()])
            pos = m.end()
            events.append(("multiline", m.group("name")))
            continue
        # fonction locale (definie dans le fichier) : ce n'est pas une lecture ISAM -> intact
        if m.group("name").lower() in skip_names:
            out.append(body[pos:close_idx + 1])
            pos = close_idx + 1
            continue
        inner = body[open_idx + 1:close_idx]
        repl, ev = build_replacement(m.group("name"), inner, resolver, skip_names, consumed, seek_index)
        out.append(body[pos:m.start()])
        if repl is None:
            # laisse l'appel d'origine intact
            out.append(body[m.start():close_idx + 1])
            if ev is not None:
                if ev[0] == "unresolved":
                    unresolved.append(ev)
                else:  # "modern" : deja API objet metier, informatif (pas de TODO)
                    events.append(ev)
        else:
            out.append(repl)
            events.append(ev)
        pos = close_idx + 1
    return "".join(out)


def process_file(path: Path, resolver: Resolver, global_skip=None, diva_filter=True, seek_index=None):
    """Traite un fichier. Retourne (changed, text, events, unresolved, modern, modules, keysplits, struct, kept).

    struct : None pour un fichier non filtre ; sinon le resultat de diva_block_range
    (('ok',start,end) | ('none',..) | ('skip',reason,..)) pour un masque .dhsf/.dhsi filtre.
    kept : seek_<ent> gardes intacts car le wrapper survit dans l'index .dhop (--objets, SC-004).
    seek_index : index des seek_* presents dans l'arbre Objets .dhop, ou None.
    """
    with open(path, "r", encoding=ENCODING, newline="") as fh:
        text = fh.read()
    skip_names = collect_local_defs(text)
    if global_skip:
        skip_names = skip_names | global_skip
    # Instances T0nn dont un champ est lu dans le fichier (acces 'T0nn.Champ') : si un Find_ est
    # genere pour une telle table, on charge l'enregistrement complet (allcolumns = true).
    consumed = {m.lower() for m in re.findall(r"\b(T0\d\d)\s*\.", text, re.IGNORECASE)}
    lines = text.splitlines(keepends=True)

    # Filtre masque [diva] : sur .dhsf/.dhsi, ne transformer QUE le bloc surcharge [diva]
    # (jamais [diva_base], copie figee du standard). Fail-safe : structure inattendue -> intact.
    apply_filter = diva_filter and path.suffix.lower() in FILTER_EXTS
    struct = None
    diva_lo = diva_hi = None
    if apply_filter:
        struct = diva_block_range(lines)
        if struct[0] == "skip":
            return False, text, {}, {}, {}, [], [], struct, {}
        if struct[0] == "ok":
            diva_lo, diva_hi = struct[1], struct[2]

    new_lines = []
    changed = False
    events_count = {}        # titre -> nb
    unresolved_count = {}    # (fonction, ent) -> nb
    modern_count = {}        # nom -> nb (deja API objet metier)
    kept_count = {}          # seek_<ent> garde intact (wrapper survit dans l'index .dhop, SC-004)
    modules_used = set()     # stems d'objets metier referencés par les conversions
    keysplit_lines = []      # (lineno, nb_champs, ligne_convertie) : cles multi-champs eclatees
    for lineno, line in enumerate(lines, 1):
        # Masque filtre : hors du bloc [diva] (tags [diva]/[/diva] inclus) -> ligne verbatim.
        if apply_filter and not (diva_lo is not None and diva_lo < lineno - 1 < diva_hi):
            new_lines.append(line)
            continue
        body, eol = split_eol(line)
        # Ligne COMMENTEE DIVA (corps commencant par ';') -> jamais transformee (SC-003 / R-003).
        # La migration de reference laisse les commentaires intacts.
        if body.lstrip().startswith(";"):
            new_lines.append(line)
            continue
        ev, unres = [], []
        getrec_nn = []       # numeros de table pour lesquels un Get_T0nn_Record() est a ajouter
        hook_ents = []       # entites seek_ converties -> rappel perte des hooks _Seek_Av/_Ap
        keywarn = []         # conversions dont l'eclatement de la cle concatenee est incertain
        line_splits = []     # nb de champs de chaque cle reellement eclatee sur cette ligne
        args_dropped = False # un arg surnumeraire NON trivial a ete tronque sur cette ligne (SC-001)
        new_body = transform_segment(body, resolver, ev, unres, skip_names, consumed, seek_index)
        for e in ev:
            if e[0] in ("applied", "findfull", "seekhook"):
                events_count[e[1]] = events_count.get(e[1], 0) + 1
                if e[2]:
                    modules_used.add(e[2])
                if e[0] == "applied":
                    w = e[3] if len(e) > 3 else None
                    sp = e[4] if len(e) > 4 else None
                    dr = e[5] if len(e) > 5 else False
                elif e[0] == "findfull":
                    getrec_nn.append(e[3])
                    w = e[4] if len(e) > 4 else None
                    sp = e[5] if len(e) > 5 else None
                    dr = e[6] if len(e) > 6 else False
                else:  # seekhook
                    hook_ents.append(e[3])
                    w = e[4] if len(e) > 4 else None
                    sp = e[5] if len(e) > 5 else None
                    dr = e[6] if len(e) > 6 else False
                if w:
                    keywarn.append(w)
                if sp:
                    line_splits.append(sp)
                if dr:
                    args_dropped = True
            elif e[0] == "modern":
                modern_count[e[1]] = modern_count.get(e[1], 0) + 1
            elif e[0] == "kept":
                kept_count[e[1]] = kept_count.get(e[1], 0) + 1
        if unres:
            for u in unres:
                unresolved_count[(u[2], u[1])] = unresolved_count.get((u[2], u[1]), 0) + 1
            # idempotence : ne pas re-ajouter le marqueur s'il est deja present (re-execution)
            if ";TODO migration" not in new_body:
                absents = sorted({u[2] for u in unres if u[0] == "unresolved"})
                new_body = new_body + " ;TODO migration: " + ", ".join(absents) + " introuvable(s) dans le pack std (objet metier absent)"
        # Find_ charge en allcolumns = true : rappeler d'ajouter le Get_T0nn_Record() (2e instruction).
        if getrec_nn and ";TODO Get_" not in new_body:
            gets = ", ".join(f"T0{n} = Get_T0{n}_Record()" for n in sorted(set(getrec_nn)))
            new_body = new_body + " ;TODO Get_Record: ajouter apres succes du Find -> " + gets
        # seek_ converti : Give_ ne declenche pas les hooks legacy <Ent>_Seek_Av/_Ap.
        if hook_ents and ";TODO hooks" not in new_body:
            hooks = ", ".join(f"{h.upper()}_Seek_Av/_Ap" for h in sorted(set(hook_ents)))
            new_body = new_body + " ;TODO hooks: Give_ ne declenche pas " + hooks \
                + " (l'ancien Seek_ oui) - verifier surcharge/standard"
        # eclatement de cle concatenee incertain : champs a separer manuellement.
        if keywarn and ";TODO cle" not in new_body:
            new_body = new_body + " ;TODO cle: eclatement a verifier (" + "; ".join(sorted(set(keywarn))) \
                + ") - Lectab/Seek concatene la cle, Give/Find prend les champs separes"
        # SC-001 : un arg surnumeraire NON trivial (autre que 0/vide) a ete tronque
        # (la signature cible a moins de parametres) -> a verifier manuellement.
        if args_dropped and ";TODO args" not in new_body:
            new_body = new_body + " ;TODO args: argument(s) surnumeraire(s) non trivial(aux) tronque(s) " \
                + "- la signature cible a moins de parametres, verifier la valeur supprimee"
        if line_splits:
            for n in line_splits:
                keysplit_lines.append((lineno, n, new_body.strip()))
        if new_body != body:
            changed = True
        new_lines.append(new_body + eol)

    # Garde-fou auto-verifiable : sur un masque filtre, AUCUNE ligne hors du bloc [diva]
    # ne doit avoir change (les lignes [diva_base] et hors blocs restent a l'identique).
    if apply_filter and diva_lo is not None:
        for i in range(len(lines)):
            if not (diva_lo < i < diva_hi) and new_lines[i] != lines[i]:
                return (False, text, {}, {}, {}, [], [],
                        ("skip", f"invariant viole : ligne {i + 1} hors [diva] modifiee (avorte par securite)", None), {})

    added_modules = []
    if changed and modules_used:
        if apply_filter and diva_lo is not None:
            # Inserer les directives Module dans le SEUL bloc [diva] (jamais dans [diva_base]).
            lo, hi = diva_lo + 1, diva_hi
            slice_lines, added_modules = ensure_modules(new_lines[lo:hi], modules_used)
            new_lines = new_lines[:lo] + slice_lines + new_lines[hi:]
        else:
            new_lines, added_modules = ensure_modules(new_lines, modules_used)

    return changed, "".join(new_lines), events_count, unresolved_count, modern_count, added_modules, keysplit_lines, struct, kept_count


def main():
    ap = argparse.ArgumentParser(description="Conversion des fonctions de lecture DIVA (migration).")
    ap.add_argument("--src", required=True, help="Dossier des sources a convertir (recursif).")
    ap.add_argument("--out", required=True, help="Dossier de sortie (fichiers modifies uniquement).")
    ap.add_argument("--std", required=True, help="Chemin du PACK STD DE DESTINATION de la migration (PAS C:\\...\\Std).")
    ap.add_argument("--objets", required=True,
                    help="OBLIGATOIRE. Arbre des Objets compiles (.dhop) de la CIBLE. Pilote la decision "
                    "3-voies des seek_<ent> (SC-004) : un seek_<ent> dont le wrapper SURVIT dans la cible "
                    "(present dans les .dhop) est GARDE intact ; sinon converti vers Give_<ent> si le pack "
                    "l'expose ; sinon ;TODO. Sans cet arbre, la decision serait aveugle (sur-conversion) : "
                    "le skill refuse donc de tourner sans --objets.")
    ap.add_argument("--report", help="Chemin du rapport (defaut: <out>/regExResult.txt).")
    ap.add_argument("--extensions", default="dhsp,dhsf,dhsi,dhsq",
                    help="Extensions traitees (csv). Defaut: dhsp,dhsf,dhsi,dhsq.")
    ap.add_argument("--exclude-pattern", default="_base",
                    help="Sous-chaine dans le nom de fichier (stem) excluant le fichier. Defaut: _base.")
    ap.add_argument("--no-diva-filter", action="store_true",
                    help="Desactive le filtre [diva] des masques .dhsf/.dhsi. DANGEREUX : risque de "
                         "modifier [diva_base] (copie figee du standard) et de casser le diff de surcharge.")
    ap.add_argument("--dry-run", action="store_true",
                    help="N'ecrit aucun fichier converti (pas de miroir) ; produit uniquement le rapport "
                         "(utile pour estimer le perimetre avant action).")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    std = Path(args.std)
    objets = Path(args.objets)

    errs = []
    if not src.is_dir():
        errs.append(f"--src introuvable : {src}")
    if not std.is_dir():
        errs.append(
            f"--std introuvable : {std}\n"
            "  Fournir le PACK STD DE DESTINATION de la migration (ex. ...\\v2026_erpX13_sp223c),\n"
            "  pas le dossier interne editeur C:\\...\\Std auquel les integrateurs n'ont pas acces."
        )
    if not objets.is_dir():
        errs.append(
            f"--objets introuvable : {objets}\n"
            "  Fournir l'arbre des Objets COMPILES (.dhop) de la version CIBLE installee.\n"
            "  Indispensable a la decision 3-voies des seek_<ent> (garder/convertir/TODO) : sans lui,\n"
            "  le skill ne peut pas savoir quels wrappers seek_ survivent dans la cible."
        )
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(2)

    out.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report) if args.report else out / "regExResult.txt"

    resolver = Resolver(std)

    # SC-004 : index des seek_* presents (en clair) dans l'arbre Objets .dhop de la cible.
    # --objets est obligatoire (valide ci-dessus) -> la decision 3-voies est toujours active.
    seek_index = build_seek_index(objets)
    print(f"Index Objets : {len(seek_index)} symboles seek_* lus dans {objets}")

    exts = [e.strip().lstrip(".").lower() for e in args.extensions.split(",") if e.strip()]
    excl = args.exclude_pattern or ""
    files = sorted(
        {f for ext in exts for f in src.rglob(f"*.{ext}")
         if not (excl and excl in f.stem)}
    )

    # Pre-passe : noms de fonctions definies dans les sources du projet. Un seek_xxx defini
    # comme fonction (ici ou dans un autre fichier du lot) est un helper projet, jamais une
    # lecture ISAM -> exclu de la conversion partout.
    global_skip = set()
    for f in files:
        try:
            with open(f, "r", encoding=ENCODING, newline="") as fh:
                global_skip |= collect_local_defs(fh.read())
        except OSError:
            continue

    report_lines = []
    n_files = 0
    n_changed = 0
    total_applied = 0
    total_unresolved = 0
    total_modern = 0
    total_modules_added = 0
    total_keysplits = 0
    total_kept = 0
    modern_global = {}
    kept_global = {}       # nom seek_<ent> -> nb garde intact (wrapper survit, SC-004)
    keysplit_report = []   # lignes "fichier:ligne (N champs) -> appel converti"
    masks_skipped = []     # (rel, raison) : masques laisses INTACTS par securite (structure inattendue)
    masks_filtered = []    # (rel, lo, hi) : masques convertis dans [diva] (invariant auto-verifie)
    todo_totals = {}       # type de ;TODO -> nb (hooks / Get_Record / migration / cle)

    for f in files:
        n_files += 1
        rel = f.relative_to(src)
        changed, new_text, events_count, unresolved_count, modern_count, added_modules, keysplit_lines, struct, kept_count = \
            process_file(f, resolver, global_skip, diva_filter=not args.no_diva_filter, seek_index=seek_index)
        if struct and struct[0] == "skip":
            masks_skipped.append((rel, struct[1]))
        elif struct and struct[0] == "ok" and changed:
            masks_filtered.append((rel, struct[1], struct[2]))
        if changed:
            n_changed += 1
            if not args.dry_run:
                target = out / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding=ENCODING, newline="") as fh:
                    fh.write(new_text)
            for kind, marker in (("hooks", ";TODO hooks"), ("Get_Record", ";TODO Get_Record"),
                                 ("migration", ";TODO migration"), ("cle", ";TODO cle"),
                                 ("args", ";TODO args")):
                c = new_text.count(marker)
                if c:
                    todo_totals[kind] = todo_totals.get(kind, 0) + c
        for title in sorted(events_count):
            cnt = events_count[title]
            total_applied += cnt
            report_lines.append(f"{title} - applique dans {rel} (x{cnt})")
        for (func, ent) in sorted(unresolved_count):
            cnt = unresolved_count[(func, ent)]
            total_unresolved += cnt
            report_lines.append(f"{func} NON converti - objet metier *tmchk{ent}.dhsp absent du pack - dans {rel} (x{cnt})")
        for name in modern_count:
            total_modern += modern_count[name]
            modern_global[name] = modern_global.get(name, 0) + modern_count[name]
        for name in kept_count:
            total_kept += kept_count[name]
            kept_global[name] = kept_global.get(name, 0) + kept_count[name]
        for mod in added_modules:
            total_modules_added += 1
            report_lines.append(f'Module "{mod}" ajoute dans {rel}')
        for (lineno, nb, txt) in keysplit_lines:
            total_keysplits += 1
            keysplit_report.append(f"{rel}:{lineno} (cle eclatee en {nb} champs) -> {txt}")

    header = []
    header.append("----------------------------------------")
    header.append("Recuperation des parametres de lancement")
    header.append("----------------------------------------")
    header.append(f"srcPath={src}")
    header.append(f"outPath={out}")
    header.append(f"stdPack={std}")
    header.append(f"extensions={','.join(exts)}")
    header.append(f"divaFilter={'OFF (danger)' if args.no_diva_filter else 'on (.dhsf/.dhsi -> bloc [diva] uniquement)'}")
    header.append(f"objetsTree={objets} (index seek_*: {len(seek_index)} symboles ; decision 3-voies SC-004)")
    header.append("recursiveSearch=True")
    header.append(f"writeNewFiles={'False (DRY-RUN : rapport seul)' if args.dry_run else 'True'}")
    header.append("")
    header.append("------------------------------------------------------")
    header.append("Traitement")
    header.append("------------------------------------------------------")

    footer = []
    footer.append("")
    footer.append("------------------------------------------------------")
    footer.append("Synthese")
    footer.append("------------------------------------------------------")
    footer.append(f"Fichiers analyses       : {n_files}")
    footer.append(f"Fichiers modifies       : {n_changed}")
    footer.append(f"Masques ignores (securite, structure inattendue) : {len(masks_skipped)}")
    footer.append(f"Conversions appliquees  : {total_applied}")
    footer.append(f"Directives Module ajoutees : {total_modules_added}")
    footer.append(f"Appels non convertis (objet metier absent) : {total_unresolved}")
    footer.append(f"Appels deja a l'API objet metier (laisses intacts) : {total_modern}")
    footer.append(f"seek_ gardes (wrapper survit en cible, --objets) : {total_kept}")
    footer.append(f"Cles multi-champs eclatees : {total_keysplits}")
    if todo_totals:
        footer.append("")
        footer.append("TODO a traiter manuellement (par type) :")
        for kind in ("hooks", "Get_Record", "migration", "cle", "args"):
            if todo_totals.get(kind):
                footer.append(f"  {kind:<11}: {todo_totals[kind]}")
        footer.append(f"  {'TOTAL':<11}: {sum(todo_totals.values())}")
    if keysplit_report:
        footer.append("")
        footer.append("------------------------------------------------------")
        footer.append("Cles multi-champs eclatees (Lectab/Seek concatene -> Give/Find separe)")
        footer.append("------------------------------------------------------")
        footer.extend(keysplit_report)
    if modern_global:
        footer.append("")
        footer.append("Detail des appels deja modernes (informatif, aucune action) :")
        for name in sorted(modern_global, key=lambda k: (-modern_global[k], k)):
            footer.append(f"  {name} (x{modern_global[name]})")
    if kept_global:
        footer.append("")
        footer.append("seek_ GARDES intacts (wrapper survit dans l'arbre Objets .dhop, --objets/SC-004) :")
        for name in sorted(kept_global, key=lambda k: (-kept_global[k], k)):
            footer.append(f"  {name} (x{kept_global[name]})")

    if masks_filtered:
        footer.append("")
        footer.append("------------------------------------------------------")
        footer.append("Masques de surcharge : conversions confinees au bloc [diva] (invariant verifie : 0 dans [diva_base])")
        footer.append("------------------------------------------------------")
        for (rel, lo, hi) in masks_filtered:
            footer.append(f"{rel} : bloc [diva] lignes {lo + 1}-{hi + 1} -- aucune modif hors [diva]")
    if masks_skipped:
        footer.append("")
        footer.append("------------------------------------------------------")
        footer.append("Masques IGNORES par securite (structure de balises inattendue) -- a traiter a la main")
        footer.append("------------------------------------------------------")
        for (rel, reason) in masks_skipped:
            footer.append(f"{rel} : {reason}")

    all_lines = header + report_lines + footer
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding=ENCODING, newline="\r\n") as fh:
        fh.write("\n".join(all_lines) + "\n")

    mode = " [DRY-RUN : aucun fichier converti ecrit]" if args.dry_run else ""
    verbe = "a modifier" if args.dry_run else "modifies"
    print(f"Termine{mode}. {n_changed}/{n_files} fichiers {verbe}. "
          f"{total_applied} conversions, {total_unresolved} non convertis. Rapport : {report_path}")


if __name__ == "__main__":
    main()
