# Surcharge d'index dans `.dhsd` -- pattern complet

## Contenu

- Quand surcharger un index
- Prerequis -- pattern de surcharge champs valide
- Structure d'un index custom en surcharge
- Convention `CLE=` avec espace + `Alias=`
- Bloc `[BASEU]` requis
- Bloc `[INDEXL]` final
- Convention de nommage `index_<descriptif>`
- Variantes position 7 -- 3 types d'index
- Filtered indexes Divalto
- Workflow complet
- Anti-patterns

---

## Quand surcharger un index

Apres avoir ajoute des champs custom via le pattern de surcharge `.dhsd` (cf. [dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md)), creer un **index custom** est la suite logique pour permettre des recherches performantes sur ces nouveaux champs. Sans index, les requetes runtime sur les colonnes custom sont en table scan SQL.

Cas typiques :

- Index simple sur un champ custom (`Dos + miRajoutFl`)
- Index filtre sur les records ou `Ce<N>` calcule par mchk vaut une valeur particuliere
- Index multi-champs custom + champs standard

> **Symptome d'echec silencieux** : a la 1ere tentative de surcharge d'index, il est tres facile de cumuler plusieurs erreurs structurelles -- la compilation ET le synchroSQL retournent toutes les deux 0 erreur, mais l'index **n'est jamais cree** en base. Bug invisible jusqu'a l'analyse manuelle.

---

## Prerequis -- pattern de surcharge champs valide

Avant de surcharger un index :

- Les champs cibles doivent etre declares dans le `.dhsd` de surcharge (cf. [dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md))
- Le bloc `[CHAMPR]` avec `nom=U<NomTable>` doit etre present
- La table cible doit etre surchargeable (avoir un container `U<NomTable>` cote standard -- anti-pattern D15)

---

## Structure d'un index custom en surcharge

Un index custom se declare via un bloc `[INDEX]` dans le `<dict>u.dhsd`, **apres** les blocs `[CHAMPR]/[TABLEU]/[BASEU]`. Exemple minimal (index simple sur `Dos + miRajoutFl` de la table `ART`) :

```ini
[INDEX]
Version=1,20260512143000,USER,20260512143000,USER
Nom=index_miRajout,Index sur miRajoutFl,1
DateM=<FILETIME courant>
CLE=GtfAt, ,Ce1,2,1,n,1,n             ; espace en position 2 + Alias= ci-dessous
Alias=miRajout                         ; nom logique de l'index
[CHAMPS]
Nom=Dos,1,0,
Nom=miRajoutFl,9,0,                    ; offset 9 = 1 + taille(Dos=8)
[/CHAMPS]
[/INDEX]
```

Puis a la fin du fichier, le bloc global `[INDEXL]` :

```ini
[INDEXL]
Nom=GtfAt,ART,index_miRajout,0
[/INDEXL]
```

---

## Convention `CLE=` avec espace + `Alias=`

