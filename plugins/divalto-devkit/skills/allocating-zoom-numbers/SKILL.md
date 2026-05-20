---
name: allocating-zoom-numbers
description: >
  Trouve un numero de zoom libre pour une plage donnee (ou un domaine ERP) en
  cross-checkant trois sources : `a5tczoom.dhsp` (constantes), `a5f.dhfi` local
  (enregistrements M4), `a5f.dhfi` de versionx9 (optionnel). Previent les
  collisions entre zooms declares et zooms reellement enregistres.
  A utiliser avant d'allouer un nouveau numero de zoom lors de la creation d'une
  entite ou d'un zoom standard.
---

# Allocating Zoom Numbers

## Contenu

- Probleme resolu
- Usage rapide
- Sources cross-checkees
- Format de sortie JSON
- Plages par domaine
- Scripts disponibles

---

## Probleme resolu

Scanner uniquement `a5f.dhfi` local pour trouver un numero libre peut produire
une collision : un zoom declare dans `a5tczoom.dhsp` du standard (ex: `C_ZOOM_TauxTvaN_9946 = 9946`)
peut etre absent de `a5f.dhfi` local parce que non propage. Allouer ce numero
produit un conflit a l'installation.

**Source de verite effective** = **union** de trois sources. Ce skill fait le
cross-check automatique.

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

### Cross-check complet (3 sources)

```bash
py .claude/skills/allocating-zoom-numbers/scripts/find_free_zoom.py \
    --a5tczoom "C:\...\a5tczoom.dhsp" \
    --a5f-local "C:\...\Standard\Version X.13\A5\fichier\a5f.dhfi" \
    --read-isam-script ".claude/skills/reading-isam-files/scripts/read_isam.py" \
    --structure ".claude/skills/reading-isam-files/scripts/structures/structure_a5f_m4.json" \
    --domain DAV --count 5
```

Retourne 5 numeros libres dans la plage DAV apres cross-check complet.

---

## Sources cross-checkees

| Source | Type | Role |
|--------|------|------|
| `a5tczoom.dhsp` | Source DIVA (.dhsp) | Catalogue officiel des constantes `C_ZOOM_*_<Num> = <Num>` (2281 entrees au 2026-04-20) |
| `a5f.dhfi` local | ISAM binaire | Enregistrements M4 reellement installes sur le poste (cle A4, champ `ZoomNum`) |
| `a5f.dhfi` versionx9 | ISAM binaire | Copie historique partagee entre dossiers (optionnel) |

**Union de ces trois sources** = numeros effectivement "occupes" dans l'ecosysteme.

Un numero declare dans `a5tczoom.dhsp` mais absent de `a5f.dhfi` est quand meme
considere comme **utilise** (une installation future propagera la declaration).

---

## Format de sortie JSON

```json
{
  "free": [9947, 9948, 9949],
  "range": "domain=DAV",
  "ranges_considered": [[9000, 9999], [21000, 21999], [22000, 22999], ...],
  "sources": {
    "a5tczoom_count": 749,
    "a5f_local_count": 2483,
    "a5f_versionx9_count": 0,
    "union_used_count": 2520
  },
  "collisions_a5f_local_vs_a5tczoom_in_range": [9946]
}
```

- `free` : liste des numeros libres dans la plage, dans l'ordre croissant
- `sources` : compteurs par source (diagnostic)
- `collisions_...` : numeros declares ET enregistres (normal, pour info)

**Exit codes** :
- `0` : au moins un numero libre trouve
- `1` : aucun numero libre dans la plage consideree
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
| `scripts/find_free_zoom.py` | Cross-check + allocation | `--a5tczoom`, [`--a5f-local`], [`--a5f-versionx9`], `--domain` OU `--range`, [`--count`], [`--read-isam-script`], [`--structure`] | `{free[], sources, collisions_...}` |
