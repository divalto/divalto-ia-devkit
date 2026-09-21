# Surcharge dictionnaire `.dhsd` -- pattern complet

## Contenu

- Quand surcharger un dictionnaire
- Prerequis -- container U<NomTable> dans le standard
- **`Filler` vs container `U` -- deux reserves, deux proprietaires**
- Structure du fichier `<dict>u.dhsd`
- Bloc `[CHAMP]` -- declarations globales
- Bloc `[CHAMPR]` / `[CHAMPL]` -- ancrage et offsets
- Bloc `[TABLEU]` -- ancrage table
- Bloc `[BASEU]` -- ancrage base
- Regle d'offset cumule dans le U-container
- Options A/B/C : modifier un champ standard est interdit
- Workflow complet
- Anti-patterns associes (DICT14/DICT15/DICT16)

---

## Quand surcharger un dictionnaire

La surcharge `.dhsd` permet d'**ajouter des champs custom** sur une table du standard livre, **sans modifier** le `.dhsd` standard. Le fichier de surcharge (`<dict>u.dhsd`) vit dans un projet de surcharge, est compile par xwin7 conjointement au standard, et produit une table SQL etendue avec les colonnes ajoutees.

Cas typiques :

- Ajouter un flag metier sur une table (ex: `miRajoutFl` sur `ART`)
- Ajouter une date ou un libelle custom (ex: `miRajoutDt` + `miRajoutLib` sur `ART`)
- Etendre plusieurs tables en parallele dans une meme surcharge

> Note : la surcharge `.dhsd` est **un maillon** de la chaine d'ajout d'un champ custom utilisable dans un masque. Voir le workflow complet ci-dessous (chaine `.dhsd` -> SQL -> `.dhsq` -> `.dhsf`).

---

## Prerequis -- container `U<NomTable>` dans le standard

La surcharge `.dhsd` repose sur un **point d'ancrage explicite** : le container `U<NomTable>` declare dans le `[CHAMPS]` de la table standard. Ce container est une zone d'octets reservee par le concepteur du standard pour permettre l'extension par les distributeurs/integrateurs.

**Regle dure** : si la table standard n'a pas de container `U<NomTable>` dans son `[CHAMPS]`, elle n'a **pas ete concue pour etre surchargeable**. Toute tentative est une mauvaise pratique :

1. Risque de **corruption silencieuse** si le standard ajoute un champ a l'offset choisi par la surcharge dans une release future
2. Pattern non documente, non supporte par xwin7 -- comportement runtime non garanti
3. Viole le principe "ne pas modifier le standard"

### Verifier qu'une table est surchargeable

Avant toute surcharge, ouvrir le `.dhsd` standard et chercher la table cible :

```ini
[TABLE]
Nom=ART,Article,1
...
[CHAMPS]
Nom=Ce1,1,2,N,0,0,N,3
Nom=Dos,2,2,N,0,0,N,3
...
Nom=UArt,847,2,N,0,0,N,3    <-- container present, Nature=1500 -> table surchargeable
[/CHAMPS]
```

Si `Nom=U<NomTable>` est absent du `[CHAMPS]`, **la table n'est pas surchargeable**. Options legitimes :

- Demander a Divalto d'ajouter un container dans une prochaine release
- Rediriger le besoin metier vers une autre table surchargeable
- Sinon abandonner la demande (anti-pattern DICT15)

> Voir aussi la regle de gouvernance : tout cas de table sans U-container devrait etre remonte a Divalto (catalogue evolutif des defauts de conception du standard).

---

## `Filler` vs container `U` -- deux reserves, deux proprietaires

Dans un `[CHAMPS]`, `Filler` et `U<NomTable>` se ressemblent : deux zones d'octets sans
usage metier, en fin de table. Ce sont pourtant **deux reserves distinctes, appartenant a
deux acteurs differents** -- et s'y tromper est la cause la plus directe de corruption
silencieuse.

