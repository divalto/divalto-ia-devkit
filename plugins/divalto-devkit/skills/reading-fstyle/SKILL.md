---
name: reading-fstyle
description: >
  Lit les feuilles de style ISAM Divalto (`fstyle.dhfi` et 3 variantes WPF /
  impression / web dans `C:\divalto\sys\`). Liste les styles disponibles,
  detaille un style, resout les references i18n des libelles `tbl*` (ex:
  TBLART -> `#tblart`). Gere les 7 Types semantiques : 1 police, 2 couleur
  RGB, 3 reference i18n, 5 style global STD, 6 cadre, 7 style compose,
  9 contexte. A utiliser pour consulter la definition graphique d'un style
  nomme consomme par les multichoix Type=4 (`LstStyleWpf` / `LstStyleImp` /
  `LstPolice` de gtfdmc.dhfi), pour identifier un cadre/police, ou pour
  resoudre un libelle `tbl*` decouvert dans les multichoix.
---

# Reading Fstyle

## Contenu

- Utilisation rapide
- Modes
- Format de sortie
- Les 7 Types en un coup d'oeil
- Variantes fstyle
- Scripts disponibles
- References
- Points ouverts

---

## Utilisation rapide

```bash
# Lister tous les styles d'une variante (par defaut : wpf)
py .claude/skills/reading-fstyle/scripts/read_fstyle.py \
    --variant wpf --list

# Detailler un style specifique
py .claude/skills/reading-fstyle/scripts/read_fstyle.py \
    --variant wpf --detail TBLART

# Statistiques par Type
py .claude/skills/reading-fstyle/scripts/read_fstyle.py \
    --variant wpf --stats

# Resoudre un nom dans les 3 variantes (wpf -> legacy -> imp)
py .claude/skills/reading-fstyle/scripts/read_fstyle.py --resolve TBLART
```

Fichier custom via `--file` :
```bash
py read_fstyle.py --file "C:\autre\chemin\fstyle.dhfi" --list
```

---

## Modes

| Mode | Parametres | Description |
|------|-----------|-------------|
| `--list` | `--variant` OU `--file` | Liste des styles (nom, type) en JSON |
| `--detail <NOM>` | `--variant` OU `--file` + `--detail` | Detail d'un style avec decodage typise |
| `--all-details` | `--variant` OU `--file` | Dump complet de tous les styles (consommation machine) |
| `--stats` | `--variant` OU `--file` | Distribution des Types rencontres |
| `--resolve <NOM>` | `--resolve` + optionnel `--variant-order` | Interroge les variantes dans l'ordre et retourne la premiere correspondance |

Modes mutuellement exclusifs. `--variant` ou `--file` sont requis sauf pour `--resolve` (qui gere son propre cycle).

---

## Format de sortie

### `--list`

```json
{
  "success": true,
  "file": ".../fstylewpf.dhfi",
  "total": 1655,
  "styles": [
    { "nom": ".POLICE", "type": "1" },
    { "nom": "TBLART", "type": "3" }
  ]
}
```

### `--detail TBLART` (Type 3)

```json
{
  "success": true,
  "file": ".../fstylewpf.dhfi",
  "type": "3",
  "nom": "TBLART",
  "cle_i18n": "#tblart",
  "flags": "001",
  "found": true
}
```

### `--detail ARIAL10` (Type 1)

```json
{
  "type": "1",
  "nom": "ARIAL10",
  "taille": "10",
  "poids": "400000",
  "famille": "Arial",
  "couleur_texte": { "r": 0, "g": 0, "b": 0 },
  "couleur_texte_composante_4": 0,
  "couleur_texte_brut": "  0  0  0  0",
  "attributs_non_decodes": ["semantique_composante_4", "drapeaux_apres_famille"],
  "found": true
}
```

> **Taille, poids et famille ne suffisent PAS a identifier une police.** La couleur du texte
> vit a un **offset fixe** (octet 109, 4 composantes de 3 caracteres) et non dans les tokens.
> Sans elle, **64 des 142 Type 1** de `fstylewpf` decodaient a l'identique -- dont 24 sur le
> seul `{8, 400000, Tahoma}`. Avec elle : **21**. Voir
> [reference/fstyle-types.md](reference/fstyle-types.md).

> **`attributs_non_decodes` dit ce que la sortie ignore.** La 4e composante vaut `0` partout et
> sa semantique n'est **pas** etablie : elle n'est donc pas nommee « alpha ». Le champ de
> drapeaux qui distingue les 21 collisions restantes n'est pas interprete non plus. **Un
> decodage muet sur ses trous parait complet** -- c'est le defaut que ce lot corrige.

### `--resolve TBLART`

```json
{
  "success": true,
  "nom": "TBLART",
  "resolved": true,
  "variant_source": "wpf",
  "type": "3",
  "cle_i18n": "#tblart",
  "decoded": { "type": "3", "nom": "TBLART", "cle_i18n": "#tblart", "flags": "001" },
  "variants_tried": ["wpf"]
}
```

### `--resolve TBLAFF` (orphelin, exit 1)

```json
{
  "success": false,
  "nom": "TBLAFF",
  "resolved": false,
  "orphan": true,
  "variants_tried": ["wpf", "legacy", "imp"]
}
```

### `--stats`

```json
{
  "total_nc": 1655,
  "by_type": {
    "1": { "count": 111, "pct": 6.7 },
    "3": { "count": 223, "pct": 13.5 }
  }
}
```

---

## Les 7 Types en un coup d'oeil

| Type | Role | Cas typique |
|------|------|-------------|
| `1` | Police (font) | `ARIAL10G` : taille 10, poids 700000 (gras), famille Arial |
| `2` | Couleur RGB nommee | `AFFERR` : 255, 0, 0 (rouge erreur) |
| `3` | Reference i18n (`#xxx`) | `TBLART` -> `#tblart` (source pour resoudre les libelles `tbl*` des multichoix) |
| `5` | Style global STD | 1 seul par variante, regroupe styles contextuels |
| `6` | Cadre (border) | 6 cadres canoniques (SANS, SIMPLE, RELIEF_*, CADRE_*) |
| `7` | Style compose | Assemblage **positionnel** `<police> <cadre> <couleur>` -- les noms des 2e et 3e slots ne tiennent pas toujours, voir ci-dessous |
| `9` | Contexte | `.BOUTON` / `.MENU` / `.TOOLBAR` + entrees `#tbr_xxx` |

> **Type 7 : se fier au type REEL de la cible, jamais au nom du slot.** Mesure sur les
> **235 Type 7** de `fstylewpf` : `police_ref` vise une police **235 fois sur 235**, mais
> `cadre_ref` ne vise un cadre que **165** fois et `couleur_ref` une couleur **222** fois.
> **Aucune reference n'est pendante** -- les 705 pointent sur un nom present. `--detail`
> expose donc `refs_types_reels`, et `refs_hors_type_attendu` quand un slot ne tient pas son
> nom.

Detail complet + exemples empiriques dans [reference/fstyle-types.md](reference/fstyle-types.md).

---

## Variantes fstyle

Les 4 variantes du dossier `C:\divalto\sys\` ont la meme structure ISAM -- seul le contenu diverge selon le contexte de rendu.

| Variante | Fichier | Role | Records | TBL* |
|----------|---------|------|---------|------|
| `wpf` | `fstylewpf.dhfi` | WPF moderne (**prioritaire**) | 1655 | 223 |
| `legacy` | `fstyle.dhfi` | WinForms historique | 794 | 73 |
| `imp` | `fstyleimp.dhfi` | Impression | 588 | 13 |
| `web` | `fstyleweb.dhfi` | Web (minimal, 0 `tbl*`) | 56 | 0 |

L'ordre de resolution par defaut pour `--resolve` est `wpf,legacy,imp` (web exclu car 0 `tbl*`). Personnalisable via `--variant-order "legacy,wpf,imp"`.

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/read_fstyle.py` | Lit et interprete `fstyle*.dhfi` selon le mode demande | `--variant` ou `--file` + mode | JSON (voir Format de sortie) |

### Exit codes

| Code | Signification |
|------|---------------|
| 0 | Lecture reussie avec resultat (ex : detail trouve, resolve resolu) |
| 1 | Lecture reussie mais resultat vide (ex : detail d'un nom inexistant, resolve d'un orphelin) |
| 2 | Erreur (DLL absente, fichier introuvable, mode invalide) |

### Prerequis

- `DhxIsam64.dll` accessible sous `C:\divalto\sys\` (meme prerequis que `reading-multichoix`)
- Python 3 (pas de dependance externe)

---

## References

- [reference/fstyle-types.md](reference/fstyle-types.md) -- detail des 7 Types avec exemples empiriques et strategie de resolution
- Skill compagnon : `reading-multichoix` -- les identifiants Type 4 de gtfdmc (`LstStyleWpf`, `LstStyleImp`, `LstPolice`) pointent vers les styles consommes par ce skill

---

## Points ouverts

- **FS-01** : localiser la ressource i18n qui resout `#tblart -> "Article"` (fichier `.lng` ou ressources XAML des DLL WPF `DH.*`). Sans cela, la resolution s'arrete a la cle i18n.
- **FS-02** : couvrir les 8 orphelins DAV (`TBLAFF`, `TBLMAINT`, `TBLMOINS`, `TBLPLUS`, `TBLSMILEY1-3`, `TBLNOTESEQ`). Verifier : 5e fstyle non identifie, custom, ou generation dynamique.
- **FS-03** : integrer ce skill dans `documenting-erp` (vendoring + enrichissement rendu `_(icone "TBLART", style WPF)_`). Leve le defaut de rendu des libelles `tbl*` dans les livrables de documentation.
- **FS-04** : formaliser la semantique des flags Type 3 (`001` / `000AUTOMATIQUE` observes empiriquement).
- **FS-05** : formaliser le **champ de drapeaux** du Type 1 (octet ~123, observe `0010000000`, `0001011111`, `0.01111011`). C'est lui qui distingue les **21 styles** encore indistinguables apres le decodage de la couleur. Declare `non decode` en attendant.
- **FS-06** : etablir la semantique de la **4e composante de couleur** du Type 1, constante a `0` sur les 142 enregistrements mesures. Ne pas la supposer equivalente au canal `a` du Type 2 sans preuve.
