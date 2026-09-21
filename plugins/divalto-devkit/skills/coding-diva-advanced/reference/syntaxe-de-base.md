# Syntaxe DIVA de base -- les faux amis et leur equivalent reel

> **Pourquoi cette page.** DIVA *ressemble* a BASIC, et le reflexe -- humain comme machine
> -- est de combler les manques avec l'analogie la plus proche. **DIVA diverge precisement
> a ces endroits**, de trois facons differentes : le mot n'existe pas (`EndFor`), il existe
> sous une autre **orthographe** (`Elsif`, pas `ElseIf`), ou il existe avec une autre
> **nature** (`Round`) voire un autre **sens** (`Continue`, `Break`). Le troisieme cas est
> le plus couteux : il compile.
>
> **Ne jamais conclure a l'inexistence sur une seule orthographe.** Cette page a d'abord
> affirme que `ElseIf` « n'existe pas » et conseille de contourner : la construction existe,
> elle s'ecrit `Elsif`. Les orthographes reellement testees sont consignees au releve.
>
> Chaque affirmation d'existence ou d'inexistence est **verifiee contre le graphe de
> connaissance** et consignee dans [keywords-verifies.json](keywords-verifies.json), avec
> son niveau de preuve. Rien ici n'est ecrit de memoire -- c'est la seule protection contre
> l'erreur que cette page corrige (voir « Le cas Round » ci-dessous).

## Contenu

- Les 4 boucles, leur terminateur, leur sortie et leur « continue »
- Faux amis : les **trois especes** (orthographe, nature, sens)
- Conditions : `If` / `Elsif` / `Else` / `Endif`
- `Switch` : la famille ou vivent `Continue` et `Break`
- **PIEGE** : on ne sort pas d'un `Switch` par un `Exit*` ni par un `Goto`
- **« Mot inconnu » ne veut presque jamais dire « absent de cette version »**
- Le cas `Round` -- pourquoi « ca n'existe pas » etait faux
- **Le booleen DIVA a trois etats** -- `NON = 1`, pas `0`
- Concatener : l'operateur est `&`
- **Champ TABLEAU** : indice obligatoire, entre parentheses
- `FReturn` / `PReturn` : deux instructions asymetriques
- Corps de fonction et de procedure, declaration des parametres
- Prototypes : `Proto` ... `EndProto`
- `Nature=A` : reservee aux parametres formels

---

## Les 4 boucles, leur terminateur, leur sortie et leur « continue »

DIVA a **quatre** structures d'iteration, et chacune a **son propre** jeu d'instructions.
Il n'y a **pas** de sortie ni de relance universelle. Et attention : `Break` et
`Continue` existent bien en DIVA, mais ils appartiennent a `Switch` -- ils ne pilotent
**pas** les boucles.

| Boucle | Terminateur | Sortie anticipee | « continue » |
|--------|-------------|------------------|--------------|
| `For <cpt> = <deb> To <fin> [Step <pas>]` | `Next` | `ExitFor` | `RedoFor` |
| `Loop <expression>` | `Endloop` | `ExitLoop` | `RedoLoop` |
| `Do [While <expr>]` (2 formes, voir ci-dessous) | `Wend` | `ExitDo` | `RedoDo` |
| `Repeat` | `Until <expr>` | `ExitRepeat` | `RedoRepeat` |

**Le tableau est regulier : 4 boucles x (sortie + continue).** Utiliser `ExitFor` dans un
`Loop`, ou `ExitLoop` dans un `For`, ne compile pas.

### Deux semantiques differentes derriere « continue »

- **`RedoFor`** branche au debut du `For` **et fait passer le compteur a la valeur
  suivante** -- c'est le vrai equivalent d'un `continue`.
- **`RedoLoop`** (et ses cousins) branche au debut de la boucle : il n'y a pas de compteur,
  la condition est simplement reevaluee. Une variable d'avancement modifiee dans le corps
  reste sous votre responsabilite -- sinon, boucle infinie.

### La seule boucle a test median : `Do` forme 2

