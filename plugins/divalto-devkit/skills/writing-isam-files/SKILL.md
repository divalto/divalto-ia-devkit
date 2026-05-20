---
name: writing-isam-files
description: >
  Ecrit, modifie et supprime des enregistrements dans les fichiers binaires ISAM
  Divalto (.dhfi) via DhxIsam64.dll (ctypes). Supporte insert (unitaire + batch),
  update (trewritelong) et delete (tdeletelong).
  A utiliser pour toute ecriture dans les fichiers indexes proprietaires Divalto.
---

# Writing ISAM Files

## Contenu

- Regle fondamentale
- Utilisation rapide
- Operations (--op insert / update / delete)
- Workflow complet
- Ecriture par lot (batch)
- Dry run (simulation sans DLL)
- Scripts disponibles
- References

---

## Regle fondamentale

Les fichiers `.dhfi` sont des fichiers binaires proprietaires Divalto. Ils ne peuvent etre lus/ecrits qu'a travers la DLL `DhxIsam64.dll` situee dans `C:\divalto\sys\`.

- **Encoding des enregistrements** : Windows-1252 (ANSI)
- **Padding** : les champs texte sont paddes a droite avec des espaces (0x20)
- **Interdit** : toute manipulation directe du fichier binaire

### Identifier le bon chemin du .dhfi cible (R-006)

Le fichier physique peut se trouver dans plusieurs arborescences selon
l'historique d'installation ERP : `.../versionx9/...`, `.../VersionX13/...`,
ou d'autres. Ecrire dans le **mauvais** fichier fait silencieusement croire
que l'operation a reussi, mais l'ERP ne voit pas le changement (et une
synchro SQL posterieure ne crée pas la table).

**Avant toute ecriture ISAM**, identifier le chemin effectif :

1. Lancer `xwin7 -action synchroauto` (ou consulter son rapport precedent)
2. Chercher dans le log la ligne qui charge `fhsqldivalto.dhfi` ou le
   fichier cible (ex: `a5f.dhfi`)
3. Extraire le chemin **reellement utilise par le runtime** -- c'est la
   seule source de verite
4. Utiliser ce chemin dans les parametres `Fichier` du JSON passe a
   `write_isam.py`

Si deux ERP cohabitent sur la machine (X.12 + X.13, heritage versionx9),
verifier ce point systematiquement.

### Convention des champs numeriques -- cadrage a droite (auto)

