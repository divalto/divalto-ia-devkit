#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le piege d'encodage des `.ps1` -- #266.

Un `.ps1` ecrit par l'outil Write est en **UTF-8 sans BOM**. PowerShell 5.1 -- la version
installee par defaut sous Windows -- lit un tel fichier en **ANSI/CP1252**. Un chemin
accentue ecrit **en dur** y est donc corrompu a l'execution, et l'ecriture echoue sur un
repertoire introuvable.

**Ce piege ne concerne aucun skill en particulier** : le retour terrain qui l'a signale
generait un script SQL, sans skill devkit charge. C'est pourquoi la regle vit **aussi** dans
le bloc de regles installe dans le `CLAUDE.md` du partenaire -- une regle qui ne vit que dans
un skill n'atteint pas quelqu'un qui n'en charge aucun.

Les cas 1 et 2 sont **fonctionnels** : ils fabriquent le fichier fautif et **mesurent** la
corruption, plutot que d'affirmer qu'elle se produit.

Lancer :
    py plugin/skills/writing-diva-files/tests/test_ps1_encodage.py
"""
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
PAGE = os.path.join(SKILL, "reference", "safe-methods.md")
INSTALL = os.path.abspath(os.path.join(SKILL, "..", "..", "instructions", "install.py"))
README = os.path.abspath(os.path.join(SKILL, "..", "..", "instructions", "README.md"))

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


# Un chemin accentue GENERIQUE : le temoin doit porter un accent, sinon il ne mesure rien.
# Premiere version de ce cas : "Developpements" sans accent -- aucune corruption possible,
# et le cas serait passe pour une mauvaise raison. Le harnais l'a montre.
CHEMIN_ACCENTUE = "C:\\R\u00e9pertoire accentu\u00e9\\donnees\\sortie.txt"


# --------------------------------------------------------------------- les cas

@cas("1. Le piege est REEL : un .ps1 UTF-8 sans BOM, relu en ANSI, corrompt le chemin")
def cas1():
    d = tempfile.mkdtemp(prefix="ps1_")
    p = os.path.join(d, "script.ps1")
    contenu = "$outPath = '%s'\n" % CHEMIN_ACCENTUE
    # Ce que produit l'outil d'ecriture : UTF-8, sans BOM.
    io.open(p, "w", encoding="utf-8", newline="\r\n").write(contenu)
    brut = io.open(p, "rb").read()
    assert not brut.startswith(b"\xef\xbb\xbf"), "l'ecriture a mis un BOM : le temoin est fausse"
    # Ce que PowerShell 5.1 en lit : CP1252.
    relu = brut.decode("cp1252")
    assert CHEMIN_ACCENTUE not in relu, \
        "le chemin survit a la relecture ANSI -- le piege ne serait pas reel"
    assert "Ã©" in relu or "Ã" in relu, "corruption attendue absente : %r" % relu[:80]
    return "chemin corrompu a la relecture : %r" % relu.split("'")[1][:34]


@cas("2. Les deux parades marchent : ISO-8859-1, ou pas d'accent dans le litteral")
def cas2():
    d = tempfile.mkdtemp(prefix="ps1_")
    # Parade A : ecrire le fichier en ISO-8859-1
    a = os.path.join(d, "iso.ps1")
    io.open(a, "w", encoding="iso-8859-1", newline="\r\n").write(
        "$outPath = '%s'\n" % CHEMIN_ACCENTUE)
    relu = io.open(a, "rb").read().decode("cp1252")
    assert CHEMIN_ACCENTUE in relu, "la parade ISO-8859-1 ne restitue pas le chemin"
    # Parade B : pas d'accent dans le litteral -- le chemin vient d'un parametre
    b = os.path.join(d, "param.ps1")
    io.open(b, "w", encoding="utf-8", newline="\r\n").write(
        "param([string]$OutPath)\nSet-Content -Path $OutPath -Value 'ok'\n")
    relu_b = io.open(b, "rb").read().decode("cp1252")
    assert "param([string]$OutPath)" in relu_b, "la parade par parametre est alteree"
    return "les deux parades restituent le script a l'identique"


@cas("3. La page du skill porte la regle, ses deux causes et ses deux parades")
def cas3():
    t = lire(PAGE)
    assert ".ps1" in t, "le skill d'ecriture de fichiers ne parle toujours pas des .ps1"
    # Chercher dans LA SECTION, pas dans la page : « PowerShell 5.1 » et « ANSI » figurent
    # aussi dans la ligne du tableau des pieges et dans l'encadre de portee. Une assertion
    # sur la page entiere survivait a la suppression de l'explication -- mutation a l'appui.
    debut = t.find("## Le piege des `.ps1`")
    assert debut > 0, "la section dediee au piege .ps1 a disparu"
    fin = t.find("\n## ", debut + 4)
    section = t[debut:fin if fin > 0 else len(t)]
    # Le TOKEN « PowerShell 5.1 » figure 3 fois dans la section : sa presence ne prouve rien.
    # Ce qui compte est la PHRASE CAUSALE -- « PowerShell 5.1 lit ... en ANSI » -- et c'est
    # elle que le controle exige. Une mutation qui la supprimait laissait le cas passer.
    plat = re.sub(r"\s*\n\s*", " ", section)
    causales = [p for p in re.split(r"(?<=[.!?])\s+", plat)
                if "PowerShell 5.1" in p and ("ANSI" in p or "CP1252" in p)]
    assert causales, ("la section ne porte plus de phrase qui EXPLIQUE la cause "
                      "(PowerShell 5.1 lit en ANSI) -- le lecteur voit la regle sans son motif")
    assert "BOM" in section, "la condition « sans BOM » a disparu : la regle devient trop large"
    assert "parametre" in section.lower(), "la parade par parametre a disparu de la section"
    assert "ISO-8859-1" in section, "la parade par encodage a disparu de la section"
    return "section de %d caracteres : cause et deux parades" % len(section)


@cas("4. La page distingue ce piege de celui du profil xwin7")
def cas4():
    t = lire(PAGE)
    assert "xwin7" in t, \
        ("la page ne dit pas qu'il existe un piege VOISIN mais distinct -- corriger l'un "
         "ne dispense pas de l'autre")
    # Exiger LES DEUX moities : la qualification (« cause distincte ») ET sa consequence
    # pratique (« corriger l'une ne dispense pas de l'autre »). Chacune seule survivait a la
    # suppression de l'autre, et la page continuait de paraitre correcte.
    assert "cause distincte" in t, \
        "la page cite xwin7 sans qualifier la cause comme DISTINCTE"
    assert "ne dispense pas" in t, \
        ("la page ne dit plus la consequence : corriger un piege ne dispense pas de "
         "verifier l'autre")
    return "distinction ET consequence pratique presentes"


@cas("5. Le bloc installe chez le partenaire declare sa PORTEE")
def cas5():
    t = lire(INSTALL)
    assert "Portee de ce bloc" in t, \
        ("le bloc ne borne pas son perimetre : c'est le defaut signale -- une regle du "
         "devkit appliquee a tort aux skills d'un autre plugin")
    i = t.index("Portee de ce bloc")
    bloc = t[i:i + 400]
    assert "divalto-devkit" in bloc, "la portee ne nomme pas le plugin"
    assert "autres plugins" in bloc or "divalto-one" in bloc, \
        "la portee ne dit pas ce qu'elle EXCLUT -- sans exclusion, elle ne borne rien"
    return "portee declaree et exclusion nommee"


@cas("6. Le declencheur RETEX est borne au plugin, dans les DEUX documents")
def cas6():
    for f, libelle in ((INSTALL, "le bloc installe"), (README, "le README partenaire")):
        t = lire(f)
        lignes = [l for l in t.split("\n")
                  if "invocation" in l and ("skill" in l.lower())]
        assert lignes, "%s n'annonce plus le declencheur d'invocation" % libelle
        assert any("divalto-devkit" in l for l in lignes), \
            ("%s garde un declencheur NON borne : %r" % (libelle, lignes[0][:110]))
    return "borne dans les deux documents"


@cas("7. Le piege .ps1 est dans le bloc installe -- il s'applique sans skill charge")
def cas7():
    t = lire(INSTALL)
    assert "Piege d'encodage des scripts `.ps1`" in t, \
        ("la regle ne vit que dans un skill : le cas d'origine n'avait AUCUN skill charge, "
         "elle ne l'aurait pas atteint")
    i = t.index("Piege d'encodage des scripts `.ps1`")
    bloc = t[i:i + 1200]
    assert "PowerShell" in bloc and ("ANSI" in bloc or "CP1252" in bloc), \
        "la regle est nommee sans sa cause"
    # Elle ne doit PAS etre presentee comme propre au devkit : ce serait faux.
    assert "pas propre au devkit" in bloc or "propriete de PowerShell" in bloc, \
        ("la regle est presentee comme specifique au devkit -- ce serait faux, et laisserait "
         "croire que les autres .ps1 sont a l'abri")
    return "regle presente, cause donnee, portee non surjouee"


@cas("8. La procedure de mise a jour est documentee, avec une commande QUI EXISTE")
def cas8():
    t = lire(README)
    assert "Mettre a jour le plugin" in t, "la procedure de mise a jour n'est pas documentee"
    assert "git pull" in t, "la procedure manuelle ne dit pas comment recuperer la version"
    assert "install.py" in t, "la procedure n'indique pas de relancer l'installation"
    # La commande de verification doit exister : une doc qui prescrit une commande fausse
    # est pire que pas de doc. Celle-ci a ete corrigee apres l'avoir LANCEE (--stats
    # n'existe pas ; le mode est `overview`).
    m = re.search(r"query_catalog\.py\s+(\S+)", t)
    assert m, "la verification post-mise-a-jour a disparu"
    assert m.group(1) in ("overview", "detail", "search", "workflow", "verb"), \
        "mode de query_catalog inexistant dans la doc : %r" % m.group(1)
    return "procedure + verification avec le mode %r" % m.group(1)


@cas("9. Le README dit pourquoi une correction n'arrive qu'a la mise a jour")
def cas9():
    t = lire(README)
    i = t.find("Mettre a jour le plugin")
    bloc = t[i:i + 2500]
    assert "CLAUDE.md" in bloc and "installation" in bloc.lower(), \
        ("le README n'explique pas que le bloc de regles est ecrit A L'INSTALLATION -- c'est "
         "la raison la plus frequente d'un comportement corrige qui persiste")
    return "le lien correction / mise a jour est ecrit"


# --------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    echecs = []
    for titre, fn in CAS:
        try:
            note = fn()
            print("  OK   %s" % titre)
            if note:
                print("         -> %s" % note)
        except AssertionError as e:
            echecs.append(titre)
            print("  ECHEC %s" % titre)
            print("         %s" % str(e)[:400])
        except Exception as e:
            echecs.append(titre)
            print("  ERREUR %s : %s: %s" % (titre, type(e).__name__, str(e)[:300]))
    print()
    if echecs:
        print("BILAN : %d/%d cas en ECHEC" % (len(echecs), len(CAS)))
        for t in echecs:
            print("  - %s" % t)
        sys.exit(1)
    print("BILAN : %d/%d cas OK" % (len(CAS), len(CAS)))


if __name__ == "__main__":
    main()
