# Structure d'un fichier RecordSql (.dhsq)

## Contenu

- Vue d'ensemble
- En-tete DictionarySql
- Section RecordSql
- Section SELECT
- Section FROM
- Section WHERE
- Section ORDERBY
- Fichier dedie vs fichier multi-entites

---


Source : `docs/SQUELETTES.md` et fichier ERP reel `rtrstab.dhsq`.

---

## Vue d'ensemble

Un RecordSql est une vue SQL declarative en syntaxe XML/DIVA. Il definit comment acceder a une table SQL depuis le framework Divalto.

```
<DictionarySql ...>     ← En-tete : dictionnaire, surcharge, module info
  <RecordSql Name=...>  ← Definition du RecordSql
    Public Record ...    ← Records partages (MZ pour multi-dossier)
    <SELECT> ...         ← Colonnes selectionnees
    <FROM ...> ...       ← Table source + droits Insert/Update/Delete
    <WHERE> ...          ← Filtre obligatoire + Cases nommes
    <ORDERBY> ...        ← Ordres de tri nommes
```

---

## En-tete DictionarySql

```xml
<DictionarySql DefaultDictionary={DICT}.dhsd DataBase=DAV
    overwrittenby="{overwrittenby_rsql}"
    ModuleInfo='$Id: {fichier_rsql} 1 {date} user $'>
```

| Attribut | Role | Obligatoire |
|----------|------|:-----------:|
| `DefaultDictionary` | Dictionnaire par defaut pour les tables | Oui |
| `DataBase` | Base de donnees logique (toujours `DAV`) | Oui |
| `overwrittenby` | Fichier de surcharge (personnalisation client) | Oui (R02) |
| `ModuleInfo` | Version du fichier (format `$Id:`) | Oui |

---

## Section RecordSql

```xml
<RecordSql Name={NomVue} Comment="{Description}" ZoomOptimize=Yes>
Public Record A5DD.dhsd    MZ
```

- **Name** : nom unique du RecordSql (attention a la non-collision avec le Record — voir naming-diva-entities)
- **Comment** : description metier
- **ZoomOptimize=Yes** : optimisation de chargement pour les zooms
- **Public Record A5DD.dhsd MZ** : necesaire pour acceder a `MZ.Dos` (filtre multi-dossier)

---

## Section SELECT

```xml
<SELECT>
    {TableSQL}.*
```

`{TableSQL}.*` selectionne toutes les colonnes de la table. Pour des jointures, ajouter les colonnes des tables jointes avec alias `as`.

---

## Section FROM

```xml
<FROM Insert=Yes Update=Yes Delete=Yes>
    {TableSQL}
```

Les attributs `Insert`, `Update`, `Delete` controlent les droits DML sur la table.

---

## Section WHERE

```xml
<WHERE>
    {TableSQL}.Dos = MZ.Dos            ← Filtre multi-dossier OBLIGATOIRE (R01)

    Case Equal_{ChampCle}(char code)   ← Recherche exacte par cle
        {TableSQL}.{ChampCle} = code

    Case Like_{ChampCle}(char code)    ← Recherche partielle par cle
        {TableSQL}.{ChampCle} LIKE code

    Case Like_Libelle(char libelle)    ← Recherche partielle par libelle
        {TableSQL}.Libelle LIKE libelle

    Case Exists(char code)             ← Test d'existence
        {TableSQL}.{ChampCle} = code

    Case PK(char code)                 ← Recherche par cle primaire
        {TableSQL}.{ChampCle} = code

    Case ID(Int id)                    ← Recherche par ID SQL auto-genere
        {TableSQL}.{TableSQL}_ID = id
```

Le filtre `{TableSQL}.Dos = MZ.Dos` est **en dehors de tout Case** — il s'applique a toutes les requetes. C'est une **obligation de securite** pour le multi-dossier.

---

## Section ORDERBY

```xml
<ORDERBY>
    Case Par_Code         "Par {ChampCle}"
        {TableSQL}.Dos
        {TableSQL}.{ChampCle}

    Case Par_Libelle      "Par libelle"
        {TableSQL}.Dos
        {TableSQL}.Libelle
        {TableSQL}.{ChampCle}
```

Le `Dos` est toujours le premier critere de tri (coherent avec le filtre WHERE).

---

## Fichier dedie vs fichier multi-entites

Le ERP standard utilise des fichiers **multi-entites** (ex: `rtrstab.dhsq` contient toutes les RecordSql du domaine Retail). Le skill genere un fichier **dedie par entite** (ex: `rtlrsfamrglt.dhsq`) pour simplifier la gestion et la surcharge.

Les deux approches sont valides. Le fichier dedie est recommande pour les nouvelles entites.