Les champs numeriques stockes dans les ISAM Divalto sont **cadres a droite**
(padding espaces a gauche jusqu'a la taille du champ). L'index A trie les
enregistrements en comparant les octets bruts ; un champ numerique mal cadre
casse le tri.

`write_isam.py` **auto-cadre** les champs declares avec `"Justify": "right"`
dans la structure JSON. L'appelant peut passer la valeur **avec ou sans padding** :
le script strip puis re-padde a la taille du champ (idempotent).

Exemple champ `Ordre` (8 octets) dans `structure_xmenuf_m2.json` :

```json
{"Nom": "Ordre", "Offset": 9, "Taille": 8, "Justify": "right", ...}
```

Et le JSON data peut indifferemment utiliser :

```json
{"Donnees": {"Ordre": "51"}}        // auto-cadre -> stocke "      51"
{"Donnees": {"Ordre": "      51"}}  // deja cadre -> stocke "      51" (idem)
```

**Champs actuellement marques `Justify: right`** : `Ordre`, `EnrNo`, `ProduitNo`
dans `structure_xmenuf_m2.json`. Pour une structure non encore annotee, l'appelant
doit continuer a passer la valeur pre-cadree (comportement defaut `"Justify": "left"`
= texte, padding droit via init buffer a 0x20).

En cas de doute sur l'intention d'un champ, relire une entree existante avec
`read_isam.py` et observer si la valeur est stockee en debut (`"51      "`) ou
en fin (`"      51"`) des octets.

### Fichiers sensibles ERP -- fermer l'ERP avant ecriture

Certains fichiers ISAM sont **gardes en cache par l'ERP pendant une session
active**. Une ecriture `write_isam` pendant qu'une session est ouverte peut :

- provoquer des conflits de locks,
- creer des incoherences (ERP affiche l'ancien etat cache alors que le fichier
  a change sur disque),
- ne pas etre visible tant que l'ERP n'est pas relance.

**Liste des fichiers sensibles connus** :

| Fichier | Role | Verifie |
|---------|------|---------|
| `g3f.dhfi` (logique `Xmenuf`) | Menu domaine (M2) | 2026-04-20 |
| `a5f.dhfi` (logique `A5F`) | Zoom des zooms (M4) | [A VERIFIER] |

**Procedure avant toute ecriture sur un fichier sensible** :

1. Fermer la session ERP : **Autres actions > Se deconnecter**
2. Fermer le navigateur (`browser_close` si Playwright est utilise)
3. Lancer le `write_isam.py`
4. Relancer l'ERP pour observer le resultat

La procedure de deconnexion ERP est detaillee ci-dessus (etapes 1-4).

### Autorisation explicite pour les operations destructives

`--op delete` et `--op update` sur des fichiers **ERP standard partages**
(`g3f.dhfi`, `a5f.dhfi`, dictionnaires, etc.) modifient un etat global non
trivial a restaurer. Obtenir une autorisation **explicite** du collaborateur
avant d'executer, et annoncer **avant** l'operation d'insertion initiale ce
qui est prevu en cas d'echec (strategie de rollback prevue ou non) pour
permettre un feu vert conditionnel.

Operations sur des fichiers de test isoles (ex : `TestClaude/isam-exercice/*`)
ne necessitent pas ce checkpoint supplementaire -- seul le perimetre ERP
standard est concerne.

---

## Utilisation rapide

### Valider une structure

```bash
py .claude/skills/writing-isam-files/scripts/validate_structure.py \
    --path "structure_m4.json"
```

### Inserer un enregistrement (defaut)

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data_m4_racechien.json"
# equivaut a : --op insert
```

### Modifier un enregistrement

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data_update.json" --op update
```

### Supprimer un enregistrement

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data_delete.json" --op delete
```

## Operations

| Op | Description | Sequence DLL | Besoins JSON |
|----|-------------|--------------|--------------|
| `insert` (defaut) | Insertion d'un nouvel enreg | `xisam_twritelong` mode `P` | `Fichier`, `Structure`, `Donnees` |
| `update` | Modification d'un enreg existant | Positionnement TDF.KEY + read + verification exacte + `xisam_trewritelong` | `Fichier`, `Structure`, `Key`, `KeyFields`, `Donnees` |
| `delete` | Suppression d'un enreg existant | Positionnement TDF.KEY + read + verification exacte + `xisam_tdeletelong` | `Fichier`, `Structure`, `Key`, `KeyFields`, `Donnees` (cle uniquement) |

> **Revision 2026-04-22 (R-014 + ISAM-SCRIPT-03)** : la semantique du parametre `mode` de
> `treadlong`/`tpreadlong` a ete corrigee -- c'est un code de reservation (F/P/R), pas de
> direction. `update_single` et `delete_single` ont ete unifies sur `tpreadlong` mode `R`
> (Reserve) + verification exacte champ par champ. La reservation est liberee au
> `tcloselong`. Voir [reference/isam-api.md](reference/isam-api.md) section 10 pour le
> pattern detaille.

### Convention de cle pour update/delete

Deux modes au choix :

**Mode 1 (recommande) : nom d'index logique via `structure.Keys`**

Le fichier de structure declare les index sous la cle `Keys`, avec leur lettre DLL et les champs qui les composent :

```json
{
    "Keys": {
        "Index_A_M2": {"Letter": "A", "Fields": ["Ce", "Reg", "Ordre"]},
        "Index_B":    {"Letter": "B", "Fields": ["Ce", "Mnemo"]}
    }
}
```

Puis dans le JSON d'operation : `"Key": "Index_A_M2"` suffit, `KeyFields` est deduit.

**Mode 2 (fallback) : lettre + KeyFields explicites**

Si la structure n'a pas de section `Keys`, ou pour un index non declare : passer directement la lettre DLL + les champs de la cle :

```json
{
    "Key": "A",
    "KeyFields": ["Ce", "Reg", "Ordre"]
}
```

**Comportement du script** :

- Le script positionne `TDF.KEY[0]` = lettre, puis concatene les valeurs des `Fields` / `KeyFields` a partir de `KEY[1]`, avec padding (espaces) issu de la taille declaree.
- Une **verification champ par champ** est faite apres lecture : si l'enreg positionne ne correspond pas exactement a la cle cible, l'operation est refusee (code 2).

Exemple JSON update/delete complet (mode 1) :

```json
{
    "Fichier": "C:\\...\\g3f.dhfi",
    "Structure": "structure_xmenuf_m2.json",
    "Key": "Index_A_M2",
    "Donnees": {"Ce": "2", "Reg": "ZZZTEST", "Ordre": "10", "Lib": "..." }
}
```

> **Note sur `xisam_GetKeyByName`** : la DLL expose cette fonction qui devrait resoudre nom logique -> lettre DLL, mais elle agit comme un passthrough sans charger les implicites (nom 1 char = copie directe, nom >1 char = 0x00 sans erreur). La resolution necessite `xisam_LoadUtil` + mot de passe utilisateur, non trivial en Python. D'ou le choix de declarer les cles dans la structure JSON (deterministe, pas de dependance runtime).

---

## Workflow complet

### 1. Preparer le fichier de structure JSON

Le fichier de structure definit le mapping champs → offsets dans l'enregistrement binaire.
Format : `{Dictionnaire, Table, Base, TailleEnreg, Structure: [{Nom, Offset, Taille}]}`.

Voir [Specification formats JSON](reference/json-formats.md) pour le detail.

### 2. Preparer le fichier de donnees JSON

Le fichier de donnees contient le chemin du fichier .dhfi cible, la reference vers la structure, et les valeurs des champs.
Format : `{Fichier, Structure, Donnees: {NomChamp: "valeur"}}`.

Toutes les valeurs sont des **strings** (meme les numeriques).

### 3. Valider la structure (recommande)

```bash
py .claude/skills/writing-isam-files/scripts/validate_structure.py \
    --path "structure_m4.json"
```

Sortie attendue : `{"valid": true, "errors": [], "fields": 44, "record_size": 1000}`

### 4. Ecrire

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data.json"
```

Si les structures sont dans un autre repertoire :

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data.json" \
    --structure-dir "structures/"
```

### 5. Verifier la sortie JSON

```json
{"success": true, "total": 1, "written": 1, "skipped": 0, "errors": []}
```

- `written` : enregistrements ecrits avec succes
- `skipped` : doublons detectes (code 9 = E_EXIST, non bloquant)
- `errors` : liste detaillee `[{index, file, error_code, message}]`

---

## Ecriture par lot (batch)

### Meme fichier, plusieurs enregistrements

`Donnees` est un tableau :

```json
{
    "Fichier": "C:\\...\\a5f.dhfi",
    "Structure": "structure_m4.json",
    "Donnees": [
        {"Ce": "4", "ZoomNum": "22109", "Lib": "Consommation"},
        {"Ce": "4", "ZoomNum": "22110", "Lib": "Cave a vin"}
    ]
}
```

### Fichiers differents

Tableau top-level :

```json
[
    {"Fichier": "C:\\...\\a5f.dhfi", "Structure": "structure_m4.json", "Donnees": {...}},
    {"Fichier": "C:\\...\\fhsql.dhfi", "Structure": "structure_afsql.json", "Donnees": {...}}
]
```

---

## Dry run (simulation sans DLL)

Le flag `--dry-run` valide la structure et les donnees **sans appeler la DLL** :

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data.json" --dry-run
```

Utile pour verifier le format des JSON sur une machine sans Divalto installe.

---

## Scripts disponibles

| Script | Role | Entree | Sortie JSON |
|--------|------|--------|-------------|
| `scripts/write_isam.py` | Insert / update / delete d'enregistrements ISAM | `--params-file` ou `--stdin` [+ `--op insert\|update\|delete`] [+ `--structure-dir`] [+ `--dry-run`] | `{success, total, written, skipped, errors[]}` |
| `scripts/validate_structure.py` | Valide un fichier de structure JSON | `--path` | `{valid, errors[], fields, record_size}` |

**Exit codes** :

| Script | 0 | 1 | 2 |
|--------|---|---|---|
| `write_isam.py` | Tous ecrits | Erreurs partielles | Fatal (DLL absente, params illisible) |
| `validate_structure.py` | Structure valide | Structure invalide | Fichier introuvable |

---

## Structures pre-construites

| Structure | Fichier | Table | Taille |
|-----------|---------|-------|--------|
| Zoom des zooms (A5F.dhfi) | `scripts/structures/structure_a5f_m4.json` | M4 | 1000 octets, 46 champs (Ce=4) |
| Visibilite F7 (A5F.dhfi) | `scripts/structures/structure_a5f_m1.json` | M1 | 50 octets, 6 champs (Ce=5) -- R-002 |
| Menu domaine choix (Xmenuf .dhfi) | `scripts/structures/structure_xmenuf_m2.json` | M2 | 1000 octets, 21 champs (Ce=2) |
| Menu domaine header (Xmenuf .dhfi) | `scripts/structures/structure_xmenuf_m0.json` | M0 | 508 octets, 12 champs (Ce=0) -- R-006 |

Pour allouer un `EnrNo` libre avant d'ecrire un M2 custom, utiliser le skill dedie `allocating-menu-enrno` (plages `standard` < 100000 / `custom` >= 100000, R-005).

---

## References

- [Enregistrer un zoom dans A5F.dhfi](reference/a5f-zoom-record.md) -- champs essentiels, plages moulinette 58, exemple complet, piege ZoomEnr
- [API DhxIsam64 en Python ctypes](reference/isam-api.md) -- signatures, TDF51, mode=reservation (F/P/R), positionnement, reservations, pieges
- [Specification formats JSON](reference/json-formats.md) -- structure, data unitaire, batch, regles valeurs
- [Champ Echange du menu Xmenuf](reference/xmenuf-echange-zones.md) -- layout des 600 octets, strategies de clonage pour un insert M2
