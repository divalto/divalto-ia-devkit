# A5PMTAB -- les pieges qui compilent

> **Ce qui fait le cout de ces defauts** : aucun ne produit d'erreur de compilation, et
> aucun ne produit de message a l'execution. On observe seulement **un ecran qui se comporte
> mal** -- une ligne qu'on ne peut plus selectionner, un tableau fige, un programme qui ne
> repond plus. Le diagnostic par tatonnement coute des heures : un RETEX rapporte une
> vingtaine d'iterations de compilation, un autre une douzaine de corrections sans rapport
> avec la cause.
>
> **La regle generale** : quand un tableau A5PMTAB se comporte mal **sans message**,
> soupconner d'abord la **declaration d'une callback**, jamais les options d'affichage.
>
> **Et le fait le plus couteux de tous** : la valeur de retour d'une callback. `0` signifie
> « je gere cet evenement moi-meme, **ne fais rien** » -- navigation et sortie comprises.
> `1` signifie « laisse A5PMTAB faire son traitement normal ». **`1` est le repli.** Voir le
> piege 4.

## 1. `Fperso` change la forme des callbacks appelees

**Le piege** : un ecran mono-tableau fonctionne avec des callbacks **non suffixees**. On
ajoute un second tableau et on reutilise les memes hooks.

**Ce qui se passe** : la forme que A5PMTAB appelle est decidee par **`Fperso`**, tableau par
tableau -- `Fperso = <vrai>` avec `Nom = '<X>'` fait appeler `DefProcInterro_<X>_*`, **qui ne
recoit pas `Id`**. Si la forme declaree n'est pas celle appelee, le compte de parametres ne
correspond plus.

**Le message, si vous avez la chance de l'avoir** :

> *« Nombre de parametres errone lors de l'appel de DEFPROCINTERRO_APRES : la fonction attend
> 0 parametre(s) et l'appelant a place 1 parametre(s) sur la pile »*

**Le point qui manque a tout le monde** : **le suffixe ne s'invente pas, il se declare dans
`Nom=`.** Ecrire `DefProcInterro_MonTableau_Apres` sans avoir passe `Nom='MonTableau'` ne
produit rien -- A5PMTAB cherchera la forme non suffixee.

### Deux correctifs valides quand on ajoute un tableau

| Voie | Comment |
|---|---|
| **Convention suffixee** *(recommandee)* | donner au second tableau son `Fperso` et son `Nom='<X>'`, puis ecrire une serie `DefProcInterro_<X>_*` **dediee**. Un ecran du standard fait exactement ca -- tableau principal sans `Perso`, tableau imbrique avec |
| **Hooks partages + drapeau d'etat** | garder `&Id` correct **partout** et introduire un drapeau au niveau module (mis a `TRUE` juste **avant** l'appel imbrique `AP_*_Tableaux`, remis a `FALSE` juste **apres**), pour que le hook partage sache quel tableau rafraichir **sans dependre uniquement** de la valeur d'`Id` recue |

> **AVERTISSEMENT -- le choix doit etre applique UNIFORMEMENT.** A tous les hooks du tableau
> secondaire, pas seulement a celui qui a casse en premier. Le cas vecu est exactement
> celui-la : `_Charger` avait ete distingue des le depart, **`_Apres` non** -- faute d'avoir
> remarque que le meme risque portait sur tous les hooks. C'est `_Apres` qui a leve l'erreur.

> **Ne PAS supprimer `&Id`** du hook partage pour « regler » le compte de parametres. C'est
> la premiere piste tentee par le partenaire, et elle est **fausse** : la signature officielle
> l'exige.

> **Ce n'est PAS le nombre de tableaux qui commande.** La premiere version de cette page le
> disait ; c'etait juste dans l'effet et faux dans la cause. Le nombre ne fait que correler.

Detail et catalogue : [callbacks-catalogue.md](callbacks-catalogue.md).

## 2. `Id` par adresse -- et le fichier de prototypes dit le contraire

**Le piege** : recopier la signature depuis `objet/proto_a5pmtab.dhsp`, qui ecrit
`DefProcInterro_Apres(Id)` **sans esperluette**.

**La realite** : `Id` est passe **par adresse**. La forme correcte est `(&Id)`.

```diva
; FAUX -- c'est pourtant la forme du fichier de prototypes
Function Int DefProcInterro_Apres(Id)
    1 Id  L

; BON -- forme des extraits de code et des ecrans du standard
Function Int DefProcInterro_Apres(&Id)
    1 Id  L
```

**Pourquoi c'est grave** : declarer un parametre par valeur quand l'appelant empile une
adresse fait **lire l'adresse comme une valeur**. Le code compile. Rien ne le signale.

**Ce que ca change dans votre facon de lire les fichiers Divalto** :
`proto_a5pmtab.dhsp` est fiable pour la **liste** des callbacks et leur **nombre** de
parametres -- pas pour leur **mode de passage**.

