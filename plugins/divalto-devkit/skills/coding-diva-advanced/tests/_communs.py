# -*- coding: utf-8 -*-
"""Helpers partages par les suites de tests de ce skill.

**Pourquoi un module partage plutot qu'un copier-coller.** Ces deux fonctions ont ete
dupliquees dans deux suites, et le meme defaut a ete corrige deux fois. A la troisieme
suite, la divergence devenait certaine -- c'est exactement le motif tracé
(une amelioration livree dans une copie ne se propage pas a sa voisine). Les suites de ce
skill importent donc ici.
"""
import io
import re


def lire(chemin):
    return io.open(chemin, encoding="utf-8").read()


def nu(texte):
    """Texte depouille du balisage d'emphase Markdown.

    ATTENTION -- ne PAS ajouter `_` a la classe supprimee. Une premiere version le faisait
    (pour les italiques `_texte_`) et **mutilait tous les identifiants** : `H_EOF` devenait
    `HEOF`, `ZOOM_SQL_CONDITION_NORMALE` devenait `ZOOMSQLCONDITIONNORMALE`, et trois cas
    echouaient sur des chaines pourtant presentes dans la page. Dans ces pages l'emphase
    s'ecrit avec `*`, jamais avec `_` -- et l'underscore est partout dans les noms DIVA.
    """
    return re.sub(r"[*`]", "", texte)


def plat(chemin):
    """Texte du fichier, aplati sur une seule ligne.

    Deux normalisations, chacune venue d'un test qui echouait a tort :

    - la prose est **enveloppee** : chercher une chaine litterale casse au moindre
      reformatage, donc on replie tout sur une ligne ;
    - le marqueur de citation `>` est retire **apres une indentation eventuelle** -- une
      citation imbriquee dans une liste s'ecrit `  > ...`, et ne retirer que le `>` collé
      au saut de ligne laissait des fragments comme « rien a > voir ».
    """
    return " ".join(re.sub(r"\n[ \t]*>", "\n", lire(chemin)).split())