`Do` a **deux** formes, et la seconde n'a d'equivalent dans aucune des trois autres
boucles :

```
Do While <expr>          ; forme 1 -- test en entree,
    <instructions>       ;   strictement equivalente a Loop / Endloop
Wend

Do                       ; forme 2 -- test AU MILIEU
    <instructions A>     ;   A s'execute toujours
While <expr>
    <instructions B>     ;   B ne s'execute que si <expr> est vraie
Wend
```

La forme 2 est l'outil naturel de la **lecture sequentielle** : lire, tester le code
retour, traiter. Sans elle, il faut dupliquer la lecture avant la boucle et en fin de
corps. `Loop` teste en entree, `Repeat` teste en sortie ; seul `Do` teste au milieu.

### Pieges du `For`

- `Next` **n'est PAS suivi du nom du compteur** (contrairement a VB).
- Autant de `Next` que de `For` imbriques.
- Un **pas negatif doit etre une constante**. Avec une variable negative, le test de fin de
  boucle genere par le compilateur est faux -- et rien ne le signale.
- Le compteur peut etre lu **et modifie** dans le corps de la boucle.

---

## Faux amis : trois especes, a ne pas confondre

Un « faux ami » n'est pas toujours un mot absent. Il y en a **trois especes**, et les
confondre produit de mauvais conseils :

1. **L'orthographe** -- la construction existe, sous un autre nom. Le pire cas : on croit
   devoir contourner alors qu'il suffit de corriger deux lettres.
2. **Le mot present, la nature differente** -- il existe, mais ce n'est pas ce qu'on croit
   (fonction vs instruction).
3. **Le mot present, le SENS different** -- le plus dangereux : il compile, et fait autre
   chose que ce qu'on attend.

| Ecrit par reflexe | Origine | Espece | Realite DIVA |
|---|---|---|---|
| `ElseIf` | VB | orthographe | **`Elsif` existe** (un seul « e »). Ne PAS imbriquer un `If` dans le `Else` : il suffit d'ecrire `Elsif`. |
| `EndFor` | Pascal / VBScript | absent | Le terminateur du `For` est `Next`. |
| `Str$(x)` | BASIC | orthographe | `Str$` **n'existe pas** : le suffixe `$` n'appartient pas au nom, la fonction est **`Str(x)`**, 1 parametre. Voir aussi `ToString`. |
| `Round(x)` | style fonction | **nature** | `Round` existe, mais comme **instruction de mode** sans parametre. Voir la section dediee. |
| `continue` (sens C) | C, Python | **SENS** | `Continue` **existe**, dans la famille `Switch` : il enchaine sur le `Case` **suivant**. Pour relancer une boucle, c'est `RedoFor` / `RedoLoop` / `RedoDo` / `RedoRepeat`. |
| `break` (sens C) | C, Python | **SENS** | `Break` **existe**, et sort du **`Switch`** -- pas d'une boucle. Pour sortir d'une boucle : `ExitFor` / `ExitLoop` / `ExitDo` / `ExitRepeat`. |
| `Exit` seul | C, VB | absent | Il n'y a pas de sortie universelle : `ExitFor`, `ExitLoop`, `ExitDo`, `ExitRepeat`. |
| `Redo` seul | -- | absent | Symetrique : `RedoFor`, `RedoLoop`, `RedoDo`, `RedoRepeat`. |
| `SplitCount` / `SplitItem` | autre ecosysteme | absent | DIVA decoupe une chaine en **un seul appel**, `SplitList`. Ce n'est pas un renommage : le modele differe (une liste construite, avec separateurs par paire, separateurs non rendus et gestion des quotes). Signature au graphe. |
| `Pos(...)` | BASIC / VB | orthographe | La recherche de position s'ecrit **`String`**. |
| `Len(...)` | BASIC / VB | orthographe | La longueur s'ecrit **`Length`**. |
| `String(n, c)` pour **fabriquer** | BASIC / VB | **SENS** | `String` existe et **cherche** : il rend une **position**. Il ne fabrique pas une chaine repetee. Et il n'a rien a voir avec **`Str`**, qui convertit un numerique en alphanumerique. |
| `Loop while <cond>` | autres langages | absent | `Loop` se termine par `EndLoop`. Le test **au milieu**, c'est `Do ... While ... Wend` -- la forme 2 du `Do`. |

