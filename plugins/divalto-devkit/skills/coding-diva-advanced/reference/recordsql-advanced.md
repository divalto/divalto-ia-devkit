# RecordSql -- API avancee

## Contenu

- Acces fluent aux conditions WHERE -- tout `Where.<X>` est un `Case`
- **Le contrat de la condition** -- ou le filtre se perd, sans une erreur
- Remplacer le critere de recherche d'un zoom standard
- Un champ disponible ici, pas la -- `Erreur 27`
- Reader -- lecture sequentielle (curseur)
- RecordSqlPtr -- pointeur generique
- Collate -- interclassement de RecordSql (moteur de ruptures)
- Paging -- lecture paginee
- **Conventions de retour** -- l'inversion silencieuse entre trois familles d'API
- Methodes Direct -- operations unitaires, et methodes d'instance
- Transactions
- Fonctions utilitaires
- Performance -- gros volumes
- Anti-pattern -- TmpRecordSql concurrent
- Callbacks modules

---


Pour la syntaxe de base du langage -- boucles, conditions, `Proto`, faux amis -- voir
[syntaxe-de-base.md](syntaxe-de-base.md).

## Acces fluent aux conditions WHERE

**Un `Where.<Quelque chose>` est toujours un `Case`** -- soit un `Case` genere pour vous
(`Equal_Champ`, `Like_Champ`...), soit un `Case` que **vous declarez** dans un `.dhsq`. Il
n'y a pas deux API : c'est la meme, et c'est pour cela que le contrat ci-dessous vaut pour
les deux.

```
; Un Case genere
MonRS.Where.Equal_MonChamp(valeur)
MonRS.Where.Like_MonChamp(param)

; Un Case que vous avez declare dans votre surcharge .dhsq
MonRS.Where.IK_MonCritere(param)

; Gestion des conditions nommees
MonRS.Where.RemoveCondition('nomCondition')
MonRS.Where.AddCondition('nom', <valeur accumulee>)

; Tri
MonRS.OrderBy.Par_Code()
MonRS.OrderBy.Par_Libelle()
```

### Fonctions Where courantes

| Pattern | Role |
|---------|------|
| `.Where.Equal_Champ(val)` | `Case` genere : `Champ = val` |
| `.Where.Like_Champ(val)` | `Case` genere : `Champ LIKE val` |
| `.Where.<VotreCase>(args)` | `Case` declare dans un `.dhsq` -- **la voie normale pour un critere maison** |
| `.Where.<Case>.AddAndCondition(var)` | **accumule** le `Case` dans `var` (ne filtre rien a lui seul) |
| `.Where.AddCondition(nom, var)` | **injecte** l'accumulation sous un nom de condition |
| `.Where.RemoveCondition(nom)` | Supprime une condition par nom |
| `GT_ClearAllCondition(RS, true)` | Supprime toutes les conditions |

---

## Le contrat de la condition -- ou le filtre se perd

C'est le piege le plus couteux de cette page, parce qu'il ne produit **aucune erreur** : la
requete s'execute, elle rend des lignes, simplement **pas les bonnes**.

**Une condition n'entre dans le `WHERE` que par `AddCondition`.** Tout ce qui precede ne
fait qu'**accumuler dans une variable**.

```diva
1 vCondition S = ' '

MonRS.Where.RemoveCondition("MACOND")                    ; 1. repartir propre

MonRS.Where.Equal_SiteCod(siteCod) | MonRS.Where.Equal_SiteCod.AddAndCondition(vCondition)
MonRS.Where.IK_MonCritere(param)   | MonRS.Where.IK_MonCritere.AddAndCondition(vCondition)
                                                          ; 2. accumuler, N fois

MonRS.Where.AddCondition("MACOND", vCondition)            ; 3. INJECTER -- sans ca, rien

if MonRS.Select() <> 0                                    ; 4. non-zero = trouve
    ...
endif
```

Le `|` est un **separateur de ligne logique** : les deux moities sont la meme instruction.

### Les deux facons de tout perdre

