# `XmeSetAttribut` -- modification dynamique des attributs d'un composant

## Contenu

- Pourquoi cette page
- Signature et principe
- Le couple `noms=<id_logique>` + `XmeSetAttribut("<id_logique>", ...)`
- Regle de groupement
- Liste des attributs `AN_*` modifiables
- Valeurs de visibilite `AV_*`
- Cas d'usage critique -- masquer un composant standard en surcharge
- Cas particuliers
- Reaffichage
- Variante tableau
- **Masquer une COLONNE de tableau** -- deux contextes a ne pas confondre
- Sources

---

## Pourquoi cette page

La fonction DIVA `XmeSetAttribut(noms, attribut, valeur)` permet de **modifier dynamiquement (a l'execution)** l'apparence et le comportement d'un composant d'un masque -- visibilite, taille, couleur, bordure, etc. Elle est cruciale pour :

1. **Masquer proprement un composant standard** en surcharge masque (alternative a la suppression du bloc dans le `.dhsf` user)
2. **Conditionner l'UI** selon le profil utilisateur, le contexte metier, le mode d'appel
3. **Grouper des modifications** : un seul appel peut piloter plusieurs composants

Couple avec [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md), c'est la mecanique runtime privilegiee pour ajuster un masque sans toucher a la structure statique du standard.

---

## Signature et principe

```diva
XmeSetAttribut(Nom_des_objets, Attribut, Valeur)
```

- `Nom_des_objets` : chaine. Identifiant logique declare dans la propriete `[presentation].noms=<id_logique>` d'un ou plusieurs composants.
- `Attribut` : constante `AN_<X>` (cf. liste ci-dessous) -- quel attribut modifier.
- `Valeur` : valeur cible -- soit constante symbolique (`AV_CACHE`, `AV_GRISE`, ...) soit valeur numerique selon l'attribut (taille, position, bitmap, ...).

La modification est **persistante** durant toute la duree de vie du programme, jusqu'a `XmeResetAttribut(noms, attribut)`.

Inverse : `XmeResetAttribut(noms, attribut)` annule la modification et restaure la valeur statique du masque.

---

## Le couple `noms=<id_logique>` + `XmeSetAttribut("<id_logique>", ...)`

Le mecanisme repose sur un **nom logique** declare dans le composant du `.dhsf` et consomme par le code DIVA :

```ini
[champ]
[presentation]
id=51
noms="Currencycod"            ; <-- nom logique
[description]
donnee=devise,currencycod,devise_sel
```

```diva
[diva]
...
Procedure ZoomDebut
BeginP
    Standard.ZoomDebut()
    switch g7.ZoomPar
        case C_Pilote_Creation
            Devise_Sel.CurrencyCod = G3XZ.CurrencyCod
            XmeSetAttribut("Currencycod", AN_VISIBILITE, AV_GRISE)
    endswitch
EndP
```

Au runtime, si le zoom Devise est appele en mode "creation pilotee", le champ id=51 est **grise** pour empecher la modification.

**Cle de robustesse** : un composant sans `noms=` n'est pas modifiable via `XmeSetAttribut`. Pour piloter dynamiquement un composant, il faut **systematiquement** lui donner un `noms=`.

### Conventions

- Casse insensible (cf. [diva-case-sensitivity.md](diva-case-sensitivity.md))
- Separateurs `;` ou `,` pour multi-noms
- Un meme composant peut avoir plusieurs noms (separes par `;` ou `,`) -> appartenance a plusieurs "familles"
- Plusieurs composants peuvent partager le meme `noms=` -> ciblage groupe

---

## Regle de groupement

> **Plusieurs objets peuvent partager la MEME valeur de `noms=`**, ce qui permet de les masquer / griser / restaurer **tous en un seul appel `XmeSetAttribut`**. Reciproquement, un objet peut avoir plusieurs noms (separes par `;` ou `,`) -> appartenance a plusieurs "familles" -> chaque famille suffit a le cibler.

Pattern typique : pour grouper visuellement un ensemble de composants lies fonctionnellement (champs d'un mode "creation rapide", options reservees admin, tous les champs d'un volet specifique), donner le **meme `noms=`** a tous, puis **un seul** `XmeSetAttribut` les pilote tous en lot.

Cette mecanique evite la duplication de code et est privilegiee pour les operations groupees.

### Granularite fine

Si deux composants pointent la meme donnee DIVA mais que seul l'un doit etre modifie dynamiquement, leur donner des `noms=` distincts (ou ne donner `noms=` qu'au composant cible). Exemple observe : sur `gtez047_sql.dhsf`, le champ `currencycod` id=51 (popup creation) a `noms="Currencycod"` ; le second champ `currencycod` id=47 (fiche detaillee) n'a PAS de `noms=` -> il n'est pas affecte par `XmeSetAttribut("Currencycod", ...)`.