## 3. `1A` sur une declaration de parametre : un modificateur d'ALIGNEMENT

**Le piege** : ecrire `1A Sortie B = false` au lieu de `1 Sortie B = false`.

**Le symptome mesure par un partenaire** : compilation a **0 erreur**, puis perte totale de
la possibilite de selectionner une ligne dans le tableau. Aucun message, aucun retour
utilisateur.

**Ce que `1A` signifie vraiment.** Ce n'est **pas** « un type adresse ou pointeur » -- c'est
le **niveau 1 avec forçage d'alignement**. Le manuel de reference l'ecrit :

> Diva verifie que les donnees de type **X et L** sont alignees sur des adresses paires. Les
> donnees de **niveau 1** et les enregistrements sont **automatiquement** alignes sur une
> adresse paire. L'alignement d'une **sous-donnee** sur une adresse paire est obtenu **en
> accolant un A au numero de niveau**.

Donc :

- `A` accole au niveau = **alignement sur adresse paire** ;
- il est destine aux **sous-donnees** (niveau 2 et au-dela) -- au niveau 1, l'alignement est
  **deja automatique** ;
- (au passage : `R` accole au niveau signifie **redefinition**, interdite au niveau 1).

**Ce qui rend le piege credible** : `1A` est **legitime** ailleurs dans les memes fichiers.
Le prototype ecrit `1A Retour X` -- un **local** de type `X`, ou l'alignement a un sens. On
voit donc `1A` a cote de `1` dans un fichier livre, sans indication de ce qui les distingue.

**La regle** : sur un parametre de callback, **reproduire exactement le niveau du prototype**.
Ne jamais ajouter `A` « pour faire comme la ligne du dessus ».

> **Mecanisme non demontre.** Que la casse vienne **precisement** du decalage d'implantation
> induit par l'alignement est notre **deduction** -- coherente avec la doc et avec le
> symptome, mais nous ne l'avons pas prouvee. Ce qui est etabli : `A` est un modificateur
> d'alignement, et le mettre la ou le prototype ne le met pas casse a l'execution.

## 4. La valeur de retour d'une callback : **`0` = « je gere », `1` = « laisse faire »**

> **C'est le fait le plus couteux a ignorer de tout A5PMTAB.** Il ne provoque aucune erreur,
> et il gele l'ecran entier.

**La regle**, pour toute callback `DefProc*` a retour `Int` :

| Retour | Ce que ca veut dire pour A5PMTAB |
|---|---|
| **`0`** | « **je gere cet evenement moi-meme** -- NE PAS faire le traitement par defaut », navigation et sortie standard **comprises** |
| **`1`** | « je ne gere pas cet evenement -- **laisse A5PMTAB faire son traitement normal** » |

**Donc `1` est le repli normal en fin de fonction.** On ne met `0` que dans **la ou les
branches** ou l'on veut reellement se substituer au moteur.

```diva
Function int DefProcInterro_<Nom>_ArretSpecifique(&Sortie)
    1 Sortie  B = False
beginf
    Switch <l evenement>
    Case <mon cas a moi>
        <mon traitement>
        Freturn 0                    ; je m'en occupe : A5PMTAB ne fait rien de plus
    EndSwitch

    Freturn 1                        ; REPLI : tout le reste, c'est A5PMTAB qui le gere
endf
```

### Pourquoi le squelette livre induit en erreur

Le prototype ecrit :

```diva
    1 Retour  L = 0
beginf
    freturn (Retour)
endf
```

**Il retourne `0` -- et c'est normal : c'est un STUB, pas un defaut fonctionnel.** Corps vide
plus « je gere moi-meme » equivaut a « ne rien faire du tout » : d'ou le tableau fige. Le
`Retour` du prototype est une **variable que vous etes cense positionner**, pas une valeur a
conserver telle quelle.

Et le commentaire de l'extrait de code est **tronque dans le fichier livre** --
`; 0 => A5PMTAB testera le parametre sortie,` s'arrete sur une virgule. C'est ce qui a fait
lire ce `0` comme une valeur neutre.

**Le cout reel, rapporte** : un tableau qui s'affiche avec les bonnes donnees mais
entierement fige -- ligne non changeable, Valider et Echap inertes, croix de fermeture morte,
aucune erreur. Plus d'une heure et une douzaine de corrections sans rapport avec la cause.

### Sortir du tableau : deux voies

| Voie | Forme |
|---|---|
| depuis `ArretSpecifique` | positionner le parametre de sortie a `True` -> `AP_*_Tableaux` rend **4** |
| depuis n'importe quelle callback | **`AP_Finir_tableau(<id>)`** -- vu dans un `Defaut` livre, sur `Case K_ESCAPE` |

`AP_Finir_tableau` a un pendant, **`AP_Annule_Finir_Tableau`**. Les deux vivent dans le
module protege `a5pmtab` : appelables, corps non lisible.

