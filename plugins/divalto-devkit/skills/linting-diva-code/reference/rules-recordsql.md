# Regles RecordSql (R01-R08)

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| R01 | warning | Filtre `Dos = MZ.Dos` manquant dans WHERE | Parse XML RecordSql, verifier clause WHERE |
| R02 | warning | Declaration `OverWrittenBy` manquante | Regex: absence de `OverWrittenBy` dans le fichier |
| R03 | warning | `GT_DeactivateJoin`/`GT_Clearallcondition` manquants | Regex: reconstruction WHERE sans clear prealable |
| R04 | warning | Fichier .dhoq nomme d'apres la table au lieu de la base | Convention nommage fichier |
| R05 | warning | Balise `<DictionarySql>` absente du fichier .dhsq | Verifier la presence de la balise racine du format RecordSql |
| R06 | *V2* | Macro `Declaration_NomVue` utilisee de maniere non sure | Necessite expansion de macro |
| R07 | warning | `ReaderSelect()` dans une boucle sans `ReaderOpen()` prealable — fuite connexions et memoire sur gros volumes | Detecter boucle (`Do While`/`Loop`) contenant `ReaderSelect()` sans `ReaderOpen()` avant la boucle |
| R08 | error | Type `Long` dans une condition `<Where>` (utiliser `int`) — Erreur 30 | Nom `Long` dans un `<Where>` ; le long DIVA s'ecrit `L`, le type entier `<Where>` est `int` |

## Contexte RecordSql

Un fichier `.dhsq` est un fichier XML declaratif qui definit une vue SQL.

**Structure attendue** :
```xml
<RecordSql>
  <HFileVersion>NomBase</HFileVersion>
  <OverWrittenBy>NomBase</OverWrittenBy>
  <Table>NomTable</Table>
  <Where>
    <Case Name="default">Dos = MZ.Dos</Case>
  </Where>
</RecordSql>
```

**R01 est critique** : sans `Dos = MZ.Dos`, un utilisateur d'un dossier peut voir les donnees d'un autre dossier (faille de securite multi-tenant).

**Types des parametres de condition `<Where>`** : `int`, `char`, `date`, `bool`, `float` -- **la casse est libre** (`Int`, `CHAR`, `Date`... sont valides ; c'est la convention du standard X.13). Le piege n'est PAS la casse : `Long` n'est pas un type `<Where>` valide -- le type long DIVA s'ecrit `L` (declaration de variable), et dans un `<Where>` le type entier est `int`. `(Long X)` provoque l'`Erreur 30 : Type du parametre incorrect` -> utiliser `(int X)` (regle R08).
