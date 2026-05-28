# Structure d'un fichier .dhpt (projet principal)

## Contenu

- En-tete -- variantes standard et surcharge
- Sections (dans l'ordre)
- Sections obligatoires meme si vides (P13)
- Arborescence type

---


## En-tete

Deux variantes valides selon le contexte du projet :

| Cas | En-tete | Quand |
|-----|---------|-------|
| **Standard** | `xwin-projet        2.0` | .dhpt d'un projet standard (projet Divalto principal, ou projet client autonome) |
| **Surcharge** | `xwin-s-projet      2.0` | .dhpt qui surcharge un projet du standard livre (nom `<base>u.dhpt`) |

Anti-patterns associes :
- `xwin-sprojet` (sans tiret entre `s` et `projet`) dans un .dhpt -> anti-pattern P05 (interdit)
- `xwin-projet` (standard) dans un projet de surcharge -> xwin7 ne reconnait pas la surcharge (script `add_to_project.py` refuse ce header dans le contexte surcharge)

### Quand utiliser la variante surcharge

Un `.dhpt` est un projet de surcharge quand :
1. Son nom suit la convention `<base>u.dhpt` (suffixe `u` final avant l'extension, ex: `divalto achat-venteu.dhpt` qui surcharge `divalto achat-vente.dhpt` du standard)
2. Il herite des sous-projets et configurations du `.dhpt` standard correspondant via le mecanisme `cheminbases`
3. Il declare des `.dhps` de surcharge (cf. [dhps-structure.md](dhps-structure.md) -- meme convention `<base>u.dhps` + en-tete `xwin-s-sprojet`)
4. Il vit dans le repertoire de surcharge du workspace integrateur (typiquement `<workspace>/projets/`)

### Relation avec les .dhps

Un projet de surcharge contient typiquement deux types de `.dhps` :

| Type | Convention | En-tete .dhps | Reference dans `[sousprojets]` du .dhpt |
|------|------------|---------------|-----------------------------------------|
| Sous-projet **standard** | `<base>.dhps` (pas de suffixe `u`) | `xwin-sprojet 2.0` | **Oui** -- declare dans `[sousprojets]` |
| Sous-projet **de surcharge** | `<base>u.dhps` (suffixe `u`) | `xwin-s-sprojet 2.0` | **Non** -- xwin7 l'auto-detecte via `cheminbases` (cf. P17) |

Voir [dhps-structure.md](dhps-structure.md) pour le detail des conventions .dhps.

### Workflow type sur un projet de surcharge

1. Ouvrir le `.dhpt` de surcharge (header `xwin-s-projet`) du workspace integrateur
2. Identifier le `.dhpt` standard correspondant (meme nom sans le `u` final) -- typiquement dans `<DIVA_ROOT>/projets/` ou repertoire equivalent du pack standard
3. Pour ajouter une nouvelle entite custom : creer une `.dhps` de surcharge `<base>u.dhps` (header `xwin-s-sprojet`), **ne pas** la lister dans `[sousprojets]` (P17 -- xwin7 l'auto-detecte)
4. Pour modifier un parametre du projet (filtres, profils, communs) : editer directement le `.dhpt` de surcharge

---

## Sections (dans l'ordre)

### [general] (OBLIGATOIRE)

```ini
[general]
nom="divalto achat-vente"
progexec="ia.dhop"
date="20260203034221264799"
util="EBX13"
filtres="??pp*;??pc*;??pm*;??pz*;??p9*"
modeweb=3
projetstandard=1
```

| Cle | Description | Exemple | Obligatoire |
|-----|-------------|---------|-------------|
| nom | Nom du projet entre guillemets | `"divalto achat-vente"` | oui |
| progexec | Programme executable (.dhop) | `"ia.dhop"` | oui |
| date | Horodatage 20 chiffres (format non strict, xwin7 ne valide pas) | `"20260203120000000000"` | oui |
| util | Utilisateur createur/modificateur | `"EBX13"` | oui |
| filtres | Patterns de filtrage (separes par `;`) | `"??pp*;??pc*"` | oui (peut etre vide) |
| modeweb | Mode web (3 = dual web/desktop) | `3` | oui |
| projetstandard | 1 = projet standard Divalto, 0 = projet partenaire | `1` | oui |
| **cheminbases** | Pointe sur le dossier des **sources** standard (cf. sous-section dediee ci-dessous) | `"/../../../sources/v2026_erpx13_p223a"` | oui sur un `.dhpt` de surcharge |
| **flagrelatif** | `1` = `cheminbases` est relatif au `.dhpt` (recommande), `0` ou absent = absolu | `1` | conseille sur un `.dhpt` de surcharge |
| **f5compile** | `1` = active la compilation incrementale F5 dans xwin7 | `1` | typiquement `1` sur un `.dhpt` de surcharge |
| **typetransport** | Mode de transport entre xwin7 et le compilateur, observe `3` sur les surcharges fonctionnelles | `3` | typiquement `3` sur un `.dhpt` de surcharge |

**Note sur `date=`** : la documentation precedente decrivait un decoupage `YYYYMMDDHHMMSSmmm999`, mais ce decoupage n'est pas applique en pratique -- l'exemple `20250925268411001599` decompose donne `MM=84` (minute > 59), impossible. xwin7 ne valide pas ce champ ; toute valeur de 20 chiffres est acceptee. Recommandation pragmatique : generer `YYYYMMDD` + 12 zeros (ex: `"20260203000000000000"`).

**Convention de casse pour les noms de version ERP** : les chemins versionnes (`cheminbases`, `repobjet`, ...) doivent utiliser le format `v<annee>_erp<x>_p<patch>` **tout en minuscule** -- par exemple `v2026_erpx13_p223a` et **pas** `v2026_erpX13_p223a` (la convention sure observee terrain est lowercase, le `X` majuscule fonctionne sur certains postes mais pas sur d'autres).

#### Sous-section `cheminbases` (specifique aux `.dhpt` de surcharge)

`cheminbases` est la cle qui declare l'emplacement des **sources standard ERP** que la surcharge etend. C'est conceptuellement different de `repobjet` du `[profil]` qui pointe sur les **objets compiles** standard :

| Champ | Pointe sur | Type d'artefact | Phase d'utilisation |
|-------|------------|------------------|----------------------|
| `cheminbases` (section `[general]`) | Repertoire des **sources** standard (`<racine_standard>/sources/v<X>/`) | Sources DIVA (.dhsp, .dhsq, .dhsd, .dhsf) | Resolution des surcharges (xwin7 retrouve les fichiers `<base>_sql.dhsf` etc. dans ce repertoire) |
| `repobjet` (section `[profil]`) | Repertoire des **objets compiles** standard (`<racine_standard>/objets/v<X>/`) | Objets compiles (.dhof, .dhoq) | Phase de link au build |

Confondre les deux (mettre `cheminbases` vers `/objets/v<X>/` au lieu de `/sources/v<X>/`) provoque l'ouverture en erreur du `.dhpt` dans xwin7 -- xwin7 ne trouve pas les sources a surcharger.

**Convention recommandee** : declarer `cheminbases` en chemin **relatif** au `.dhpt`, avec `flagrelatif=1` dans `[general]`. Cela rend le `.dhpt` portable d'un poste a l'autre sans depatcher les chemins absolus.

```ini
[general]
...
cheminbases="/../../../sources/v2026_erpx13_p223a"
flagrelatif=1
f5compile=1
typetransport=3
```

Le chemin `../../../sources/v2026_erpx13_p223a` est relatif a l'emplacement du `.dhpt` lui-meme : depuis `<workspace>/projets/<domaine>u.dhpt`, on remonte 3 niveaux (`projets/` puis `<workspace>/` puis racine du partenaire), puis on descend dans `sources/v2026_erpx13_p223a` -- a adapter selon la profondeur du workspace.

#### Exemple complet d'un `.dhpt` de surcharge fonctionnel

```ini
xwin-s-projet      2.0
[general]
nom="divalto achat-venteu"
progexec="ia.dhop"
date="20260527120000000000"
util="EBX13"
filtres="??pp*;??pc*;??pm*;??pz*;??p9*"
modeweb=3
projetstandard=0
cheminbases="/../../../sources/v2026_erpx13_p223a"
flagrelatif=1
f5compile=1
typetransport=3
[profildefaut]
[profil]
nom="développement"
repobjet="/objets/v2026_erpx13_p223a"
repobjetsurcharge="/specifs/<workspace>/objets/"
repbrowse="/objets/v2026_erpx13_p223a/browse"
repbrowsesurcharge="/specifs/<workspace>/navigation/"
implicites="impltmp.txt"
versioncible="X.13"
[communs]
nom="surcharges_communes"
[sousprojets]
[projetsfusion]
[fabricationmere]
[autres]
```

Conventions appliquees :
- En-tete `xwin-s-projet` (variante surcharge)
- `projetstandard=0` (projet partenaire, pas livre Divalto)
- `cheminbases` relatif vers les **sources** standard (`/sources/v.../`, pas `/objets/v.../`)
- `flagrelatif=1`, `f5compile=1`, `typetransport=3` -- les 3 cles `[general]` souvent oubliees a la generation
- Noms de version en lowercase (`v2026_erpx13_p223a`)
- Pas de `.dhps` de surcharge dans `[sousprojets]` -- ils sont auto-detectes via `cheminbases` (cf. P17)

### [profildefaut] (OBLIGATOIRE, peut etre vide)

```ini
[profildefaut]
```

Profil par defaut. Generalement vide.

### [profil] (OBLIGATOIRE, au moins 1)

```ini
[profil]
nom="développement"
repobjet="/vx13/objet"
implicites="développement_x13.txt"
versioncible="X.45"
```

| Cle | Description |
|-----|-------------|
| nom | Nom du profil (attention accent `\xe9` en ISO-8859-1) |
| repobjet | Chemin du repertoire objet |
| implicites | Fichier d'implicites (attention accent) |
| versioncible | Version cible de compilation |

**Attention encodage** : `développement` contient `\xe9` (e accent aigu en ISO-8859-1). Ne pas ecrire `developpement` sans accent (P14, P15).

Plusieurs sections `[profil]` possibles dans un meme fichier.

### [communs] (OBLIGATOIRE, multiple)

```ini
[communs]
nom="a5_base"
fic="a5pm000.dhsp"," "
fic="a5ee600.dhsf"," "

[communs]
nom="dictionnaires"
fic="a5dd.dhsd"," "
fic="grfdd.dhsd"," "
```

- Chaque bloc `[communs]` definit un **groupe nomme** de fichiers partages
- `nom` : nom du groupe (convention : `prefixe_domaine`)
- `fic` : fichier dans le groupe, syntaxe `fic="nom"," "`
- Les .dhps referent ces groupes via `incl="nom_groupe"," "`

### [sousprojets] (OBLIGATOIRE)

```ini
[sousprojets]
fic="gt_zoom article.dhps"," "
fic="gt_zoom client.dhps"," "
fic="cc_dashboard.dhps"," "
```

- Chaque sous-projet .dhps doit y etre declare (sinon P08)
- Syntaxe : `fic="nom.dhps"," "` (avec `," "`)
- Variante : `fic="nom.dhps","<priv>1"` pour fichier prive

### [projetsfusion] (OBLIGATOIRE, peut etre vide)

```ini
[projetsfusion]
fic="divalto comptabilité.dhpt"," "
fic="divalto achat-vente.dhpt"," "
```

References vers d'autres .dhpt a fusionner. Vide si projet autonome.

### [fabricationmere] (OBLIGATOIRE, peut etre vide)

```ini
[fabricationmere]
repdest="/vx13/projet"
compilation=0
copierobjets=0
profil="développement"
```

Configuration de construction du projet mere. Generalement vide pour les projets non-meres.

### [autres] (OBLIGATOIRE, peut etre vide)

```ini
[autres]
fic="p3ferr.dhfd"," "
fic="erreurs.config"," "
```

Fichiers divers : .dhfd, .dhfi, .dhop, .config, images. Vide si aucun.

---

## Sections obligatoires meme si vides (P13)

Les 3 sections suivantes doivent toujours etre presentes, meme vides :
- `[projetsfusion]`
- `[fabricationmere]`
- `[autres]`

---

## Arborescence type

```
Module/
  projet/
    divalto achat-vente.dhpt     (1 projet principal)
    gt_zoom article.dhps         (sous-projets)
    gt_zoom client.dhps
    ...
  source/
    Dav/                         (sources par domaine)
```
