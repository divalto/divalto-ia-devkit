# Plages EnrNo G3F -- reference allocating-menu-enrno

> Reference locale du skill `allocating-menu-enrno`. Documente la semantique des plages d'EnrNo dans `g3f.dhfi` table M2.

## Contenu

- Contexte
- Plages observees
- Hypothese `[A VERIFIER]`
- Workflow d'allocation
- Cas particuliers

---

## Contexte

La table M2 de `g3f.dhfi` (base Xmenuf) stocke les choix du menu domaine. Chaque enreg M2 porte un champ `EnrNo` (9 octets a l'offset 797) qui doit etre **unique** pour alimenter l'index C `(Ce, EnrNo)`.

Source canonique de la structure M2 : `reading-isam-files/scripts/structures/structure_xmenuf_m2.json`.

---

## Plages observees (empirique X.13 Achat-Vente, 2026-04-23)

Scan sur 1367 choix M2 (apres filtre `Ce=2` -- piege R-006) :

| Plage | Count | Exemples | Source d'allocation |
|-------|-------|----------|---------------------|
| 1 -- 99999 | 1367 (100 %) | Race de chien = 1564, ... | IHM native ERP (allocation auto a la creation standard) |
| >= 100000 | 0 (0 %) | -- | Zone vide |

**Constat** : aucun EnrNo >= 100000 actuellement utilise dans le standard X.13 Achat-Vente.

---

## Hypothese `[A VERIFIER]`

Pour eviter les collisions avec les numeros alloues par l'IHM standard (et par consequent les conflits a l'installation de correctifs ou evolutions ERP), **l'hypothese retenue** par ce skill est :

- **Zone standard ERP** : `EnrNo < 100000` -- reservee a l'allocation automatique par l'IHM native lors de la creation de choix standard. A ne **pas** utiliser pour une customisation utilisateur.
- **Zone customisation** : `EnrNo >= 100000` -- reservee aux creations custom (zooms metier, choix menu d'entites ajoutees par developpement).

Ceci constitue une **hypothese documentee dans le RETEX R-005** mais **non-officiellement confirmee** par la documentation Divalto. A valider avec :

1. Scan empirique sur **plusieurs modules** (Achat-Vente, Compta, Paie, GC...) pour verifier l'absence systematique d'EnrNo >= 100000 dans le standard.
2. Demande a Divalto (ou lecture de la doc officielle si existante) pour confirmer la convention.
3. Test d'installation d'un correctif ERP apres creation custom >= 100000 : verifier absence de conflit.

Items A-VERIFIER dans `docs/A-VERIFIER.md`.

---

## Workflow d'allocation

Le script `find_free_enrno.py` applique :

1. Invoque `read_isam.py` en subprocess avec `--filter "Ce=2"` (eviter pollution M0)
2. Parse tous les EnrNo retournes, filtre ceux dans la plage demandee
3. Calcule `max_used_in_range`
4. Retourne `max_used_in_range + 1` (ou le premier libre si un trou existe)

**Optimisation** : pour les allocations `custom`, `max_used_in_range = None` sur Achat-Vente X.13 -> retour direct = `100000` (premier de la plage).

---

## Cas particuliers

### Plage saturee

Si la plage custom atteint `999999` (plus de 900000 customisations sur un module, improbable), le script retourne exit code 1 + `free: []`. Cas a signaler si rencontre -> elargir la plage ou migrer vers une convention differente.

### EnrNo 0 ou vide

Certains M2 pourraient avoir un EnrNo a 0 ou vide (cas degrades). Le parser ignore ces cas (`val.isdigit()` exclut les chaines vides ou espaces). Ils ne perturbent pas le calcul max.

### Coherence M1 <-> M2

Le RETEX R-002 mentionne une visibilite F7 via M1 (Ce=5 dans `a5f.dhfi`). Certains patterns applicatifs peuvent aligner le `Ordre` du M1 sur l'EnrNo correspondant M2 -- **a verifier**. Ce skill n'impose pas cet alignement ; il retourne juste un EnrNo libre pour M2.

---

## Items A-VERIFIER

Suivis dans `docs/A-VERIFIER.md` section MULTICHOIX / batch 30 :

- Confirmation empirique multi-modules (Compta, Paie, GC, Retail, autres) du pattern `< 100000` standard
- Comportement du framework IHM si un EnrNo >= 100000 est rencontre (acceptation normale ou message d'avertissement ?)
- Alignement M1.Ordre <-> M2.EnrNo : convention ou libre ?