| Ce qu'on oublie | Ce qui se passe |
|---|---|
| `.AddAndCondition(vCondition)` apres un `Case` | ce `Case`-la n'est jamais accumule : `vCondition` ne le contient pas, le filtre est **incomplet** |
| le `AddCondition(nom, vCondition)` final | **tout** ce qui a ete accumule est perdu : la requete part **quasi non filtree** |

Le second cas est le plus violent, et c'est un defaut **vecu** : cinq `Case` accumules
correctement, aucun `AddCondition` final, et une requete client qui ramenait presque toute
la table. Aucune erreur de compilation, aucune erreur a l'execution.

> **Reflexe de relecture** : compter les `AddAndCondition` et chercher **le** `AddCondition`
> qui les cloture. S'il n'y en a pas, le filtre n'existe pas.

### Ne PAS injecter de SQL brut

`AddCondition` prend, en second parametre, **la variable d'accumulation** -- pas une chaine
SQL ecrite a la main.

```diva
; A NE PAS FAIRE
MonRS.Where.AddCondition("MACOND", "ART.Code LIKE 'X%' AND ART.Statut = 1")
```

Pour ajouter un critere qui n'existe pas, **declarez un `Case` dans une surcharge `.dhsq`**
(`<DictionarySql OverWrite=...>`), puis appelez-le comme n'importe quel autre `Case`. Le
critere devient nomme, relisible, surchargeable a son tour, et il ne depend pas des alias
internes du RecordSql -- alias que vous ne voyez pas (cf. « Un champ disponible ici, pas
la » plus bas).

> Une precedente version de cette page presentait `AddCondition(nom, 'sql_brut')` comme un
> usage normal. C'etait une erreur : elle confondait les **deux** roles de `AddCondition` --
> cloturer une accumulation (obligatoire) et injecter du SQL a la main (a eviter).

---

## Remplacer le critere de recherche d'un zoom standard

Cas d'usage frequent : « le zoom cherche sur le nom, je veux qu'il cherche autrement ». On ne
peut **pas** retoucher la condition standard apres coup -- elle est **agregee dans une seule
chaine nommee**, injectee en un `AddCondition` unique. Il n'y a rien a editer.

### La forme du standard -- mesuree

`Construire_Condition_Selection(nom, premier)` existe **1 125 fois** dans le standard X.13,
et n'est protegee que **2 fois** : elle est donc lisible partout. La forme est stable --

| Marqueur dans le corps | Occurrences |
|---|---|
| la garde `If <champ de selection> <> ' '` | **1 051** (94 %) |
| une accumulation `.AddAndCondition(...)` | **1 064** (95 %) |
| un `RemoveCondition(<nom>)` en entree | **1 071** (95 %) |

-- ce qui suit n'est donc pas extrapole d'un exemple, mais l'ossature de ~94 % des cas :

```diva
Tbl.where.RemoveCondition(Nom)

If <RecordSel>.Conf <> ' '                        ; <-- CHAQUE critere est garde par un test
    Param = banaliser_condition(<RecordSel>.Conf, premier)
    Tbl.where.Like_Conf(Param)
    Tbl.where.Like_Conf.AddAndCondition(Valeur_Condition)
Endif
; ... autres criteres, sur le meme modele

If Valeur_Condition <> ' '                        ; rien accumule -> AUCUNE condition posee
    Tbl.where.AddCondition(Nom, Valeur_Condition)
Endif
```

**C'est ce `If <champ de selection> <> ' '` qui donne le point d'injection.** Le standard
n'accumule un critere que si son champ de selection est renseigne.

### Deux cas, et le simple est le plus frequent

> **Provenance.** L'ossature du standard ci-dessus est **mesuree** (1 125 occurrences). La
> forme du **cas 1** ci-dessous est **observee dans une surcharge de production reelle** --
> ce n'est donc plus une deduction. Elle n'a en revanche **pas ete compilee par nous**, et
> il n'existe aucun module de surcharge dans le standard qui permette de la recouper une
> seconde fois. Le **cas 2** (suppression) reste, lui, **deduit** de l'ossature : nous
> n'avons pas vu de code reel qui masque un champ de selection.
>
> Cette lecture a **corrige trois points** de notre premiere redaction : le masquage n'est
> pas la technique courante mais l'exception, `Standard.<proc>()` s'appelle **en premier**,
> et la production accumule par un helper que nous ne connaissions pas.

