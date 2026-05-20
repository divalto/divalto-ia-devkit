---
name: reading-isam-files
description: >
  Lit des enregistrements dans les fichiers binaires ISAM Divalto (.dhfi)
  via DhxIsam64.dll (ctypes). Supporte la lecture par cle, le parcours sequentiel,
  les filtres et la projection de champs.
  A utiliser pour consulter le contenu des fichiers indexes proprietaires Divalto.
---

# Reading ISAM Files

## Contenu

- Utilisation rapide
- Modes de lecture
- Workflow complet
- Scripts disponibles
- Structures pre-construites
- References

---

## Utilisation rapide

```bash
# Lire tous les enregistrements zoom (cle A4)
py .claude/skills/reading-isam-files/scripts/read_isam.py \
    --file "{CHEMIN_FICHIERS}/a5f.dhfi" \
    --structure .claude/skills/reading-isam-files/scripts/structures/structure_a5f_m4.json \
    --key A4

# Chercher un enregistrement par valeur de cle
py .claude/skills/reading-isam-files/scripts/read_isam.py \
    --file "{CHEMIN_FICHIERS}/g3f.dhfi" \
    --structure .claude/skills/reading-isam-files/scripts/structures/structure_xmenuf_m2.json \
    --key A2 --key-value "FIC"

# Filtrer + projeter des champs
py .claude/skills/reading-isam-files/scripts/read_isam.py \
    --file "chemin/a5f.dhfi" \
    --structure .claude/skills/reading-isam-files/scripts/structures/structure_a5f_m4.json \
    --key A4 --filter "ZoomNum=9490" --fields "ZoomNum,Lib,ZoomEnr"
```

---

## Modes de lecture

| Mode | Parametres | Description |
|------|-----------|-------------|
| Parcours sequentiel | `--key A4` | Lit tous les enregistrements dans l'ordre de la cle |
| Recherche par cle | `--key A2 --key-value "FIC"` | Positionne sur la cle puis lit sequentiellement tant que la cle correspond |
| **Parcours inverse** | `--reverse` | Lit du dernier au premier (positionne via 0xFF en fin de cle TDF, lit en mode reservation `P`) |
| Filtre | `--filter "Champ=Valeur"` | Filtre les enregistrements (cumulable, AND logique) |
| Projection | `--fields "Champ1,Champ2"` | Ne retourne que les champs specifies |
| Limite | `--max 5` | Limite le nombre d'enregistrements retournes (defaut: 100) |

Les modes sont combinables : `--key A4 --filter "ZoomNum=9490" --fields "Lib" --max 10`.

### Parcours inverse (`--reverse`)