| Zone | Proprietaire | Evolution observee entre deux versions majeures du standard |
|------|--------------|--------------------------------------------------------------|
| `Filler` | **Divalto** | **262 tables** l'ont vu **diminuer** : l'editeur consomme sa propre reserve pour ajouter des champs standard **a taille de table constante** |
| `U<NomTable>` | **le distributeur / l'integrateur** | **5 changements** seulement sur le meme pas -- une zone `U` reste **stable ou s'agrandit** |

**Regle** : le seul point d'ancrage legitime d'un champ custom est le container
`U<NomTable>`. Ancrer un champ dans le `Filler`, ou a un offset pris « dans ce qui reste
apres le dernier champ », revient a **poser son champ dans la reserve de Divalto** : la
prochaine release y ecrira ses propres champs, a la meme place, **sans changer la taille
de la table** -- donc **sans qu'aucun controle de compatibilite ne le detecte**.

> Une reduction de zone `U` est en soi **anormale** (nous en avons mesure une seule, qui
> s'analyse comme une correction d'une valeur erronee). Si un pas de version reduit une
> zone `U` que vous utilisez, c'est a **remonter a Divalto**.

### Corollaire rassurant : un Service Pack qui mange du `Filler` est transparent

Si vos champs sont dans la zone `U`, **vous n'avez rien a verifier** cote `Filler` : le
standard consomme sa reserve, la taille de la table ne change pas, vos offsets sont
intacts. C'est precisement la contrepartie de la regle -- elle est contraignante a
l'ecriture, et elle vous protege ensuite.

Reste le cas ou la table **change de taille** : la, il faut recompiler votre specifique
(voir [dhsd-diff-downgrade.md](dhsd-diff-downgrade.md), section « Compatibilite binaire »).

### Piege de lecture : la capacite d'un `U` n'est PAS sur la ligne `[CHAMPS]`

Les deux zones n'exposent pas leur taille au meme endroit :

```ini
Nom=Filler,2097,2,N,0,404,N,1     <-- 404 octets : la taille est EN LIGNE (6e position)
Nom=UArt,847,2,N,0,0,N,3          <-- 0 en 6e position : ce n'est PAS une zone vide !
```

Pour un container `U<X>`, la 6e position vaut **toujours 0**. Sa capacite reelle est la
**`Nature=` de sa declaration globale** dans le bloc `[CHAMP]` (ici `UArt` -> `Nature=1500`,
soit 1500 octets). Lire la 6e position conduit a conclure « container vide / capacite 0 »
sur **toutes** les tables surchargeables.

---

## Structure du fichier `<dict>u.dhsd`

Encodage : **ISO-8859-1 + CRLF** (identique au standard).

```ini
;>xwinobj      dictionnaire
[Dictionnaire]
Version=1,,,20260512143000,USER_PADDE_20_CHARS
Nom=gtfdd.dhsd,gtfdd.dhsd,1    ; IDENTIQUE au standard, pas le nom de la surcharge

; --- DECLARATIONS GLOBALES DES CHAMPS AJOUTES ---

[CHAMP]
Version=1,20260512143000,USER,20260512143000,USER
Nom=miRajoutFl,Flag de rajout,1
Gel=1                            ; convention surcharge (vs Gel=3 standard)
Nature=1,0
Flags=n,1,n,n,n,n,n,n,n          ; 9 flags, 1er=n (vs 1er=o standard)

[CHAMP]
Version=1,20260512143000,USER,20260512143000,USER
Nom=miRajoutDt,Date de rajout,1
Gel=1
Nature=D8
Flags=n,1,n,n,n,n,n,n,n

[CHAMP]
Version=1,20260512143000,USER,20260512143000,USER
Nom=miRajoutLib,Libelle de rajout,1
Gel=1
Nature=20
Flags=n,1,n,n,n,n,n,n,n

; --- ANCRAGE DES CHAMPS SUR LES TABLES STANDARD ---

[CHAMPR]
nom=UArt                         ; ancrage sur le container UArt de la table ART standard
[CHAMPL]
Nom=miRajoutFl,1,0,0,N,1         ; offset 1 dans UArt
Nom=miRajoutDt,2,0,0,N,1         ; offset 2 = 1 + taille(miRajoutFl=1,0 -> 1 octet)
Nom=miRajoutLib,10,0,0,N,1       ; offset 10 = 2 + taille(miRajoutDt=D8 -> 8 octets)
[/CHAMPL]
nom=UCli                         ; ancrage sur le container UCli de la table CLI (meme bloc CHAMPR)
[CHAMPL]
Nom=miRajoutFl,1,0,0,N,1
[/CHAMPL]
[/CHAMPR]

; --- METADONNEES TABLE (recopiees du standard) ---

[TABLEU]
Version=<repris du standard de la table>
Nom=ART,Article,1
DateM=<ts_origine_table_du_standard>,<ts_derniere_modif_FILETIME_courant>

[TABLEU]
Version=<repris du standard de la table>
Nom=CLI,Client,1
DateM=<ts_origine_table_du_standard>,<ts_derniere_modif_FILETIME_courant>

; --- METADONNEES BASE (recopiees du standard) ---

[BASEU]
Version=<repris du standard de la base>
Nom=GtfAt,Article tarif,1
DateM=<repris du standard>
DateMIndex=<FILETIME courant>
[TABLES]
[/TABLES]
```

