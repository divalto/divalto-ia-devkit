---
name: managing-diva-error-messages
description: A utiliser pour lire, comparer ou gerer les messages d'erreur applicatifs DIVA (fichiers XXferr : gtferr/ccferr... standard, ou <prefixe>ferr specifique partenaire), ou quand un controle GererErreurCheck(NNN) necessite un message dedie | Lit codes et libelles via reading-isam-files (ISAM, pas de regex sur octets bruts) ; compare deux fichiers pour detecter codes ajoutes/retires/custom (arbitrage downgrade) ; documente la gestion sure (ajout via la mecanique standard IHM, jamais d'ecriture binaire ; verification --check). Norme : un XXferr standard ne se modifie jamais (lecture seule) ; le specifique partenaire est modifiable. Emplacement localise via understanding-integrator-workspace.
---

# managing-diva-error-messages -- Messages d'erreur applicatifs (XXferr)

## Contenu

- Quand l'utiliser
- Norme et permissions
- Emplacement
- Lecture (codes + libelles)
- Diff / arbitrage downgrade
- Gestion (ajout d'un message)
- Structure de l'enregistrement d'erreur
- Voir aussi

---

## Quand l'utiliser

- **Lire** les codes/libelles d'erreur d'un module (`--list`, `--check <code>`).
- **Comparer** deux fichiers d'erreur (`--diff`) : codes ajoutes/retires entre deux
  packs, detection d'un **custom** (arbitrage downgrade/migration).
- **Gerer** : quand un controle `GererErreurCheck(NNN, ...)` reference un numero
  **absent** des `XXferr`, l'utilisateur ne voit aucun texte -> il faut ajouter le
  message. Ce skill documente la **procedure sure** d'ajout.

**Ne pas utiliser pour** :
- Modifier un fichier d'erreur **standard** (interdit -- voir Norme).
- Ecrire le `.dhfi`/`.dhfd` en **binaire direct** (corruption -- voir `writing-isam-files`).

---

## Norme et permissions

| Fichier | Exemples | Permission |
|---------|----------|------------|
| `XXferr` **standard** | `gtferr`, `ccferr`, `a5ferr`, `rcferr`... | **Lecture seule** -- ne jamais modifier (comme tout source standard) |
| `XXferr` **specifique partenaire** | `<prefixe>ferr` (prefixe du partenaire) | **Lecture + ecriture** -- c'est ton fichier |

Consequence : un **code custom present dans un fichier standard = violation de norme**
(le custom doit vivre dans le `XXferr` **propre** du partenaire). C'est ce que le
`--diff` aide a detecter.

**Technique d'ecriture** (independante de la permission) : meme sur ton fichier
specifique, **ne jamais ecrire le binaire en direct**. Les enregistrements sont a
longueur variable et une ecriture mal dimensionnee corrompt le fichier (cf.
`writing-isam-files`, garde-fou taille). L'ajout passe par la **mecanique standard**
(voir Gestion).

---

## Emplacement

Les `XXferr.dhfi`/`.dhfd` sont **par convention** dans le repertoire **`objets/`** d'un
pack (un par prefixe module), **mais rien ne l'impose** -- ils peuvent etre ailleurs.
Pour les localiser de facon fiable, resoudre les chemins de recherche du workspace via
le skill **`understanding-integrator-workspace`**. *(A ne pas confondre avec les
multichoix `XXfdmc`, plutot cote `sources/` -- cf. `reading-multichoix`.)*

---

## Lecture (codes + libelles)

Un `XXferr.dhfi` est un **ISAM sequentiel indexe** (table `XErr`). On le lit **via le
skill `reading-isam-files`** -- pas de regex sur octets bruts : un extracteur texte
naif sous-compte (les cles numeriques sont **cadrees a droite avec espaces**, ex.
`A 9129`), ce qui a deja fait conclure a tort « pas de custom » et faillit detruire des
messages custom. Lire les **vrais enregistrements** evite tout ce piege.

```bash
# Lister tous les codes + libelles
py .claude/skills/managing-diva-error-messages/scripts/manage_error_messages.py \
    --file "<...objets...>/gtferr.dhfi" \
    --read-isam-script .claude/skills/reading-isam-files/scripts/read_isam.py \
    --list

# Verifier l'existence d'un code (et lire son libelle)
py .claude/skills/managing-diva-error-messages/scripts/manage_error_messages.py \
    --file "<...>/gtferr.dhfi" \
    --read-isam-script .claude/skills/reading-isam-files/scripts/read_isam.py \
    --check 1183
```

`--list` -> `{total_codes, codes:[{code, message}]}` ; `--check <code>` ->
`{found, message}` (exit 1 si absent). Les `$N` dans un libelle (`$1`, `$2`...) sont
des **parametres runtime**. Les enregistrements de `Errnum=0` sont des lignes de
commentaire (`;*`), ecartees du comptage.

La structure d'enregistrement par defaut (`scripts/structures/structure_xxferr.json`)
couvre les `XXferr` standard **et** specifiques (meme table `XErr`).

---

## Diff / arbitrage downgrade

```bash
py .claude/skills/managing-diva-error-messages/scripts/manage_error_messages.py \
    --file "<pack_downgrade>/gtferr.dhfi" \
    --read-isam-script .claude/skills/reading-isam-files/scripts/read_isam.py \
    --diff "<pack_standard>/gtferr.dhfi"
```

Sortie : `count_a` / `count_b` / `common` / `only_in_a` / `only_in_b`.

**Lecture pour un arbitrage downgrade/migration** (A = downgrade/courant, B = standard) :
`only_in_a` = codes **presents chez toi, absents du standard** = candidats **CUSTOM a
PRESERVER**. **Ne jamais adopter aveuglement** le standard : on **conserve** les customs
(les remettre dans le `XXferr` **propre** du partenaire). Cross-ref
`migrating-erp-downgrade` (meme logique d'arbitrage que pour le dico et le RecordSQL).

> Il n'existe **pas** d'outil natif Divalto de comparaison de fichiers d'erreur
> (contrairement aux multichoix). Ce `--diff` (lecture seule) est donc le moyen outille.

---

## Gestion (ajout d'un message)

Ajouter/editer un message dans **ton** `XXferr` specifique est **legitime** (c'est le
besoin recurrent : chaque nouveau `GererErreurCheck(NNN)` veut son texte). Procedure
**sure** :

1. **Backup** des deux fichiers (`.dhfi` + `.dhfd`) avant toute operation.
2. **Ajouter le message via l'IHM standard** de gestion des messages applicatifs (la
   meme mecanique que pour les fichiers standard ; elle pilote `.dhfi`+`.dhfd`
   **atomiquement**). Cette gestion est **interactive (IHM), non scriptable**.
3. **Verifier apres ecriture** avec `--check <code>` (relit l'enregistrement et
   confirme code + libelle).

> **Ne jamais** ecrire le binaire directement (ni `write_isam`) : enregistrements a
> longueur variable -> corruption silencieuse (cf. `writing-isam-files`). On passe par
> l'IHM, qui est le canal supporte.

---

## Structure de l'enregistrement d'erreur

Table `XErr` (« Table des messages »), **206 octets** :

| Champ | Offset | Taille | Sens |
|-------|--------|--------|------|
| `Nivalerte` | 0 | 1 | Niveau d'alerte |
| `Errnum` | 1 | 5 | Numero du code (cadre a droite, espaces) |
| `Errtxt` | 6 | 200 | Libelle (`$N` = parametres runtime) |

Cle d'index : lettre `A` + `Errnum` cadre a droite sur 5 (ex. `A 9129`). Detail :
[reference/error-message-files.md](reference/error-message-files.md).

---

## Voir aussi

- `reading-isam-files` -- lecture ISAM des `XXferr` (ce skill l'invoque)
- `understanding-integrator-workspace` -- localiser les `XXferr` (chemins de recherche)
- `writing-isam-files` -- garde-fou taille (pourquoi on n'ecrit pas le binaire)
- `generating-objet-metier` -- genere les appels `GererErreurCheck(NNN)` (consommateur des codes)
- `migrating-erp-downgrade` -- arbitrage downgrade (meme logique que `--diff`)
- [reference/error-message-files.md](reference/error-message-files.md) -- structure, cle, format `.dhfd`, lecons RETEX
