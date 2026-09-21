# Surcharge -- OverWrittenBy / OverWrite

## Contenu

- Principe
- Hierarchie de surcharge -- niveaux `u`, surchargeabilite **opt-in**, add-ons `AS alias`
- Declaration des procedures surchargees -- `Public` / `Private` / aucun modificateur
- Visibilite des declarations dans une surcharge (records, fichiers, RSQL, constantes)
- Pattern canonique de surcharge de procedure
- Visibilite et partage inter-module -- fonctions, puis donnees (`Public` / `Protected` / `Extern`)
- La declaration `Module` n'est **pas transitive**
- `PP` / `TT` : ce qui est surchargeable et ce qui ne l'est pas
- Retrouver la signature d'une fonction protegee
- Surcharge RecordSql
- Regles
- Advisory -- analyse d'impact avant surcharge (via diva-mcp)

---


Mecanisme de verticalisation : un module utilisateur surcharge les fonctions du module standard sans modifier le code original.

## Principe

```
; Module original (fichier standard)
OverWrittenBy 'MONMODULEU.dhop'   ; Convention : suffixe 'U'

; Module de surcharge (fichier utilisateur)
OverWrite 'MONMODULE.dhop'

; Appeler la version originale depuis la surcharge
Standard.MaFonction(params)    ; Prefixe Standard.
```

## Hierarchie de surcharge

Convention de nommage multi-niveaux :

| Niveau | Fichier | Suffixe |
|--------|---------|---------|
| Standard | `monmodule.dhop` | _(aucun)_ |
| Surcharge niveau 1 | `monmoduleu.dhop` | `u` |
| Surcharge niveau 2 | `monmoduleuu.dhop` | `uu` |

Chaque niveau fait `OverWrite` du niveau precedent et peut appeler `Standard.Fonction()` pour invoquer l'implementation originale.

**Le nombre de `u` indique le niveau** -- c'est la convention documentee, pas une simple
habitude de nommage.

### La surchargeabilite est **declaree par la base**, pas acquise

Un objet n'est pas surchargeable par defaut : la **base** doit l'annoncer. Pour un
dictionnaire de RecordSql, c'est l'attribut `OverWrittenBy` de la balise `<DictionarySql>`
qui le rend surchargeable ; sans lui, la surcharge est refusee. La reciproque `OverWrite`
declare, dans la surcharge, ce qu'elle surcharge -- et **l'objet surcharge doit etre present
pour compiler la surcharge**. A l'execution, en revanche, la presence de la surcharge est
**facultative**.

C'est ce principe d'**opt-in** qui explique l'erreur 106 sur les modules non surchargeables
(voir la section `PP` / `TT` plus bas).

> **Montee de version** : apres modification de la base -- nouvelle version ou service pack
> -- il est **vivement conseille de recompiler les dictionnaires de surcharge**. Certaines
> modifications de la base ne se manifestent qu'a **l'execution** si la surcharge n'a pas
> ete recompilee.

### Surcharges multiples (add-ons) : `Module ... AS alias`

Quand **plusieurs add-ons** surchargent le meme module, la declaration peut nommer l'add-on
et recevoir un **alias**, qui remplace ensuite le nom du module a l'appel :

```diva
Module addon1.modulegttmfic.dhop as addon1_modulegttmfic
Module addon2.modulegttmfic.dhop as addon2_modulegttmfic

; l'alias remplace le nom du module
addon2_modulegttmfic.gttmfic_Proc1()    ; Proc1 du module de l'add-on 2
```

Utile des qu'un partenaire livre un add-on destine a cohabiter avec d'autres.

## Declaration des procedures surchargees

Dans une `.dhsp` `OverWrite`, une procedure qui surcharge une procedure publique du
standard **ne doit pas repeter `Public`** -- meme si la procedure d'origine le porte.
La visibilite est heritee du module standard. **Forme canonique : aucun modificateur.**