---

## Bloc `[CHAMP]` -- declarations globales

Un bloc `[CHAMP]` par champ ajoute. Conventions surcharge :

| Ligne | Standard (`gtfdd.dhsd`) | Surcharge (`<dict>u.dhsd`) |
|-------|-------------------------|-----------------------------|
| `Version=` | timestamps + createur initial | `1,<ts>,<USER>,<ts>,<USER>` (le createur de la surcharge) |
| `Nom=` | `<X>,<libelle>,1` | identique |
| `Gel=` | `3` | **`1`** (convention surcharge) |
| `Nature=` | code Nature | code Nature -- meme grammaire |
| `Flags=` | `o,1,n,n,n,n,n,n,n` | **`n,1,n,n,n,n,n,n,n`** (1er flag = `n`) |
| `NomOdbc=` | optionnel | optionnel |

**Pourquoi `Gel=1` et 1er flag `n`** : marquent le champ comme "ajout de surcharge", visible par xwin7 et le synchroauto pour le distinguer des champs standard. Ne pas s'ecarter de cette convention.

---

## Bloc `[CHAMPR]` / `[CHAMPL]` -- ancrage et offsets

`[CHAMPR]` = "Champs Rajoutes". Le bloc declare **dans quel container** les champs ajoutes vivent.

**Regle critique** : il y a **UN SEUL bloc** `[CHAMPR]/[/CHAMPR]` au global du fichier surcharge, pas un par table cible. A l'interieur du bloc, on enchaine plusieurs paires `nom=U<X>` + `[CHAMPL]...[/CHAMPL]` :

```ini
[CHAMPR]
nom=UArt
[CHAMPL]
Nom=miRajoutFl,1,0,0,N,1
...
[/CHAMPL]
nom=UCli                         <-- pas de [CHAMPR] reouvert
[CHAMPL]
Nom=miRajoutFl,1,0,0,N,1
[/CHAMPL]
[/CHAMPR]
```

> Erreur classique : ouvrir un `[CHAMPR]` par table cible. xwin7 ne signale pas d'erreur de compilation, mais le **2eme bloc est silencieusement ignore** -- les colonnes correspondantes ne sont jamais creees en base.

Format `[CHAMPL]` : `Nom=<NomChamp>,<offset_octets_1based>,0,0,N,1`. Le **1er nombre est l'offset en octets, 1-based**, dans le bloc `U<NomTable>` (cf. regle d'offset cumule).

### Composite reutilisable cross-tables

Un meme `nom=<composite>` declare dans `[CHAMPR]` peut etre **reference depuis plusieurs U-containers**. Pattern observe :