### « Mot inconnu » ne veut presque jamais dire « absent de cette version »

C'est le reflexe qui coute le plus cher **apres** le faux ami lui-meme : le compilateur
refuse un nom, on travaille sur un pack ancien, et on en conclut que la fonction « n'existe
pas encore dans cette version ». On ecrit alors un contournement -- qui marche -- et on
retient une regle **fausse**.

**Le cas vecu.** Un partenaire compile sur un pack ancien et obtient « Mot inconnu » sur
`SplitCount`, `SplitItem`, `Pos`, `Len` et `Loop while`. Il conclut a un ecart entre versions
d'ERP, et demande un **tableau des fonctions chaine par version**. Verification faite : les
**cinq** sont des faux amis. Aucune n'a jamais existe sous ce nom, dans aucune version. Le
tableau demande aurait encode une **cause fausse** -- un lecteur sur un pack recent aurait
cru pouvoir ecrire `Pos`.

**Ce qui varie et ce qui ne varie pas.** Le **standard livre** (les modules, leurs fonctions
publiques, les dictionnaires) depend evidemment de la version de l'ERP. Les **mots-cles et
fonctions natives du langage**, non : ils appartiennent au langage, pas au pack. Une
disponibilite qui dependrait reellement de la version releverait du **compilateur/runtime**
livre avec le pack -- pas du numero de version de l'ERP.

**Le reflexe correct**, dans cet ordre :

1. **Chercher le vrai nom** avant tout : le graphe de connaissance repond en une requete, et
   les inexistences deja etablies sont dans [keywords-verifies.json](keywords-verifies.json),
   chacune avec l'equivalent reel a ecrire a la place.
2. **Essayer les orthographes plausibles** -- c'est la lecon de `Elsif` : conclure a
   l'inexistence sur une seule graphie est la faute la plus facile a commettre ici.
3. **Ne conclure a un ecart de version qu'en dernier**, et alors nommer ce qui varie
   (le compilateur), pas ce qu'on suppose (le numero d'ERP).

> Le contournement du partenaire, lui, etait **juste et verifie en production** :
> `String` + `Mid` + `Length` + une boucle `Repeat ... Until`. Ce n'est pas un pis-aller de
> vieille version -- **c'est la facon DIVA de faire**, avec `SplitList` quand un vrai
> decoupage est voulu.
>
> **Verifie au graphe le 2026-08-31**, et deux precisions que la forme observee ne montrait
> pas : la **longueur de `Mid` est OPTIONNELLE** -- `Mid(variable, position [, longueur])`,
> retour alphanumerique -- et `Mid` **peut se trouver a gauche d'une affectation**, il sert
> donc aussi a ecrire dans une sous-chaine, pas seulement a en extraire une. La famille
> compte six variantes typees : `Nmid` (numerique), `Bmid` (binaire), `Xmid` (16 bits),
> `Lmid` (32 bits), `Zmid` (= `Mid` avec les espaces remplaces par des zeros, utilise par les
> dates et heures) et `Znmid`.

---

> **`Continue` et `Break` sont les deux pieges les plus couteux de cette page** : ils
> compilent. Un `Break` ecrit dans une boucle pour en sortir, ou un `Continue` ecrit pour
> passer a l'iteration suivante, ne donnera pas une erreur -- il donnera un autre
> comportement.

---

## Conditions : `If` / `Elsif` / `Else` / `Endif`

```
If (expression1)
    <instructions1>
Elsif (expression2)          ; facultatif, chainable
    <instructions2>
Else                         ; facultatif
    <instructions3>
Endif                        ; OBLIGATOIRE
```

- **`Endif` est obligatoire**, et il en faut **autant que de `If` imbriques**.
- `Elsif` s'ecrit avec **un seul « e »**. `ElseIf` (VB) ne compile pas.
- Ne pas confondre avec les **pseudo-instructions** `/If` `/Else` `/Endif`, qui font de la
  **compilation conditionnelle** (couplees a `/Value`) : ce n'est pas la meme chose.
