# Enregistrer un zoom dans A5F.dhfi

## Contenu

- Structure pre-construite
- Champs essentiels
- Plages moulinette 58 (numeros de zoom par domaine)
- Exemple complet
- Apres l'ecriture
- Ajouter au menu du domaine

---


Reference pratique pour ecrire un enregistrement zoom (table M4) dans le fichier
A5F.dhfi (zoom des zooms). Voir `docs/ZOOM-INTEGRATION.md` pour la documentation
complete (structure, plages moulinette 58, menu domaine).

---

## Structure pre-construite

Le fichier de structure est fourni : `scripts/structures/structure_a5f_m4.json`.
Il contient le mapping des 46 champs de la table M4 (1000 octets).

Validation :

```bash
py .claude/skills/writing-isam-files/scripts/validate_structure.py \
    --path ".claude/skills/writing-isam-files/scripts/structures/structure_a5f_m4.json"
```

---

## Champs essentiels

Pour un zoom CRUD standard, renseigner au minimum :

| Champ | Valeur | Exemple |
|-------|--------|---------|
| Ce | **toujours "4"** | "4" |
| ZoomNum | Numero unique, cadre droite (respect plages moulinette 58) | " 9490" |
| Lib | Libelle du zoom | "Livre" |
| ZoomEnr | Nom de l'enregistrement (tel que dans le RecordSQL) | "LivreRS" |
| ZoomFic | **toujours "ZOOMSQL"** (generique, pas le nom physique) | "ZOOMSQL" |
| Ap | Code application du domaine | "DAV" |
| Reg | Regroupement dans l'arborescence | "LIVRE" |
| Ordre | Ordre d'affichage, **cadre droite** | "      10" |
| MsqEcran | Masque ecran **compile** (.dhof, pas .dhsf) | "gtezlivre_sql.dhof" |
| ModTrait | Module traitement **compile** (.dhop, pas .dhsp) | "gttzlivre_sql.dhop" |
| ConfM | Confidentialite modification — code de protection | "GzA" |
| ConfC | Confidentialite creation | "GzA" |
| ConfS | Confidentialite suppression | "GzA" |
| SceAction | Action du scenario (1=Standard) | "1" |
| SceMode | Mode initial (2=Liste) | "2" |
| SceSens | Sens lecture (1=Normal) | "1" |
| SceSaisie | Saisie cle depart (2=Oui) | "2" |
| SceCleCrea | Saisie cle en creation (2=Oui) | "2" |
| ChoixIZY | Divalto iZy actif (2=Oui) | "2" |
| ProductCode | Code produit (licencing) | "10999" |

Les champs non renseignes restent paddes avec des espaces (0x20).

**Regles critiques :**
- `ZoomFic` est toujours `ZOOMSQL` (pas le nom physique du fichier .dhfi)
- `MsqEcran` et `ModTrait` referent les fichiers **compiles** (.dhof/.dhop)
- Les champs numeriques dans les cles d'index (ZoomNum, Ordre) doivent etre **cadres a droite**

### Piege `ZoomEnr` : nom du RecordSql public, pas nom de table (R-007, 2026-04-22)

`ZoomEnr` **doit contenir le nom du RecordSql public** declare dans le module zoom
(`gttz<entite>_sql.dhsp`), et **pas** le nom de la table dans le dictionnaire.
Extraction : `grep "^Public RecordSql" gttz<entite>_sql.dhsp`. Exemple :
`Public RecordSql 'gtfrsracechien.dhoq' RaceChienGtf` -> `ZoomEnr = "RaceChienGtf"`.
Erreur runtime si incorrect : `"Le RecordSql public X n'est pas defini dans le
module gttz<entite>_sql.dhop"` au premier clic sur l'entree menu.

---

## Plages moulinette 58 (numeros de zoom par domaine)

