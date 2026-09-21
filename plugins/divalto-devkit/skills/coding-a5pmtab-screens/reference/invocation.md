# Invoquer un tableau A5PMTAB

> Forme **lue dans un ecran du standard livre**, en production. Ce n'est pas une
> reconstitution : c'est le patron reel, avec ses 16 options.

## Les deux modules a declarer

```diva
Module "A5PMTAB.dhop"
Module "A5PMTAB000.DHOP"
```

**Les deux.** La declaration `Module` **n'est pas transitive** en DIVA : declarer l'un ne
donne aucun acces aux publiques de l'autre. Sans les deux, on obtient
`Erreur 99 : Mot inconnu` sur des fonctions qui existent pourtant.

## Le patron complet

```diva
Public Procedure Gerer_Tab
1  options    S
Beginp

    ; --- 1. base des options
    options = Creer_Parametre(<idOuNomTableauXme>, <codeArret>, <recordLigne>, <ascenseur>)

    ; --- 2. options, une par ligne, en HMP
    options &= '<Privilege>'              & HmpEncode(<privilege>)
    options &= '<Selection>'              & HmpEncode(true)     ; multiselection
    options &= '<tri>'                    & HmpEncode(true)
    options &= '<couleur>'                & HmpEncode(true)
    options &= '<TRI_AUTO>'               & HmpEncode(false)
    options &= '<TRI_Conserve_courant>'   & HmpEncode(true)
    options &= '<RECHERCHE>'              & HmpEncode(true)
    options &= '<RECHERCHE_TYPE>'         & HmpEncode('T')
    options &= '<Recherche_key>'          & HmpEncode(K_CTRL_F)
    options &= '<recherche_key_s>'        & HmpEncode(K_F3)
    options &= '<recherche_key_p>'        & HmpEncode(K_SF3)
    options &= '<CTRLF4>'                 & HmpEncode(true)
    options &= '<SCTRLF4>'                & HmpEncode(true)
    options &= '<Export>'                 & HmpEncode(true)
    options &= '<EXPORTTABLEUR>'          & HmpEncode(true)
    options &= '<FILTRE>'                 & HmpEncode(true)

    ; --- 3. affichage des pages, dans cet ordre
    XmeDispv(MZ.MeCle, <pageAccordeon>,      XME_MODE_GOTO)
    XmeDispv(MZ.MeCle, <pageEnteteSelection>, XME_MODE_GOSUB)  | xmeret
    XmeDispv(MZ.MeCle, <pageTableau>,         XME_MODE_GOSUB)

    ; --- 4. preparation des colonnes
    XmeList_ScanColumn(<varTableauXme>)

    ; --- 5. la main passe a A5PMTAB : il appellera vos callbacks
    ;     (le standard commente cette ligne « Passage de relai au tableau »)
    res = AP_Interroger_Tableaux(<constanteApplic>, <idOuNomTableauXme>, options)

    xmeret
    XmeRet
Endp
```

Pour un tableau **en saisie**, remplacer l'appel par `AP_Saisir_Tableaux(...)` et la famille
de callbacks par `DefProcSaisie_*`. **Forme lue dans le standard** :

```diva
public procedure Modif_tableau(IdTableau)
1  param      S
1  res        1,0
1  IdTableau  L
beginp
    Param = Creer_Parametre(IdTableau, <codeArret>, <recordLigne>, <ascenseur>)
    Param &= '<Privilege>' & HmpEncode(ToString(<privilegeModification>))
    Param &= '<Tri>'       & HmpEncode(True)

    ; Passage de relai au tableau
    res = AP_Saisir_Tableaux(<constanteApplic>, IdTableau, param)
endp
```

**Le retour est exploitable**, et le standard l'affecte -- alors que l'ecran de consultation
lu plus haut appelle `AP_Interroger_Tableaux` en instruction et **ignore** son retour.

## Les trois choses a comprendre

### 1. `options` est une chaine HMP, construite par concatenation

`Creer_Parametre(...)` rend la **base**, puis chaque option s'ajoute par
`options &= '<Tag>' & HmpEncode(valeur)`. Ce n'est pas une liste de parametres : c'est une
chaine balisee. D'ou deux consequences :

- une option mal orthographiee **ne provoque aucune erreur** -- elle est simplement ignoree ;
- l'ordre des options n'a pas d'importance, mais `Creer_Parametre` doit venir **en premier**.

### 2. `Creer_Parametre` prend 4 parametres, plus DEUX parametres nommes optionnels

```
Creer_Parametre(<idOuNomTableauXme>, <codeArret>, <recordLigne>, <ascenseur>
                [, Fperso = <booleen>] [, Nom = '<suffixe>'])
```

