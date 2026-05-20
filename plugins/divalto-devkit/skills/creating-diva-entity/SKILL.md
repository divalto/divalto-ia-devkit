---
name: creating-diva-entity
description: >
  Orchestre la creation de bout en bout d'une entite metier DIVA en mode collaboratif.
  A partir des parametres utilisateur (domaine, entite, table, champ cle, description),
  enchaine : calcul des noms, generation RecordSql, Module Check, Zoom SQL, bloc d'alias,
  validation croisee inter-fichiers, dictionnaire, compilation, ISAM et menu.
  Orchestration LLM avec 11 checkpoints de validation humaine — Claude s'arrete
  apres chaque etape significative pour expliquer et attendre le feu vert.
---

# Creating DIVA Entity

## Prerequis

Ce skill est un **orchestrateur LLM** : il coordonne l'execution sequentielle des skills
de generation. Les skills suivants doivent etre disponibles :

- `naming-diva-entities` (calcul des tokens)
- `generating-recordsql` (generation RecordSql)
- `generating-objet-metier` (generation Module Check)
- `generating-zoom-sql` (generation Zoom SQL)
- `manipulating-dhsf-screens` (generation masque ecran)
- `writing-diva-files` (verification encodage)
- `compiling-diva-projects` (compilation standalone)
- `writing-isam-files` (zoom des zooms, menu domaine)

---

## Carte des checkpoints

13 checkpoints ponctuent l'orchestration : CP1 (Nommage, apres etape 1), CP1bis (FK detectees, apres 1bis), CP2 (Sources generees, apres 2-5ter), CP3 (Coherence inter-fichiers, apres 6-7), CP3bis (Champs metier, apres 7bis), CP4 (Dictionnaire, 8), CP5 (Integration ERP, 9-10), CP6 (Compilation, 11-12), CP7 (Sous-projet, 13), CP8 (Synchro SQL, 14), CP9 (Zoom des zooms, 15-16), CP10 (Menu domaine, 17), CP11 (Visibilite F7 via M1, 18).

A chaque checkpoint, Claude : (1) decrit ce qu'il a fait, (2) explique ses choix, (3) montre les resultats de validation, (4) attend la validation du collaborateur.

---

## Workflow complet (orchestration LLM)

Parametres requis de l'utilisateur :

| Parametre | Exemple |
|-----------|---------|
| Domaine | Retail |
| Entite | FamRglt |
| Table SQL | RtlFamRglt |
| Champ cle | RgltFam |
| Description | Famille de reglement |
| Repertoire de sortie | output |

### Etape 0 : Pre-check advisory -- unicite de l'entite (optionnel)

> **Advisory, non bloquant**. Base sur le **snapshot X.12** du standard ERP via `diva-mcp`. Ne reflete pas les modifications apportees au standard depuis. **Ne JAMAIS en faire un garde-fou de decision** -- c'est une aide a la decouverte, pas une validation.

Avant de lancer la generation, verifier via `diva-mcp` (si disponible) si une entite ou une table du meme nom existe deja dans le standard :

```cypher
// Chercher si une DomainEntity du meme nom existe deja
MATCH (e:DomainEntity) WHERE toLower(e.name) = toLower($entite) RETURN e;

// Chercher si une DbTable du meme nom existe deja (canonique)
MATCH (t:DbTable) WHERE toLower(t.table_name) = toLower($table) RETURN t;

// Chercher si un RecordSql du meme nom existe deja
MATCH (rs:RecordSQL) WHERE toLower(rs.name) = toLower($nom_vue_pressenti)
RETURN DISTINCT rs.program, rs.name LIMIT 10;
```

Si un resultat est trouve, l'orchestrateur doit **presenter l'information** au collaborateur, **sans bloquer** :
- "Une entite/table/RecordSql du meme nom existe dans le snapshot X.12 (programme X, domaine Y). A verifier avec la version X.13 courante avant de continuer."

Si `diva-mcp` n'est pas disponible ou si la verification echoue, continuer sans bloquer -- c'est purement advisory.

