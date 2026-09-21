# Catalogue des callbacks A5PMTAB

> **Source autoritaire** : `Standard/Version X.13/objet/proto_a5pmtab.dhsp` -- le fichier de
> **prototypes** livre avec l'ERP. **2 151 lignes, 188 declarations** pour **180 noms distincts**
> -- **90 suffixees** et **90 non suffixees**, appariees une a une. L'ecart de 8 vient
> de `Defaut` et `Apres`, qui existent chacune en deux declarations : une
> `Function Int` avec parametres **et** une `(XMT) Procedure` sans. C'est le contrat, pas une reconstitution.
>
> **Ne pas ecrire une signature de memoire, et ne pas la deduire.** Trois RETEX partenaires
> se sont plantes exactement la, et les echecs se produisent **a l'execution**, sans une
> erreur de compilation.

## La regle qui commande tout : **`Fperso` decide de la forme appelee**

C'est le point le plus important de cette page, et il n'est ecrit nulle part dans la doc.

| Ouverture du tableau | Forme appelee par A5PMTAB | 1er parametre |
|---|---|---|
| `Creer_Parametre(..., Fperso = <vrai>, Nom = '<X>')` | **suffixee** `DefProcInterro_<X>_Apres` | **aucun `Id`** |
| `Creer_Parametre(...)` sans `Fperso` | **non suffixee** `DefProcInterro_Apres` | **`&Id`** |

**Le suffixe ne s'invente pas : c'est la valeur que vous passez dans `Nom=`.** Ecrire
`DefProcInterro_MonTableau_Apres` sans avoir declare `Nom='MonTableau'` ne produit rien --
A5PMTAB appellera la forme non suffixee, qu'il ne trouvera pas.

Les deux formes ne sont pas interchangeables : **elles n'ont pas le meme nombre de
parametres**. Mesure sur les **82 paires** de noms appariees du prototype : **75 ont
exactement un parametre d'ecart** -- ce parametre etant `Id`.

### C'est l'explication exacte de l'erreur d'appel

> *« Nombre de parametres errone lors de l'appel de DEFPROCINTERRO_APRES : la fonction
> attend 0 parametre(s) et l'appelant a place 1 parametre(s) sur la pile »*

Ce message n'est pas obscur une fois la regle connue : **la forme appelee et la forme
declaree ne correspondent pas.** Soit `Fperso` est actif et vous avez ecrit la forme non
suffixee, soit l'inverse.

### Un ecran du standard porte les DEUX formes cote a cote

C'est le modele a suivre pour un tableau imbrique. Meme programme, deux procedures :

```diva
; --- tableau PRINCIPAL : pas de Fperso -> callbacks DefProcInterro_*(&Id)
options = Creer_Parametre(<nomTableauXme>, <codeArret>, <recordLigne>, <ascenseur>)
AP_Interroger_Tableaux(<applic>, <nomTableauXme>, options)

; --- tableau IMBRIQUE : Fperso + Nom -> callbacks DefProcInterro_Detail_*
options = Creer_Parametre(<idTableau2>, <codeArret2>, <recordLigne2>, <ascenseur2>,
                          Fperso = <vrai>, Nom = 'Detail')
options &= '<Perso>' & HmpEncode(true)
AP_Interroger_Tableaux(<applic>, <idTableau2>, options)
```

**Ce n'est donc pas le nombre de tableaux qui commande** -- c'est `Fperso`, tableau par
tableau. Le nombre ne fait que **correler** : le tableau principal se passe de `Perso`, le
secondaire en a besoin pour se distinguer.

> **Correction du 2026-08-28.** La premiere version de cette page enoncait la regle comme
> « un tableau -> non suffixee ; plusieurs tableaux -> suffixee ». **Juste dans l'effet, faux
> dans la cause** -- et surtout, elle omettait le point actionnable : `Nom=`.

**Le cas vecu** : un ecran mono-tableau fonctionnel, callbacks non suffixees ; on ajoute un
second tableau en **reutilisant les memes hooks**. Les deux tableaux se disputent alors la
meme serie de callbacks. **Le correctif** : donner au second tableau son `Fperso` et son
`Nom='<X>'`, et ecrire une serie `DefProcInterro_<X>_*` dediee.