- Pour un test simple, la fonction **`Condition(expression, valeur_si_vrai, valeur_si_faux)`**
  remplace quatre lignes. Les deux valeurs doivent etre de **meme type**.

---

## `Switch` : la famille ou vivent `Continue` et `Break`

```
Switch <selecteur>
Case <expression1>
    <instructions>
    [ RedoSwitch ]           ; rebranche sur Switch, selecteur REEVALUE
    [ Continue ]             ; enchaine sur le Case SUIVANT
    [ Break ]                ; sort du Switch
Case <expression2>
    <instructions>
[ Default                    ; facultatif
    <instructions> ]
Endswitch                    ; OBLIGATOIRE
```

`Case` accepte une **constante**, une **variable**, ou une **expression de test** (si elle
contient un operateur de test, elle est evaluee telle quelle, sans tenir compte du
selecteur).

**Deux variantes** : `Switch2` n'accepte que des **constantes** en selection, et son
branchement est a temps constant quel que soit le nombre de cas -- c'est la forme rapide.
`SwitchString` traite un selecteur **alpha**.

### PIEGE -- on ne sort pas d'un `Switch` par un `Exit*` ni par un `Goto`

La documentation avertit : « **la valeur du selecteur est empilee. Il ne faut jamais sortir
de la structure par un GOTO ni par un EXIT.** » Le mot « EXIT » y designe bien la **famille
`Exit*`** : `ExitFor`, `ExitLoop`, `ExitDo`, `ExitRepeat`.

**C'est le piege le plus facile a ecrire de cette page**, parce que le motif est le plus
naturel qui soit : boucler, tester, sortir des qu'on a trouve.

```
; A NE PAS FAIRE -- ExitFor traverse le Switch et laisse le selecteur sur la pile
For i = 1 To n
    Switch <selecteur>
    Case <cas trouve>
        ExitFor                  ; <-- INTERDIT
    Endswitch
Next
```

La sortie de boucle doit se faire **apres `Endswitch`**. On quitte le `Switch` par `Break`,
et on teste ensuite :

```
For i = 1 To n
    Switch <selecteur>
    Case <cas trouve>
        vIndex = i
        Break                    ; sort du Switch, PAS de la boucle
    Endswitch
    If (vIndex <> 0)
        ExitFor                  ; la sortie de boucle se fait ICI, hors du Switch
    Endif
Next
```

Meme regle pour `Goto` -- qui, par ailleurs, ne peut de toute facon pas sortir d'une
fonction ou d'une procedure : ses etiquettes y sont **locales**.

---

## Le cas `Round` -- pourquoi « ca n'existe pas » etait faux

Un RETEX signalait que `Round()` etait propose dans du code genere « alors qu'il n'existe
pas en Diva procedural ». **La moitie de l'affirmation etait fausse**, et l'ecrire telle
quelle aurait fait rejeter du code correct.

`Round` **existe** -- comme **instruction de mode, sans parametre** :

> A partir de l'execution d'une instruction `Round`, les affectations se font avec arrondi.
> C'est le mode par defaut au lancement du programme. `Truncate` permet de passer en
> troncature.

Ce qui n'existe pas, c'est la **fonction** `Round(x)` qui rendrait une valeur arrondie.

### Comment arrondir, alors

Par l'**indicateur porte par l'affectation** :

```
[ A ]   variable = expression       ; A = arrondi (defaut)
[ T ]   variable = expression       ; T = tronque
[ S ]   variable = expression       ; S = arrondi a la valeur superieure
```

Ces indicateurs sont **prioritaires** sur le mode global defini par `Round` / `Truncate`.

