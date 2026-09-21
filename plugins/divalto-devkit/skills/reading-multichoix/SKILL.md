---
name: reading-multichoix
description: >
  Lit les dictionnaires de multichoix Divalto (fichiers `XXfdmc.dhfi` d'un module
  ERP : `gtfdmc`, `ccfdmc`, ...). Liste les multichoix disponibles, detaille les
  entrees d'un multichoix donne, et (a venir) resout les lookups Type=3 en lisant
  la table cible. Gere les 3 Types rencontres (1 liste fixe, 3 lookup dynamique,
  4 identifiant externe). A utiliser pour consulter la definition d'une liste de
  choix avant de binder un champ de dictionnaire metier via `Choix=<XXfdmc>.dhfi`
  + `NomChoix=<NC>`. Rappelle aussi la norme (ne jamais modifier un `XXfdmc`
  standard ; gerer son propre `XXfdmc`) et comment localiser/comparer un `XXfdmc`.
---

# Reading Multichoix

## Contenu

- Emplacement, norme et controle des XXfdmc
- Utilisation rapide
- Modes
- Format de sortie
- Les 3 Types en un coup d'oeil
- Scripts disponibles
- References

---

## Emplacement, norme et controle des XXfdmc

Ce skill lit les dictionnaires multichoix de **n'importe quel module** : `gtfdmc`,
`ccfdmc`, ... (notes generiquement `XXfdmc`).

### Emplacement

Les `XXfdmc` se trouvent **generalement dans les repertoires de sources** du pack,
mais **rien ne l'impose** -- ils peuvent etre ailleurs. Pour les localiser de facon
fiable, resoudre les **chemins de recherche** du workspace via le skill
**`understanding-integrator-workspace`** (`divaltopath.cfg`, `fconfig`, profils
`.dhpt`). A ne pas confondre avec les fichiers d'**erreur** `XXferr`, qui sont
plutot dans `objets/`.

### Norme : ne jamais modifier un XXfdmc standard

Comme tout source standard, un `XXfdmc` **standard ne doit jamais etre modifie**.
Un besoin de multichoix specifique se gere dans **le propre `XXfdmc` du partenaire**
(prefixe partenaire) -- il n'interfere pas avec le standard et **ne genere aucun
conflit** au passage de Service Pack ou en migration.

Consequence : le scenario « j'ai customise un dmc standard, le SP en livre une
nouvelle version, il faut fusionner » **ne devrait jamais se produire** si la norme
est respectee. S'il survient, c'est le **signe d'une violation** (custom place dans
un dmc standard) -- a corriger en **deplacant le custom vers le `XXfdmc` propre** du
partenaire, pas en fusionnant.

### Detecter qu'un XXfdmc standard a ete modifie

Un `XXfdmc` standard non touche est **identique a sa reference** (la copie saine du
pack standard livre). Pour detecter une modification, **comparer le fichier a sa
reference standard**. Il faut donc disposer d'une **copie de reference propre** ;
**sans reference, une modification est indetectable** (aucun marqueur fiable dans le
fichier -- le `datemc` bouge a chaque recompilation). Un simple diff de fichiers
suffit a **signaler** identique / different.

Pour la **comparaison detaillee**, utiliser l'**outil natif Harmony** :
`Utilitaires > Comparaison entre 2 dictionnaires de multi-choix`. Ce skill se limite
a **signaler** une divergence ; le **developpeur** examine (outil natif + `--detail`
sur les Nc divergents) et reporte ce qui doit l'etre.

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
| `--all-details` | `--file` | Dump de TOUS les multichoix en **une passe** : `multichoix` est un **dictionnaire indexe par Nc** (et non une liste comme `--list`), chaque valeur portant `type`, `entries` (liste decodee) et `lookup` pour les Type 3. Destine aux consommateurs machine (ex: pipeline `documenting-erp` -- le script `extract_codified_values.py` vendore ce script). |
| `--stats` | `--file` | Distribution des Types rencontres (1 / 3 / 4) |
| `--resolve <NC>` | `--file --resolve AXENO` | Resout un lookup Type=3 en lisant la table cible |

Ces modes sont mutuellement exclusifs. Le fichier est toujours passe via `--file` (chemin complet du `gtfdmc.dhfi`).

---

## Format de sortie

> **La sortie JSON est en UTF-8**, quelle que soit la console -- le script force son
> encodage de sortie. Sans cela, Python ecrirait dans l'encodage local (cp1252 sous
> Windows FR) et une sortie **redirigee** deviendrait illisible pour qui la lit en UTF-8 :
> les libelles de multichoix sont du francais accentue, un dump `--all-details` du
> dictionnaire standard porte **842 caracteres accentues**.

> **`multichoix` n'a pas la meme forme selon le mode** : une **liste** pour `--list`, un
> **dictionnaire indexe par Nc** pour `--all-details`. C'est le piege qui a coute un
> script a un partenaire -- lire attentivement les deux exemples ci-dessous.

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

Ici `multichoix` est une **liste**, et `entries` un **compteur**.

### `--all-details`

```json
{
  "success": true,
  "file": ".../Achat-Vente/fichier/gtfdmc.dhfi",
  "total_nc": 879,
  "multichoix": {
    "ACOMPTE": {
      "nc": "ACOMPTE",
      "type": "1",
      "entries": [
        { "ce": "1", "choix": "", "valeur": "" },
        { "ce": "2", "choix": "#aff_compta", "valeur": "" }
      ]
    },
    "AXENO": {
      "nc": "AXENO",
      "type": "3",
      "entries": [ { "ce": "1" } ],
      "lookup": { "enreg": "ca", "donnee": "axelibtb", "prefixe": "ca", "ideb": 1, "ifin": 4 }
    }
  }
}
```

Ici `multichoix` est un **dictionnaire indexe par Nc**, et `entries` la **liste des
entrees decodees** -- pas un compteur. La cle `lookup` n'est presente que pour les
**Type=3**.

**Un seul appel suffit** pour obtenir tout le dictionnaire : le fichier est lu en **une
passe** et les enregistrements regroupes par Nc. Ne pas boucler `--detail` par Nc (N
lectures ISAM du meme fichier pour rien).

Iteration correcte cote consommateur :

```python
import json, subprocess
r = subprocess.run(["py", "read_multichoix.py", "--file", chemin, "--all-details"],
                   capture_output=True)
d = json.loads(r.stdout.decode("utf-8"))          # UTF-8 garanti
for nc, mc in d["multichoix"].items():            # dict, PAS une liste
    for entree in mc["entries"]:                  # liste d'objets, PAS un compteur
        traiter(nc, mc["type"], entree)
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
