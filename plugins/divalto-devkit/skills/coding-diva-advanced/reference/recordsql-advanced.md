# RecordSql -- API avancee

## Contenu

- Acces fluent aux conditions WHERE
- Reader -- lecture sequentielle (curseur)
- RecordSqlPtr -- pointeur generique
- Collate -- fusion de RecordSql
- Paging -- lecture paginee
- Methodes Direct -- operations unitaires
- Transactions
- Fonctions utilitaires
- Performance -- gros volumes
- Anti-pattern -- TmpRecordSql concurrent
- Callbacks modules

---


Pour la declaration de base des RecordSql, voir la référence syntaxe du langage (interne).

## Acces fluent aux conditions WHERE

```
; Syntaxe objet pour construire les conditions
MonRS.Where.Equal_MonChamp(valeur)
MonRS.Where.Like_MonChamp(param)
MonRS.Where.Like_MonChamp.AddAndCondition(valeur)
MonRS.Where.RemoveCondition('nomCondition')
MonRS.Where.AddCondition('nom', 'sql_brut')

; Tri
MonRS.OrderBy.Par_Code()
MonRS.OrderBy.Par_Libelle()
```

### Fonctions Where courantes

| Pattern | Role |
|---------|------|
| `.Where.Equal_Champ(val)` | Condition `Champ = val` |
| `.Where.Like_Champ(val)` | Condition `Champ LIKE val` |
| `.Where.AddCondition(nom, sql)` | Condition SQL brute nommee |
| `.Where.RemoveCondition(nom)` | Supprime une condition par nom |
| `GT_ClearAllCondition(RS, true)` | Supprime toutes les conditions |

### Piege : `Where.Equal_*` doit etre chaine avec `AddAndCondition`

Une clause `Where.Equal_*` **seule** ne filtre rien : `vCondition` reste vide et le `Select` ignore la condition malgre l'apparence du code. Le triplet est **obligatoire** :

```diva
1 vCondition S = ' '

MonRS.Where.Equal_SiteCod(siteCod) | MonRS.Where.Equal_SiteCod.AddAndCondition(vCondition)
MonRS.Where.Equal_Statut(statut)   | MonRS.Where.Equal_Statut.AddAndCondition(vCondition)
MonRS.Where.AddCondition("TABLE", vCondition)   ; AVANT le Select

idReader = MonRS.Select()
```

1. declarer `vCondition S = ' '` ;
2. chaque `Where.Equal_X(...)` chaine `| Where.Equal_X.AddAndCondition(vCondition)` (le `|` est un separateur de ligne, meme ligne logique) ;
3. `Where.AddCondition("TABLE", vCondition)` **avant** le `Select`.

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

## Collate -- fusion de RecordSql

Optimisation : fusionne les resultats de plusieurs RecordSql en une seule iteration.

```
CollateOpen(ticket)
CollateAddRecordSql(ticket, RS1)
CollateAddRecordSql(ticket, RS2)
Loop CollateNext(ticket) = 0
    ; Traitement des resultats fusionnes
EndLoop
CollateClose(ticket)
```

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

## Methodes Direct -- operations unitaires

| Methode | Role | Retour |
|---------|------|--------|
| `Select()` | Execute la requete, renvoie la 1re ligne. Libere les ressources. | 1=OK, 0=echec |
| `Insert()` | Insere une nouvelle ligne dans la table de base (From). | ID SQL |
| `Update()` | Met a jour la ligne lue par `Select()`. Detecte les champs modifies. | 1=OK |
| `Delete()` | Supprime la derniere ligne lue par `Select()`. | 1=OK |
| `GetCount()` | Nombre de lignes correspondant aux filtres. | Nombre |
| `DeleteWhere()` | Supprime toutes les lignes correspondant a la condition. | 1=OK, 0=echec |

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
