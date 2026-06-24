# Fichiers de messages d'erreur applicatifs (XXferr)

Reference du skill `managing-diva-error-messages`. Couvre la structure, la cle, le
format, l'emplacement et les pieges (lecons RETEX), pour les fichiers d'erreur
**standard** (`gtferr`, `ccferr`, `a5ferr`, `rcferr`...) **et specifiques** partenaire.

## Vue d'ensemble

Un message d'erreur applicatif est porte par deux fichiers solidaires :

| Fichier | Role |
|---------|------|
| `XXferr.dhfi` | ISAM (donnees + index) : un enregistrement par code, **le libelle y est** |
| `XXferr.dhfd` | Dictionnaire / donnees associe |

Ils sont gere s **atomiquement** par la mecanique standard de gestion des messages
applicatifs (IHM). Cote lecture, on lit le `.dhfi` via `reading-isam-files`.

## Structure de l'enregistrement (table XErr)

Tous les `XXferr` (standard et specifiques) partagent la **meme table `XErr`**
(« Table des messages »), declaree dans le dico `a5dd.dhsd` (base `a5ferr`),
**206 octets** :

| Champ | Offset | Taille | Sens |
|-------|--------|--------|------|
| `Nivalerte` | 0 | 1 | Niveau d'alerte |
| `Errnum` | 1 | 5 | Numero du code erreur (numerique, cadre a droite) |
| `Errtxt` | 6 | 200 | Libelle du message (`$1`, `$2`... = parametres runtime) |

Structure prete a l'emploi : `scripts/structures/structure_xxferr.json`.

## Cle d'index -- cadrage a droite (piege)

La cle du code erreur est `'A'` + `Errnum` **cadre a droite sur 5 positions, padde
d'espaces** a gauche. Exemple : code `9129` -> cle octets `41 20 39 31 32 39` =
`"A 9129"` (`A` + espace + `9129`).

> **Lecon RETEX (R-033 / #106)** : un extracteur **texte naif** `A[0-9]{5}` (5 chiffres
> colles) **rate tous les codes < 5 chiffres** -> sous-comptage massif. Cas reel sur un
> `gtferr.dhfi` : extraction naive = **2182** codes ; reelle = **~4700**. Pire, des codes
> **custom** etaient invisibles -> conclusion erronee « pas de custom, adopter le
> standard », qui aurait **detruit** les messages custom.
>
> **C'est pourquoi ce skill lit via `reading-isam-files`** (parcours des vrais
> enregistrements sur la cle `A`), et **non** par regex sur octets. Data-proof : `--list`
> sur un `gtferr.dhfi` reel = **4699** codes (compte complet, sans sous-comptage).

Si un jour on extrait des cles a la main : motif `A[ 0-9]{5}` (espace **inclus**) +
`strip` + `isdigit`. Plus generalement, les cles ISAM numeriques DIVA sont souvent
cadrees a droite avec espaces -- tout extracteur doit accepter l'espace.

## Emplacement

Par **convention** dans le repertoire **`objets/`** d'un pack (un `XXferr` par prefixe
module), **mais pas une regle** -- peut etre ailleurs. Localiser via
`understanding-integrator-workspace` (chemins de recherche du workspace). Contraste : les
multichoix `XXfdmc` sont plutot cote `sources/` (cf. `reading-multichoix`).

## Norme : standard vs specifique

- `XXferr` **standard** (`gtferr`...) : **lecture seule**, jamais modifie.
- `XXferr` **specifique** (`<prefixe>ferr` du partenaire) : **modifiable** (read/write).
- Un code **custom present dans un fichier standard** = **violation de norme** : le
  custom doit vivre dans le `XXferr` propre du partenaire. Le `--diff` aide a le detecter.

## Diff / arbitrage downgrade

`--diff A B` compare les ensembles de codes (`only_in_a`, `only_in_b`, `common`). Pour un
**arbitrage downgrade/migration** (A = downgrade/courant, B = standard) : `only_in_a` =
codes **custom a preserver** -> **fusion**, jamais d'adoption aveugle du standard. Meme
logique d'arbitrage que `migrating-erp-downgrade` (dico) et `generating-recordsql`
(RecordSQL). **Aucun outil natif Divalto** de comparaison de fichiers d'erreur
(contrairement aux multichoix) -> ce `--diff` lecture-seule est le moyen outille.

## Gestion (ajout) -- procedure sure

1. **Backup** `.dhfi` + `.dhfd`.
2. **Ajout via l'IHM standard** des messages applicatifs (pilote les 2 fichiers
   atomiquement ; **interactive, non scriptable**).
3. **Verification** `--check <code>` (relit l'enregistrement, confirme code + libelle).

**Interdit** : ecrire le binaire directement (`write_isam` ou autre) -- enregistrements a
longueur variable, corruption silencieuse (cf. garde-fou `writing-isam-files`).

## Lien avec le code

Les controles metier appellent `{PREFIX_}GererErreurCheck(NNN, ...)` (genere par
`generating-objet-metier`). Si `NNN` est absent du `XXferr`, le champ est bloque mais
**aucun texte ne s'affiche** -> d'ou le besoin d'ajouter le message (volet Gestion).