> **Recommandation : preferer l'indicateur au mode global.** `Round` et `Truncate` fixent un
> mode « **a partir de l'execution** de l'instruction ». **Jusqu'ou ce mode porte n'est pas
> documente** -- survit-il au retour d'une procedure appelee, d'un module ? Nous ne le savons
> pas, et la question a ete posee sans reponse (cf. `non_verifie` dans
> [keywords-verifies.json](keywords-verifies.json)).
>
> Consequence pratique : **utiliser l'indicateur porte par l'affectation**, dont la portee
> est locale et certaine. Un `Truncate` pose dans une procedure partagee pourrait changer
> silencieusement l'arrondi de tout ce qui s'execute ensuite -- des montants *presque* justes,
> et un defaut introuvable.

### L'affectation numerique porte aussi un traitement du debordement

La forme complete de l'affectation numerique ne s'arrete pas a l'indicateur :

```
[ A ] variable_receptrice = expression [ <etiquette_ovf> ]
```

- `<etiquette_ovf>` provoque un **branchement** en cas de **depassement de capacite**.
- **Contrainte** : si l'etiquette de debordement est fournie, elle doit **obligatoirement
  etre precedee de l'indicateur d'arrondi**. On ne peut donc pas ecrire l'etiquette seule.
- `SharpOnOverflow` demande, lui, que la variable receptrice soit **garnie de `#`** en cas
  de debordement.

> **Piege du transfert alphanumerique**, dans la meme page de documentation : mettre a
> espace une donnee **structuree** qui ne contient ni type `X` ni binaire met a espace les
> zones alphanumeriques **et a zero les numeriques**. Les variables numeriques contiennent
> alors des espaces, mais **leur valeur est nulle** -- deux representations pour la meme
> chose, et c'est la valeur qui compte.

> **La lecon depasse `Round`.** Une affirmation d'inexistence est une affirmation comme une
> autre : elle se verifie. C'est pour cela que cette page s'appuie sur un releve date plutot
> que sur la memoire.

---

## Le booleen DIVA a TROIS etats -- et `NON` ne vaut pas `0`

C'est un piege de **donnee**, pas de syntaxe : il ne produit aucune erreur de compilation, et
le code se trompe silencieusement d'un etat.

| Etat | Champ numerique | Champ alphanumerique |
|---|---|---|
| **non renseigne** | `0` | espace |
| **NON** | **`1`** | `1` |
| **OUI** | **`2`** | `2` |

**Le reflexe faux** est d'ecrire un test a zero pour dire « non » :

```
; FAUX -- teste « non renseigne », pas « non »
If MonRecord.MonFlag = 0
    ; ... on croit traiter les « non », on traite les champs jamais garnis
Endif

; JUSTE
If MonRecord.MonFlag = Non
    ; ...
Endif
```

**Ecrire les constantes nommees `Oui` / `Non`, pas les litteraux `2` / `1`.** C'est ce que fait
le standard -- voir `Initialiser_CaseACocher(<champ>, Non)` dans
[module-table.md](module-table.md). Un litteral est juste aujourd'hui et fragile pour rien.

> **Mesure (2026-08-30, base X.13).** Sur les **905** colonnes de drapeau numeriques :
> **40** portent `0`, `1` **et** `2` **dans la meme colonne** -- ce sont donc trois etats
> distincts, et `0` ne peut pas etre `NON`. Le motif dominant du drapeau correctement garni
> est **`{1, 2}`** : **143** colonnes. Sur les **29** drapeaux alphanumeriques d'un caractere,
> les valeurs sont `1`, `2` et l'espace -- **`0` n'apparait jamais**, l'espace y tenant le
> role du zero.
>
> **Ce que la mesure ne dit pas** : elle porte sur des **donnees stockees**, pas sur la
> declaration des constantes. La correspondance est deduite, coherente sur deux typages
> independants.
>
> **CONFIRME AU GRAPHE le 2026-08-31.** `Non` est declaree dans **71** programmes du
> standard, toujours a **`1`** ; `Oui` dans **81**, toujours a **`2`**. Aucune variation :
> pas un seul programme ne leur donne une autre valeur. La mesure en base et la declaration
> concordent.

### Piege : `Oui` / `Non` ne sont PAS des constantes du langage

