# Surcharge RecordSql (.dhsq) -- pattern delta strict

## Contenu

- Quand surcharger un RecordSql
- Mecanisme `overwrite` / `overwrittenby` -- entetes
- Grammaire delta strict -- les 9 interdits empiriques
- Pattern delta correct (exemple minimal)
- Convention de rattachement : groupe `[communs]` partage
- Workflow complet -- chaine `.dhsd` -> SQL -> `.dhsq` -> `.dhsf`
- Anti-patterns

---

## Quand surcharger un RecordSql

Un `RecordSql` compile (`.dhoq`) capture les colonnes des tables a la **date de compilation du standard**. Si la structure d'une table change apres synchro SQL (ex: ajout d'une colonne via U-container du dictionnaire), le `.dhoq` standard ne connait pas la nouvelle colonne -- tout masque qui veut l'utiliser echoue au compile avec "Donnee inconnue : `<table>.<champ>`".

La surcharge `.dhsq` permet de **recompiler le RecordSql** avec la structure de table a jour, **sans toucher au standard livre**. Le `.dhoq` surcharge expose alors la nouvelle colonne et le masque compile.

**Cas typiques** :
- Ajout d'un champ via U-container dans le dictionnaire (`.dhsd`) + synchro SQL -> besoin d'un `.dhsq` surcharge pour rendre le champ visible aux masques
- Ajout d'une colonne calculee, d'une jointure, d'un critere -- toute extension qui doit etre exposee aux masques

---

## Mecanisme `overwrite` / `overwrittenby` -- entetes

Le standard signale qu'un fichier surcharge peut etre defini, via `overwrittenby` :

```diva
; Standard : gtrstab.dhsq
<DictionarySql defaultDictionary=GTFDD.dhsd DataBase=DAV overwrittenby="gtrstabu.dhoq" ModuleInfo='...'>
```

La surcharge declare son intention en tete via `overwrite` :

```diva
; Surcharge : gtrstabu.dhsq
<DictionarySql overwrite="gtrstab.dhoq" ModuleInfo='$Id$'>
```

Note importante : la surcharge **ne repete PAS** `defaultDictionary` ni `DataBase` -- ces proprietes sont heritees automatiquement du standard via le mecanisme `overwrite`. Les repeter releve d'erreurs "double definition".

Convention de nommage (cf. [overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) du skill `coding-diva-advanced`) : suffixe `u` dans le nom de fichier source (`gtrstabu.dhsq`), suffixe `u.dhoq` dans le `overwrittenby` (`gtrstabu.dhoq`).

---

## Grammaire delta strict -- les 9 interdits empiriques

Une surcharge `.dhsq` doit contenir **uniquement le delta** par rapport au standard. **Toute redeclaration du standard est interdite** et provoque des erreurs explicites a la compilation.

Liste des 9 interdits releves empiriquement (24 erreurs compilateur xwin7 dans un cas de migration, session 2026-05-12) :

| # | Erreur compilateur | Code | Cause typique | Correctif |
|---|---|---|---|---|
| 1 | "COMMENT interdit dans une surcharge" | 62 | `<RECORDSQL Name=X Comment="...">` | Retirer l'attribut `Comment` |
| 2 | "`<X>` : Double definition" (MZ, T000, ...) | 15 | `Public Record 'A5DD.dhsd' MZ` repete le standard | Retirer les `Public Record` (heritage du standard) |
| 3 | "Chapitre FROM interdit dans une surcharge" | 61 | `<FROM ...>` complet | Retirer la section `FROM` entiere |
| 4 | "`<X>` : Double definition" (LIBELLECURRENCY...) | 15 | Alias SELECT du standard repete | Ne lister que les **NOUVEAUX** champs SELECT |
| 5 | "Parametre INSERT/UPDATE/DELETE deja defini" | 8 | `<FROM INSERT=Yes UPDATE=Yes DELETE=Yes>` | Retirer les flags `FROM` (heritage standard) |
| 6 | "NOACTIVATE interdit dans une surcharge" | 62 | `<LEFTJOIN noactivate>` | Retirer `noactivate` |
| 7 | "Jointure de surcharge ne peut contenir ON/USING/CASE" | 104 | `<LEFTJOIN ... USING X>` | Jointure simple sans clause (si ajout) |
| 8 | "Clause commune pour le Where ne peut etre surchargee" | 79 | `SwitchSql T000.TabTyp(7)` | Retirer la clause `WHERE` commune |
| 9 | "Critere de tri `<X>` defini plusieurs fois" | 82 | `<ORDERBY>` repete des criteres du standard | Ne lister que les **NOUVEAUX** criteres ORDERBY |

**Principe sous-jacent** : la surcharge **n'a que le droit d'ajouter**. Elle ne peut pas redefinir, repeter ou modifier ce qui existe deja dans le standard. C'est un append-only delta.

---

## Pattern delta correct (exemple minimal)

Surcharge minimale qui ajoute un champ d'un U-container au `<SELECT>` :

```diva
<DictionarySql overwrite="gtrstab.dhoq" ModuleInfo='$Id$'>
;*
;*    Surcharge du dictionnaire des RECORDSQL du GTFTAB
;*    Projet ClaudeIntegration -- delta SELECT pour exposer miRajoutFl (UT007)
;*

<RECORDSQL Name=Devise>
<SELECT>
    T007.miRajoutFl
```