> **Correction du 2026-08-28.** La premiere version de cette page declarait ce point
> « **non resolu** », au motif que le RETEX et le prototype se contredisaient. Ils ne se
> contredisent pas : le prototype est un stub. **La semantique etait ecrite dans le RETEX
> lui-meme**, dans sa section « Suggestion », que nous n'avions pas lue avec assez
> d'attention. Le partenaire demandait d'ailleurs explicitement d'en faire un point de tete
> de chapitre.

## 5. L'aller-retour saisie <-> tableau : le motif `bFirstInput` / `XmeNext`

**Ce que rapporte un RETEX** : un motif trouve dans **deux sources partenaires deployees en
production** orchestre l'alternance « saisie de la page selection -> tableau -> retour
saisie » avec un drapeau `bFirstInput`, mis a `false` au premier `XmeInput` et **jamais
reinitialise**. Toute reprise ulterieure passe par
`XmeNext(Harmony.Retour, Harmony.Cplretour)`, en supposant que ces variables systeme decrivent
encore une session de saisie valide. Resultat : **le premier aller-retour marche, le second
part en boucle infinie** -- programme non repondant, arret force.

**Ce que nous avons mesure** : sur les **56 routines** du standard qui appellent
`AP_Interroger_Tableaux` ou `AP_Saisir_Tableaux`, **ZERO** n'utilise `XmeNext`.

**Conclusion** : ce motif **n'a aucune base dans le standard**. Qu'il figure dans du code de
production ne le rend pas correct -- il rend seulement son echec plus tardif.

**La cause exacte** : le drapeau est mis a `false` au premier `XmeInput` et **jamais
reinitialise**. Toute reprise ulterieure passe donc par `XmeNext`, en supposant que
`Harmony.Retour` / `Harmony.Cplretour` decrivent encore une session de saisie valide -- alors
qu'elles ont ete ecrasees entre-temps.

### Le correctif

**Reinitialiser le drapeau a `TRUE` a CHAQUE sortie du tableau** -- et non a la seule
initialisation du programme. L'endroit : dans `ArretSpecifique`, **au meme endroit** ou l'on
positionne le parametre de sortie a `True` (ou ou l'on appelle `AP_Finir_tableau`).

```diva
Function int DefProcInterro_<Nom>_ArretSpecifique(&Sortie)
    1 Sortie  B = False
beginf
    Switch <l evenement de sortie>
    Case <retour a la saisie>
        Sortie       = TRUE          ; on quitte le tableau
        bFirstInput  = TRUE          ; <-- LE CORRECTIF : la prochaine reprise de
        Freturn 0                    ;     saisie fera un XmeInput FRAIS
    EndSwitch

    Freturn 1
endf
```

Ainsi **chaque** retour vers la page de saisie declenche un `XmeInput` neuf -- positionne sur
`Harmony.Sourisseq` -- et jamais un `XmeNext` sur un contexte perime.

**Ce que fait le standard** quand le flux est a sens unique (selection -> tableau, sans
retour) : une boucle de saisie simple, sans drapeau et sans `XmeNext`.

```diva
XmeDispv(<masque>, <page>, XME_MODE_GOTO)
Loop <Saisie_de_la_page>(<masque>, <page>) <> 0
EndLoop
<lancement du traitement qui alimente et affiche le tableau>
XmeRet
```

> **La lecon que le partenaire tire lui-meme, et qui depasse ce cas** : ne jamais supposer
> qu'un motif trouve dans du code client **en production** couvre tous les cas d'usage, y
> compris les plus evidents -- ici, **plusieurs allers-retours successifs**. Faire tester le
> cycle **repete**, pas un aller-retour unique, avant de considerer un motif comme valide.

> **Correction du 2026-08-28.** La premiere version de cette page declarait ne pas pouvoir
> montrer la forme correcte d'un aller-retour, faute d'exemple dans le standard. **Le
> correctif etait dans le RETEX**, section « Contournement ». La mesure (0 des 56 routines
> n'utilise `XmeNext`) restait juste, mais nous en avions tire une conclusion trop large.

## Recapitulatif

| # | Piege | Se voit a la compilation ? | Symptome |
|---|---|---|---|
| 1 | `Fperso` / forme des callbacks | non -- message runtime, parfois | erreur d'appel, tableau inerte |
| 2 | `Id` sans `&` (forme du prototype) | **non** | comportement casse, sans message |
| 3 | `1A` sur un parametre | **non** | selection de ligne perdue |
| 4 | **valeur de retour d'une callback** (`0` = je gere, `1` = laisse faire) | **non** | tableau entierement fige |
| 5 | `bFirstInput` non reinitialise a chaque sortie | **non** | boucle infinie au 2e aller-retour |

## Voir aussi

- [callbacks-catalogue.md](callbacks-catalogue.md) -- les signatures, et la regle du suffixe
- [invocation.md](invocation.md) -- `Creer_Parametre`, `AP_Interroger_Tableaux`, les options
- [keywords-verifies.json](keywords-verifies.json) -- le releve date, et les 3 points non resolus