| Modificateur | Sens **documente** | Sur une surcharge |
|---|---|---|
| aucun | dans un module de surcharge : **c'est une surcharge** | **forme canonique.** Mesure : 141 surcharges prouvees d'un specifique reel, toutes sans modificateur |
| `Public` | la fonction est appelable depuis un autre module | **refuse** -- erreur compilateur 210 : « La fonction/procedure est une surcharge. Elle ne peut etre PUBLIC » |
| `Private` | **« cette fonction n'est PAS une surcharge »** -- et n'est pas publique. Ne peut se trouver que dans un **module de surcharge** | sert a declarer une fonction **neuve**, absente du module de base -- pas a surcharger. Voir la mise en garde ci-dessous |
| `Protected` | modificateur de **DONNEES**, pas de fonction (`HFile`, `HTmpFile`, `Record`, `RecordDiva`) | **hors sujet ici** : il ne peut pas preceder une `Procedure` ni une `Function` |

**La regle qui structure tout le reste** : *toute fonction d'un module de surcharge qui
n'est declaree **ni** `Public` **ni** `Private` est une fonction de surcharge.* C'est de la
que vient l'erreur 210 -- `Public` affirme « je suis une nouvelle fonction publique », ce qui
contredit le fait d'en surcharger une.

> **Correction 2026-08-28.** Les deux dernieres lignes de ce tableau disaient autre chose :
> `Private` y etait donne « non verifie » et `Protected` « inexistant en pratique, 0
> declaration mesuree ». Les deux etaient faux. `Private` est un mecanisme **documente**, et
> `Protected` n'avait 0 declaration que parce qu'on le cherchait **la ou il ne peut pas
> apparaitre** : ce n'est pas un modificateur de fonction.

### Mise en garde -- `Private` compile meme quand il ne devrait pas

Le compilateur ne verifie qu'une fonction non-`Private` est bien une surcharge **que si
l'option de profil « Verifier que les fonctions non private sont des surcharges » est a
oui**. Option desactivee : du code non conforme compile sans un mot. C'est pourquoi on
trouve du `Private` -- et son absence -- dans du specifique de production sans que rien
n'ait jamais proteste.

Deux consequences a connaitre, sans en faire une regle d'ecriture :

