# Formats JSON -- Structure et Data ISAM

## Contenu

- 1. Fichier de structure
- 2. Fichier de donnees -- Format unitaire
- 3. Fichier de donnees -- Batch meme fichier
- 4. Fichier de donnees -- Batch multi-fichiers
- 5. Regles sur les valeurs
- 6. Resolution du chemin Structure

---


## 1. Fichier de structure

Definit la correspondance entre les champs metier et leur position dans l'enregistrement binaire.

```json
{
    "Dictionnaire": "a5dd.dhsd",
    "Table": "M4",
    "Base": "A5f",
    "TailleEnreg": 1000,
    "Structure": [
        {"Nom": "Ce", "Offset": 0, "Taille": 1, "Description": "Code enregistrement"},
        {"Nom": "ZoomNum", "Offset": 1, "Taille": 5, "Description": "Numero du zoom"}
    ]
}
```

| Cle | Type | Description |
|-----|------|-------------|
| `Dictionnaire` | string | Fichier dictionnaire source (.dhsd) |
| `Table` | string | Nom de la table dans le dictionnaire |
| `Base` | string | Nom de la base physique (prefixe du .dhfi) |
| `TailleEnreg` | int | Taille totale de l'enregistrement en octets |
| `Keys` | object | Optionnel. Mapping `nom_d_index` -> `{Letter, Fields}` (voir ci-dessous) |
| `Structure` | array | Liste des champs avec Nom, Offset, Taille |

### Section `Keys` (optionnelle)

Declare les index du fichier ISAM pour resoudre un nom logique en lettre DLL + champs de la cle. Utilise par `write_isam.py --op update|delete` pour eviter au user de hardcoder la lettre et la liste des champs a chaque appel.

```json
{
    "Keys": {
        "Index_A_M2": {"Letter": "A", "Fields": ["Ce", "Reg", "Ordre"]},
        "Index_B":    {"Letter": "B", "Fields": ["Ce", "Mnemo"]},
        "Index_C":    {"Letter": "C", "Fields": ["Ce", "EnrNo"]}
    }
}
```

Les noms de cles `Index_*` proviennent de la zone `[INDEX]` du dictionnaire `.dhsd` Divalto (ligne `Nom=Index_...`). La lettre et les champs sont extraits des lignes `CLE=<base>,<lettre>,<prefix>,...` et `[CHAMPS] Nom=...`.

### Champ dans Structure

| Cle | Type | Description |
|-----|------|-------------|
| `Nom` | string | Nom du champ (unique dans la structure) |
| `Offset` | int >= 0 | Position en octets dans l'enregistrement (0-indexed) |
| `Taille` | int > 0 | Taille du champ en octets |
| `Type` | string | Optionnel. `C` (caractere, rstrip), `N` (numerique, strip), `D` (date, strip). Defaut : strip |
| `Description` | string | Optionnel. Description lisible |

### Semantique du champ `Type`

| Type | Decoding | Usage |
|------|----------|-------|
| `C` | `rstrip()` -- preserve les espaces de tete | Champs texte reguliers |
| `N` | `strip()` des 2 cotes | Champs numeriques cadres a droite (avec espaces devant) |
| `D` | `strip()` des 2 cotes | Champs date (formatage reserve a l'appelant) |
| absent | `strip()` des 2 cotes | Comportement historique (back-compat) |

### Contraintes

- `Offset + Taille <= TailleEnreg` pour chaque champ
- Les noms de champs doivent etre uniques
- Les offsets ne sont PAS forcement sequentiels (des zones reservees peuvent exister)

---

## 2. Fichier de donnees -- Format unitaire

Un seul enregistrement a ecrire.

```json
{
    "Fichier": "C:\\Developpements harmony\\Bases sql\\a5f.dhfi",
    "Structure": "structure_m4.json",
    "Donnees": {
        "Ce": "4",
        "ZoomNum": "22111",
        "Lib": "Race de chien",
        "ZoomEnr": "RaceChien",
        "ZoomFic": "ZOOMSQL"
    }
}
```

| Cle | Type | Description |
|-----|------|-------------|
| `Fichier` | string | Chemin absolu vers le fichier .dhfi cible |
| `Structure` | string | Nom du fichier de structure JSON (resolu relativement) |
| `Donnees` | object | Paires NomChamp: valeur (toutes les valeurs sont des strings) |

---

## 3. Fichier de donnees -- Batch meme fichier

Plusieurs enregistrements dans le meme fichier .dhfi.

```json
{
    "Fichier": "C:\\...\\a5f.dhfi",
    "Structure": "structure_m4.json",
    "Donnees": [
        {"Ce": "4", "ZoomNum": "22109", "Lib": "Consommation"},
        {"Ce": "4", "ZoomNum": "22110", "Lib": "Cave a vin - Bouteilles"}
    ]
}
```

`Donnees` est un tableau d'objets. Chaque objet suit le meme format que le format unitaire.

---

## 4. Fichier de donnees -- Batch multi-fichiers

Tableau top-level, chaque element vise un fichier/structure different.

```json
[
    {"Fichier": "C:\\...\\a5f.dhfi", "Structure": "structure_m4.json", "Donnees": {"Ce": "4", "ZoomNum": "22111"}},
    {"Fichier": "C:\\...\\fhsqldivalto.dhfi", "Structure": "structure_afsql.json", "Donnees": {"Ce": "A", "FichierHarmony": "gtfcons.dhfi"}}
]
```

---

## 5. Regles sur les valeurs

- Toutes les valeurs sont des **strings** (meme les numeriques : `"22111"`, `"223"`)
- Encoding : **Windows-1252** (codepage 1252 / ANSI)
- Les valeurs plus courtes que `Taille` sont **paddees a droite avec des espaces** (0x20)
- Les valeurs plus longues que `Taille` sont **tronquees** silencieusement
- **Cadrage droite** : les champs numeriques qui servent de cle d'index (ex: Ordre, ZoomNum)
  doivent etre **cadres a droite avec espaces devant** dans la valeur passee.
  Exemple : `"Ordre": "      14"` (6 espaces + "14"). L'index ISAM trie octet par octet
  (espace 0x20 < chiffre 0x30+), un cadrage a gauche trie mal.
- Les champs de la structure absents de `Donnees` restent remplis d'espaces
- Les champs de `Donnees` absents de la structure generent un warning (ignores)

---

## 6. Resolution du chemin Structure

Le champ `Structure` est un nom de fichier (ex: `"structure_m4.json"`), resolu dans cet ordre :

1. Si `--structure-dir` est fourni : relatif a ce repertoire
2. Sinon : relatif au repertoire du fichier `--params-file`