**Cas 1 -- AJOUTER un critere.** C'est le cas courant, et il ne demande **aucune ruse** :
on laisse le standard faire son travail, puis on pose ses propres criteres sous un **nom de
condition distinct**. Forme observee dans une surcharge de production :

```diva
Procedure Construire_Condition_Selection(nom, premier)
1  Nom                A
1  Premier            1,0 = false
1  Valeur_Condition   S
1  Param              S
Beginp
    Standard.Construire_Condition_Selection(nom, premier)   ; 1. LE STANDARD D'ABORD

    <Tbl>.Where.RemoveCondition('<MON_NOM>')                ; 2. sur SON nom, pas le sien

    If <RecordSel>.<MonChamp> <> ' '                        ; 3. meme ossature que le standard
        Param = Banaliser_Condition(<RecordSel>.<MonChamp>, premier)
        <Tbl>.Where.like_<MonChamp>(Param)
        Ajouter_Condition(Valeur_Condition, 'like_<MonChamp>')
    Endif
    ; ... autres criteres, sur le meme modele

    If Valeur_Condition <> ' '                              ; 4. injecter sous SON nom
        <Tbl>.Where.AddCondition('<MON_NOM>', Valeur_Condition)
    EndIf
Endp
```

Les points qui comptent :

- **`Standard.<proc>()` en premier**, conformement au pattern canonique -- pas de masquage,
  pas de contournement : on **ajoute**.
- **Nom de condition distinct.** `AddCondition` est indexe par nom : reutiliser le nom
  standard **ecrase** son travail au lieu de s'y ajouter. Et le `RemoveCondition` d'entree
  porte sur **votre** nom, pour repartir propre a chaque appel.
- **`Ajouter_Condition(<accumulateur>, '<nom du Case>')`** est une **variante** de
  `.<Case>.AddAndCondition(<accumulateur>)` : elle prend le nom du `Case` en **chaine**.
  C'est un helper standard (module protege, donc appelable mais non lisible) -- **119**
  routines livrees l'utilisent, contre **3 456** pour `.AddAndCondition`. Les deux
  conviennent ; l'accumulation est la meme.

**Cas 2 -- SUPPRIMER un critere du standard.** Seulement si vous voulez qu'un critere
standard cesse de s'appliquer. Le standard n'accumule un critere que si son champ de
selection est renseigne : il suffit donc de **mettre ce champ a espaces avant** l'appel.

```diva
    <RecordSel>.<ChampAneutraliser> = ' '     ; son If devient faux
    Standard.Construire_Condition_Selection(nom, premier)
```

> **Precaution non observee en production, a votre appreciation.** La procedure est appelee
> **une fois par nom de condition** (le standard distingue au moins une clause « normale »
> et une clause « pilotee »). Filtrer sur `nom` avant d'agir evite de poser son critere sur
> une clause non voulue. La surcharge de production que nous avons lue **ne le fait pas** --
> ce qui est sans consequence si le zoom n'utilise qu'un seul nom, mais nous ne pouvons pas
> le garantir dans le cas general.

Et le critere lui-meme se declare en `Case` dans une surcharge `.dhsq`
(`<DictionarySql OverWrite=...>`) -- **pas** en SQL brut. Voir « Ne PAS injecter de SQL
brut » plus haut.

---

## Un champ disponible ici, pas la -- `Erreur 27`

Un champ peut etre utilisable dans un `WHERE` **via l'alias d'une table jointe** et refuse
**via l'alias d'une autre table** du meme RecordSql -- alors que le champ existe bel et bien
dans le dictionnaire des **deux** tables physiques. Symptome :
`Erreur 27 : Champ <X> non trouve`.