---

## Liste des attributs `AN_*` modifiables

Constantes definies dans `Zdiva` (incluses systematiquement via `Include "zdiva.dhsp"`) :

### Position / taille

| Constante | Code | Effet |
|-----------|------|-------|
| `AN_POSITION_X` | 1 | Position horizontale |
| `AN_POSITION_Y` | 2 | Position verticale |
| `AN_TAILLE_X` | 3 | Largeur |
| `AN_TAILLE_Y` | 4 | Hauteur |
| `AN_TAILLE_SAISIE` | 30 | Taille de saisie d'un champ |

### Style

| Constante | Code | Effet |
|-----------|------|-------|
| `AN_POLICE` | 5 | Police |
| `AN_COULEUR` | 6 | Couleur du texte |
| `AN_COULEUR_FOND` | 7 | Couleur de fond |
| `AN_COULEUR_FOND_GROUPE` | 32 | Couleur de fond d'un groupe |
| `AN_BORDURE` | 8 | Bordure |
| `AN_STYLE` | 26 | Style global (regroupe POLICE+COULEUR_FOND+BORDURE) |
| `AN_EPAISSEUR` | 13 | Epaisseur de trait |
| `AN_ARRONDI` | 14 | Arrondi des coins |
| `AN_ANGLE` | 9 | Angle (rotation) |

### Texte

| Constante | Code | Effet |
|-----------|------|-------|
| `AN_TITRE` | 16 | Texte affiche |
| `AN_BULLE` | 19 | Texte d'info-bulle |
| `AN_CADRAGE_TEXTE` | 10 | Alignement du texte |
| `AN_CADRAGE_BOUTON` | 15 | Alignement bouton |
| `AN_CODE_PAGE` | 31 | Code page de l'affichage |
| `AN_LARGEUR_RICH_TEXT` | 18 | Largeur d'un rich-text |

### Image / bouton

| Constante | Code | Effet |
|-----------|------|-------|
| `AN_BITMAP` | 17 | Image (cf. composants bitmap_constante / bitmap_variable) |
| `AN_BOUTON` | 27 | Bouton (regroupe BITMAP + POLICE + BULLE + ...) |
| `AN_BITMAPS_ET_TITRE` | 28 | Combinaison image+titre |
| `AN_SURVOL_BITMAP` | 22 | Image au survol |
| `AN_SURVOL_CURSEUR` | 23 | Curseur au survol |
| `AN_SURVOL_SON` | 24 | Son au survol |
| `AN_CLIC_SON` | 25 | Son au clic |

### Saisie

| Constante | Code | Effet |
|-----------|------|-------|
| `AN_HALO_CHAMP_OBLIGATOIRE` | 33 | Halo "champ obligatoire" |
| `AN_TABLE_ASSOCIEE` | 34 | Table associee au champ |

### Visibilite (le plus important pour la surcharge)

| Constante | Code | Effet |
|-----------|------|-------|
| **`AN_VISIBILITE`** | **20** | **Cle pour cacher / griser / restaurer -- cf. valeurs ci-dessous** |

### Special

| Constante | Code | Effet |
|-----------|------|-------|
| `AN_TOUS_ATTRIBUTS` | 0 | Tous attributs (utilise par `XmeResetAttribut` pour tout restaurer) |

> **`AN_STYLE` et `AN_BOUTON`** sont des attributs composes. Regle "le dernier a gagne" en cas de modifs combinees (ex: `XmeSetAttribut("X", AN_STYLE, ...)` puis `XmeSetAttribut("X", AN_POLICE, ...)` -- la police prend priorite).

---

## Valeurs de visibilite `AV_*`

Constantes `AV_*` pour l'attribut `AN_VISIBILITE` :

| Constante | Code | Effet runtime |
|-----------|------|---------------|
| `AV_VISIBLE` | 0 | Visible et interactif (defaut) |
| `AV_GRISE` | 1 | Apparent mais non cliquable / saisissable |
| `AV_ILLISIBLE` | 2 | Lecture seule -- texte/champ en AFFICHAGE uniquement |
| `AV_CACHE` | 3 | N'apparait plus du tout a l'ecran |

### Restrictions par type

`AV_ILLISIBLE` n'est pas applicable a :

- Bitmaps (`bitmap_constante`, `bitmap_variable`)
- Cadres (`cadre`)
- Boutons
- Cases a cocher
- Multi-choix en saisie
- Onglets
- Radio-boutons
- Rich-text
- Champs caches

Pour ces types, utiliser `AV_VISIBLE` / `AV_CACHE` uniquement.

### Cas multi-choix

`AV_VISIBLE` / `AV_CACHE` peuvent etre appliques aux **choix individuels** d'un multi-choix (masquage selectif d'entrees d'une liste).

---

