# Les 5 zones a modifier pour ajouter une table dans un .dhsd

## Contenu

- Vue d'ensemble
- Zone 1 : [CHAMP] -- Declaration des champs
- Zone 2 : [TABLE] -- Structure de la table
- Zone 3 : [BASE] -- Fichier physique
- Zone 4 : [INDEX] -- Definition d'index
- Zone 5 : [INDEXL] -- Mapping base/table/index

---


Source : `docs/DICTIONNAIRE-DHSD.md`.

---

## Vue d'ensemble

Pour ajouter une table dans un dictionnaire, il faut modifier **5 zones** dans l'ordre :

```
[CHAMP] -> [TABLE] -> [BASE] -> [INDEX] -> [INDEXL]
```

Chaque zone est triee par ordre alphabetique de son nom. Le fichier est en ISO-8859-1 + CRLF.

---

## Zone 1 : [CHAMP] -- Declaration des champs

Un bloc `[CHAMP]` par champ metier **nouveau**. Les champs standard (Ce1, Dos, UserCr, UserMo, UserTrace) existent deja -- ne pas les redeclarer. `Filler` est un mot-cle special sans declaration.

### Format

```ini
[CHAMP]
Version=1,20260101120000,Claude              ,20260101120000,Claude              
Nom=MonChamp,Description du champ,1
Gel=3
Nature=20
NomOdbc=MonChamp
Flags=o,1,n,n,n,n,n,n,n
```

### Champs du bloc

| Ligne | Obligatoire | Valeur |
|-------|-------------|--------|
| `Version=` | Oui | `1,{timestamp},{createur_20car},{timestamp},{modificateur_20car}` |
| `Nom=` | Oui | `{NomChamp},{Description},1` -- toujours `,1` a la fin |
| `Gel=` | Oui | `3` (standard) ou `1` (verrouille) |
| `Nature=` | Oui | Code nature (voir nature-types.md) |
| `NomOdbc=` | Non | Nom SQL si different du nom DIVA |
| `Flags=` | Oui | `o,1,n,n,n,n,n,n,n` (standard) |

### U-field (champ reserve distributeur)

Chaque table doit avoir un champ `U{NomTable}`. Declaration :

```ini
[CHAMP]
Version=1,{timestamp},{createur},{timestamp},{modificateur}
Nom=U{NomTable},Reserve distributeur {NomTable},1
Gel=3
Nature={taille_reserve}
NomOdbc=U{NomTable}
Flags=n,1,o,o,n,n,n,n,o
```

**Attention** : Les Flags du U-field sont differents (`n,1,o,o,n,n,n,n,o`).

---

## Zone 2 : [TABLE] -- Structure de la table

### Format

```ini
[TABLE]
Version=1,{timestamp},{createur},{timestamp},{modificateur}
Nom={NomTable},{Description},1
NomOdbc={Nom_SQL}
Taille={taille},{taille}
Pack=0,0
CE=Ce1,{ValeurCE}
[CHAMPS]
Nom=Ce1,1,2,N,0,0,N,3
Nom=Dos,{pos_dos},2,N,0,0,N,3
Nom={Champ1},{pos1},2,N,0,0,N,3
...
Nom=UserCr,{pos_usercr},2,N,0,0,N,3
Nom=UserMo,{pos_usermo},2,N,0,0,N,3
Nom=UserTrace,{pos_usertrace},2,N,0,0,N,3
Nom=Filler,{pos_filler},2,N,0,{taille_filler},N,1
Nom=U{NomTable},{pos_ufield},2,N,0,0,N,3
[/CHAMPS]
```

### Calcul des positions (REGLE FONDAMENTALE)

**Pas de trou** entre les champs :

```
Position(champ N+1) = Position(champ N) + Nature(champ N)
```

Le premier champ (Ce1) commence a la position 1.

### Calcul de la taille

```
Taille = Position(dernier champ) + Nature(dernier champ) - 1
```

La valeur est doublee : `Taille={T},{T}`.

### Ordre des champs dans [CHAMPS]

1. `Ce1` (position 1, Nature=1)
2. `Dos` (Nature=8)
3. Champs metier (par ordre logique)
4. `UserCr` (Nature=20)
5. `UserMo` (Nature=20)
6. `UserTrace` (Nature=28)
7. `Filler` (bourrage, Gel=1, 6e champ = taille du bourrage)
8. `U{NomTable}` (reserve distributeur, dernier)