### Etape 1 : Calculer les tokens

Invoquer le skill `naming-diva-entities` :

```
py .claude/skills/naming-diva-entities/scripts/compute_names.py \
    --domaine {DOMAINE} --entite {ENTITE} --nomrecordsql {NOM_RSQL} \
    --champ-cle {CHAMP_CLE} --description "{DESCRIPTION}" \
    [--champ-libelle {CHAMP_LIBELLE}] [--no-libelle] > {OUTPUT_DIR}/tokens.json
```

Le nom `{NOM_RSQL}` est le nom de la vue / RecordSql (ex `RaceChienSQL`). La
table SQL est derivee par `compute_names.py` (le script n'a pas d'argument
`--table`).

Verifier : `collision_detected` doit etre `false`. Si `true`, relancer avec `--nom-vue`.

**Champ libelle** : si la table utilise un champ libelle autre que `Libelle`
(ex: `Lib` de Nature 40 declare globalement dans le dictionnaire), preciser
`--champ-libelle Lib`. Le token se propage dans les 3 fichiers generes (RSQL,
mchk, zoom) et dans le masque. Defaut : `Libelle`.

> **CHECKPOINT CP1 -- Nommage**
> Presenter au collaborateur :
> - Les tokens calcules : noms de fichiers (.dhsq, .dhsp, .dhsf), instances, variables
> - Le domaine detecte, le prefixe, les conventions de nommage appliquees
> - Si collision detectee : expliquer le probleme et la resolution
> Attendre validation avant de lancer la generation des sources.

### Etape 1bis : Detection et validation des foreign keys (FK)

Detection automatique via `suggest_nature.py` + classification (auto >= 90 %, ambigu, simple) + validation collaborateur. Liste FK propagee aux etapes 3 (generating-objet-metier `--fk`) et 5ter (dhsf_add_fk.py). Si pas de FK, saut a l'etape 2.

Detail complet (sous-etapes a/b/c/d + CP1bis) : [reference/fk-detection.md](reference/fk-detection.md).

### Etape 2 : Generer RecordSql

Invoquer le skill `generating-recordsql` :

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --file {OUTPUT_DIR}/tokens.json --output "{OUTPUT_DIR}/{fichier_rsql}"
```

Puis valider :

```
py .claude/skills/generating-recordsql/scripts/validate_rsql.py \
    --path "{OUTPUT_DIR}/{fichier_rsql}" --tokens {OUTPUT_DIR}/tokens.json
```

### Etape 3 : Generer Module Check

Invoquer le skill `generating-objet-metier`. Si des FK ont ete validees a **CP1bis**, les propager via `--fk` (cf. FK-02) -- cela genere automatiquement les imports `Module "Gttmchk<cible>.dhop"` et les procedures `Check_<SRC>_Field_<CHAMP>(+_Lib)` :

```
py .claude/skills/generating-objet-metier/scripts/generate_mchk.py \
    --file {OUTPUT_DIR}/tokens.json \
    --output "{OUTPUT_DIR}/{fichier_mchk}" \
    [--fk CHAMP1:TARGET1:ZOOM1] [--fk CHAMP2:TARGET2] ...
```

Sans `--fk`, le Module Check est genere standard (retrocompat pre-FK-02).

Puis valider :

```
py .claude/skills/generating-objet-metier/scripts/validate_mchk.py \
    --path "{OUTPUT_DIR}/{fichier_mchk}" --tokens {OUTPUT_DIR}/tokens.json
```

### Etape 4 : Generer Zoom SQL

Invoquer le skill `generating-zoom-sql` :

```
py .claude/skills/generating-zoom-sql/scripts/generate_zoom.py \
    --file {OUTPUT_DIR}/tokens.json --output "{OUTPUT_DIR}/{fichier_zoom}"
```

Puis valider :

```
py .claude/skills/generating-zoom-sql/scripts/validate_zoom.py \
    --path "{OUTPUT_DIR}/{fichier_zoom}" --tokens {OUTPUT_DIR}/tokens.json
