---
name: allocating-menu-enrno
description: >
  Trouve un EnrNo libre dans le fichier menu `g3f.dhfi` d'un domaine ERP, selon
  la plage demandee (`standard` < 100000 reserve ERP, `custom` >= 100000
  recommande pour creations utilisateur). Scan des enregistrements M2 (Ce=2)
  avec filtre obligatoire (piege multi-structure M0/M2, cf RETEX R-006), puis
  calcul max+1 dans la plage. Previent les collisions d'EnrNo lors de l'ecriture
  d'un nouveau choix de menu.
  A utiliser avant d'ecrire un enreg M2 dans `g3f.dhfi` (ou un enreg M1 de
  visibilite F7 dans `a5f.dhfi`) pour une entite metier custom.
---

# Allocating Menu EnrNo

## Contenu

- Probleme resolu
- Usage rapide
- Plages semantiques
- Format de sortie JSON
- Piege "multi-structure G3F" (R-006)
- Scripts disponibles
- References

---

## Probleme resolu

Le fichier menu `g3f.dhfi` (base Xmenuf) stocke les choix de menu en table M2 (Ce=2) avec un champ `EnrNo` qui doit etre **unique**. Lors de l'ecriture d'un nouveau choix (ajout d'une entree menu pour un zoom custom), il faut trouver un EnrNo libre pour eviter la collision et preserver la coherence de l'index C (Ce, EnrNo).

Observation empirique (RETEX R-005, 2026-04-23) :

- Les ~1367 choix M2 existants dans `g3f.dhfi` Achat-Vente X.13 ont tous un EnrNo **< 100000** (ex : Race de chien = 1564).
- Hypothese documentee : la zone `>= 100000` est **reservee aux customisations utilisateur** pour eviter les collisions avec les numeros alloues par l'IHM standard. `[A VERIFIER]`

Ce skill encapsule cette logique.

---

## Usage rapide

### Plage custom (recommande pour creations utilisateur)

```bash
py .claude/skills/allocating-menu-enrno/scripts/find_free_enrno.py \
    --file "{CHEMIN_ERP_STANDARD}\Achat-Vente\fichier\g3f.dhfi" \
    --range custom
```

Retourne le premier EnrNo libre dans `[100000, 999999]`.

### Plusieurs numeros d'un coup

```bash
py .claude/skills/allocating-menu-enrno/scripts/find_free_enrno.py \
    --file "<g3f.dhfi>" \
    --range custom --count 5
```

### Plage standard (rare -- reserve a l'ERP)

```bash
py .claude/skills/allocating-menu-enrno/scripts/find_free_enrno.py \
    --file "<g3f.dhfi>" \
    --range standard
```

A n'utiliser **que** si on installe des choix "ERP-standard" (cas exceptionnel pour une customisation qui s'integre au standard plutot que de s'isoler).

---

## Plages semantiques

| Plage | Bornes | Usage | Recommandation |
|-------|--------|-------|----------------|
| `standard` | 1 -- 99999 | Zone reservee ERP standard, allouee par l'IHM native | **Deconseille** pour customisation -- risque de collision a l'installation d'un correctif ERP |
| `custom` | 100000 -- 999999 | Zone customisations utilisateur | **Recommande** pour toute creation custom (zoom metier, nouveau choix menu) |

Detail + hypothese `[A VERIFIER]` : [reference/plages-enrno.md](reference/plages-enrno.md).

---

## Format de sortie JSON

```json
{
  "file": "C:\\...\\Achat-Vente\\fichier\\g3f.dhfi",
  "range": "custom",
  "range_bounds": [100000, 999999],
  "free": [100001],
  "sources": {
    "m2_records": 1367,
    "enrno_parsed": 1367,
    "used_in_range": 0,
    "max_used_in_range": null
  },
  "note": "Hypothese plages standard < 100000 / custom >= 100000 [A VERIFIER] RETEX R-005 2026-04-23"
}
```

Champs :
- `free` : liste des EnrNo libres (ordre croissant, `--count N`)
- `sources.m2_records` : nombre de choix M2 lus (apres filtre Ce=2)
- `sources.used_in_range` : nombre de M2 dont EnrNo est dans la plage
- `sources.max_used_in_range` : plus grand EnrNo actuellement utilise dans la plage (null si plage vide)

**Exit codes** :
- `0` : au moins un EnrNo libre trouve
- `1` : aucun libre (plage saturee) OU aucun M2 lu (fichier vide / erreur silencieuse)
- `2` : erreur (fichier introuvable, read_isam.py inaccessible, JSON invalide)

---

## Piege "multi-structure G3F" (R-006)

`g3f.dhfi` contient 2 tables distinctes :
- **M0** (`Ce=0`, 508 octets) : parametres generaux du domaine (1 enreg par fichier, header)
- **M2** (`Ce=2`, 1000 octets) : choix du menu (les "vraies" entrees)

Un scan M2 **sans filtre `Ce=2`** lit aussi l'enreg M0 avec les offsets M2 -> valeurs aberrantes qui polluent les stats. Ce skill applique **systematiquement** `--filter "Ce=2"` via subprocess `read_isam.py`.

Structure M0 disponible dans `reading-isam-files/scripts/structures/structure_xmenuf_m0.json` pour decoder proprement ce header si besoin.

---

## Scripts disponibles

| Script | Role | Entree | Sortie JSON |
|--------|------|--------|-------------|
| `scripts/find_free_enrno.py` | Scan M2 + calcul EnrNo libre | `--file <g3f.dhfi>` + `--range {standard, custom}` + [`--count N`] + [`--read-isam-script PATH`] | `{free[], sources, range_bounds}` |

Le script **vendored** `scripts/structure_xmenuf_m2.json` rend ce skill autonome : pas de dependance au skill `reading-isam-files` au niveau structure (mais appel subprocess a son `read_isam.py` pour l'ISAM).

---

## Quand utiliser ce skill

- Avant toute **ecriture M2** (nouveau choix menu) dans `g3f.dhfi` -- typiquement dans `creating-diva-entity` CP10 (Menu domaine)
- Avant toute **ecriture M1** (visibilite F7) dans `a5f.dhfi` -- si l'application preconise d'aligner le numero d'ordre M1 sur l'EnrNo correspondant M2 (pattern a verifier)
- Par un outil `modifying-diva-entity` qui ajoute des choix menu a une entite existante

---

## References

- [reference/plages-enrno.md](reference/plages-enrno.md) : semantique des plages + hypothese RETEX R-005
- `reading-isam-files/scripts/structures/structure_xmenuf_m2.json` : structure canonique M2 (source du vendored)
- RETEX R-005 (2026-04-23) : documentation initiale du probleme