### Format d'une ligne [CHAMPS]

`Nom={NomChamp},{Position},2,N,0,{Repetition},N,{Gel}`

| Champ | Valeur |
|-------|--------|
| Position | Position en octets (commence a 1) |
| 3e | Toujours `2` |
| 4e | Toujours `N` |
| 5e | Toujours `0` |
| Repetition | `0` sauf Filler (= taille bourrage) |
| 7e | Toujours `N` |
| Gel | `3` (standard) ou `1` (Filler, verrouille) |

### CE -- Code enregistrement

`CE=Ce1,{Lettre}` ou `Lettre` est unique dans la base (1-9, puis A-Z).

---

## Zone 3 : [BASE] -- Fichier physique

### Format

```ini
[BASE]
Version=1,{timestamp},{createur},{timestamp},{modificateur}
Nom={PrefixeBase}{NomBase},{Description},1
DateM={hash}
Fichier=I,0,{PREFIXEBASE}{NOMBASE}.dhfi
Versionbase=223
DateMIndex={hash}
[TABLES]
Nom={NomTable},0
[/TABLES]
```

### Convention de prefixe

Le prefixe de la base depend du dictionnaire :

| Dictionnaire | Prefixe base |
|-------------|-------------|
| gtfdd.dhsd | Gtf |
| ccfdd.dhsd | Ccf |
| rtlfdd.dhsd | Rtl |
| ggfdd.dhsd | Ggf |
| wmsfdd.dhsd | Wms |
| ppfdd.dhsd | Ppf |
| a5dd.dhsd | A5f |

### Points cles

- `Fichier=I,0,{NOM}.dhfi` : format fixe (le nom est en MAJUSCULES)
- `Versionbase=223` : valeur standard
- Une base peut contenir **plusieurs tables** -- dans ce cas, ajouter la nouvelle table dans `[TABLES]`
- Pour une nouvelle base, creer un nouveau bloc `[BASE]`
- `DateM` et `DateMIndex` : hash hex genere automatiquement (utiliser un hash aleatoire)

---

## Zone 4 : [INDEX] -- Definition d'index

### Format

```ini
[INDEX]
Version=1,{timestamp},{createur},{timestamp},{modificateur}
Nom=Index_A,{Description},1
DateM={hash}
CLE={NomBase},{LettreIndex},{ChampCE},{flag},{ValeurCE},{Unique},{flag2},n
[CHAMPS]
Nom=Dos,1,0,
Nom={Champ1},{pos},0,
Nom={Champ2},{pos},0,
[/CHAMPS]
[/INDEX]
```

### Format CLE

`CLE={NomBase},{Lettre},{ChampCE},{flag},{ValeurCE},{Unique},{flag2},n`

| Champ | Description |
|-------|-------------|
| NomBase | Nom de la base physique (de la zone [BASE]) |
| Lettre | Lettre de l'index (A, B, C...) |
| ChampCE | Champ code enregistrement (Ce1, Ce) |
| flag | `2` (pour gtfdd) ou `1` (pour ccfdd) |
| ValeurCE | Valeur CE de la table (meme que dans CE= de la [TABLE]) |
| Unique | `o` (unique) ou `n` (non unique) |
| flag2 | `1` (standard) |
| dernier | Toujours `n` |

### Positions dans les CHAMPS d'index

Les positions sont cumulees a partir de 1 avec la taille de chaque champ :

```
Dos     pos=1   (Nature=8  -> suivant a 9)
Champ1  pos=9   (Nature=20 -> suivant a 29)
```

### Index minimum obligatoire

Au moins **Index_A** avec `Dos` + champ(s) cle metier.

---

## Zone 5 : [INDEXL] -- Mapping base/table/index

### Format

```
Nom={NomBase},{NomTable},{NomIndex},0
```

Une ligne par combinaison base/table/index, dans la section unique `[INDEXL]` du fichier.

Le dernier champ est toujours `0`. Tri par nom de base.

### Exemple

```
Nom=GtfMonEntite,MonEntite,Index_A,0
Nom=GtfMonEntite,MonEntite,Index_B,0
```
