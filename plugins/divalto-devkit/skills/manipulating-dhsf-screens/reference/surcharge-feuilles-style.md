# Surcharge des feuilles de style `.dhfi`

## Contenu

- Les 3 feuilles de style standard
- Convention de surcharge -- suffixe `u` final
- Placement dans le projet
- Cas d'usage (override, extension, modification)
- Implication pour `wstyle` des composants
- Questions ouvertes a Stephane Castelain

---

## Les 3 feuilles de style standard

Les masques `.dhsf` referencent leur feuille de style via la propriete `[masque].feuille_style="<fichier>.dhfi"`. Trois feuilles standard sont livrees dans `C:\divalto\sys\` (ou equivalent du chemin ERP du partenaire) :

| Fichier | Role |
|---------|------|
| `fstyle.dhfi` | Styles classiques (anciens masques, anterieurs WPF) |
| `fstylewpf.dhfi` | Styles WPF (masques modernes -- typique en X.13) |
| `fstyleimp.dhfi` | Styles impression |

Chaque `.dhfi` est un fichier ISAM accompagne de son `.dhfd` (dictionnaire de structure -- couple standard). `fstylewpf.dhfi` du pack standard X.13 v2026_erpX13_p223a fait ~175 KB et contient 559+ identifiants de styles distincts (`STD`, `STD_AFF`, `STD_GRAS`, `ZOOM`, `GROUPE`, etc.).

> **Pourquoi un fichier ISAM et pas un INI** : les feuilles de style sont consultees a haute frequence au runtime, l'acces indexe est plus rapide. Voir `reading-isam-files` et `writing-isam-files` pour la manipulation generique des `.dhfi`/`.dhfd`.

---

## Convention de surcharge -- suffixe `u` final

Chaque feuille de style standard peut etre **surchargee** par un fichier compagnon au suffixe `u` final, conforme au pattern de surcharge global Divalto (cf. [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md) pour les masques) :

| Standard | Surcharge | Contexte |
|----------|-----------|----------|
| `C:\divalto\sys\fstyle.dhfi` | `<projet>/fichiers/fstyleu.dhfi` | Styles classiques |
| `C:\divalto\sys\fstylewpf.dhfi` | `<projet>/fichiers/fstylewpfu.dhfi` | Styles WPF (typique) |
| `C:\divalto\sys\fstyleimp.dhfi` | `<projet>/fichiers/fstyleimpu.dhfi` | Styles impression |

Le pattern uniforme "tout est surchargeable par suffixe `u` final" s'applique aussi aux feuilles de style. Voir la taxonomie complete des surcharges :

| Type | Standard | Surcharge | Doc dediee |
|------|----------|-----------|------------|
| Dictionnaire | `<dict>.dhsd` | `<dict>u.dhsd` | [managing-diva-dictionaries/dhsd-surcharge-pattern.md](../../managing-diva-dictionaries/reference/dhsd-surcharge-pattern.md) |
| Source DIVA | `<base>.dhsp` | `<base>u.dhsp` | [coding-diva-advanced/overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) |
| RecordSql | `<base>.dhsq` | `<base>u.dhsq` | [generating-recordsql/dhsq-overwrite-pattern.md](../../generating-recordsql/reference/dhsq-overwrite-pattern.md) |
| Masque | `<base>.dhsf` | `<base>u.dhsf` | [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md) |
| Sous-projet | `<base>.dhps` | `<base>u.dhps` (suffixe final) | [managing-diva-projects/dhps-structure.md](../../managing-diva-projects/reference/dhps-structure.md) |
| Projet | `<base>.dhpt` | en-tete `xwin-s-projet` | [managing-diva-projects/SKILL.md](../../managing-diva-projects/SKILL.md) |
| **Feuille de style** | `<fstyle>.dhfi` | `<fstyle>u.dhfi` | (cette page) |

---

## Placement dans le projet

Les feuilles de style surchargees vont dans `<projet>/fichiers/`, PAS dans `<projet>/sources/` :

| Type | Repertoire |
|------|------------|
| Sources DIVA (`.dhsp`, `.dhsf`, `.dhsq`, `.dhsd`) | `<projet>/sources/` |
| Fichiers ISAM (`.dhfi`, `.dhfd`) y compris feuilles de style | `<projet>/fichiers/` |

C'est la convention generale : `fichiers/` pour les artefacts ISAM, `sources/` pour les sources compilables.

---

## Cas d'usage

### 1. Reutilisation -- utiliser un wstyle existant du standard

Aucune surcharge necessaire. Dans le masque user, referencer directement un wstyle livre :

```ini
[champ]
[presentation]
  id=51
  wstyle="STD_GRAS"
```

Les 559+ styles livres couvrent la majorite des besoins UI.

### 2. Extension -- ajouter un nouveau wstyle custom

Creer / enrichir `<projet>/fichiers/fstylewpfu.dhfi` avec un nouvel enregistrement (clef = nouveau nom de style), puis le referencer dans le masque :

```ini
[champ]
[presentation]
  id=52
  wstyle="MON_STYLE_CUSTOM"
```

La feuille de style surchargee n'ecrase pas les styles standard ; elle les **complete**.

### 3. Modification -- surcharger un wstyle standard

Creer dans `<projet>/fichiers/fstylewpfu.dhfi` un enregistrement avec **le meme nom de clef** qu'un style standard (ex: `ZOOM`). Le style standard est **ecrase** par la surcharge.

> Comportement xwin7 : la surcharge prend priorite sur le standard (pattern conforme aux surcharges `.dhsd` / `.dhsp` / `.dhsf`). Empiriquement plausible mais a confirmer avec `XmeSetAttribut` au runtime.

---

## Implication pour `wstyle` des composants

La propriete `wstyle="<X>"` d'un composant (`obj_texte`, `champ`, `groupbox`, etc.) n'est **pas une enumeration fermee** : c'est une **clef** dans le fichier ISAM de feuille de style. Implications :

- Aucun lint ne peut prouver qu'un `wstyle` est invalide sans consulter le fichier de style (standard + surcharge eventuelle).
- Pour valider un wstyle utilise dans un masque, il faut introspectionner `fstylewpf.dhfi` (standard) et `fstylewpfu.dhfi` (surcharge du projet en cours).

Voir [reading-isam-files](../../reading-isam-files/SKILL.md) pour lire un `.dhfi` et lister les styles disponibles. Un script `list_styles.py` reste un candidat futur SC.

---

## Questions ouvertes a Stephane Castelain

- **Priorite override** : empiriquement, la surcharge ecrase-t-elle le standard pour une meme clef ? Ou comportement different (merge, refus...) ?
- **Detection des conflits** : xwin7 signale-t-il les surcharges de styles standards (warning au build) ?
- **Ordre de chargement** : si plusieurs projets de surcharge sont actifs en parallele, ordre de priorite ?

A confirmer empiriquement ou via Stephane et remonter via RETEX SUGGESTION-DOC.