```ini
; Declaration globale d'un champ composite
[CHAMP]
Nom=miNiv1,Niveau hierarchique 1,1
Gel=1
Nature=20
Flags=n,1,n,n,n,n,n,n,n

; Ancrage sur 2 tables differentes
[CHAMPR]
nom=UArt
[CHAMPL]
Nom=miNiv1,31,0,0,N,1
[/CHAMPL]
nom=UCli
[CHAMPL]
Nom=miNiv1,36,0,0,N,1
[/CHAMPL]
[/CHAMPR]
```

Resultat SQL : les tables `ART` et `CLI` recoivent toutes deux la colonne `MINIV1` au sein de leur U-container respectif.

---

## Bloc `[TABLEU]` -- ancrage table

Un bloc `[TABLEU]` par table cible. **Metadonnees recopiees du `[TABLE]` standard correspondant** :

```ini
[TABLEU]
Version=<repris du [TABLE] standard>
Nom=ART,Article,1                          ; libelle IDENTIQUE au standard
DateM=<ts_origine_du_standard>,<FILETIME_courant>
```

- `Version=`, `Nom=`, premier `DateM=` -- recopies a l'identique du `[TABLE]` standard
- Second `DateM=` (timestamp FILETIME) -- date courante (modif de la surcharge)

**Ne JAMAIS inventer** un libelle ou un timestamp `DateM` : un `Nom=ART,Article extension,1` divergeant peut casser le merge surcharge/standard de facon non deterministe (anti-pattern DICT14).

---

## Bloc `[BASEU]` -- ancrage base

Un bloc `[BASEU]` par base cible. **Metadonnees recopiees du `[BASE]` standard correspondant**, plus `DateMIndex=` specifique :

```ini
[BASEU]
Version=<repris du [BASE] standard>
Nom=GtfAt,Article tarif,1                  ; libelle IDENTIQUE au standard
DateM=<repris du standard>
DateMIndex=<FILETIME courant>              ; nouveau, timestamp dernier index custom
[TABLES]
[/TABLES]
```

- `Version=`, `Nom=`, `DateM=` -- recopies du `[BASE]` standard
- `DateMIndex=` -- specifique `[BASEU]`, FILETIME courant
- `[TABLES]/[/TABLES]` typiquement **vide** dans la surcharge (le merge avec le standard recupere les tables)

`[BASEU]` est **obligatoire** si l'on ajoute des index custom (cf. `dhsd-surcharge-indexes.md`). Sans ce bloc, les index sont orphelins et silencieusement ignores au synchroauto.

---

## Regle d'offset cumule dans le U-container

Le premier nombre de chaque ligne `[CHAMPL] Nom=<X>,<offset>,...` est **l'offset en octets, 1-based**, dans le container `U<NomTable>`. Le calcul est **strictement cumulatif** :

```
offset(0)   = 1
offset(n+1) = offset(n) + taille(Nature(n))
```

Exemple valide (3 champs sur `UArt`, container Nature=1500) :

| # | Champ | Nature | Taille | Offset | Calcul |
|---|-------|--------|--------|--------|--------|
| 1 | miRajoutFl | `1,0` | 1 | **1** | debut UArt |
| 2 | miRajoutDt | `D8` | 8 | **2** | 1 + 1 |
| 3 | miRajoutLib | `20` | 20 | **10** | 2 + 8 |

> **Piege le plus dangereux de la surcharge dictionnaire** : interpretation "ordre d'ajout" (1, 2, 3) au lieu d'offsets cumules (1, 2, 10). xwin7 **n'effectue aucune verification de chevauchement** ; un mauvais offset est accepte au compile et au synchroauto, les colonnes en base se chevauchent silencieusement, les donnees runtime sont corrompues. Bug invisible jusqu'a l'execution, parfois bien apres mise en production.

> Voir [nature-types.md](nature-types.md) pour la taille en octets des Natures observees. Si la Nature n'est pas documentee (couverture ~40 %), inspecter le standard pour trouver un autre champ de meme Nature et confirmer la taille -- ne pas deviner.

### Contrainte de capacite du container