Le graphe est net sur leur nature : ce sont des **constantes declarees au niveau de chaque
programme**, pas des mots-cles du langage. Elles sont presentes dans 71 et 81 programmes du
standard **parce que chacun les declare** (ou inclut ce qui les declare) -- et non parce que
le langage les fournirait.

**Consequence pour du specifique** : ecrire `Oui` ou `Non` dans votre propre module donne
**« Mot inconnu »** tant que ce module ne les declare pas. Ce n'est pas un ecart de version,
c'est une declaration manquante -- exactement le meme piege que la section precedente, avec
un nom qui a l'air standard parce qu'il l'est **ailleurs**.

Deux sorties, et la premiere est preferable : declarer les deux constantes dans votre module
(ou son include commun), ou -- a defaut -- ecrire les litteraux `2` / `1` en assumant la
fragilite.

> **Correction du 2026-08-30.** Ce skill affirmait `NON = 0` et « etat intermediaire = 1 ».
> **Les deux etaient faux** : `1` **est** le non, et le troisieme etat est le zero (ou
> l'espace), c'est-a-dire l'absence de saisie. L'affirmation ne vivait que dans le SKILL.md
> et dans une eval -- **aucune page de reference ne portait la regle**, donc rien ne la
> confrontait. C'est le RETEX qui avait raison.

---

## Concatener : l'operateur est `&`

Ni `+`, ni des crochets. Le message de compilation est **trompeur** :

```
Parenthese attendue apres un nom de fonction
```

Le compilateur a vu un identifiant suivi d'un delimiteur qu'il n'attendait pas ; il parle donc
de parenthese manquante, pas de concatenation. **Le message ne nomme jamais la vraie cause.**

```
; FAUX -- reflexes venus d'ailleurs
resultat = 'texte' + variable
resultat = ['texte', variable]

; JUSTE
resultat = 'texte' & variable & 'texte'
```

Le standard l'ecrit ainsi partout -- par exemple `Version_ERP_UX & ' ' & Indice_ERP_UX` dans
la procedure d'entree d'un module de domaine.

---

## Un champ TABLEAU s'accede avec un indice, entre PARENTHESES

Ecrire un champ multi-occurrence sans son indice donne :

```
Tableau sans parenthese
```

```
; FAUX -- champ multi-occurrence lu comme un scalaire
MonRecord.AdrTiers = <valeur>

; FAUX -- les crochets ne sont pas l'indexation DIVA
MonRecord.AdrTiers[4] = <valeur>

; JUSTE
MonRecord.AdrTiers(4) = <valeur>
```

**L'indice peut etre une variable**, pas seulement un litteral : le standard ecrit
`WMSOC.ActionCod(NumAction)`.

### Le piege : le MEME nom peut etre tableau ici et scalaire ailleurs

C'est ce qui rend l'erreur si facile a commettre -- on a vu le champ ecrit sans indice
quelque part, et on reproduit.

> **Mesure (2026-08-30, base X.13).** Sur **49 735** colonnes, **10 827** appartiennent a un
> champ multi-occurrence, soit **1 029** champs tableau portes par **615** noms distincts.
> Et **148 de ces 615 noms** designent un tableau dans un enregistrement **et un scalaire
> dans un autre**. Le nombre d'occurrences est le plus souvent petit -- 3, 2, 4, 5 ou 6 --
> avec une queue jusqu'a 40.
>
> Mesure faite sur la **projection SQL** : un champ multi-occurrence y apparait en colonnes
> `<CHAMP>_0001` ... `<CHAMP>_000N`. La correspondance avec la declaration DIVA est deduite
> de cette forme, pas lue dans le dictionnaire.

**Donc : ne jamais decider d'apres un autre programme sans verifier l'enregistrement.** Deux
moyens :

1. **Le dictionnaire** -- un champ tableau porte une `Nature` avec `*` (`X*N`, `20*3`...).
   C'est le domaine du skill managing-diva-dictionaries, qui documente la taxonomie et
   signale le suffixe `Tb`.
2. **Un usage existant du meme domaine** -- c'est aussi la seule facon de connaitre la
   **semantique de l'indice**, qui ne se devine pas. Un partenaire a ainsi etabli qu'une
   position donnee du bloc d'adresses correspondait a l'adresse de livraison, en la lisant
   dans un autre programme du meme domaine.

> **L'indice porte du metier, pas un rang arbitraire.** Aucune convention generale ne dit ce
> que vaut `(4)` : cela depend du champ. Le chercher, ne pas le supposer.

---

## `FReturn` / `PReturn` : deux instructions asymetriques

Ce ne sont pas deux variantes du meme mot. **Leurs contrats different sur trois points** :

| | `FReturn` (Function) | `PReturn` (Procedure) |
|---|---|---|
| Parametre | **oui** -- la valeur de retour | **aucun** |
| Obligatoire ? | **OUI** | **non**, facultatif |
| Si absent | le programme est **INTERROMPU a l'execution** | retour normal en fin de procedure |

Le point le plus dangereux : l'absence de `FReturn` dans une `Function` n'est **pas** une
erreur de compilation. Elle passe le compilateur et casse **a l'execution**. Il peut y
avoir plusieurs `FReturn` dans une meme fonction.

Et le mot-cle suit la nature de l'objet : `FReturn` dans une `Function`, `PReturn` dans une
`Procedure` -- les intervertir ne compile pas.

---

## Corps de fonction et de procedure, declaration des parametres

Le corps est encadre par une paire **qui depend elle aussi de la nature** :

| | Ouverture | Fermeture |
|---|---|---|
| `Procedure` | `Beginp` | `Endp` |
| `Function` | `Beginf` | `Endf` |

Les **parametres se declarent sur des lignes separees**, apres la signature, au format
`<niveau> <nom> <Nature>` :

```
Procedure AfficheMessage(mess)
1 mess A
Beginp
    MessageBox(mess, " ")
Endp

Function int Carre(i)
1 i 24,10
Beginf
    i = i * i
    Freturn (i)
Endf
```

La signature ne porte donc **que les noms** ; les types vivent dans les lignes de
declaration qui suivent.

---

## Prototypes : `Proto` ... `EndProto`

Un prototype permet d'**appeler une fonction avant qu'elle soit definie**. Il resout les
problemes d'ordre des fonctions dans les sources et autorise les **references croisees**
dans un meme module.

```
Proto Procedure <nom> [ ( p1, ..., pn ) ]
<declaration des parametres formels>
EndProto

Proto Function <type_retour> <nom> [ ( p1, ..., pn ) ]
<declaration des parametres formels>
EndProto
```

**La declaration d'un prototype est identique a celle de la fonction ou de la procedure
elle-meme.** Deux consequences, et ce sont les deux pieges :

1. Le mot-cle `Function` ou `Procedure` doit etre **precede de `Proto`**.
2. La declaration des parametres formels doit **se terminer par `EndProto`** -- il est
   **obligatoire**.

Autrement dit, un prototype reprend les **lignes de declaration** des parametres (`1 mess A`),
pas seulement leurs noms dans la signature : c'est la meme regle que pour la fonction, et
c'est ce que la signature seule ne porte pas.

```
Proto Function int Carre(i)
1 i 24,10
EndProto
```

---

## `Nature=A` : reservee aux parametres formels

Dans l'exemple ci-dessus, `1 mess A` declare un parametre de Nature `A` : alphanumerique
**de taille non fixee**, la taille reelle etant celle de la donnee passee par l'appelant.

**C'est justement pour cela que `Nature=A` n'a de sens que sur un parametre formel.** Une
variable locale declaree en `A` n'a aucune taille a heriter. Un patch reel a du remplacer
**11 declarations** de ce type par des Natures dimensionnees pour compiler.

Regle : `A` en parametre, une Nature **dimensionnee** partout ailleurs.

---

## Voir aussi

- [keywords-verifies.json](keywords-verifies.json) -- le releve, sa date, sa source et le
  niveau de preuve de chaque entree
- [overwrite-pattern.md](overwrite-pattern.md) -- surcharge, visibilite, `standard.<Proc>`
- [recordsql-advanced.md](recordsql-advanced.md) -- RecordSql, Reader, conditions