```

### Etape 5 : Generer le bloc d'alias (script local)

```
py .claude/skills/creating-diva-entity/scripts/generate_alias.py \
    --file {OUTPUT_DIR}/tokens.json --output "{OUTPUT_DIR}/alias_{NomVue}.txt"
```

### Etape 5bis : Generer le masque ecran (.dhsf)

> **PREREQUIS -- formules normes-graphiques (R-007 2026-04-23)**
>
> Avant toute manipulation de groupbox / champ / position, LIRE `manipulating-dhsf-screens/reference/normes-graphiques.md` section 5 "Formules". Ne JAMAIS iterer aveuglement sur les positions -- l'incident RaceChat du 2026-04-23 a montre 4+ iterations perdues (titres tronques, erreur "clip grille" mal diagnostiquee) parce que la charte n'a pas ete consultee.
>
> Rappel des 3 formules critiques :
>
> | Regle | Formule |
> |-------|---------|
> | Taille d'un groupbox standard | `taille = NbLignes * espacement (10 / 12 / 14) + 18` -- taille=30 si 1 ligne |
> | Reserve titre en haut du groupbox | premier champ a `Y >= Y(groupbox) + 15` |
> | Gap entre 2 groupbox consecutives | `>= 8` unites |
> | Bornes de grille (erreur "clip grille") | `max_X <= nb_col * 4` et `max_Y <= nb_lig * 14` |
>
> Toute generation ou modification du masque (template initial, `dhsf_add_fk.py`, `dhsf_modify.py add-field/add-column/add-page`) invoque automatiquement `validate_groupbox_layout()` et retourne `post_validation` dans le JSON. **Lire `post_validation.violations` apres chaque operation** : une violation `severity=error` (R1/R4/R5) signifie que la compilation xwin7 echouera avec "Objet en dehors de la clip grille".

Invoquer le skill `manipulating-dhsf-screens` (template zoom) :

```
py .claude/skills/manipulating-dhsf-screens/scripts/dhsf_template.py \
    --template zoom \
    --output "{OUTPUT_DIR}/{prefix_module}mz{entity_lower}_sql.dhsf" \
    --params '{
        "rsql_file":       "{fichier_rsql_sans_ext}",
        "vue_lower":       "{NomVue_lower}",
        "vue_camel":       "{NomVue}",
        "champ_cle":       "{ChampCle_lower}",
        "champ_cle_label": "{ChampCle}",
        "libelle_masque":  "{Description}",
        "fichier_aide":    "{prefix_db}aide",
        "masque_file":     "{prefix_module}mz{entity_lower}_sql",
        "titre_creation":  "{Description} a creer",
        "utilisateur":     "ROOT",
        "no_libelle":      true
    }'
```

Les tokens entre `{}` sont extraits de `tokens.json` (etape 1).
Ajouter `"no_libelle": true` si la table n'a pas de champ Libelle (supprime les widgets Lib du masque).
Le fichier genere est en ISO-8859-1+CRLF (gere par dhsf_template.py).

### Etape 5ter : Appliquer le binding FK au masque (si FK validees a CP1bis)

Si des FK ont ete validees a CP1bis, enrichir le masque avec `dhsf_add_fk.py` (cf. FK-03) :

```
py .claude/skills/manipulating-dhsf-screens/scripts/dhsf_add_fk.py \
    --path "{OUTPUT_DIR}/{prefix_module}mz{entity_lower}_sql.dhsf" \
    --rsql {NOM_RSQL} \
    --src-table {NOM_TABLE} \
    [--fk CHAMP1:TARGET1:ZOOM1] [--fk CHAMP2:TARGET2] ...