C'est tout. Le `RECORDSQL Devise` herite **tout** du standard (`FROM`, `WHERE`, `ORDERBY`, `JOIN`, autres colonnes `SELECT`) et n'ajoute que `T007.miRajoutFl` au `SELECT`.

**Structure minimale d'une surcharge valide** :

1. Entete `<DictionarySql overwrite="<standard>.dhoq" ModuleInfo='...'>`
2. Section de commentaire descriptive (`;*` ...)
3. `<RECORDSQL Name=X>` -- nom du RecordSql cible (defini dans le standard)
4. Une ou plusieurs sections `<SELECT>`, `<LEFTJOIN>` (simple), `<ORDERBY>` (nouveaux criteres) -- avec uniquement les ajouts

---

## Convention de rattachement : groupe `[communs]` partage

Un `.dhsq` surcharge est typiquement partage entre plusieurs sous-projets (plusieurs masques peuvent vouloir exposer la meme nouvelle colonne). Pour eviter la duplication, on **declare un groupe `[communs]`** dans le `.dhpt` et chaque sous-projet l'**inclut** via `incl=`.

**Regle critique** : NE PAS lister un `.dhsq` directement dans `[fichiers]` d'un `.dhps` -- ca casse la convention de partage et duplique potentiellement la compilation.

Structure type :

```ini
; Dans le .dhpt (projet)
[communs]
nom="dgs recordsql"
fic="gtrstabu.dhsq"," "
fic="<autre>u.dhsq"," "
```

```ini
; Dans le .dhps (sous-projet consommateur)
[communs]
incl="dgs recordsql"," "
[fichiers]
fic="<masque>u.dhsf"," "
; PAS de fic="gtrstabu.dhsq"," " ici !
```

**Verbe different selon le contexte** :
- `[communs]` du `.dhpt` -- **declaration** du groupe avec ses fichiers (`nom=...` + `fic=...`)
- `[communs]` du `.dhps` -- **inclusion** du groupe (`incl=...`)

Conventions de nommage de groupe observees dans le standard DGS : `"dgs recordsql"`, `"mi recordsql"`, `"mi recordSQL"`. Voir aussi les projets DGS de reference (`SoiX10`, `dmcX2`, `dmcX12`, `lmcX7`, `AdisX5`).

---

## Workflow complet -- chaine `.dhsd` -> SQL -> `.dhsq` -> `.dhsf`

La surcharge `.dhsq` est typiquement un maillon dans une chaine plus large d'ajout d'un champ custom dans un masque. Sequence canonique :

1. **Surcharger le dictionnaire `.dhsd`** -- ajouter le champ dans un U-container reserve, recopier les metadonnees, respecter les offsets cumules (voir `managing-diva-dictionaries` du skill).
2. **Synchroniser SQL** (`buildall` + `synchroauto`) -- creer la colonne SQL via `synchroauto` ; verifier `C:\divalto\DivaltoLog\DhOdbcConfigSqlScript.sql` ou via le skill `syncing-diva-sql`.
3. **Surcharger le RecordSql `.dhsq`** -- recompiler le RecordSql pour exposer la nouvelle colonne via delta strict (present document).
4. **Surcharger le masque `.dhsf`** -- ajouter le composant qui reference le champ via `donnee=record,champ,instance` (voir `manipulating-dhsf-screens`).

> Sans l'etape 3, le masque echoue meme si la colonne SQL existe. Le RecordSql est **souvent le maillon manquant** car invisible (`.dhoq` compile dans le standard, pas explicit dans le projet). Quand un compile echoue sur "Donnee inconnue", verifier la chaine complete avant d'incriminer le `.dhsd` ou la synchro.

**Indicateur de succes** : a la fin du `buildall`, le rapport mentionne `Sql=N` ou N est le nombre de `.dhsq` compiles. Si N est superieur a 0 et que le `.dhoq` surcharge est present (ex: `gtrstabu.dhoq`, 18408 octets), la surcharge a bien ete traitee.

---

## Anti-patterns

1. **Copier l'integralite du RecordSql standard** dans la surcharge -> 20+ erreurs "double definition" garanties. La surcharge est un delta append-only, pas une copie modifiable.
2. **Mettre `Comment="..."` sur le `RECORDSQL` surcharge** -> erreur 62.
3. **Redeclarer `Public Record '<dict>.dhsd' <alias>`** dans la surcharge -> erreur 15.
4. **Reproduire `<FROM ...>` complet** (interdit total) ou avec flags `INSERT/UPDATE/DELETE` -> erreur 61 ou 8.
5. **Reproduire `<WHERE>` avec `SwitchSql` commune** -> erreur 79.
6. **Mettre le `.dhsq` directement dans `[fichiers]` du sous-projet** -- casse la convention de partage `[communs]`.
7. **Confusion entre `[communs]` du `.dhpt` (declaration de groupe avec fichiers) et `[communs]` du `.dhps` (inclusion de groupe via `incl=`)**.
8. **Ne pas declarer le groupe `[communs]` dans le `.dhpt`** -- le `incl=` du sous-projet pointera vers un groupe inexistant.
