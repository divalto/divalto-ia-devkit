---
name: allocating-zoom-numbers
description: >
  Trouve un numero de zoom libre en cross-checkant les sources enregistrees
  (`a5tczoom.dhsp` constantes standard, `a5f.dhfi` zooms standard, **`a5fu.dhfi`
  zooms specifiques/surcharge**, `a5f.dhfi` versionx9 optionnel), puis verifie le
  candidat par une recherche large dans les sources specifiques uniquement
  (occurrences remontees et etiquetees pour jugement, jamais de decision auto).
  Convention : un nouveau zoom specifique partenaire demarre a 90000. Previent les
  collisions entre zooms declares, enregistres et reellement appeles dans le code.
  A utiliser avant d'allouer un nouveau numero de zoom (creation d'entite ou de zoom).
---

# Allocating Zoom Numbers

## Contenu

- Probleme resolu
- Convention de numerotation (90000)
- Usage rapide
- Sources cross-checkees
- Verification phase 2 (recherche large)
- Format de sortie JSON
- Plages par domaine
- Scripts disponibles
- References

---

## Probleme resolu

Scanner uniquement `a5f.dhfi` pour trouver un numero libre peut produire une
collision. Deux pieges :

1. **`a5f` est STANDARD, jamais modifie.** Les zooms **specifiques / surcharge**
   du partenaire vivent dans **`a5fu.dhfi`** (overlay de `a5f`, meme structure M4).
   Ignorer `a5fu` = ignorer la vraie source des zooms partenaire -> re-allocation.
2. Un zoom declare dans `a5tczoom.dhsp` (ex: `C_ZOOM_TauxTvaN_9946 = 9946`) peut
   etre absent des `.dhfi` parce que non encore propage/enregistre. Il reste
   **utilise**.

**Source de verite du used-set** = **union** de `a5tczoom` + `a5f` + `a5fu`
(+ versionx9 optionnel). En complement, une **recherche large** dans les sources
**specifiques** confirme qu'un candidat n'est pas deja appele/reference ailleurs.

---

## Convention de numerotation (90000)

Un **nouveau zoom specifique** cree par un partenaire demarre par convention a
**90000** (plage `90000-99999`, plafond 5 caracteres). C'est la **plage par defaut
d'allocation** quand ni `--domain` ni `--range` n'est fourni.

Attention : ce n'est **qu'une convention de creation**. Des zooms specifiques
**< 90000 existent** -> la **detection** du used-set reste **globale (toutes
plages)** ; 90000 ne borne que la **recherche** d'un numero libre, pas la detection.

---

## Usage rapide

### Par domaine (plage standard)

```bash
py .claude/skills/allocating-zoom-numbers/scripts/find_free_zoom.py \
    --a5tczoom "{CHEMIN_ERP_STANDARD}\A5\source\a5tczoom.dhsp" \
    --domain DAV
```

### Avec plage explicite

```bash
py .claude/skills/allocating-zoom-numbers/scripts/find_free_zoom.py \
    --a5tczoom "C:\...\a5tczoom.dhsp" \
    --range 9900-9999
```

### Allocation partenaire complete (used-set + verification specifique)

```bash
py .claude/skills/allocating-zoom-numbers/scripts/find_free_zoom.py \
    --a5tczoom "C:\...\a5tczoom.dhsp" \
    --a5f-local "{CHEMIN_ERP_STANDARD}\A5\fichier\a5f.dhfi" \
    --a5fu "C:\...\specifs\...\a5fu.dhfi" \
    --read-isam-script ".claude/skills/reading-isam-files/scripts/read_isam.py" \
    --structure ".claude/skills/reading-isam-files/scripts/structures/structure_a5f_m4.json" \
    --specifs-root "C:\...\specifs" \
    --count 3
```

Sans `--domain` ni `--range` -> allocation dans la plage partenaire **90000+**.
Retourne 3 numeros **libres confirmes** (used-set OK + 0 occurrence dans les
sources specifiques) + un rapport des candidats "suspects" a juger.

---

## Sources cross-checkees (used-set)

| Source | Type | Role |
|--------|------|------|
| `a5tczoom.dhsp` | Source DIVA (.dhsp) | Catalogue des constantes standard `C_ZOOM_*_<Num> = <Num>` |
| `a5f.dhfi` | ISAM binaire (M4, cle A4, `ZoomNum`) | Zooms **STANDARD** enregistres |
| **`a5fu.dhfi`** | ISAM binaire (meme structure M4) | Zooms **SPECIFIQUES / surcharge** enregistres (overlay de `a5f` ; `a5f` n'est jamais modifie) |
| `a5f.dhfi` versionx9 | ISAM binaire | Copie historique d'une version anterieure (optionnel) |

**Union** = numeros "occupes". Un numero declare dans `a5tczoom.dhsp` mais absent
des `.dhfi` est quand meme considere **utilise**. La detection est **globale
(toutes plages)**, independamment de la plage d'allocation demandee.

> **Doublons a5f / a5fu = normaux.** Surcharger un zoom standard (ex. 9021)
> cree une entree 9021 dans `a5fu` **prioritaire** sur celle de `a5f` : c'est la
> signature d'une surcharge, pas une anomalie. Le used-set etant une **union
> d'ensembles**, le doublon se fond en une seule entree (compte une fois dans
> `union_used_count` ; les compteurs par source se chevauchent legitimement). Aucun
> doublon a5f/a5fu n'est signale comme collision.