La position 2 de la ligne `CLE=` (= "Lettre" de l'index) accepte **deux formes** :

| Forme | Quand | Exemple |
|-------|-------|---------|
| Lettre A-Z / a-z | Index standard historique nomme `Index_<Lettre>` | `CLE=GtfAt,A,Ce1,2,1,n,1,n` (Index_A "Par reference") |
| Espace (caractere `0x20`) | Index custom nomme via `Alias=` | `CLE=GtfAt, ,Ce1,2,1,n,1,n` + `Alias=miRajout` |

Quand position 2 est un espace, la **ligne suivante** doit etre `Alias=<NomLogique>` :

```ini
CLE=GtfAt, ,Ce1,2,1,n,1,n
Alias=miRajout
```

C'est cet `Alias=` qui figure ensuite dans `[INDEXL]` (cf. ci-dessous).

> Cette convention `<espace>` + `Alias=` n'est pas documentee dans la zone 4 standard (`dhsd-5-zones.md`). Le format de `CLE=` reste identique au standard sur les autres positions (cf. [dhsd-5-zones.md zone 4](dhsd-5-zones.md)).

---

## Bloc `[BASEU]` requis

`[BASEU]` est **obligatoire** lorsque l'on ajoute un index custom. C'est l'ancrage de la base sur laquelle l'index sera cree.

```ini
[BASEU]
Version=<repris du [BASE] standard>
Nom=GtfAt,Article tarif,1            ; libelle IDENTIQUE au standard
DateM=<repris du standard>
DateMIndex=<FILETIME courant>        ; nouveau, marque la modif d'index
[TABLES]
[/TABLES]
```

**Sans ce bloc, l'index est orphelin** -- xwin7 accepte la compilation, synchroauto retourne 0 erreur, mais l'index **n'est jamais cree** en base. C'est probablement le bloc le plus critique manquant lors d'une premiere tentative.

Conventions :

- `Version=`, `Nom=`, `DateM=` recopies du `[BASE]` standard (anti-pattern D14 sinon)
- `DateMIndex=` est specifique `[BASEU]`, FILETIME courant
- `[TABLES]/[/TABLES]` typiquement vide (le merge avec le standard recupere les tables)

---

## Bloc `[INDEXL]` final

A la fin du `<dict>u.dhsd`, un bloc `[INDEXL]/[/INDEXL]` global contient **une ligne par index custom** :

```ini
[INDEXL]
Nom=GtfAt,ART,index_miRajout,0
Nom=GtfAt,ART,index_miRajoutFl_ean,0
[/INDEXL]
```

Format `Nom=<NomBase>,<NomTable>,<NomIndex>,<flag>` (4 valeurs, dernier toujours `0`).

Le standard a son propre `[INDEXL]` global qui mappe tous ses index ; la surcharge a son `[INDEXL]` qui contient **uniquement les nouveaux index custom**. Le merge concatene les deux a la compilation.

---

## Convention de nommage `index_<descriptif>`

Le standard utilise `Index_<Lettre>` (PascalCase + 1 caractere alphanumerique) -- ex: `Index_A`, `Index_B`, `Index_K`.

Les index custom de surcharge utilisent une convention differente : `index_<NomDescriptif>` (snake_case minuscule, descriptif libre). Exemples observes :

- `index_miRajout` -- index sur le champ ajoute miRajoutFl
- `index_miRajoutFl_ean` -- index filtre sur les records ayant un EAN
- `index_<entite>_<critere>` -- generaliser au cas par cas

> Convention non documentee dans la zone 4 standard. Cette convention `index_<descriptif>` minuscule permet une distinction immediate visuelle entre index standard et index de surcharge.

---

## Variantes position 7 -- 3 types d'index

La position 7 de `CLE=` indique le **type d'index**. Trois valeurs observees dans le standard sur table ART (base GtfAt) :

| Type | Position 7 | Particularite `[CHAMPS]` | Cas d'usage |
|------|------------|--------------------------|-------------|
| **Principal** | `1` | Champs metier (pas de Ce1) | Index principal de la table, pas de filtre, 1 par table |
| **Conditionnel / filtre** | `4` | Champs metier (pas de Ce1) | **1 seule table SQL**, filtre via Ce<N> -> SQL filtered index |
| **Avec identifiant** | `5` | **Ce1 PRESENT dans la cle** (ex: offset 9) | Plusieurs tables SQL partagent l'index, Ce1 discrimine le type |

### Exemples standard (table ART, base GtfAt)

| Index | Position 7 | CLE | Semantique |
|-------|------------|-----|------------|
| `Index_A` "Par reference" | `1` | `GtfAt,A,Ce1,2,1,n,1,n` | Index principal sur Dos+Ref |
| `Index_I` "Par EAN" | `4` | `GtfAt,I,Ce4,2,1,n,4,n` | Filtre sur Ce4='1' = articles avec EAN |
| `Index_L` partage Cli/Fou/Pro | `5` | `GtfPcf,L,Ce5,2,1,n,5,n` | Multi-table, Ce1 discrimine le tiers |

### Regle pour un index custom de surcharge

| Cas | Position 7 | `[CHAMPS]` doit contenir Ce1 ? |
|-----|------------|---------------------------------|
| Index simple sur 1 table | `4` | Non |
| Index filtre via colonne Ce<N> calculee mchk | `4` | Non |
| Index partage entre plusieurs tables (rare en surcharge) | `5` | Oui (Ce1 a un offset dans la cle) |

**Erreur classique** : copier `5` par analogie avec un `Index_L_<X>` du standard sans verifier que cet index est partage entre plusieurs tables. Verifier **systematiquement** le contenu `[CHAMPS]` de l'index standard de reference :

- `[CHAMPS]` contient `Nom=Ce1,...` -> standard de type "avec identifiant" (5), partage entre tables
- `[CHAMPS]` ne contient pas Ce1 -> standard de type "conditionnel" (4) ou "principal" (1)

Pour un index custom **uniquement sur la table cible** (cas courant en surcharge), le type correct est **`4` conditionnel**, pas `5`.

---

## Filtered indexes Divalto

Mecanisme : un index "conditionnel" (position 7 = `4`) est materialise en SQL Server comme un **filtered index** (`CREATE INDEX ... WHERE <colonne> = '<valeur>'`). Le filtre passe par une **colonne discriminante calculee par mchk** a chaque ecriture du record.

### Anatomie

| Element | Role |
|---------|------|
| `Ce<N>` (champ table) | Colonne discriminante calculee par le mchk -- valeur etat-de-fait du record |
| Position 3 de `CLE=` | Reference au champ discriminant (ex: `Ce4`) |
| Position 5 de `CLE=` | **Valeur** du discriminant a filtrer (ex: `1` = "inclure dans l'index si Ce4='1'") |
| Position 7 de `CLE=` | Marqueur "filtre" : `4` |
| Synchro SQL | Genere un `CREATE INDEX ... WHERE <CeN>='<valeur>'` -- vrai filtered index SQL Server |

Effet : l'index ne contient **que les records dont la valeur du champ discriminant est celle indiquee**. C'est un filtered index materialise via **colonne calculee**, pas via clause `WHERE` libre.

### Exemple : `Index_I` "Par EAN" sur ART

Le standard declare dans `gttmchkart.dhsp` :

```diva
ART.Ce4 = Condition(ART.Ean <> ' ', '1', ' ')
```

`Ce4` est un champ ordinaire de la table ART (au cote de Dos, Ref, Ean, ...), **automatiquement calcule** par le mchk a chaque ecriture :

- Si `ART.Ean` non vide -> `ART.Ce4 = '1'`
- Sinon -> `ART.Ce4 = ' '`

Et `Index_I` est defini ainsi :

```ini
[INDEX]
Nom=Index_I,Par EAN,1
CLE=GtfAt,I,Ce4,2,1,n,4,n              ; filtre sur Ce4='1' (= avec EAN)
[CHAMPS]
Nom=Dos,1,0,
Nom=Ean,9,0,
[/CHAMPS]
[/INDEX]
```

Resultat SQL : un filtered index nonclustered sur `(DOS, EAN)` avec clause `WHERE CE4 = '1'`.

### Pattern pour un filtered index custom

1. Identifier (ou ajouter) un champ `Ce<N>` calcule par le mchk de surcharge
2. Declarer un index avec `CLE=<base>, ,Ce<N>,2,<valeur>,n,4,n` + `Alias=<nom>`
3. Renseigner `[CHAMPS]` avec les colonnes a indexer (sans Ce1)
4. Reference dans `[INDEXL]`

> Pour ajouter un nouveau `Ce<N>` custom (au-dela des Ce<N> standards), il faut a la fois :
> - Declarer le champ `Ce<N>` dans le `[CHAMPS]` de la surcharge de table (`[CHAMPR]`)
> - Maintenir sa valeur via le mchk de surcharge (`OverWrittenBy` du mchk standard, voir `coding-diva-advanced/overwrite-pattern.md`)

---

## Workflow complet

Surcharge d'un index custom -- sequence canonique :

1. **Pre-requis** : les champs cibles existent dans la surcharge `.dhsd` (cf. [dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md))
2. **Declarer `[BASEU]`** pour la base cible (avec metadonnees recopiees du standard)
3. **Declarer `[INDEX]`** avec `CLE=<base>, ,<discriminant>,2,<valeur>,n,<type>,n` + `Alias=<nom>`
4. **Renseigner `[CHAMPS]`** avec les colonnes a indexer, offsets cumules
5. **Ajouter la ligne dans `[INDEXL]`** : `Nom=<base>,<table>,<alias>,0`
6. **Buildall + synchroauto** -- verifier que l'index apparait en SQL Server
7. **Verifier l'index en SQL** : `SELECT name, has_filter, filter_definition FROM sys.indexes WHERE name = '<NomIndex>'`

Si l'index n'apparait pas malgre 0 erreur compile/synchro : verifier dans l'ordre les 6 points ci-dessous (les "ecarts marketplace classiques").

---

## Anti-patterns

Les 6 ecarts classiques (premiere tentative de surcharge d'index, erreurs structurelles silencieuses) :

| # | Ecart | Symptome | Correctif |
|---|-------|----------|-----------|
| 1 | Plusieurs `[CHAMPR]` au lieu d'un seul global | Le 2eme `[CHAMPR]` est ignore, colonnes custom non creees | Un seul `[CHAMPR]/[/CHAMPR]` avec plusieurs `nom=U<X>` a l'interieur |
| 2 | `[BASEU]` manquant | Index orphelin, jamais cree en base | Ajouter `[BASEU]` avec metadonnees recopiees du standard |
| 3 | Position 2 de `CLE=` = lettre arbitraire (ex `z`) | xwin7 accepte mais index conflictuel | Utiliser un espace + ligne `Alias=<nom>` |
| 4 | `Alias=<nom>` manquant apres `CLE=<base>, ,...` | Pas de nom logique pour `[INDEXL]` | Ajouter `Alias=<NomIndex>` immediatement apres `CLE=` |
| 5 | `[INDEXL]` final manquant | Index non mappe vers la base | Ajouter `[INDEXL]/[/INDEXL]` global avec une ligne par index custom |
| 6 | Nommage `Index_<Lettre>` au lieu de `index_<descriptif>` | Conflit avec un index standard | Utiliser la convention `index_<descriptif>` (snake_case) |

Tous ces ecarts **ne produisent aucune erreur de compilation ni de synchro**. Echec runtime invisible. Verification post-synchroauto en SQL recommandee.