```

`--rsql` est le RecordSql case mixte (ex `RaceChienSQL`). `--src-table` est la
table source case mixte (ex `RaceChien`) -- la version uppercase est utilisee
pour le nom de fonction `Check_<SRC>_Field_<C>_Lib`. Le pattern callback
genere est :
`Check_<SRC_UPPER>_Field_<CHAMP>_Lib(<rsql>.<src_table>, <rsql>.<champ>_Lib)`.

Pour chaque FK :
- Localise le bloc `[champ]` dont `donnee=...,<champ>,...`
- Enrichit `[param_saisie]`, `[touches]` (`f8=<zoom>`), `[traitements]` (`diva_apres`), `[boutons]`
- Injecte la procedure `Champ_<CHAMP>_<id>_Ap` dans `[diva]` qui appelle `Check_<TABLE>_Field_<CHAMP>_Lib`

Le compteur `<id>` est global au masque, coherent avec la convention Divalto.

Si un bloc `[champ]` correspondant n'existe pas (champ FK pas encore present dans le masque), le script emet un warning et ajoute la procedure dans `[diva]` ; le bloc `[champ]` reste a ajouter manuellement (ou via `dhsf_modify.py add-field`).

**Post-validation layout** : `dhsf_add_fk.py` retourne un `post_validation` dans le JSON. Verifier `violations[].severity == "error"` avant de passer a l'etape suivante. En cas d'erreur R1/R4/R5, ajuster les positions/tailles et re-valider (`dhsf_modify.py --action validate`).

Sans `--fk`, aucune modification (inutile d'appeler le script).

> **CHECKPOINT CP2 -- Sources generees**
> Presenter au collaborateur :
> - Les 5 fichiers generes : RecordSql (.dhsq), Module Check (.dhsp), Zoom SQL (.dhsp), masque ecran (.dhsf), bloc d'alias
> - Pour chaque fichier : nom, taille, resultat de la validation individuelle (0 erreur / N erreurs)
> - Les choix effectues : champ cle, presence/absence de Libelle, structure du masque
> Attendre validation avant la cross-validation.

### Etape 6 : Validation croisee inter-fichiers (script local)

```
py .claude/skills/creating-diva-entity/scripts/cross_validate.py \
    --rsql "{OUTPUT_DIR}/{fichier_rsql}" \
    --mchk "{OUTPUT_DIR}/{fichier_mchk}" \
    --zoom "{OUTPUT_DIR}/{fichier_zoom}" \
    --tokens {OUTPUT_DIR}/tokens.json \
    --alias "{OUTPUT_DIR}/alias_{NomVue}.txt"
```

### Etape 7 : Rapport de generation

Presenter a l'utilisateur les fichiers generes et les resultats de validation :

1. **Fichiers generes** : RecordSql, Module Check, Zoom SQL, masque ecran (.dhsf), bloc d'alias
2. **Resultats de validation** : erreurs/warnings de chaque validation + cross-validation
3. Si 0 erreur : passer aux etapes suivantes

> **CHECKPOINT CP3 -- Coherence inter-fichiers**
> Presenter au collaborateur :
> - Le rapport complet de cross-validation (regles XV01-XV07)
> - Nombre d'erreurs et warnings
> - Si erreurs : les corrections appliquees et la re-validation
> Attendre validation avant de toucher au dictionnaire.

### Etape 7bis : Definition des champs metier (proposition + validation)

Collecte collaborative des champs metier : description semantique -> nom PascalCase -> deduction Nature via `suggest_nature.py` (3 seuils de confiance) -> CP3bis validation. Socle audit ajoute automatiquement.

Detail sous-etapes + checkpoint CP3bis : [reference/champs-metier.md](reference/champs-metier.md).

### Etape 8 : Dictionnaire (skill `managing-diva-dictionaries`)

Generer les blocs puis inserer dans une copie {REPERTOIRE_TRAVAIL} du dictionnaire :

```
py .claude/skills/managing-diva-dictionaries/scripts/generate_dhsd_block.py \
    --stdin --output {OUTPUT_DIR}/blocs.json < params.json
py .claude/skills/managing-diva-dictionaries/scripts/insert_dhsd_blocks.py \
    --dhsd "{REPERTOIRE_TRAVAIL}/{DICT_lower}.dhsd" --blocks {OUTPUT_DIR}/blocs.json