- Sans `--key-value` : positionne en fin de fichier (KEY charge avec un octet 0xFF apres la lettre d'index) puis remonte
- Avec `--key-value` : usage non recommande (la verification d'egalite de cle stoppe des le premier enreg qui quitte la plage)
- Implementation : appel `xisam_tpreadlong` avec mode de reservation `P` (Partage, pas de lock). La direction (remontee) est portee par la cle TDF, pas par le mode. Revision R-014 (2026-04-22) : avant cette date, le script passait des modes `F`/`P`/`S`/`D`/`G` comme codes de direction, ce qui etait une interpretation erronee -- `mode` est un code de reservation uniquement.

---

## Workflow complet

### Etape 1 -- Identifier le fichier et la structure

- Fichier `.dhfi` : chemin complet du fichier ISAM
- Structure JSON : fichier decrivant les champs, offsets et tailles de l'enregistrement

Utiliser `validate_structure.py` pour verifier la structure avant lecture :

```bash
py .claude/skills/reading-isam-files/scripts/validate_structure.py \
    --path .claude/skills/reading-isam-files/scripts/structures/structure_a5f_m4.json
```

### Etape 2 -- Choisir la cle d'index et les filtres

- **Cle d'index** : identifiant de la cle dans le fichier ISAM (ex: A4 pour zoom, A2 pour menu)
- **Valeur de cle** (optionnel) : valeur pour positionner la lecture (ex: "FIC" pour les menus fichier)
- **Filtres** (optionnel) : conditions `Champ=Valeur` pour filtrer les resultats

### Etape 3 -- Lire et analyser

Executer `read_isam.py` avec les parametres choisis. La sortie JSON contient :

```json
{
  "success": true,
  "file": "chemin/a5f.dhfi",
  "records": [ { "Ce": "4", "ZoomNum": "9490", "Lib": "..." }, ... ],
  "count": 1
}
```

- `success=true` : au moins 1 enregistrement trouve
- `success=false` + exit code 1 : aucun enregistrement correspondant
- Exit code 2 : erreur (DLL absente, fichier introuvable, structure invalide)

---

## Scripts disponibles

| Script | Role | Entree | Sortie JSON |
|--------|------|--------|-------------|
| `scripts/read_isam.py` | Lit des enregistrements ISAM | `--file` `--structure` `--key` [+ `--key-value`] [+ `--filter`] [+ `--fields`] [+ `--max`] [+ `--reverse`] | `{success, records[], count}` |
| `scripts/validate_structure.py` | Valide un fichier de structure JSON | `--path` | `{valid, errors[], fields, record_size}` |

**Exit codes** :

| Script | 0 | 1 | 2 |
|--------|---|---|---|
| `read_isam.py` | Enregistrements trouves | Aucun enregistrement | Erreur (DLL, fichier, structure) |
| `validate_structure.py` | Structure valide | Structure invalide | Fichier introuvable |

---

## Structures pre-construites

| Structure | Fichier | Table | Taille |
|-----------|---------|-------|--------|
| Zoom des zooms (A5F.dhfi) | `scripts/structures/structure_a5f_m4.json` | M4 | 1000 octets, 46 champs (Ce=4) |
| Visibilite F7 (A5F.dhfi) | `scripts/structures/structure_a5f_m1.json` | M1 | 50 octets, 6 champs (Ce=5) |
| Menu domaine choix (Xmenuf .dhfi) | `scripts/structures/structure_xmenuf_m2.json` | M2 | 1000 octets, 21 champs (Ce=2) |
| Menu domaine header (Xmenuf .dhfi) | `scripts/structures/structure_xmenuf_m0.json` | M0 | 508 octets, 12 champs (Ce=0) |
| Dictionnaire multichoix (gtfdmc.dhfi) | `scripts/structures/structure_gtfdmc_ch60.json` | ch60 (vue 6.0) | 420 octets, 12 champs (dont `datemc` Type="B") |

Pour une lecture **interpretee** du dictionnaire multichoix (liste des Nc, detail par Nc, resolution des 3 Types 1/3/4), utiliser le skill dedie `reading-multichoix` qui orchestre les vues specifiques aux Types.

**Piege multi-structure G3F (R-006, 2026-04-23)** : le fichier `g3f.dhfi` (base Xmenuf) contient **2 tables distinctes** M0 (`Ce=0`, parametres generaux, 1 enreg = header du domaine) et M2 (`Ce=2`, choix du menu, N enregs). Un scan M2 sans filtre `Ce=2` inclut l'enreg M0 decode avec les offsets M2 -> valeurs aberrantes. Toujours **`--filter "Ce=2"`** quand on analyse les choix de menu, **`--filter "Ce=0"`** pour le header. Structure M0 disponible ci-dessus.

**Plage d'allocation EnrNo M2 (R-005, 2026-04-23)** : hypothese empiriquement validee sur Achat-Vente X.13 : `EnrNo < 100000` = zone standard (allouee par l'IHM native), `EnrNo >= 100000` = zone customisation. Skill dedie `allocating-menu-enrno` automatise la selection.

---

## Types de champs (`Type` dans la structure)

| Type | Semantique | Traitement |
|------|------------|------------|
| `C` (caractere) | Chaine texte | decode cp1252 + rstrip (preserve les espaces de tete) |
| `N` (numerique) | Numerique ASCII | decode cp1252 + strip (2 cotes) |
| `D` (date) | Date ASCII | decode cp1252 + strip (2 cotes) |
| `B` (binaire) | Champ binaire (FILETIME, UID, bytes non-cp1252...) | retour hex uppercase, aucun decode texte |
| absent | Comportement historique | decode cp1252 + strip (2 cotes) |

Le type `"B"` (ajoute 2026-04-23) evite les `UnicodeDecodeError` sur des zones binaires non encodables en cp1252 (ex : `datemc` de `gtfdmc.dhfi`, 8 octets FILETIME-like avec bytes 0x9D / 0x8F hors table). Un fallback `errors="replace"` avec warning stderr protege aussi les champs texte des bytes invalides isoles.

---

## References

- `reference/isam-api.md` : API DhxIsam64.dll (signatures ctypes, TDF, modes, erreurs)
- `reference/json-formats.md` : format des fichiers structure JSON
- `reference/a5f-zoom-record.md` : structure specifique des enregistrements zoom A5F
