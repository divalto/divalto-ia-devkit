---
name: reading-multichoix
description: >
  Lit le dictionnaire des multichoix Divalto (fichier `gtfdmc.dhfi` d'un module
  ERP). Liste les multichoix disponibles, detaille les entrees d'un multichoix
  donne, et (a venir) resout les lookups Type=3 en lisant la table cible. Gere
  les 3 Types rencontres (1 liste fixe, 3 lookup dynamique, 4 identifiant externe).
  A utiliser pour consulter la definition d'une liste de choix avant de binder
  un champ de dictionnaire metier via `Choix=gtfdmc.dhfi` + `NomChoix=<NC>`.
---

# Reading Multichoix

## Contenu

- Utilisation rapide
- Modes
- Format de sortie
- Les 3 Types en un coup d'oeil
- Scripts disponibles
- References

---

## Utilisation rapide

```bash
# Lister tous les multichoix d'un module (Nc, Type, nb entrees)
py .claude/skills/reading-multichoix/scripts/read_multichoix.py \
    --file "{CHEMIN_ERP_STANDARD}\Achat-Vente\fichier\gtfdmc.dhfi" \
    --list

# Detailler un multichoix precis
py .claude/skills/reading-multichoix/scripts/read_multichoix.py \
    --file "{CHEMIN_ERP_STANDARD}\Achat-Vente\fichier\gtfdmc.dhfi" \
    --detail AXENO

# Statistiques par Type
py .claude/skills/reading-multichoix/scripts/read_multichoix.py \
    --file "{CHEMIN_ERP_STANDARD}\Achat-Vente\fichier\gtfdmc.dhfi" \
    --stats
```

---

## Modes

| Mode | Parametres | Description |
|------|-----------|-------------|
| `--list` | `--file` | Liste les multichoix (Nc, Type dominant, nb entrees) en JSON |
| `--detail <NC>` | `--file --detail NONOUI` | Dump des entrees du multichoix avec decodage selon son Type |
| `--all-details` | `--file` | Dump de TOUS les multichoix avec leur type, entries et lookup (Type 3). Destine aux consommateurs machine (ex: pipeline `documenting-erp` -- le script `extract_codified_values.py` vendore ce script). |
| `--stats` | `--file` | Distribution des Types rencontres (1 / 3 / 4) |
| `--resolve <NC>` | `--file --resolve AXENO` | **[BACKLOG MC-03]** Resout un lookup Type=3 en lisant la table cible |

Ces modes sont mutuellement exclusifs. Le fichier est toujours passe via `--file` (chemin complet du `gtfdmc.dhfi`).

---

## Format de sortie

### `--list`

```json
{
  "success": true,
  "file": ".../Achat-Vente/fichier/gtfdmc.dhfi",
  "total_nc": 881,
  "total_records": 2869,
  "multichoix": [
    { "nc": "ACOMPTE", "type": "1", "entries": 2 },
    { "nc": "AXENO", "type": "3", "entries": 1 },
    { "nc": "CHOIX_FICJOINT", "type": "4", "entries": 1 }
  ]
}
```

### `--detail <NC>`

Pour Type=1 (liste fixe) -- le champ `choix` est le libelle affiche, `valeur` est parfois vide (le libelle fait office de code), parfois rempli (code numerique separe) :

```json
{
  "success": true,
  "nc": "NONOUI",
  "type": "1",
  "entries": [
    { "ce": "1", "choix": "Non", "valeur": "" },
    { "ce": "2", "choix": "Oui", "valeur": "" }
  ]
}
```

Pour Type=3 (lookup dynamique) -- les champs enreg/donnee/prefixe/ideb/ifin definissent la table cible :

```json
{
  "success": true,
  "nc": "AXENO",
  "type": "3",
  "lookup": {
    "enreg": "ca",
    "donnee": "axelibtb",
    "prefixe": "ca",
    "ideb": 1,
    "ifin": 4
  },
  "entries": [
    { "ce": "1", "enreg": "ca", "donnee": "axelibtb", "prefixe": "ca", "ideb": "1", "ifin": "4" }
  ]
}
```

Pour Type=4 (identifiant externe) -- le champ `valeur` porte l'identifiant :

```json
{
  "success": true,
  "nc": "CHOIX_FICJOINT",
  "type": "4",
  "entries": [
    { "ce": "1", "valeur": "IdFic", "choix": "" }
  ]
}
```

### `--stats`

```json
{
  "success": true,
  "total_nc": 881,
  "by_type": {
    "1": { "count": 795, "pct": 90.2 },
    "3": { "count": 31,  "pct": 3.5 },
    "4": { "count": 55,  "pct": 6.2 }
  }
}
```

---

## Les 3 Types en un coup d'oeil

| Type | Semantique | Vue utile | Exemple |
|------|------------|-----------|---------|
| `1` | Liste fixe (libelles hardcodes) | `choix` (104 bytes texte) + `valeur` (code retourne, parfois vide) | `NONOUI` -> Non/Oui, `AFFETATPFC` -> codes 1..6 |
| `3` | Lookup dynamique sur table | `enreg` / `donnee` / `prefixe` / `ideb..ifin` | `AXENO` -> lire `ca.axelibtb` pour codes `ca1`..`ca4` |
| `4` | Identifiant externe | `valeur` (ID resolu par framework) | `CHOIX_FICJOINT` -> `IdFic` |

Detail complet : [reference/multichoix-types.md](reference/multichoix-types.md).

Documentation generale du dictionnaire multichoix : section dediee du workspace.

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/read_multichoix.py` | Lit et interprete `gtfdmc.dhfi` selon le mode demande | `--file` + `--list` / `--detail NC` / `--stats` / `--resolve NC` | JSON (voir section Format de sortie) |

**Exit codes** :

| 0 | Lecture reussie, au moins 1 resultat |
| 1 | Lecture reussie mais resultat vide (ex : `--detail` d'un Nc inexistant) |
| 2 | Erreur (DLL absente, fichier introuvable, mode invalide) |

---

## References

- [reference/multichoix-types.md](reference/multichoix-types.md) : detail des 3 Types avec exemples empiriques
- Structure JSON compatible `reading-isam-files` : `.claude/skills/reading-isam-files/scripts/structures/structure_gtfdmc_ch60.json`

## Points ouverts

- **MC-01** : generalisation aux dictionnaires `rtfdmc` / `wmfdmc` / autres modules
- **MC-02** : semantique precise des Type=4 (IdFic, LstPolice, LstStyleWpf...)
- **MC-03** : implementation du mode `--resolve` (lecture effective de la table cible pour Type=3)