```

Le `base` dans les params est `{FichierDico}` (ex: GtfLivre), la `table` est `{entite}` (ex: Livre).
Les champs de `params.json["fields"]` sont ceux valides au CP3bis.

> **CHECKPOINT CP4 -- Dictionnaire**
> Presenter au collaborateur :
> - Le dictionnaire modifie et le fichier .dhsd cible
> - La table ajoutee : nom, champs avec types Nature, tailles, positions
> - Les index crees et leur composition
> - Le backup cree (.dhsd.bak)
> Attendre validation avant d'inserer alias et Declaration.

### Etape 9 : Inserer alias dans gtpmficsql.dhsp

Copier `gtpmficsql.dhsp` dans {REPERTOIRE_TRAVAIL}, inserer le contenu de `alias_{NomVue}.txt`
**APRES le dernier Alias existant** (~ligne 9661), pas au debut du fichier.

### Etape 10 : Inserer Declaration dans gttcficsql.dhsp

Copier `{domaine_2l}tcficsql.dhsp` dans {REPERTOIRE_TRAVAIL} (ex: `gttcficsql.dhsp` pour DAV).
Ajouter **apres le dernier `Define Declaration_`** existant :

```
Define Declaration_{NomVue}					= RecordSql '{fichier_rsql_compile}' 	{NomVue}
```

Exemple pour Livre :
```
Define Declaration_LivreRS					= RecordSql 'gtfrslivre.dhoq' 	LivreRS
```

Ce Define cree la macro `Declaration_LivreRS` qui est utilisee dans le mchk pour declarer
l'instance RecordSQL. Sans cette ligne, le mchk echoue avec "Mot inconnu : Declaration_LivreRS".

> **CHECKPOINT CP5 -- Integration ERP**
> Presenter au collaborateur :
> - L'alias insere dans gtpmficsql.dhsp : contenu exact, emplacement (apres quel alias existant)
> - Le Define Declaration insere dans gttcficsql.dhsp : ligne exacte, emplacement
> - Les fichiers copies dans {REPERTOIRE_TRAVAIL}
> Attendre validation avant de lancer la compilation.

### Etape 11 : Compilation incremental ERP (prerequis)

Compiler `gtpmficsql.dhsp` (alias) et `gttcficsql.dhsp` (Declaration) via compilation incremental ERP.
Cela met a jour les `.dhop` dans le repertoire objet ERP.

**Attention** : La modification de `gttcficsql.dhsp` declenche une cascade de recompilation
(~2000 fichiers, ~30 min) car ce fichier est inclus par de nombreux sources du domaine.

**Cette etape est un prerequis** pour que le harness et la compilation du sous-projet fonctionnent.

> **Piege [communs]** : ces fichiers appartiennent aux groupes `[communs]` du .dhpt ERP.
> Ils ne sont PAS recompiles par `-sousproject`. Il faut un `build` sur le projet principal
> (`divalto.dhpt`) ou ajouter temporairement ces fichiers dans `[fichiers]` du sous-projet.
> Cette etape 11 DOIT etre terminee avant l'etape 12 (harness standalone).

### Etape 12 : Compilation harness standalone (validation rapide, ~44s)

```
py .claude/skills/compiling-diva-projects/scripts/generate_harness.py \
    --sources "{REPERTOIRE_TRAVAIL}/{fichier_rsql}" "{REPERTOIRE_TRAVAIL}/{fichier_mchk}" "{REPERTOIRE_TRAVAIL}/{fichier_zoom}" \
    --with-zdiva --with-communs
```

Le script retourne le chemin du log unique (ex: `harness_20260414_185848.txt`).

```
powershell -ExecutionPolicy Bypass -File "{REPERTOIRE_TRAVAIL}/scripts/harness_compile.ps1"

py .claude/skills/compiling-diva-projects/scripts/parse_compilation.py \
    --path "{log_file retourne par generate_harness}"