## Cas d'usage critique -- masquer un composant standard en surcharge

C'est la **bonne pratique** pour faire disparaitre un composant standard d'un masque en surcharge, **sans le supprimer du fichier**. Procedure :

### Etape 1 -- dans le `.dhsf` user

Editer en place le bloc du composant standard a cacher. Ajouter dans `[presentation]` :

```ini
[champ]
[presentation]
id=42                                  ; <-- id standard preserve
noms="cache_<nom_logique>"             ; <-- nouveau nom logique
[description]
...
```

L'id standard est preserve (l'unicite des ids dans le masque reste assuree).

### Etape 2 -- dans la section `[diva]` (ou `[diva_base]`) du `.dhsf` user

Au point de traitement approprie (avant_saisie_page, init_module, etc.), appeler :

```diva
XmeSetAttribut("cache_<nom_logique>", AN_VISIBILITE, AV_CACHE)
```

### Avantages vs suppression du bloc

- Le composant **reste present** dans le fichier -> coherence preservee avec l'evolution du standard. Le compagnon `_base.dhsf` peut detecter les divergences si le standard change.
- **Reactivable dynamiquement** : `XmeResetAttribut("cache_<nom_logique>", AN_VISIBILITE)` ou changement contextuel.
- **Conditionnable** : on peut masquer selon profil utilisateur, contexte metier, etc.
- **Pattern conforme** a la mecanique Divalto native (pas un hack).

Voir [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md) pour le workflow complet de surcharge masque.

---

## Cas particuliers

### Objets reproduits plusieurs fois (offsets)

Si une page Xwin est affichee plusieurs fois avec differents offsets, concatener `$L$$C$` au nom dans le masque :

```ini
[champ]
[presentation]
noms="<nom_logique>$L$$C$"
```

Puis passer un nom forme avec les offsets au format `LLLCCC` (3 chiffres ligne + 3 chiffres colonne) :

```diva
XmeSetAttribut("<nom_logique>" & FormatNum(lig, 3) & FormatNum(col, 3), AN_VISIBILITE, AV_CACHE)
```

### Boutons de barre d'outils

Les boutons de barre d'outils **NE sont PAS** concernes par `XmeSetAttribut`. Pour les griser, utiliser :

```diva
XmeToolbarEnableButton(<id_bouton>, <oui_non>)
```

---

## Reaffichage

Apres `XmeSetAttribut`, l'objet n'est **pas automatiquement reaffiche** s'il est deja a l'ecran. Reaffichage automatique au retour d'une sequence de traitement, lors d'un `Xme(List)Next`, d'un `XmeRet` ou d'une entree clavier.

Sinon, forcer le reaffichage explicitement :

| Cas | Fonction |
|-----|----------|
| Reaffichage d'un masque "fiche" | `XmeDispv(<nom_masque>)` ou `XmeConsult(<nom_masque>)` |
| Reaffichage d'un masque "liste" | `XmeListDisplay(<nom_masque>)` ou `XmeListConsult(<nom_masque>)` |

---

## Variante tableau