- **Asymetrie selon ce qu'on surcharge.** Pour une fonction **absente du code de base**, la
  regle s'inverse selon le support :

  | Support surcharge | Fonction absente de la base |
  |---|---|
  | **Masque** (`[diva]` d'un `.dhsf`) | doit etre **`Private`** |
  | **Traitement de dictionnaire** (bloc `[diva]` dans un `.dhsd`) | doit etre **`Public`** |

  **Le cas courant est celui du masque.** Le second est **rare et en voie d'abandon** :
  c'est du code DIVA place dans un bloc `[diva]` **a l'interieur d'un `.dhsd`**, sur le
  meme principe que dans un masque.

  > **Ne pas confondre avec le travail habituel sur un `.dhsd`.** Declarer une table, un
  > champ, un index -- ce que couvre le skill `managing-diva-dictionaries` -- n'a **rien a
  > voir** : ce sont des zones de declaration, pas du code, et cette regle de visibilite ne
  > s'y applique pas. Elle ne concerne que les rares `.dhsd` qui portent un bloc `[diva]`.

- **Piege de montee de version -- et sa sortie.** Vous ajoutez `Private Procedure ApresRead`
  parce qu'elle n'existe pas dans la base. Une version ulterieure de Divalto ajoute
  `Public Procedure ApresRead` au standard. La recompilation de votre surcharge **echoue** :
  la fonction `Private` est devenue, par homonymie, une surcharge -- et `Private` dit
  l'inverse. Rien ne l'annonce avant la montee de version.

  La correction ne consiste pas a bricoler le modificateur : **votre fonction est devenue
  une vraie surcharge**, il faut donc l'ecrire comme telle et chainer sur le standard.

  ```diva
  ; AVANT -- legitime tant que rien de ce nom n'existait dans la base
  Private Procedure ApresRead
  Beginp
      ; lecture des donnees complementaires
  Endp

  ; APRES la montee de version, le standard porte Public Procedure ApresRead
  Procedure ApresRead              ; plus de Private : c'est une surcharge
  Beginp
      Standard.ApresRead()         ; on chaine sur le nouveau code de base
      ; lecture des donnees complementaires
  Endp
  ```

  On retombe exactement sur le **pattern canonique** decrit plus haut -- `Standard.<proc>()`
  en premier, specifique ensuite.

```diva
; MAUVAIS -- erreur compilateur xwin7 #210
;   "La fonction/procedure ZoomAbandon est une surcharge.
;    Elle ne peut etre PUBLIC"
Public Procedure ZoomAbandon
BeginP
    ...
EndP

; BON -- la visibilite est heritee du standard
Procedure ZoomAbandon
BeginP
    ...
EndP
```

Verifier la declaration du standard (`Public Procedure ZoomAbandon` dans le module original) confirme la visibilite, mais ne pas la repeter dans la surcharge.

## Visibilite des declarations dans une surcharge

Les `Record`, fichiers, `RecordSql` et constantes utilises par une procedure surchargee **ne sont PAS herites** du module standard. Ils doivent etre **redeclares localement** au fichier de surcharge.

```diva
; Fichier standard : gtuz021.dhsp
OverWrittenBy 'gtuz021u.dhop'
Public Record DDSYS.dhsd ZOOM

Public Procedure ZoomCreation
BeginP
    Zoom.Ok = 'O'
    ...
EndP

; -----------------------------------------------------
; Fichier de surcharge : gtuz021u.dhsp
OverWrite 'gtuz021.dhop'

Public Record DDSYS.dhsd ZOOM   ; <-- OBLIGATOIRE : redeclaration locale
                                ;     sinon erreur compilateur xwin7 #99
                                ;     "Mot inconnu : Zoom"

Procedure ZoomCreation          ; <-- sans Public (cf. section precedente)
BeginP
    Standard.ZoomCreation()
    if Zoom.Ok = 'O'
        ; specifique
    endif
EndP
```

Regle : seules les `Procedure` / `Function` sont surchargees au sens runtime. Tout symbole non-procedural (record, file, RecordSql, constante, define) utilise dans le corps doit etre redeclare en haut de la `.dhsp` de surcharge, **identique a la declaration du standard**.

### Constantes : re-`Include` ou redeclaration locale minimale

Les constantes d'un `.dhsp` standard (ex `GTTC000.dhsp`) **ne sont pas heritees** dans une surcharge -- les y utiliser sans rien faire donne `Erreur 99 : Mot inconnu`. C'est le **contexte de compilation du sous-projet** (les `Include` de son `.dhps`) qui determine ce qui est accessible, **pas** les includes du fichier parent surcharge. Deux options :

1. **Re-`Include` explicitement** le `.dhsp` qui fournit les constantes, meme si le standard l'inclut deja.
2. **Redeclarer localement et minimalement** la seule constante manquante, pour eviter qu'un double `Include` ne provoque une double definition :
   ```diva
   Const C_PICOD_BL = 3   ; cf. GTTC000.dhsp -- redeclaration locale minimale
   ```

Exemple concret : un sous-projet OverWrite dont le `.dhps` n'inclut que `zdiva.dhsp` rend toutes les constantes metier (`C_PICOD_BL`, `C_PICOD_CDE`...) inaccessibles -> declarer `Const C_PICOD_BL = 3` directement dans le `.dhsp` de surcharge.

### Record commun redeclare localement

Un `Record` commun (ex un parametrage via `<dico>.dhsd`) utilise dans un module qui n'inclut pas le `.dhsp` le fournissant doit etre redeclare localement, sinon `Erreur 31 : Signe egal attendu` :

```diva
Record "<dico>.dhsd" X LocX   ; redeclaration locale du Record commun
```

## Pattern canonique de surcharge de procedure

Trois regles, dans l'ordre :

1. **Toujours appeler `Standard.<proc>()`** -- meme si le standard est vide aujourd'hui. L'omettre cree une dette de compatibilite ascendante invisible : ca casse au prochain upgrade de pack si Divalto enrichit la procedure (cleanup, journalisation, validation metier).
2. **`Standard.<proc>()` en PREMIER**, code specifique ensuite. Le specifique observe l'etat post-standard et peut decider de ne pas s'executer si le standard a deja tranche (ex: standard a deja mis `Zoom.Ok = 'I'` -> ne pas afficher de pop-up de confirmation).
3. **Structurer en "tester l'acceptation"** (`if <flag> = 'O'`) plutot qu'en "tester le refus avec preturn". Un seul `if`/`endif` imbrique, branchement unique, plus lisible.

```diva
; Pattern canonique
Procedure ZoomAbandon
BeginP

    Standard.ZoomAbandon()

    if Zoom.Ok = 'O'                       ; le standard accepte l'abandon
        if MessageBox(...) = IDNO          ; on demande confirmation specifique
            Zoom.Ok = 'I'                  ; on annule l'abandon
        endif
    endif

EndP
```

A comparer au pattern "tester l'echec" (fonctionnellement equivalent mais moins lisible) :

```diva
Procedure ZoomAbandon
BeginP

    Standard.ZoomAbandon()

    if Zoom.Ok = 'I'                       ; standard a refuse
        preturn                            ; sortie precoce 1
    endif

    if MessageBox(...) = IDNO
        Zoom.Ok = 'I'
        preturn                            ; sortie precoce 2
    endif

EndP
```

Deux `preturn`, deux branches de sortie = code moins maintenable.

**Le pattern s'applique a toutes les procedures surchargees**, pas seulement aux `Zoom*` : modules de pieces (`Pre/PostInsert`, `Pre/PostUpdate`, `Pre/PostDelete`), tarification, calcul, etc. L'ordre "Standard puis specifique" + test du flag d'acceptation est la convention solide.

> Note : la grille des flags de retour (`'O'`, `'N'`, `'I'`, `'C'`...) varie selon le hook. Voir [zoom-hooks-reference.md](zoom-hooks-reference.md) pour les codes par hook Zoom*.

## Visibilite et partage inter-module

Au-dela de la surcharge, le partage de symboles entre modules DIVA obeit a des regles strictes. Ce qui **ne marche pas** (confirme au compile) :

| Tentative | Erreur | A la place |
|-----------|--------|-----------|
| `Public Structure` contenant un champ type `S` (string variable) | 216 | Champs de type fixe uniquement ; passer les chaines en parametres individuels |
| `public 1 xxx L` (variable simple en `Public`) | 82 | `PUBLIC` doit etre suivi de `FILE`/`HFILE`/`RECORD`/`FUNCTION`/`PROCEDURE` |
| `module.Variable` (lire une variable d'un autre module) | 98 ("Fonction inconnue dans le module") | N'exposer que des `Public Function`/`Public Procedure` ; lire via un accesseur |
| `RecordDiva StructureType Var` local a une fonction d'un autre module | "table absente" | La structure n'est pas exportee via `Module` -- passer les champs en parametres |
| `XmeListGetPosition(<id>, <var L>)` | 142 | Le 2e parametre recoit l'adresse du courant **et l'etat** de la liste : ce n'est pas un `L`, il faut un **buffer alphanumerique** |

Regle pour les **fonctions** : n'exposer entre modules que des `Public Function` /
`Public Procedure`.

### Les DONNEES, elles, ont un mecanisme dedie : `Extern`

Le tableau ci-dessus dit ce qui ne marche pas pour exposer une **variable** ou une
**structure**. Il ne faut pas en conclure que tout doit passer en parametres : DIVA a un
mecanisme documente pour partager des **fichiers et enregistrements** entre modules.

| Modificateur | Ce que Diva alloue | Qui y accede |
|---|---|---|
| `Public` | une donnee **commune** | tous les modules et masques qui la declarent `Public`. Les enregistrements utilises dans un **masque** sont **toujours** publics |
| `Protected` | une instance **propre a chaque module** declarant | ce module, plus ceux qui declarent la meme donnee `Extern`. Un `Record` `Protected` ne peut **pas** etre affiche ni saisi dans un masque |
| `Extern` | **rien** -- aucune memoire | a l'appel, la donnee pointe sur l'instance `Public` ou `Protected` **du module appelant** |

Ces trois-la precedent une declaration `HFile`, `HTmpFile`, `Record` ou `RecordDiva` --
jamais une `Function` ni une `Procedure`.

Le patron : un module de service declare ses donnees `Extern` ; chaque appelant declare les
siennes `Protected` (instance isolee) ou `Public` (instance partagee). Le module de service
travaille alors sur les donnees **de son appelant courant**, sans les connaitre.

> Si une donnee `Extern` n'a jamais ete allouee par aucun module au moment de l'appel, elle
> est allouee en `Public` par le module appele.

### Une `Public` definie dans un module de surcharge exige sa declaration chez l'appelant

Le mecanisme `OverWrite` expose au **runtime** les symboles connus du module standard.
Mais la **compilation** d'un appelant resout contre l'interface des modules qu'il
declare. Une `Public Function` / `Public Procedure` definie **uniquement** dans le
module de surcharge (`<base>u`) n'est donc pas visible d'un appelant qui ne declare que
le module standard :

```diva
; MAUVAIS -- chez l'appelant
Module "GTTTPCE000.dhop"        ; le module STANDARD seul
; ... appel d'une Public definie uniquement dans gtutpce000 -> ne compile pas

; BON -- declarer AUSSI le module de surcharge
Module "GTTTPCE000.dhop"
Module "GTUTPCE000.dhop"        ; le module de SURCHARGE qui porte la nouvelle Public
```

Regle : **une nouvelle `Public` dans un module de surcharge, appelee ailleurs, exige la
declaration `Module "<u>.dhop"` chez chaque appelant.**

### Avant de deplacer ou supprimer une `Public`, recenser ses appelants

La resolution d'un appel inter-module est **figee a la compilation de l'appelant**.
Deplacer une `Public` d'un module a un autre, ou la supprimer, **ne casse pas la
compilation des modules modifies** : les appelants non recompiles continuent de
referencer l'ancien module, et la rupture n'apparait qu'a **l'execution**.

Avant tout deplacement ou suppression d'une `Public` :

1. **Rechercher chaque nom deplace dans tout le projet**, pas seulement dans son module
   d'origine.
2. Recompiler **les appelants**, pas uniquement les modules touches.

> **Piege aggravant** : une `Public` exposee via `OverWrite` apparait, dans le message
> d'erreur runtime, comme appartenant au **module standard** (`gttz000_sql`) et non au
> module de surcharge qui la definit reellement. Le message oriente donc vers le mauvais
> fichier.

---

### Fonctions partagees dhsp + dhsf -> module tiers

Pour reutiliser des fonctions a la fois depuis un `.dhsp` ET depuis le `[diva]` d'un `.dhsf` : les rendre `Public` dans le `.dhsp` puis ajouter `Module "<dhsp>.dhop"` dans `[diva]` cree une **reference circulaire** (`.dhop` -> `.dhof` -> `.dhop`) -- ca compile en harness mais le statut runtime est incertain.

Norme : placer ces fonctions dans un **module tiers** (`.dhop`) declare par les deux consommateurs. Validation en harness multi-sources :
```
--sources <module_tiers>.dhsp <appelant>.dhsp
```
(le `.dhsp` appelant seul echoue, le `.dhop` tiers etant absent). Pour le harness multi-sources, voir le skill `compiling-diva-projects`.

## La declaration `Module` n'est **pas transitive**

Le reflexe venu d'autres ecosystemes -- ou les dependances se propagent -- ne s'applique
pas. La documentation est explicite : *un module qui veut utiliser une fonction/procedure
d'un module externe **doit declarer** le module externe par la declarative `Module`.*

**Chacun pour soi** : declarer un module A qui depend lui-meme de B ne donne **aucun** acces
aux publiques de B. Il faut declarer B aussi, dans **votre** source.

```diva
; MAUVAIS -- gttmpce depend de gtpmpce, mais ca ne se propage pas
Module "gttmpce.dhop"
; ... appel de Piece_Imprimer (definie dans gtpmpce) -> Erreur 99 : Mot inconnu

; BON -- declarer chaque module dont on appelle DIRECTEMENT une publique
Module "gttmpce.dhop"
Module "gtpmpce.dhop"
```

Le fait que `get_program_overview` montre `gtpmpce` dans les dependances de `gttmpce` ne
change rien : le graphe decrit les dependances **internes** du module, pas ce que **votre**
source a le droit d'appeler.

**Le cas inverse est encore plus net.** Un appelant reclamait `Mode_Lecture_Impression`
-- une `Public function int` de **`gttmpce`**, source livree -- en n'ayant declare que
`Module "gtpmpce.dhop"`. Or `gtpmpce` **ne declare meme pas** `gttmpce` : la dependance
n'existe que dans l'autre sens. Aucune transitivite, meme imaginaire, n'aurait pu le sauver.
Le programme du standard qui utilise les deux fonctions, `gttt545`, declare **les deux**.

**Regle operatoire** : une declaration `Module` par module dont vous appelez directement une
`Public`, etablie a partir du module qui **definit** la fonction -- jamais a partir de celui
qui a l'air proche.

**Corollaire pratique -- le module manquant n'est pas toujours greppable.** Les familles de
helpers generees (par exemple les helpers `RecordSql` d'un groupe `fic-sql` : effacement de
conditions, `Select_<instance>`) vivent dans un module **compile** dont la source n'est pas
dans l'arborescence standard livree. Symptome typique : les methodes `.Where.*` de
l'instance resolvent correctement, mais les helpers du groupe donnent `Erreur 99 : Mot
inconnu`. La recherche textuelle dans les sources ne trouvera rien -- c'est bien une
declaration `Module "<le .dhop>"` qui manque, pas un nom mal orthographie.

**Le cas le plus facile a rater : les deux blocs d'un masque surcharge.** Un `.dhsf`/`.dhsi`
de surcharge porte **deux** blocs de code -- `[diva] … [/diva]`, votre surcharge, et
`[diva_base] … [/diva]`, la copie figee du standard. Leurs declarations `Module` sont
**independantes** : elles ne s'heritent pas d'un bloc a l'autre. Une procedure ajoutee dans
`[diva]` qui appelle une fonction d'un module declare seulement dans `[diva_base]` donne la
meme `Erreur 99 : Mot inconnu`.

```diva
; [diva_base] -- copie du standard, INTOUCHABLE
Module "gttmpce.dhop"

; [diva] -- votre surcharge : redeclarer ce dont VOS procedures ont besoin
Module "gttmpce.dhop"        ; sans cette ligne -> Erreur 99 dans [diva]
```

C'est la meme regle que ci-dessus -- *chacun pour soi* -- appliquee la ou le decoupage n'est
pas un fichier mais un **bloc**. Deux consequences pratiques : ne jamais ajouter une
declaration dans `[diva_base]` pour « depanner » le bloc voisin (modifier la copie figee
casse le diff de surcharge), et verifier ses `Module` dans `[diva]` avant de chercher une
faute de frappe.

> **Niveau de preuve.** Le mecanisme est **rapporte** (retour terrain, non reproduit de notre
> cote). Il est **corrobore** par un outil du devkit : `converting-diva-lectab` **restreint
> l'insertion des directives `Module` au seul bloc `[diva]`**, regle qu'il qualifie de
> non-negociable et qu'il auto-verifie fichier par fichier (aucune ligne modifiee hors
> `[diva]`).

---

### `Module` n'apporte PAS les enregistrements

La non-transitivite ci-dessus porte sur les fonctions et les procedures. Pour les **donnees**,
c'est plus radical : **une declaration `Module` n'apporte aucun enregistrement**, qu'il soit
declare `Public` dans le module lui-meme ou dans l'un de ses `Include`.

```diva
; MAUVAIS -- G3XZ est pourtant declare dans un include de gtpmpce
Module "gtpmpce.dhop"
; ... utilisation de G3XZ -> Erreur 99 : Mot inconnu : G3XZ

; BON -- chaque programme qui utilise l'enregistrement le declare LUI-MEME
Public Record 'GTFDD.dhsd' XZ G3XZ
```

**Ce n'est pas une bizarrerie de `G3XZ`, c'est la convention DIVA**, et le manuel l'impose
explicitement pour d'autres enregistrements partages :

- Zoom SQL -- dans le module de traitements d'un zoom, l'enregistrement `Zoom` **doit**
  etre declare `Public` ; idem pour le `RecordSql` considere.
- Ywpf -- l'enregistrement `RowInfo` **doit** etre declare `Public` dans votre programme.

> **Mesure (X.13)** : **1 306 declarations** d'un enregistrement de type `XZ`, reparties sur
> **1 050 programmes**. La declaration locale n'est pas un contournement : c'est la norme.

Le mecanisme qui partage reellement une donnee entre modules, c'est le trio
`Public` / `Protected` / `Extern` decrit plus haut -- pas `Module`.

> **Le meme message, trois causes.** `Erreur 99 : Mot inconnu` ne dit pas laquelle : un
> **implicite actif** qui ne correspond pas au projet, un **`Module` manquant** pour une
> fonction, ou un **enregistrement non declare** chez vous. Le tri est dans le skill
> `compiling-diva-projects` (`reference/compilation-errors.md`) -- y aller **avant** de
> toucher au source, la premiere cause n'en releve pas.

> **Niveau de preuve.** La structure est **mesuree** : `gtpmpce` inclut bien `gtpc000`, qui
> declare bien un enregistrement `XZ`. Que cette declaration ne franchisse pas la frontiere du
> module est **observe en production** -- Erreur 99 au compile, releve par un partenaire --
> et non reproduit ici : le workspace n'a pas de compilateur.

## `PP` / `TT` : ce qui est surchargeable et ce qui ne l'est pas

Convention de nommage **non documentee** mais massive dans le standard :

| Infixe | Role | Source livree ? | Surchargeable ? |
|---|---|---|---|
| `PP<nnn>` | **Programme Principal** | **non** | **non** -- `OverWrite` echoue en `Erreur 106 : Le module X.DHOP ne peut etre surcharge` |
| `TT<nnn>` | module de **Traitement** associe, **meme numero** | **oui** | **oui**, et il porte souvent des hooks prevus pour ca |

**Mesure sur le standard X.13** (via le graphe de connaissance) :

- **410** programmes `PP`, **399** programmes `TT` ;
- **392 des 410 `PP` (95,6 %) ont un `TT` de meme numero** -- quasi systematique, mais **pas
  absolu** : 18 exceptions. Verifier, ne pas presupposer ;
- **`PP` : 11 169 fonctions/procedures sur 11 169 sont protegees** (corps non livre) ;
- **`TT` : 40 sur 6 447 seulement** (0,6 %) -- autrement dit `TT` **est** livre.

La protection porte sur le **module compile entier**, pas sur une fonction precise : c'est
pour cela que l'erreur 106 parle du module et non de la procedure visee. C'est le pendant
du principe d'opt-in vu plus haut -- un `PP` ne se declare pas surchargeable.

### Ou aller quand la cible est un `PP`

Vers le `TT` de meme numero, qui porte tres souvent le point d'extension deja prevu :

- **301** modules `TT` portent au total **3305** hooks nommes `..._Av` / `..._Ap` (avant /
  apres) ;
- **2195 de ces hooks (66 %) ont un corps quasi vide** -- ils existent precisement pour
  qu'on y ajoute du specifique.

Exemple verifie : `Traitement_Validation_Av` et `Traitement_Validation_Ap` sont presents,
avec des corps de 4 a 5 lignes, dans de nombreux `TT`.

Le reflexe utile : **ne pas s'acharner sur le `PP`**. Chercher d'abord le hook vide du `TT`
de meme numero.

---

## Retrouver la signature d'une fonction protegee

Ecrire une surcharge ou un appel demande la signature exacte. Quand le corps n'est pas
livre, le graphe rend litteralement la chaine **« Programme protégé, non livré. »** a la
place du code -- et **la liste des parametres n'y est pas** (verifie : la propriete
`params` vaut `[]` sur les **195 665** fonctions et procedures du graphe, sans exception).

**Il n'y a donc pas de propriete a interroger pour obtenir une signature protegee.** La
voie qui marche est indirecte : passer par un **appelant livre**.

Un appel depuis du code livre montre les arguments reels au site d'appel. Exemple mesure :
`Piece_Imprimer` est protegee, mais elle est appelee depuis `gttt545.Integration_BL_Ap` --
une fonction `TT`, donc livree, dont le corps est lisible.

Marche a suivre : voir [mcp-query-pitfalls.md](../../querying-diva-graph/reference/mcp-query-pitfalls.md)
dans le skill `querying-diva-graph`.

---

## Surcharge RecordSql

```xml
; Dans le .dhsq d'origine
<RecordSql Name=MaVue ... OverWrittenBy="monfichierU.dhoq">
```

Convention de nommage : `gtrsart.dhoq` → `gtrsartu.dhoq` → `gtrsartuu.dhoq`

La surcharge RecordSql peut ajouter :
- Champs SELECT supplementaires
- JOINs additionnels (avec restrictions, cf. delta strict)
- Criteres WHERE / ORDERBY (avec restrictions)

**Important** : la surcharge `.dhsq` obeit a une grammaire "delta strict" -- toute redeclaration du standard est interdite et provoque des erreurs explicites au compile. Voir la doc dediee du skill `generating-recordsql` : [dhsq-overwrite-pattern.md](../../generating-recordsql/reference/dhsq-overwrite-pattern.md) pour les 9 interdits empiriques, le pattern delta correct, et la convention de rattachement via groupe `[communs]`.

## Regles

- **Ne jamais modifier le module standard** -- toujours surcharger
- Le fichier surcharge doit etre dans le meme sous-projet (ou un sous-projet de surcharge dedie)
- `Standard.` est le seul moyen d'appeler la version originale depuis la surcharge
- Convention stricte sur le nommage : suffixe `U` (puis `UU`) en majuscule dans le `OverWrittenBy`, minuscule dans le nom de fichier
- Pas de modificateur de visibilite sur la procedure surchargee -- **`Public` est refuse**
  (erreur 210) ; l'absence de modificateur EST ce qui la designe comme surcharge
- Declarer, dans **son propre** source, **chaque** module dont on appelle directement une
  publique : la declaration `Module` n'est pas transitive
- Ne pas s'acharner sur un `PP<nnn>` (non livre, non surchargeable) -- chercher le hook du
  `TT<nnn>` de meme numero
- Redeclarer localement tout symbole non-procedural utilise (records, fichiers, RSQL, constantes)
- Appeler `Standard.<proc>()` systematiquement, en premier, et structurer le test sur le flag d'acceptation

---

## Advisory -- analyse d'impact avant surcharge (via diva-mcp)

> **Snapshot X.12, non bloquant**. Toujours croiser avec X.13 avant decision -- le graphe est une aide a la decouverte, pas une validation. Ne jamais utiliser ces resultats comme garde-fou.

Avant de surcharger un module (zoom, mchk, recordsql), il est utile d'identifier **qui depend deja** des exports publics du module. Le graphe `diva-mcp` permet des explorations rapides.

### Reutilisateurs d'une procedure / fonction publique

Typiquement utile pour mchk (`Get_TABLE_Record`, `Check_TABLE`, `Initialize_*_New` sont tres reutilises).

```cypher
// Nombre de reutilisateurs d'une procedure/fonction publique (hors programme d'origine)
MATCH (proc)
WHERE (proc:Procedure OR proc:Function)
  AND toLower(proc.name) = toLower($nom_procedure)
  AND toLower(proc.decla_type) = 'public'
OPTIONAL MATCH (caller)-[:CALLS]->(proc)
WHERE caller.program <> proc.program
WITH proc, count(DISTINCT caller) AS nb_callers_externes,
     collect(DISTINCT caller.program)[..15] AS sample_programs
RETURN proc.program AS module_source, proc.name AS procedure,
       nb_callers_externes, sample_programs
ORDER BY nb_callers_externes DESC;
```

### RecordSql surcharges deja existants dans le standard

Utile pour eviter de surcharger un RecordSql qui l'est deja, ou pour s'inspirer d'une surcharge existante.

```cypher
// Lister les RecordSql ayant deja une surcharge dans le standard X.12
// (property OverWrittenBy exposee dans le DObj du fichier .dhsq)
MATCH (p:Program)-[:CONTAINS]->(rs:RecordSQL)
WHERE rs.name IS NOT NULL
RETURN p.name AS fichier, rs.name AS recordsql_name LIMIT 50;

// Pour un RecordSql donne, quels programmes l'utilisent (via USES_QUERY)
MATCH (rs:RecordSQL {name: $nom_vue})-[:USES_QUERY]->(q:QueryFile)
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(rs2:RecordSQL {name: $nom_vue})
RETURN DISTINCT prog.name AS program, q.name AS query_file LIMIT 30;
```

### Impact "en amont" d'une surcharge de zoom

Les procedures `Zoom*` (ZoomDebut, ZoomCreation, ...) ne sont typiquement pas appelees par du code applicatif mais par le framework via hook. En revanche, les **constantes de zoom** (numeros) et les **libelles exposes** sont tres consommes.

```cypher
// Constantes publiques declarees dans un zoom
MATCH (p:Program {name: $nom_zoom_programme})-[:CONTAINS]->(c:Const)
WHERE toLower(c.decla_type) = 'public'
RETURN c.name, c.value, c.line ORDER BY c.line;

// Defines declarees dans le mchk associe au zoom
MATCH (p:Program {name: $nom_mchk_programme})-[:CONTAINS]->(d:Define)
RETURN d.name, d.line ORDER BY d.line;
```

### Bonnes pratiques advisory

- Lancer ces requetes **avant** de decider de la portee de la surcharge (standard, standard + uU, ou uniquement uU).
- Reflechir a la compatibilite ascendante : une surcharge qui change la signature d'une fonction publique peut casser tous les reutilisateurs identifies.
- **Ne pas bloquer sur ces chiffres** -- croiser avec la version X.13 courante si la surcharge vise le code actuel (grep dans le filesystem standard, inspection SQL).