## `Id` est passe PAR ADRESSE -- et le fichier de prototypes ecrit le contraire

**`Id` se declare `&Id`.**

```diva
Function Int DefProcInterro_Apres(&Id)      ; & dans la SIGNATURE
    1 Id    L                               ; sans & dans la declaration
beginf
    freturn (0)
endf
```

> **PIEGE MAJEUR -- ne pas recopier le `Id` du fichier de prototypes.**
>
> `objet/proto_a5pmtab.dhsp` ecrit `DefProcInterro_Apres(Id)`, **sans esperluette**, et
> **aucune** de ses 90 callbacks non suffixees n'en porte. C'est **faux** : A5PMTAB passe
> `Id` **par adresse** (confirme par l'architecte du workspace).
>
> **C'est le fichier dont le role est de declarer le contrat qui se trompe sur le point le
> plus dangereux.** Les deux autres sources livrees sont, elles, correctes -- les extraits
> de code `A5/source/ExtraitsErp/divalto_a5pmtab_*.dhsp` **et** les ecrans du standard en
> production ecrivent bien `&Id`.
>
> **Consequence de methode** : sur A5PMTAB, `proto_a5pmtab.dhsp` sert a connaitre la
> **liste** des callbacks et leur **nombre de parametres** -- pas leur mode de passage.
> Pour le mode de passage, se referer aux extraits ou a un ecran du standard.

Un parametre declare `Id` alors que l'appelant empile une adresse fait lire une adresse
comme une valeur : c'est la meme famille de defaut que le `1A` de
[pieges-execution.md](pieges-execution.md) -- **ca compile, et ca casse a l'execution sans
un message**.

## Les familles

Deux familles principales, **strictement symetriques** : `DefProcInterro_*` (tableau en
consultation, via `AP_Interroger_Tableaux`) et `DefProcSaisie_*` (tableau en saisie, via
`AP_Saisir_Tableaux`). Memes noms, memes signatures.

### Cycle de vie du tableau

| Callback | Params (forme non suffixee) |
|---|---|
| `Charger` | `(Id)` |
| `InitOption` | `(Id)` |
| `AvantBoucle` | `(Id, &ToucheInitiale, &ArretInitial, &ToucheFinale, &ArretFinal)` |
| `Pilotage` | `(Id, &ToucheInitiale, &ArretInitial, &ToucheFinale, &ArretFinal)` |
| `AvantConsult` | `(Id)` |
| `Defaut` | `(Id, &Ligne, &Ascenseur, &Privilege, &selection, &perso)` |
| `Apres` | `(Id)` |
| **`ArretSpecifique`** | **`(Id, &Sortie)`** -- voir ci-dessous |
| `Validation` | `(Id)` |
| `Abandon` | `(Id)` |
| `Fin` | `(Id)` |
| `ModeFiche` | `(Id)` |
| `Suivant` / `Precedent` | `(Id)` |
| `F11` | `(Id)` |

### Chargement dynamique (arbres, sous-niveaux)

`Charger_Dynamique(Id, &cle, Avant)` · `Charger_Dynamique_SousNiveau(Id, &nombre, &Avant)` ·
`Charger_Dynamique_debut(Id)` · `Charger_Dynamique_fin(Id)` ·
`Charger_Dynamique_Debut_Init(Id)` · `Charger_Dynamique_Fin_Init(Id)` ·
`Charger_Dynamique_recharge_init(Id)` · `Charger_Dynamique_recharge_modif(Id)`

### Tri, recherche, filtre, export

`InitTri(Id, &Colonne)` · `InitColRecherche(Id, &Colonne)` · `Recherche(Id, &Ligne, &Ascenseur)`
(retour **`Char`**) · `InitFiltre(Id)` · `Filtre_Av(Id)` · `Init_Protection_Export(Id)` ·
`DefProcTriAvant(Id)` · `DefProcTriApres(Id)` · `DefProcTriAvantErase(Id)` ·
`DefProcTriSelectionNiveau(Id, &Ligne)` · `DefProcTriTraiterNiveau(Id, &Ligne)` ·
`DefProcTriAvantNiveau(Id, &Ligne, Niveau, NivMax)` · `DefProcTriLecturElemTrie(Id, Ligne)`

### Lignes, ruptures, niveaux

`Lecture_Ligne_tableau_Av(Id, &Ligne)` · `Lecture_Ligne_tableau_Ap(Id, &Ligne)` ·
`Rupture_Ligne_tableau(Id, &Niv, &Ligne)` · `Rupture_Ligne_tableau_Av/_Ap(Id, &Ligne)` ·
`DefProcExpanser(Id)` · `DefProc_DeploiementNiveaux_Maj(Id)`

> **Mise en route des ruptures**, documentee dans le prototype : appeler dans `Charger` --
> `AP_Init_Liste_rupture(id)`, puis un `AP_Ajouter_Liste_rupture(id, <niveau>, <colonne>)` par
> niveau, puis `AP_Ajouter_Niveau_rupture(id)`. Si `Niv` rendu vaut **0**, aucun ajout dans la
> XmeList.

### Saisie, edition, presentation

`DefProcSaisie(Id, Operation)` · `DefProcDelete(Id, Operation)` · `DefProcCopier(Id)` ·
`DefProcColler(Id)` · `DefProc_Couleur_Tableau_Actif(Id, Actif)` ·
`DefProc_Couleur_Colonne_Tableau_Actif(Id, Actif, i)` (retour **`Char`**) ·
`DefProc_Image_Colonne_Etat(Id)` (retour **`Char`**) · `DefProc_List_Height_Changing(Id)` ·
`DefProc_Click_Autre_Tableau(arret)`

### Arbre AIV

`DefProcSaisie_AIV_Renvoyer_Id(Id)` · `DefProcSaisie_AIV_Maj_Ligne_fonctionel(Id, &Naiv, &Eid, &Ligne)` ·
`DefProcSaisie_AIV_Maj_Ligne_tableau(Id, &Ligne, &Idc, &Eid)` ·
`DefProcSaisie_AIV_Sup_Branche_fonctionel(Id, BorneGa, BorneDr)`

## `ArretSpecifique` : le corps du prototype, a reproduire tel quel

```diva
Function int DefProcInterro_ArretSpecifique(Id, &Sortie)
    1 Id      L
    1 Sortie  B = False
    1 Retour  L = 0
beginf
    freturn (Retour)
endf
```

Et la forme **suffixee**, sans `Id` :

```diva
Function int DefProcInterro_G1T1_ArretSpecifique(&Sortie)
    1 Sortie  B = False
    1 Retour  L = 0
beginf
    freturn (Retour)
endf
```

Deux choses a ne pas changer : **`1 Sortie B`** -- surtout pas `1A` (voir
[pieges-execution.md](pieges-execution.md)) -- et le **retour `int`**.

## Irregularites du fichier livre, a connaitre

1. **Certaines formes non suffixees perdent le tiret bas** : la paire de
   `DefProcSaisie_G1T1_Saisie` est **`DefProcSaisie`** (pas `DefProcSaisie_Saisie`) ; celle de
   `DefProcSaisie_G1T1_Delete` est **`DefProcDelete`** ; celles de `DefProc_G1T1_TriAvant` /
   `_TriApres` sont **`DefProcTriAvant`** / **`DefProcTriApres`**. Ne pas deduire le nom :
   le lire.
2. **`DefProc_Click_Autre_Tableau(arret)`** declare `1 Id L` dans son corps **sans lister
   `Id` dans sa signature**. Incoherence du fichier livre -- signalee ici, non tranchee.
3. Les callbacks **`Defaut`** et **`Apres`** existent en **deux declarations** chacune : une
   `Function Int` (avec parametres) **et** une `(XMT) Procedure` sans parametre.

## Voir aussi

- [invocation.md](invocation.md) -- `Creer_Parametre`, `AP_Interroger_Tableaux`, les 16 options
- [pieges-execution.md](pieges-execution.md) -- les pieges qui **compilent**
- [keywords-verifies.json](keywords-verifies.json) -- le releve date, ses sources, ses limites