Pour modifier les attributs d'une **ligne ou cellule isolee** d'un tableau (et non d'une colonne complete), utiliser :

```diva
XmeListSetAttribut(<noms_logique>, <ligne>, <attribut>, <valeur>)
```

`XmeListResetAttribut` est l'inverse (restauration).

---

## Masquer une COLONNE de tableau -- deux contextes a ne pas confondre

Masquer conditionnellement une **colonne entiere** ne se fait pas de la meme facon selon qui
pilote le tableau. Confondre les deux coute une demi-journee : le code ecrit compile, et **la
procedure n'est simplement jamais appelee**.

| Contexte | Comment obtenir l'identifiant du tableau | Ou brancher le traitement |
|---|---|---|
| **Zoom SQL** | `Zoom.Idtableau` | la procedure `ZoomEnteteTableau` du module de traitements |
| **Programme protege ou custom, hors Zoom SQL** | **`XmeListGetId(...)`** | un traitement « avant affichage » dans une **surcharge du masque** |

> **`ZoomEnteteTableau` n'est appelee que par le moteur Zoom SQL.** Un programme protege qui
> gere son propre tableau ne la declenche **jamais** -- l'implementer n'y produit aucun effet,
> et aucune erreur.

**Mesure sur le corpus du standard**, qui separe nettement les deux mondes :

| | |
|---|---|
| Programmes appelant `ZoomEnteteTableau` | **718** -- et **718 sur 718** portent le `z` de la convention de nommage des zooms |
| Programmes appelant `XmeListGetId` | **119**, dont **93 sans aucun `z`** dans leur nom |
| Programmes a `XmeListGetId` **sans** `Zoom.Idtableau` | **106 sur 119**, soit **89 %** |
| Programmes ou les deux mondes se croisent | **13** |

`Zoom.Idtableau` n'est pas disponible hors contexte Zoom SQL : c'est ce qui rend
`XmeListGetId` necessaire.

### `XmeListGetId` prend QUATRE arguments

```
XmeListGetId(<cleMasque>, <n>, '<NomDuTableau>', <idRetourne>)
```

**Le nom du tableau est le 3e argument, pas le 1er.** Mesure sur **132 appels** du standard :
**131 en passent quatre** ; le 1er est une **cle de masque** (`MZ.*` 86 fois, `Zoom.*` 29,
`HQL.*` 9, `Harmony.*` 4), et le 3e est le nom du tableau -- litteral dans 108 cas.

> Ecrire `XmeListGetId('<NomDuTableau>')` produit une erreur de nombre de parametres.

### La colonne se designe par son NUMERO, jamais par son nom

```diva
XmeListGetColumn(<idTableau>, <noColonne>, <COLUMNINFO>)
; ... modifier le champ voulu de COLUMNINFO ...
XmeListSetColumn(<idTableau>, <noColonne>, <COLUMNINFO>)
```

Sur **103 appels** du standard, le 2e argument est **toujours un numero** -- 38 litteraux,
65 variables -- et **jamais un nom**. Il n'existe aucune fonction de correspondance nom vers
numero.

> **Ce numero est un ordinal fige a la compilation dans Xwin.** Il est stable tant que l'ordre
> des colonnes n'est pas modifie -- et **change silencieusement** si on l'est. Le determiner une
> fois dans Xwin, puis **l'ecrire en commentaire a cote de l'appel** : c'est la seule trace qui
> survivra a une reorganisation.

### Le champ a modifier

`COLUMNINFO` est un enregistrement du dictionnaire systeme `ddsys.dhsd`. Il porte **40 champs**,
dont deux qui touchent a l'affichage et **qu'il ne faut pas confondre** :

| Champ | |
|---|---|
| `Affichage` | celui que vise ce cas d'usage |
| `Visibilite` | **un autre champ**, distinct |

Les champs de `COLUMNINFO` que le standard emploie reellement sont d'un tout autre ordre :
`Libelle` (133 usages), `Nomdonnee` (49), `Bulle` (42), `Bitmap1` (25), `Indices` (5),
`Sequence` (1).

> **Ce qui n'est PAS etabli : les VALEURS a affecter.** Un retour terrain nomme
> `AFFCOL_NON` et `AFFCOL_JAMAIS`. Ces constantes n'apparaissent **nulle part** -- ni dans les
> **8 022** sources livrees du pack (`.dhsp`, `.dhsi`, `.dhsq`, `.dhsf`), ni dans le repertoire
> systeme. Elles sont vraisemblablement declarees dans un module **compile** dont la source
> n'est pas livree, comme d'autres constantes du socle. **Le champ `Affichage`, lui, existe
> bien** -- verifie dans `ddsys.dhsd`. Interroger le graphe de connaissance avant de s'appuyer
> sur les noms de valeurs.

### La demarche complete, en contexte non-Zoom

1. Creer une **surcharge du masque** (`<base>u.dhsf`).
2. Y ajouter un traitement **« avant affichage »** sur la page qui porte le tableau.
3. Dans ce traitement, `XmeListGetId(<cleMasque>, <n>, '<NomDuTableau>', <id>)`.
4. `XmeListGetColumn(<id>, <noColonne>, <COLUMNINFO>)`.
5. Modifier `COLUMNINFO.Affichage`, puis `XmeListSetColumn(<id>, <noColonne>, <COLUMNINFO>)`.

Les etapes **1 a 4 sont mesurees** sur le standard. L'etape **5 vient d'un retour terrain** : le
champ est confirme, les valeurs ne le sont pas.

---

## Sources

Documentation officielle Divalto (chemin standard ERP) :

- `<CHEMIN_ERP_STANDARD>/sys/ymeg.chm` -- manuel "Ywpf - Executeur de masque d'ecran"
  - `XmeSetAttribut.htm` -- signature complete, tableau attributs, exemples
  - `XmeResetAttribut.htm` -- annulation
  - `XmeListSetAttribut.htm` / `XmeListResetAttribut.htm` -- variantes tableau
  - `Modificationdesattributsd_affichagedesobjets.htm` -- cas particuliers offsets
- `<CHEMIN_ERP_STANDARD>/sys/xwin-ecran.chm`
  - `Attributsdynamiques.htm` -- vue cote masque
  - `Visibilité_des_onglets.htm` -- cas onglets
- `<CHEMIN_ERP_STANDARD>/sys/ymeg2.chm`
  - `Visibilité_d_un_groupe_d_onglets.htm` -- cas groupes d'onglets

Constantes `AN_*` et `AV_*` definies dans `Zdiva` (`Include "zdiva.dhsp"`).