| Domaine | Code Ap | Plage principale |
|---------|---------|-----------------|
| Commun | COMMUN | 11000-18999 |
| Comptabilite | DCPT | 19000-19999 |
| Achat-Vente | DAV | 9000-9999 |
| Paie | DPAIE | 25000-29999 |
| Relations Tiers | DRT | 30000-30999 |
| Affaires | DAFF | 31000-31999 |
| Processus | DSP | 32000-32999 |
| Qualite | DQUAL | 40000-40999 |
| Documents | DDOC | 41000-41999 |
| Controle | DCONT | 44000-44999 |
| Gestion Ressources | DGRM | 45000-45999 |
| Reglement | DREG | 49000-49999 |

Certains domaines ont des plages secondaires (voir `docs/ZOOM-INTEGRATION.md` section 4.2).

---

## Exemple complet

### Fichier de donnees (data_zoom_maentite.json)

```json
{
    "Fichier": "C:\\Developpements harmony\\Bases sql\\a5f.dhfi",
    "Structure": "structure_a5f_m4.json",
    "Donnees": {
        "Ce": "4",
        "ZoomNum": " 9490",
        "Lib": "Livre",
        "ZoomEnr": "LivreRS",
        "ZoomFic": "ZOOMSQL",
        "Ap": "DAV",
        "Reg": "LIVRE",
        "Ordre": "      10",
        "MsqEcran": "gtezlivre_sql.dhof",
        "ModTrait": "gttzlivre_sql.dhop",
        "ConfM": "GzA",
        "ConfC": "GzA",
        "ConfS": "GzA",
        "SceAction": "1",
        "SceMode": "2",
        "SceSens": "1",
        "SceSaisie": "2",
        "SceCleCrea": "2",
        "ChoixIZY": "2",
        "ProductCode": "10999"
    }
}
```

### Commande

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data_zoom_maentite.json" \
    --structure-dir ".claude/skills/writing-isam-files/scripts/structures"
```

### Sortie attendue

```json
{"success": true, "total": 1, "written": 1, "skipped": 0, "errors": []}
```

---

## Apres l'ecriture

1. **Declarer la constante** dans `a5tczoom.dhsp` (voir `docs/ZOOM-INTEGRATION.md` section 3)
2. **Recompiler** (a5tczoom.dhsp modifie)
3. **Ajouter au menu du domaine** -- ecrire un M2 dans le .dhfi du domaine (voir ci-dessous)
4. **Tester dans l'ERP**

---

## Ajouter au menu du domaine

Structure pre-construite : `scripts/structures/structure_xmenuf_m2.json` (table M2, base Xmenuf).

### Fichier de donnees (data_menu_maentite.json)

```json
{
    "Fichier": "C:\\Developpements harmony\\Bases sql\\g3f.dhfi",
    "Structure": "structure_xmenuf_m2.json",
    "Donnees": {
        "Ce": "2",
        "Reg": "FIC",
        "Ordre": "      14",
        "Lib": "Livre",
        "TypeChain": "3",
        "Enchain": "09490",
        "ChoixActif": "2",
        "ChoixVisible": "2",
        "ChoixIZY": "2",
        "ProductCode": "10999",
        "EnrNo": "100001"
    }
}
```

- **TypeChain = "3"** : chainage vers un zoom (Enchain = numero du zoom)
- **Reg** : code court du groupe parent (ex : `FIC`, pas `FICHIER`). Lire le menu existant pour trouver le bon code.
- **Ordre** : **cadre a droite** avec espaces (l'index ISAM trie octet par octet)
- **Enchain** : prefixe `0` sur 5 chars (ex : `09490`, pas `9490`)
- **ChoixActif / ChoixVisible** : `"2"` = oui (pas `"1"`)
- **EnrNo** : numero unique >= 100000 pour la surcharge

### Commande

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file "data_menu_maentite.json" \
    --structure-dir ".claude/skills/writing-isam-files/scripts/structures"
```

Voir `docs/ZOOM-INTEGRATION.md` section 5 pour la reference complete (TypeChain, regroupements, index).