```

Si `success: true` → passer a l'etape suivante. Sinon corriger et recompiler.

> **CHECKPOINT CP6 -- Compilation**
> Presenter au collaborateur :
> - Resultat de la compilation : succes (0 erreur) ou liste des erreurs avec fichier/ligne
> - Fichiers compiles generes (.dhop, .dhoq) et leur taille
> - Si erreurs corrigees : decrire les corrections appliquees
> Attendre validation avant de creer le sous-projet.

### Etape 12bis : Cleanup post-compilation [communs] (conditionnel)

Si un workaround `[communs]` a ete applique a l'Etape 13 (push temporaire de
`gtfdd.dhsd` / `gtpmficsql.dhsp` en `[fichiers]`), nettoyer apres reussite de
la compilation CP6.

**Procedure detaillee, commande, comportement du script et CHECKPOINT CP6bis** :
voir `reference/cleanup-post-compilation.md`.

Saute cette etape si aucun workaround [communs] n'a ete applique.

### Etape 13 : Sous-projet (skill `managing-diva-projects`)

Creer `gt_zoom {entite}.dhps` base sur le modele `gt_zoom article.dhps`, ajouter dans `divalto.dhpt`, puis compiler en incremental ERP.

Structure obligatoire (sections `[communs]`, `[fichiers]`, `[includes]`) + regles critiques (dependance `gt_base` / `gt_dictionnaires` / `gt_recordsql`, include `gttcficsql.dhsp`) + checkpoint CP7 : [reference/sous-projet-config.md](reference/sous-projet-config.md).

### Etape 14 : Synchro SQL (skill `syncing-diva-sql`)

Synchroniser la base de donnees pour creer la table SQL a partir du dictionnaire.

> **CHECKPOINT CP8 -- Synchro SQL**
> Presenter au collaborateur :
> - Le resultat de la synchro : table SQL creee, colonnes, index
> - Les erreurs eventuelles et leur resolution
> Attendre validation avant l'enregistrement dans le zoom des zooms.

### Etape 15 : Zoom des zooms (skill `writing-isam-files`)

Choisir un numero de zoom libre dans la plage du domaine (plage de numeros attribuee par module ERP).

```
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file {OUTPUT_DIR}/data_zoom.json \
    --structure-dir .claude/skills/writing-isam-files/scripts/structures
```

Champs M4 obligatoires : voir `writing-isam-files/reference/a5f-zoom-record.md` pour la structure complete (20+ champs). Points de vigilance : `ZoomFic=ZOOMSQL` (pas le nom physique), `MsqEcran`/`ModTrait` referent les fichiers **compiles** (.dhof/.dhop).

### Etape 16 : Constante zoom (skill `writing-diva-files`)


```
py .claude/skills/writing-diva-files/scripts/add_zoom_constant.py \
    --file "{CHEMIN_CIBLE}/a5tczoom.dhsp" \
    --instance "{NomVue}" --num "{numero}" --comment "{Description}"