La somme des tailles des champs ajoutes ne doit pas depasser la taille du container :

```
sum(taille(champ_n)) <= taille(U<NomTable>)
```

Exemple : `UArt` est `Nature=1500`. Les 3 champs ci-dessus consomment 1 + 8 + 20 = 29 octets. Reste 1471 octets disponibles pour de futurs ajouts.

---

## Options A/B/C : modifier un champ standard est interdit

Quand un champ existe deja dans le `.dhsd` standard avec `[CHAMP] Nom=<X>,Nature=<Y>`, trois options se presentent en surcharge :

| Option | Action | Valide ? |
|--------|--------|----------|
| **A** | Reutiliser le champ tel quel (Nature standard inchangee) | OK |
| **B** | Creer un nouveau champ prefixe (`<prefixe><X>`, ex. `spe<X>`) avec Nature librement choisie | OK |
| **C** | Redeclarer le `[CHAMP]` standard avec Nature/Gel/Flags differents | **INTERDIT** |

L'option C est interdite car :

- Soit xwin7 rejette la redeclaration (compilation echoue)
- Soit (pire) il accepte et **applique le changement globalement** -- toutes les tables qui utilisent ce champ heritent de la nouvelle Nature -> casse `ART`, `ArtTax`, etc. silencieusement
- Viole le principe "ne pas modifier le standard"

Exemple :

- Standard : `[CHAMP] Nom=Ref,Reference,1 Nature=25 NomOdbc=Reference`
- Demande : ajouter un Ref de Nature=8 sur la table CLI
- Reponse correcte : refuser l'option C, proposer A (reutiliser Nature=25) ou B (creer `miRef` Nature=8 avec prefixe)

Anti-pattern DICT16. Le validator peut detecter en mode cross-reference avec `--dhsd-standard <path>`.

---

## Workflow complet

Surcharge `.dhsd` -> ajout d'un champ custom utilisable dans un masque. Sequence canonique :

1. **Surcharger le dictionnaire `.dhsd`** -- ajouter le champ dans un U-container reserve (present document)
2. **Synchroniser SQL** (`buildall` + `synchroauto`) -- creer la colonne SQL via `synchroauto` ; verifier `C:\divalto\DivaltoLog\DhOdbcConfigSqlScript.sql` ou via le skill `syncing-diva-sql`
3. **Surcharger le RecordSql `.dhsq`** -- recompiler le RecordSql pour exposer la nouvelle colonne (voir `generating-recordsql/reference/dhsq-overwrite-pattern.md` -- delta strict)
4. **Surcharger le masque `.dhsf`** -- ajouter le composant qui reference le champ via `donnee=record,champ,instance` (voir `manipulating-dhsf-screens`)

Sans l'etape 3, le masque echoue meme si la colonne SQL existe. Sans l'etape 1, rien ne fonctionne (la colonne SQL n'existe pas).

### Verification synchroauto

Apres `buildall` + `synchroauto`, comparer le nombre de colonnes SQL avant/apres :

```sql
SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'ART';
-- attendu : nb_colonnes_standard + nb_champs_ajoutes
```

Si le compte n'augmente pas, le merge surcharge/standard a echoue silencieusement -- verifier les metadonnees `[BASEU]`/`[TABLEU]` (anti-pattern DICT14) ou l'existence du U-container cible (anti-pattern DICT15).

---

## Anti-patterns associes

| Code | Severite | Quoi |
|------|----------|------|
| DICT14 | warning (error si `--dhsd-standard` fourni) | Metadonnees `[BASEU]/[TABLEU]` divergentes du standard (libelle, Version, DateM) |
| DICT15 | error | Ajout `[CHAMPR] nom=<X>` sans container `U<NomTable>` correspondant dans le standard -- table non surchargeable |
| DICT16 | error | Redeclaration d'un `[CHAMP]` global du standard avec Nature/Gel/Flags differents -- option C interdite |

Voir [dhsd-anti-patterns.md](dhsd-anti-patterns.md) pour le detail des regles DICT01-DICT16.