---

## Verification phase 2 (recherche large)

Activee par `--specifs-root` (repetable). Pour chaque candidat libre du used-set,
le skill cherche le numero **uniquement dans les sources specifiques/surcharge**
(jamais le standard) sur les extensions `.dhsp` et `.dhsf` :

- **0 occurrence** -> candidat **disponible** (place dans `free`).
- **occurrence(s)** -> candidat **"suspect"**, remonte avec `fichier:ligne` +
  extrait + **etiquette de confiance**. **Aucune decision automatique** : c'est au
  collaborateur de juger.

Etiquetage via un **registre de patterns extensible** (cf.
[reference/zoom-number-patterns.md](reference/zoom-number-patterns.md)) :

| Etiquette | Confiance | Exemple |
|-----------|-----------|---------|
| `zoom_call` | fort | `Tnt_Zoom_Call(9022)` |
| `touche_masque` | fort | binding `[touches]` : `f8=9022` |
| `affectation` | faible | `= 9022` (constante ou autre, a juger) |
| `non_reconnu` | inconnu | aucun pattern connu -> **signal d'apprentissage** (pattern potentiellement nouveau, a confirmer par un RETEX) |

Le registre **grandit au fil des RETEX** : une occurrence `non_reconnu` qui se
revele etre un vrai usage de zoom devient un nouveau pattern documente.

---

## Format de sortie JSON

```json
{
  "free": [90000, 90007, 90009],
  "allocation_origin": "partenaire 90000+ (convention par defaut)",
  "ranges_considered": [[90000, 99999]],
  "sources": {
    "a5tczoom_count": 749,
    "a5f_local_count": 2483,
    "a5f_versionx9_count": 0,
    "a5fu_count": 18,
    "union_used_count": 2538
  },
  "specifs_search": {
    "enabled": true,
    "roots": ["C:/.../specifs"],
    "exts": [".dhsp", ".dhsf"],
    "files_scanned": 412,
    "truncated": false,
    "candidates_examined": [90000, 90002, ...],
    "suspects": [
      {"num": 90005, "occurrences": [
        {"file": "...\\xxx.dhsf", "line": 2, "text": "f8=90005",
         "label": "touche_masque", "confidence": "fort"}
      ]}
    ]
  }
}
```

- `free` : numeros **libres confirmes** (used-set OK + 0 occurrence specifique)
- `allocation_origin` : d'ou vient la plage (90000 par defaut, ou `--domain`/`--range`)
- `sources` : compteurs du used-set (dont `a5fu_count` = zooms specifiques)
- `specifs_search.suspects` : candidats trouves dans les sources specifiques,
  **a juger** (jamais ecartes automatiquement)

**Exit codes** :
- `0` : au moins un numero libre confirme
- `1` : aucun numero libre confirme dans la plage consideree
- `2` : erreur (argument manquant, fichier introuvable)

---

## Plages par domaine

> **Limite structure M4** : un ZoomNum est stocke sur **5 caracteres**
> dans `a5f.dhfi` (cle A4). Toute plage demandee via `--range` est refusee si
> elle depasse `99999`. Pour les **EnrNo menu** (M2 sur 6 chars, plage >= 100000
> recommandee pour le custom), utiliser le skill `allocating-menu-enrno`.

Source : moulinette 58 ERP (`Outils/source/outm058.dhsp`).

| Code domaine | Plage(s) |
|--------------|----------|
| DAV | 9000-9999, 21000-21999, 22000-22999, 39000-39999, 46000-46999, 47000-47999 |
| DAFF | 31000-31999, 12592-12593 |
| DRT | 30000-30999 |
| DCPT | 19000-19999 |
| DPAIE | 25000-29999 |
| DSP | 32000-32999 |
| DQUAL | 40000-40999 |
| DDOC | 41000-41999 |
| DCONT | 44000-44999 |
| DGRM | 22039-22040, 45000-45999 |
| DREG | 49000-49999 |
| COMMUN | 11000-18999 |
| ZOOM | 99050-99060 |

---

## Scripts disponibles

| Script | Role | Entree | Sortie JSON |
|--------|------|--------|-------------|
| `scripts/find_free_zoom.py` | Used-set + allocation + verif specifique | `--a5tczoom`, [`--a5f-local`], [`--a5fu`], [`--a5f-versionx9`], [`--domain` \| `--range` ; defaut 90000+], [`--count`], [`--read-isam-script`], [`--structure`], [`--specifs-root` (repetable)], [`--max-files`] | `{free[], sources, specifs_search{suspects[]}}` |

Si ni `--domain` ni `--range` : allocation dans la plage partenaire **90000+**.
`--a5fu`/`--a5f-local`/`--a5f-versionx9` requierent `--read-isam-script` ET `--structure`.

---

## References

- [reference/zoom-number-patterns.md](reference/zoom-number-patterns.md) -- registre
  vivant des patterns d'usage d'un numero de zoom dans le code (phase 2). Etendu au
  fil des RETEX ; chaque pattern est trace a son RETEX d'origine.
