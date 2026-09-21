# Regles RecordSql (R01-R08)

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| R01 | warning | Filtre `Dos = MZ.Dos` manquant dans WHERE | Parse XML RecordSql, verifier clause WHERE |
| R02 | warning | Declaration `OverWrittenBy` manquante | Regex: absence de `OverWrittenBy` dans le fichier |
| R03 | warning | Fichier vide ou tres court | Moins de 5 lignes non vides dans le `.dhsq` |
| R04 | warning | Nom de fichier `.dhsq` hors forme attendue | Le nom doit commencer par 2 a 4 lettres suivies de caracteres de mot (`^[a-z]{2,4}\w+\.dhsq$`) |
| R05 | warning | Balise `<DictionarySql>` absente du fichier .dhsq | Verifier la presence de la balise racine du format RecordSql |
| R06 | *V2* | Macro `Declaration_NomVue` utilisee de maniere non sure | Necessite expansion de macro |
| R07 | *V2* | Cycle de vie du Reader non tenu (`ReaderOpen` sans `ReaderClose`, ou `ReaderSelect` sans `ReaderOpen`) — fuite de connexions et de memoire sur gros volumes | **Necessite une analyse de flux** : le `ReaderClose` peut vivre dans une branche conditionnelle et le `ReaderOpen` dans la procedure appelante. Mesure : la formulation « aucun `ReaderClose` dans le fichier » donne 0 constat sur le standard et 9 sur un specifique partenaire, mais reste indecidable sans suivre les appels. Le standard contient par ailleurs un `ReaderSelect` sans aucun `ReaderOpen` (`a5tznotif_sql.dhsp`), ce qui disqualifie la seconde formulation prise seule. |
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