| Position | Ce que c'est |
|---|---|
| 1 | le tableau -- **soit le nom** de la variable de tableau du masque, **soit un `Id`** (un `L`) obtenu au runtime |
| 2 | le **code d'arret** -- numerique ; vu en constante (`C_..._Arret`) et en litteral (`3002`) |
| 3 | le **record de ligne** du tableau |
| 4 | l'**ascenseur DU tableau** -- `SCROLLBAR32` pour l'un, `SCROLLBAR_<X>` ou `<record>_ASC` pour un autre. **Ce n'est pas un jeton fixe.** |
| `Fperso =` | **decide de la forme des callbacks appelees** -- voir [callbacks-catalogue.md](callbacks-catalogue.md) |
| `Nom =` | **le suffixe** utilise par la forme suffixee |

C'est le meme parametre qui est passe ensuite a `AP_*_Tableaux` : il identifie le tableau de
bout en bout.

> **`Fperso` et `Nom` ne sont pas des details de confort** : ils changent la **signature**
> des callbacks qu'A5PMTAB va appeler. Un ecran du standard passe `Fperso` et `Nom='Detail'`
> pour son tableau imbrique, et rien pour son tableau principal -- les deux formes cohabitent
> dans le meme programme.

### 3. La main passe a A5PMTAB, et il rend un code de sortie

Apres `AP_*_Tableaux`, **vous n'ecrivez plus le flux** : A5PMTAB prend le controle et appelle
vos callbacks aux moments prevus. Tout le travail specifique vit dans les callbacks, pas
apres l'appel.

C'est le meme renversement que `Collate` en RecordSql -- avec une difference : **`Collate`
recoit les noms de procedures en chaine, A5PMTAB non.** Il les resout implicitement, par
convention de nommage. **Comment, exactement, n'est pas etabli** (cf. `non_verifie` dans
[keywords-verifies.json](keywords-verifies.json)).

**Les callbacks sont optionnelles.** Un ecran du standard confie un tableau **en saisie**
sans declarer **aucune** callback : le moteur tourne sur ses defauts
(`DefProc*_Defaut` -> `XmeListConsultDefault`). C'est le cas d'usage le plus simple, et il
suffit souvent.

**Le code de sortie dit quelle callback a mis fin au tableau** -- lu dans les commentaires
des squelettes :

| Retour de `AP_*_Tableaux` | Cause |
|---|---|
| **1** | `Abandon` a rendu `False` |
| **2** | `Validation` a rendu `False` |
| **3** | `Apres` a rendu `True` |
| **4** | `ArretSpecifique` a positionne son parametre de sortie a `True` |

C'est par la que se lit le contrat entre vos callbacks et le code appelant : une callback ne
« retourne » pas au sens habituel, **elle choisit comment le moteur s'arrete**.

## Les 16 options observees

| Tag | Type | Role |
|---|---|---|
| `<Perso>` | booleen | **change la forme des callbacks appelees** -- voir `Fperso` ci-dessus |
| `<Privilege>` | numerique | privilege passe a `XmeListConsultDefProc` |
| `<Selection>` | booleen | **multiselection** de lignes |
| `<tri>` | booleen | tri par clic sur en-tete |
| `<TRI_AUTO>` | booleen | tri automatique |
| `<TRI_Conserve_courant>` | booleen | garde la ligne courante apres tri |
| `<couleur>` | booleen | coloration de lignes (active les callbacks `Couleur_*`) |
| `<RECHERCHE>` | booleen | fonction de recherche |
| `<RECHERCHE_TYPE>` | caractere | type de recherche (`'T'` observe) |
| `<Recherche_key>` | touche | touche d'ouverture de la recherche |
| `<recherche_key_s>` | touche | recherche suivante |
| `<recherche_key_p>` | touche | recherche precedente |
| `<CTRLF4>` / `<SCTRLF4>` | booleen | raccourcis de fermeture |
| `<Export>` | booleen | export |
| `<EXPORTTABLEUR>` | booleen | export tableur |
| `<FILTRE>` | booleen | filtre (active la callback `InitFiltre`) |

> **Cette liste est celle d'un ecran, pas la liste exhaustive de l'API.** Une option absente
> ici peut tres bien exister. Pour en chercher d'autres, la voie est le corpus : les options
> apparaissent litteralement dans le code, sous la forme `options &= '<...>'`.

## Ne pas se laisser piloter par les options

Un partenaire, cherchant a debloquer un tableau fige, a **bascule `<Selection>` de `true` a
`false` et retour** parmi une douzaine de tentatives -- la cause etait ailleurs (une callback
mal declaree). Les options changent le **comportement de l'interface** ; elles ne reparent
pas une signature.

Quand un tableau se comporte mal **sans message**, commencer par
[callbacks-catalogue.md](callbacks-catalogue.md) et
[pieges-execution.md](pieges-execution.md) -- pas par les options.

## Voir aussi

- [callbacks-catalogue.md](callbacks-catalogue.md) -- les callbacks, et la regle du suffixe
- [pieges-execution.md](pieges-execution.md) -- ce qui compile et casse au runtime
- [keywords-verifies.json](keywords-verifies.json) -- le releve date et ses limites
