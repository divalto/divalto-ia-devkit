# Structure d'un fichier .dhpt (projet principal)

## Contenu

- En-tete
- Sections (dans l'ordre)
- Sections obligatoires meme si vides (P13)
- Arborescence type

---


## En-tete

```
xwin-projet        2.0
```

Exactement `xwin-projet` suivi d'espaces puis `2.0`. Ne JAMAIS utiliser `xwin-sprojet` (anti-pattern P05).

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

| Cle | Description | Exemple |
|-----|-------------|---------|
| nom | Nom du projet entre guillemets | `"divalto achat-vente"` |
| progexec | Programme executable (.dhop) | `"ia.dhop"` |
| date | Horodatage 20 caracteres : `YYYYMMDDHHMMSSmmm999` | `"20260203034221264799"` |
| util | Utilisateur createur/modificateur | `"EBX13"` |
| filtres | Patterns de filtrage (separes par `;`) | `"??pp*;??pc*"` |
| modeweb | Mode web (3 = dual web/desktop) | `3` |
| projetstandard | 1 = projet standard Divalto | `1` |

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
