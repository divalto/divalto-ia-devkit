# Multichoix -- Detail des 3 Types

> Reference locale du skill `reading-multichoix`. Chiffres issus de l'analyse empirique de `gtfdmc.dhfi` Achat-Vente X.13 (881 Nc, 2869 enregistrements, 2026-04-23).

## Contenu

- Vue d'ensemble
- Type 1 -- Liste fixe
- Type 3 -- Lookup dynamique
- Type 4 -- Identifiant externe
- Encodage

---

## Vue d'ensemble

| Type | Semantique | Count | % | Vue dominante de `choix` |
|------|------------|-------|---|---------------------------|
| `1` | Liste fixe (libelles hardcodes) | 795 | 90.2 | Texte libre 104 octets |
| `3` | Lookup dynamique sur table | 31 | 3.5 | Sous-structure enreg/donnee/prefixe/ideb/ifin |
| `4` | Identifiant externe | 55 | 6.2 | `choix` vide, `valeur` = IdXxx |

Le Type est stocke a l'offset 17 (1 octet ASCII) et est identique sur toutes les entrees d'un meme Nc (premiere `Ce=1` + suivantes `Ce=2`).

---

## Type 1 -- Liste fixe

Chaque entree stocke un libelle textuel dans `choix` (offsets 18..121, 104 bytes) et un code retourne dans `valeur` (offsets 131..210, 80 bytes).

Regle de composition typique :
- Premiere entree (`Ce=1`) -> premier choix de la liste (peut etre le defaut / "aucun")
- Entrees suivantes (`Ce=2`) -> autres options

### Exemple `NONOUI` (2 entrees, `valeur` vide)

| Ce | Type | choix | valeur |
|----|------|-------|--------|
| 1 | 1 | Non | (vide) |
| 2 | 1 | Oui | (vide) |

Sur cet exemple, le libelle affiche `Non`/`Oui` fait office de code retourne -- `valeur` n'est pas rempli. Selon le multichoix, `valeur` peut etre une chaine code (ex: numerique `1`/`2`/`3` pour `AFFETATPFC`).

### Exemple `AFFETATPFC` (6 entrees, codes numeriques dans `valeur`)

| Ce | Type | choix | valeur |
|----|------|-------|--------|
| 1 | 1 | Non genere | 1 |
| 2 | 1 | Genere | 2 |
| 2 | 1 | Avis paiement | 3 |

Les 3 entrees complementaires (Facture / Regle partiel / Regle total) avec codes 4/5/6 completent ce multichoix (6 entrees au total).

### Piege -- reference vers une table de traduction

Le texte `choix` peut etre un marqueur `#<nomtable>` qui pointe vers une table de libelles externe. Le framework DIVA resoudra le libelle affiche au runtime. Ces entrees apparaissent avec `choix` contenant une valeur de type `#aff_compta` ou `#tblfactacpt` :

| Ce | Type | choix | valeur |
|----|------|-------|--------|
| 1 | 1 | (vide) | (vide) |
| 2 | 1 | #aff_compta | (vide) |

---

## Type 3 -- Lookup dynamique

Le libelle affiche n'est pas stocke dans `gtfdmc.dhfi`. L'entree porte une configuration de lookup (sous-structure) qui designe une table cible a lire au runtime.

### Sous-champs (offsets dans la vue ch60)

| Offset | Taille | Champ | Description |
|--------|--------|-------|-------------|
| 18 | 32 | `enreg` | Nom d'enregistrement de la table cible |
| 50 | 32 | `donnee` | Nom du champ qui porte le libelle |
| 82 | 32 | `prefixe` | Prefixe a appliquer au code |
| 114 | 4 | `ideb` | Indice de debut (ASCII numerique) |
| 118 | 4 | `ifin` | Indice de fin (ASCII numerique) |

### Exemple `AXENO` (1 entree Ce=1)

| enreg | donnee | prefixe | ideb | ifin |
|-------|--------|---------|------|------|
| `ca` | `axelibtb` | `ca` | `1` | `4` |

**Interpretation** : lire la table `axelibtb` pour les codes `ca1`, `ca2`, `ca3`, `ca4` -> chaque entree retourne le libelle `axelibtb.<code>`.

### Resolution

La resolution effective (lecture de la table cible) est prevue par le mode `--resolve` du script (BACKLOG MC-03, pas encore implemente).

En attendant, utiliser `reading-isam-files` avec la structure adequate du dictionnaire cible pour lire `axelibtb.dhfi`.

---

## Type 4 -- Identifiant externe

Le champ `choix` est vide. Le champ `valeur` contient un identifiant qui designe une source externe de valeurs :
- Fichier joint (`IdFic`)
- Police de caractere (`LstPolice`)
- Style WPF (`LstStyleWpf`, `LstStyleImp`)

Le framework DIVA / IHM resout ces identifiants au runtime.

### Exemples

| Nc | Ce | valeur |
|----|-----|--------|
| `CHOIX_FICJOINT` | 1 | `IdFic` |
| `CHOIX_POLICE` | 1 | `LstPolice` |
| `CHOIX_STYLE` | 1 | `LstStyleWpf` |
| `CHOIX_STYLEIMP` | 1 | `LstStyleImp` |

### Semantique complete -- `[A VERIFIER]` BACKLOG MC-02

La liste exhaustive des identifiants Type=4 valides et leur interpretation ne sont pas entierement documentees a partir du RETEX initial. Les 55 Nc de Type=4 de l'Achat-Vente X.13 devront etre scannes pour etablir un catalogue complet.

---

## Encodage

| Zone | Encodage |
|------|----------|
| `Nc`, `choix`, `enreg`, `donnee`, `prefixe`, `valeur`, `Noms` | windows-1252 (cp1252) |
| `ideb`, `ifin` | ASCII numerique (4 chars) |
| `datemc` | Binaire 8 octets (FILETIME-like) -- **ne pas decoder texte** |

Le type `"B"` de la structure JSON (`structure_gtfdmc_ch60.json`) bascule `datemc` en mode binaire (retour hex) dans le script generique `read_isam.py` -- cf skill `reading-isam-files`.