**Ce n'est pas une anomalie.** La disponibilite d'un champ dans un `WHERE` ne depend pas de
son existence au dictionnaire, mais de la maniere dont **ce RecordSql-la** expose et joint
cette table : quels `Select` existent deja, quel alias porte quel synonyme. Deux tables
peuvent porter conceptuellement la meme donnee -- un numero de piece, par exemple -- sans
que les deux alias l'exposent.

**Ou regarder** : le **`.dhsq`** du RecordSql, sections `<From>` / `<Join>` et les `<Select>`
existants. C'est la seule source. Le graphe de connaissance **n'expose pas** cette structure
(un noeud `RecordSQL` porte `sqlfile`, `recordSQL_name`, `instance` -- pas la liste des champs
ni les jointures), et si le module porteur est protege, son corps ne dira rien non plus
(cf. `overwrite-pattern.md`, section « Retrouver la signature d'une fonction protegee »).

**Le reflexe** : ne pas s'acharner a faire marcher l'alias qui refuse. Si un autre alias du
meme RecordSql expose le champ, l'utiliser ; sinon, **declarer un `Case` dans une surcharge
`.dhsq`**, ou la jointure et l'alias sont sous votre controle.

---

## Reader -- lecture sequentielle (curseur)

```
1   ReaderId    L

ReaderOpen_MaTable(MonRS, ReaderId)
GT_ClearAllCondition(MonRS, true)
MonRS.Where.Equal_Code(valeurRecherche)
MonRS.OrderBy.Par_Code()

ReaderSelect_MaTable(MonRS, ReaderId)
Loop ReaderNext_MaTable(MonRS, ReaderId) = 0
    ; Traitement de chaque enregistrement
    If MonRS.Champ > valeurMax
        ExitLoop
    EndIf
EndLoop
ReaderClose_MaTable(MonRS, ReaderId)
```

### Sequence Reader

1. `ReaderOpen_Table(RS, &ReaderId)` -- ouvre un curseur
2. `GT_ClearAllCondition(RS, true)` -- nettoie les conditions
3. Ajouter Where / OrderBy
4. `ReaderSelect_Table(RS, ReaderId)` -- execute la requete
5. `Loop ReaderNext_Table(RS, ReaderId) = 0` -- iterer
6. `ReaderClose_Table(RS, ReaderId)` -- **fermer le curseur**

### Pieges Reader / ListMode

- **`GT_Reader_recordSql(...)` n'existe pas** en DIVA. Utiliser le pattern `ReaderOpen/Select/Next/Close_<Table>` ci-dessus (+ `AddAndCondition` / `AddCondition('Record', valCond)` pour les filtres).
- **`ListMode(id, mode, adrFct)` exige 3 parametres**, meme en mode FIFO (`mode = 0`). Recuperer l'adresse de fonction via `GetAdressFunction` :
  ```diva
  ListMode(id, 0, GetAdressFunction("MaFonction"))
  ```

---

## RecordSqlPtr -- pointeur generique

```
RecordSqlPtr  InstanceRS    ; Parametre acceptant n'importe quel RecordSql

; Creation dynamique
PtrRecordSqlNew("gtrsart.dhoq", "article", ptart)

; Duplication d'instance
DuplicateInstance(existingRS, newRS)
```

Utile pour ecrire des fonctions generiques operant sur plusieurs types de RecordSql.

---

## Collate -- interclassement de RecordSql

> **Cette section ne recopie pas le manuel.** Elle porte uniquement ce que le manuel rend
> mal exploitable (l'ordre et l'optionalite des parametres, la forme du code) et un
> avertissement. **Ne PAS l'etendre de memoire** : les 5 fonctions vivent dans le module
> **`Ycollate.dhop`** et sont documentees au chapitre « Fonctions Collate » du manuel de
> reference, interrogeable via `get_native_keyword_doc` (`CollateOpen`,
> `CollateAddRecordSQL`, `CollateNext`, `CollateClose`, `CollateProgressBar`).
>
> **Pourquoi cet avertissement.** La version precedente de cette section etait **fausse sur
> trois points** parce qu'elle avait ete ecrite de memoire : signature a 2 parametres au lieu
> de 7, identifiant passe en parametre alors qu'il est la **valeur de retour**, et surtout
> aucune trace du mecanisme reel.

### Ce que `Collate` est vraiment

Pas une boucle de fusion ou l'on ecrit son traitement : un **moteur de ruptures pilote par
callbacks**. Pour **chaque** RecordSql, on declare trois procedures -- rupture de **debut**,
**detail**, rupture de **fin**. Le moteur lit la premiere ligne de chaque RecordSql, puis,
apres chaque `Detail`, avance le RecordSql concerne.

Les RecordSql peuvent etre **heterogenes** (instances de RecordSql differents) : *« la seule
obligation etant que le critere de tri des RecordSQL soit le meme »*.

> Avec **un seul** RecordSql dans la liste, `Collate` devient simplement une gestion de
> ruptures -- c'est un usage legitime et documente.

### La forme du code

```diva
1 idCollate L
1 idRs      L

idCollate = CollateOpen(<ProcFinInterclassement>)   ; l'ID est le RETOUR, pas un parametre

; ATTENTION : poser le tri (et le filtrage) AVANT d'ajouter -- CollateAddRecordSQL
; execute lui-meme le ReaderSelect et lit la premiere ligne.
RS1.OrderBy.Par_Code()
CollateAddRecordSQL(idCollate, "RS1", "Debut_T1", "Fin_T1", "Detail_T1", <FuncKey>)

RS2.OrderBy.Par_Code()                              ; MEME critere de tri
CollateAddRecordSQL(idCollate, "RS2", "Debut_T2", "Fin_T2", "Detail_T2", <FuncKey>)

Loop CollateNext(idCollate) <> H_EOF                ; sentinelle nommee : H_EOF
    ; rien a ecrire ici : le moteur appelle vos procedures Debut / Detail / Fin
Endloop

CollateClose(idCollate)
```

| Point | A retenir |
|---|---|
| `CollateOpen(EndProc)` | l'identifiant est la **valeur de retour** ; le parametre est une procedure de fin |
| `CollateAddRecordSQL(idCollate, Name, ProcBegin, ProcEnd, ProcDetail, FuncKey [, ModuleName])` | `Name` est le **nom du RecordSql public, sous forme de chaine** ; les quatre suivants sont des **noms de procedures/fonctions publiques** |
| Tri **avant** l'ajout | `CollateAddRecordSQL` execute le `ReaderSelect` et lit la 1re ligne |
| Meme critere de tri partout | c'est la **seule** obligation entre RecordSql heterogenes |
| `CollateNext` | rend `0` (normal) ou **`H_EOF`** (fin d'interclassement) -- tester `H_EOF`, la sentinelle nommee |
| `CollateProgressBar(idCollate, ProgressBar)` | barre de progression, souvent utile sur les gros volumes |

**Quand y penser** : le gain est important quand l'algorithme naif fait *un select par ligne
de la table principale*. L'exemple emblematique du manuel est le grand livre des stocks --
sans interclassement, 1 select sur les articles puis 3 selects par article.

---

## Paging -- lecture paginee

| Fonction | Role |
|----------|------|
| `GT_PagingReaderSelect_recordSql(RS, ReaderId, Offset, NB, EndFl)` | SELECT pagine |
| `GT_PagingReaderNext_recordSql(RS, ReaderId, Offset, Nb, EndFl)` | Next pagine |
| `GT_ReaderHasRows_recordSql(RS, ReaderId)` | Verifie si le reader a des lignes |
| `GT_InitForUpdateWhere(RS)` | Initialise avant UpdateWhere |

Le paging est utilise pour les affichages en grille avec chargement progressif.

---

## Conventions de retour -- l'inversion silencieuse

**Trois familles d'API de lecture cohabitent, et elles n'ont pas la meme convention de
retour.** Se tromper ne produit **aucune erreur** : le bloc s'execute quand la ligne n'est
**pas** trouvee, et inversement.

| Famille | Exemples | Succes (ligne trouvee) |
|---|---|---|
| Objet metier | `Give_<Entite>(...)`, `Find_T<nnn>(...)` | **`0`** |
| Wrappers generes | `Select_<Name>(...)`, `ReaderNext_<Name>(...)` | **`0`** |
| **Methodes d'instance** | `<inst>.Select()`, `<inst>.ReaderNext()` | **non-zero / vrai** |

```diva
; BON -- wrapper genere : 0 = on continue
Loop ReaderNext_gtrsart(RS, idReader) = 0
    ...
Endloop

; BON -- methode d'instance : non-zero = trouve
if MonRS.Select() <> 0
    ...
endif

; FAUX -- compile, et fait exactement l'inverse de ce qu'on croit
if MonRS.Select() = 0
    ; ce bloc s'execute quand AUCUNE ligne n'a ete trouvee
endif
```

### Pourquoi ce piege est particulierement traitre

Le reflexe `= 0` est **juste** dans les deux familles que l'on lit tout le temps, et **faux**
dans la troisieme -- que le standard n'utilise presque pas. Mesure sur le standard X.13
(routines livrees, corps protege exclus) :

| Forme | Routines | dont testees `= 0` |
|---|---|---|
| `ReaderNext_<Name>` (wrapper) | **642** | **628** (98 %) |
| `Select_<Name>` (wrapper) | **3 181** | -- |
| `<inst>.Select()` (methode) | **7** | **0** |
| `<inst>.ReaderNext()` (methode) | **0** | -- |

Autrement dit : **il n'y a quasiment aucun exemple dans le standard pour vous apprendre la
convention inverse.** Le reflexe se forme sur 3 800 occurrences de la forme wrapper, puis se
transpose a une methode d'instance ou il est faux -- et rien ne le contredit.

> **Regle de relecture** : des qu'on voit `.Select()` ou `.ReaderNext()` **sur une instance**
> (avec le point, sans suffixe `_<Name>`), le test correct est `<> 0` -- jamais `= 0`.

### Les formes reellement rencontrees dans le standard

Les 7 usages de `.Select()` ont ete lus un par un -- **4 sont en commentaire**. Les formes
vivantes :

| Forme | Verdict |
|---|---|
| `if <inst>.Select()` | **test de verite nu**, sans comparaison -- correct et utilise |
| `<inst>.Select() = SQL_RESULTOK` | correct, mais **voir l'avertissement ci-dessous** |
| `<inst>.Select() = 1` | correct (le tableau « Methodes Direct » donne 1=OK) -- vu en commentaire |
| `<inst>.Select() = 0` | **jamais** dans le standard, ni en commentaire |

> **`SQL_RESULTOK` n'est PAS une constante generale.** Elle vaut `1`, mais elle est
> declaree **localement dans deux programmes seulement** (`a5tcetl000`, `a5tzetl010_sql`),
> en portee `root` de leur module. L'ecrire dans votre code sans la declarer donne
> `Erreur 99 : Mot inconnu`. Ne pas la reprendre par mimetisme apres l'avoir vue dans le
> standard -- **la forme portable est le test de verite nu, ou `<> 0`**.

---

## Methodes Direct -- operations unitaires

| Methode | Role | Retour |
|---------|------|--------|
| `Select()` | Execute la requete, renvoie la 1re ligne. Libere les ressources. | 1=OK, 0=echec |
| `Insert()` | Insere une nouvelle ligne dans la table de base (From). | ID SQL |
| `Update()` | Met a jour la ligne lue par `Select()`. Detecte les champs modifies. | 1=OK |
| `Delete()` | Supprime la derniere ligne lue par `Select()`. | 1=OK |
| `GetCount()` | Nombre de lignes correspondant aux filtres. | Nombre |
| `DeleteWhere()` | Supprime toutes les lignes correspondant a la condition. | 1=OK, 0=echec |
| `Init()` | Reinitialise l'instance. | -- |
| `InitForUpdateWhere()` | Prepare l'instance pour un `UpdateWhere`. Existe aussi en fonction : `GT_InitForUpdateWhere(RS)`. | -- |

### Methode d'instance ou fonction generee ?

Les deux formes coexistent et **compilent** toutes les deux :

```diva
1 RecordSql 'gtrstiers.dhoq' Client Client_loc

Client_loc.Update()                  ; methode d'instance
Update_Client(Client_loc, true)      ; fonction generee, avec le drapeau maj-CE
```

**Ne pas conclure qu'une methode d'instance n'existe pas parce qu'elle n'est pas
documentee** : la forme `<instance>.Update()` est valide. Elle a deja ete signalee a tort
comme a remplacer.

> **NON VERIFIE -- socle d'audit.** Nous ne savons **pas** si `<instance>.Update()` entretient
> le socle d'audit (`UserMo`, `UserMoDh`) comme le fait `Update_<Entite>(inst, majce)`. La
> question a ete posee par le partenaire qui a signale la methode, et elle reste ouverte :
> elle demande une verification **a l'execution** sur une base reelle, pas une lecture de
> code. **En attendant, sur une table portant le socle d'audit, preferer la fonction
> generee** -- si elle fait plus, on ne perd rien ; si les deux sont equivalentes, on ne perd
> rien non plus. Voir `non_verifie` dans [keywords-verifies.json](keywords-verifies.json).

---

## Transactions

```diva
1  idTrans  L

idTrans = TransactionGetId()
MonRecord.SetTransaction(idTrans)
; ... operations ...
TransactionCommit(idTrans)
; ou TransactionRollback(idTrans)
```

**Contrainte** : tous les RecordSql d'une meme transaction doivent utiliser la meme connexion.

| Fonction | Role | Retour |
|----------|------|--------|
| `TransactionGetId()` | Obtient un ID (pas de verrou) | 0=echec, sinon=ID |
| `RS.SetTransaction(idTrans)` | Affecte a une transaction | 0=OK |
| `TransactionCommit(idTrans)` | Valide | 0=OK |
| `TransactionRollback(idTrans)` | Annule | 0=OK |

---

## Fonctions utilitaires

### SqlSelect / DirectReader

Permet de composer une requete SQL par programme (jointures ajoutees dynamiquement).

```diva
TOTO.SqlSelect("JOIN TITI as TITI ON TITI.DOS = TOTO.DOS and TITI.NOM = TOTO.NOM")
idReader = TOTO.DirectReaderOpen()
idReader = TOTO.DirectReaderSelect(idReader)
Loop TOTO.DirectReaderNext(idReader) = 1
    Display TOTO.Nom
EndLoop
TOTO.DirectReaderClose(idReader)
```

### Autres fonctions

| Fonction | Role | Retour |
|----------|------|--------|
| `GetId()` | ID unique de la derniere ligne lue | ID |
| `GetInfo(commande, &resultat)` | Info sur le RecordSql (voir `zdiva.dhsp`) | 1=OK, 0=echec |
| `Exists()` | Ligne existe-t-elle ? (zoom uniquement) | 1=oui, 0=non |
| `ReadAgain(idReader, id)` | Relit une ligne par ID (zoom) | 1=OK, 0=supprimee |
| `Bind nom` | Peuple les records DIVA publics. **Uniquement avec RecordSql publics.** | — |
| `ReaderSelectDistinctValue(idReader, champ)` | SELECT DISTINCT TOP 200 sur un champ | 0=echec, sinon=ID |
| `ChangeTable(table, version)` | Remplace FROM par CHANGETABLE (BI) | 1=OK, 0=echec |

---

## Performance -- gros volumes

### ReaderOpen hors de la boucle

```diva
; MAUVAIS : ReaderSelect dans la boucle (ouverture/fermeture a chaque tour)
Do While COMPTE.ReaderNext(IdReaderCompte) <> 0
    IdReaderEcriture = ECRITURE.ReaderSelect()
    Do While ECRITURE.ReaderNext(IdReaderEcriture) <> 0
        ...
    Wend
Wend

; BON : ReaderOpen une seule fois
IdReaderEcriture = ECRITURE.ReaderOpen()
Do While COMPTE.ReaderNext(IdReaderCompte) <> 0
    ECRITURE.ReaderSelect(IdReaderEcriture)
    Do While ECRITURE.ReaderNext(IdReaderEcriture) <> 0
        ...
    Wend
Wend
ECRITURE.ReaderClose(IdReaderEcriture)
```

### Autres optimisations

- Sortir de la boucle : `Init()`, `Join.Deactivate('$ALL')`, `OrderBy.xxx()` invariants
- Affichage : `OpenTrace` / `Afficher_selection` au lieu de `XMEDISPV` a chaque iteration
- Profiling : `AnalyzeStart(200, 0)` + `AnalyzePause` pour generer un XPerf

### Resultats mesures

| Configuration | Temps | Aboutissement |
|--------------|-------|---------------|
| Code initial (ReaderSelect en boucle) | 5000s | Ne termine pas (memoire) |
| Optimisation affichage seul | 450s | Ne termine pas |
| Optimisation complete (ReaderOpen + affichage) | 396s | Termine sans erreur |

---

## Anti-pattern -- TmpRecordSql concurrent

En batch **multi-processus** (ex. `ProgramCall` lance N instances en parallele), `TmpRecordSql` peut declencher `Erreur SQL 300A` ("There is already an object named '<table>_<N>'") : le nom de table temporaire derive d'un identifiant (suffixe timestamp/SPID) qui peut se repeter entre processus proches. Le flag `KeepOnExit` aggrave le cas (table persistante apres crash -> blocage de l'execution suivante).

**Alternative recommandee** quand (a) le programme est appele par `ProgramCall` depuis plusieurs processus simultanes et (b) on passe une liste de cles : remplacer `TmpRecordSql` par le passage d'une **liste CSV via Ping**.

- Emetteur : construire une chaine CSV des cles (sans espaces, separateur `,`) et l'envoyer en un seul `Ping S` avant le `ProgramCall`.
- Recepteur : decoder avec `String(',', str, pos)` + `Mid` + `Length` + `repeat...until`.

Avantages : aucune ressource SQL partagee (zero collision), chaque processus est un silo memoire isole, et `Ping S` n'a pas de limite de taille pratique. Voir [tunnels.md](tunnels.md) pour Ping/PingReceive.

> Note version : `String`/`Mid`/`Length`/`repeat...until` ne sont pas tous disponibles avant X.13 (cf. `analyzing-diva-request` pour la table des fonctions par version ERP).

## Callbacks modules

Procedures appelees automatiquement par le framework. `XXXX` = prefixe du module.

### Operations Reader

| Callback | Moment | Retour special |
|----------|--------|---------------|
| `XXXX_ReaderSelect_Av` | Avant execution SQL | |
| `XXXX_ReaderSelect_Ap` | Apres execution SQL | |
| `XXXX_ReaderNext_Av` | Avant lecture ligne suivante | |
| `XXXX_ReaderNext_Ap` | Apres lecture d'une ligne | `"I"` = skip, `"N"` = fin |
| `XXXX_ReaderUpdate_Av` | Avant reecriture ligne courante | |
| `XXXX_ReaderDelete_Av` | Avant suppression ligne courante | |

### Operations Direct

| Callback | Moment |
|----------|--------|
| `XXXX_Select_Av` | Avant execution SQL |
| `XXXX_Select_Ap` | Apres execution SQL |
| `XXXX_Insert_Av` | Avant insertion |
| `XXXX_Update_Av` | Avant reecriture |
| `XXXX_Delete_Av` | Avant suppression |

### Operations multi-enregistrements

| Callback | Moment |
|----------|--------|
| `XXXX_UpdateWhere_Av` | Avant reecriture multiple |
| `XXXX_DeleteWhere_Av` | Avant suppression multiple |

---

> Reference exhaustive : référence RecordSql interne