```

> **CHECKPOINT CP9 -- Zoom des zooms**
> Presenter au collaborateur :
> - Le numero de zoom choisi et pourquoi (plage du domaine, premier libre)
> - L'enregistrement M4 insere dans a5f.dhfi : champs ZoomNum, ZoomEnr, MsqEcran, ModTrait
> - La constante ajoutee dans a5tczoom.dhsp : nom, valeur, commentaire
> Attendre validation avant l'ajout au menu.

### Etape 17 : Menu domaine (skill `writing-isam-files`)

> **Preambule -- fermer l'ERP avant cette etape** : l'ecriture ISAM sur `g3f.dhfi`
> (fichier physique du menu, nom logique `Xmenuf`) doit etre faite ERP ferme
> pour eviter locks et cache stale. Procedure : **Autres actions > Se deconnecter**
> dans l'ERP, puis fermer le navigateur. Cf. skill [`writing-isam-files`](../writing-isam-files/SKILL.md) section "Fichiers sensibles ERP".

Ajouter une entree dans un regroupement du menu domaine. Le menu Divalto est un
**graphe de regroupements plats** (pas une arborescence) — creer une entree signifie
ajouter une ligne dans un regroupement existant.

Voir [reference/menu-domain.md](reference/menu-domain.md) pour le detail :
- Questions a poser au collaborateur (regroupement cible, ordre, libelle, icone, code produit)
- Commande d'insertion (`write_isam.py`)
- Structure M2 obligatoire (13 champs dont `Echange` **clone obligatoire**) et contraintes (`Reg`, `Ordre` cadre droite, `Enchain` prefixe `0`, `TypeChain=3` pour Zoom)

> **CHECKPOINT CP10 -- Menu domaine**
> Presenter au collaborateur :
> - Le regroupement cible choisi (`Reg`) et son role fonctionnel
> - L'ordre retenu et pourquoi (multiple de 10, libre, etc.)
> - L'enregistrement M2 insere : `Reg`, `Ordre`, `Lib`, `Enchain` (numero zoom prefixe), `EnrNo` (alloue via `allocating-menu-enrno` plage custom)
> - Resultat attendu : une nouvelle entree dans le menu ERP a l'emplacement prevu
> Attendre validation avant l'etape de visibilite F7.

### Etape 18 : Visibilite F7 via M1 (skill `writing-isam-files`) -- R-002

RETEX R-002 (2026-04-23) : **M4 seul ne suffit pas**. Sans enreg M1 (`Ce=5`) dans `a5f.dhfi` pour ce `ZoomNum`, le zoom est **invisible via F7**.

Pattern : 1 enreg M1 par domaine de visibilite (typique = M4.Ap ; multi-domaine pour tables communes type Pays/Devise, ex `ZoomNum=540` visible en DAV+DCPT+DPAIE = 3 M1).

Questions collaborateur : domaines de visibilite (defaut `M4.Ap`). Pour chaque domaine cible, `write_isam.py` avec `structure_a5f_m1.json` : `Ce=5`, `ZoomNum/Ap/Reg/Ordre` copies de M4, `Applic=domaine_cible`. Detail commande et pattern multi-domaine : [reference/menu-domain.md](reference/menu-domain.md) section M1.

> **CHECKPOINT CP11 -- Visibilite F7 (M1)**
> Presenter : domaine(s) retenus, N enregs M1 inseres, resultat attendu = F7 OK dans chaque `Applic` declare.
> Workflow termine. Tester via `testing-erp` (CP3 coherence F1 + test F7 par domaine).

## Validation croisee

Le script `cross_validate.py` verifie 7 regles inter-fichiers :

| Regle | Severite | Quoi |
|-------|----------|------|
| XV01 | error | NomVue present dans les 3 fichiers |
| XV02 | error | RecordSql compile reference dans le zoom |
| XV03 | error | Module mchk reference dans le zoom |
| XV04 | error | Meme prefixe domaine dans mchk et zoom |
| XV05 | warning | OverWrittenBy coherent dans mchk et zoom |
| XV06 | warning | ChampCle reference dans les 3 fichiers |
| XV07 | error | Bloc d'alias : 16 alias, bon NomVue, bon PREFIX_ |

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/generate_alias.py` | Genere le bloc de 16 alias | JSON tokens (stdin ou fichier) + --output | JSON rapport + fichier alias |
| `scripts/cross_validate.py` | Coherence inter-fichiers | --rsql --mchk --zoom --tokens [--alias] | JSON rapport (errors/warnings) |
| `scripts/templates/alias_block.txt.j2` | Template Jinja2 alias | (utilise par generate_alias.py) | — |
| `scripts/_naming.py` | Calcul des tokens de nommage (vendored) | (utilise localement si besoin) | — |

---

## References

- **Checklist des 6 elements** : Voir [reference/entity-checklist.md](reference/entity-checklist.md)
- **Format du bloc d'alias** : Voir [reference/alias-block.md](reference/alias-block.md)
- **Menu domaine (CP10)** : Voir [reference/menu-domain.md](reference/menu-domain.md)
- **Champs JSON ISAM (M4 zoom + M2 menu)** : Voir [reference/isam-fields.md](reference/isam-fields.md)
