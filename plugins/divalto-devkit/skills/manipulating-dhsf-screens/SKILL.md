---
name: manipulating-dhsf-screens
description: Parse, genere et modifie les masques ecran Divalto (.dhsf). Parse un .dhsf en arbre structurel JSON, genere un .dhsf depuis un template (zoom SQL, ecran CRUD, simple) avec remplacement de tokens, et effectue des modifications incrementales (ajout champ, colonne, page). A utiliser quand il faut creer ou modifier un masque ecran DIVA (zoom SQL, ecran de saisie, affichage d'une entite).
---

# manipulating-dhsf-screens

Manipulation complete des fichiers masque ecran Divalto (.dhsf) : parsing structurel, generation par template, et modifications incrementales.

## References documentaires

- **Ergonomie (UX)** : [reference/normes-graphiques.md](reference/normes-graphiques.md) -- espacements canoniques (X=5, Y=8/26), tailles autorisees, styles WPF, ordre onglet Identifiants, formules de placement.

Lors de la generation ou de la modification d'un masque, appliquer systematiquement les regles de `reference/normes-graphiques.md` :
- Toute page FICHE commence a X=5 (bord gauche), premier objet a Y=8 sans onglet ou Y=26 avec onglet.
- Les groupes se terminent a 5 du bord droit.
- Les libelles accoles suivent `Pos X(libelle) = 1 + Pos X(champ) + Taille(champ)`.
- Si le masque est associe a un dictionnaire contenant `Ce1`/`Note`/`Joint`/`UserCr`/`UserCrDh`/`UserMo`/`UserMoDh`, l'onglet Identifiants doit les exposer dans l'ordre canonique (Codes enregistrements -> [Protection/Derniere operation] -> Creation + Derniere modification).

## Quand utiliser ce skill

- Creer un nouveau masque ecran (.dhsf) a partir d'un template
- Ajouter un champ, une colonne de tableau, ou une page a un masque existant
- Analyser la structure d'un masque (pages, elements, widgets, enregistrements)
- Inspecter les liaisons donnees (vue, champ, alias) d'un masque

## Scripts

### 1. dhsf_parser.py -- Parseur structurel

Entree : chemin vers un .dhsf
Sortie : arbre JSON complet (masque, pages, elements, ressources, diva) avec line ranges

```
py scripts/dhsf_parser.py --path <fichier.dhsf>
py scripts/dhsf_parser.py --path <fichier.dhsf> --summary
```

Mode `--summary` : metriques et squelette (pages avec compteurs d'elements).
Mode complet : arbre avec chaque element detaille (position, taille, id, wstyle, donnee, children).

Les line ranges (`line_start`, `line_end`) permettent le round-tripping pour les modifications.

Metriques compatibles avec `linting-diva-code/scripts/dhsf_info.py`.

### 2. dhsf_template.py -- Generation par template

Entree : type de template + parametres JSON + chemin de sortie
Sortie : fichier .dhsf pret (ISO-8859-1 + CRLF)

```
py scripts/dhsf_template.py --template zoom --output <fichier.dhsf> --params '<json>'
```

Templates disponibles :
- `zoom` : zoom SQL standard (12 pages, FICHE + LISTE, toolbars)
- `crud` : ecran CRUD (ENTETE + LIGNE + PIED, menu + toolbar)
- `simple` : dialogue minimal (1 page, 2 widgets)

Parametres JSON (zoom) :
| Parametre | Description | Exemple |
|-----------|-------------|---------|
| `rsql_file` | RecordSql sans .dhoq | `"rtlrsfamrglt"` |
| `vue_lower` | Nom de vue minuscule | `"famrglt"` |
| `vue_camel` | Nom de vue CamelCase | `"FamRglt"` |
| `champ_cle` | Champ cle minuscule | `"rgltfam"` |
| `champ_cle_label` | Libelle du champ cle | `"Code"` |
| `libelle_masque` | Description du masque | `"familles de reglement"` |
| `fichier_aide` | Fichier aide sans extension | `"rtfaide"` |
| `masque_file` | Nom du fichier sans .dhsf | `"rtez099_sql"` |
| `titre_creation` | Titre popup creation | `"Famille a creer"` |
| `no_libelle` | Si true, supprime les widgets Lib du masque | `true` (optionnel) |

**Check SVN pre-modification** (optionnel) : avant de modifier un masque .dhsf existant, verifier les modifs locales non committees et l'activite recente pour detecter un refactor en cours.

```bash
py .claude/skills/manipulating-dhsf-screens/scripts/check_svn_recent.py     --path "{DHSF_PATH}" --limit 5 --days 30
```

Si `warning != null` ou `local_changes.has_changes=true`, signaler au collaborateur avant de poursuivre. Degradation gracieuse si SVN indispo. Voir [reference/svn-policy.md](reference/svn-policy.md).

### 3. dhsf_modify.py -- Modifications incrementales

Entree : chemin .dhsf + action + parametres JSON
Sortie : fichier modifie en place, JSON de resultat sur stdout

```
py scripts/dhsf_modify.py --path <fichier.dhsf> --action <action> --params '<json>'
```

Actions :
| Action | Description | Parametres obligatoires |
|--------|-------------|------------------------|
| `add-field` | Ajoute obj_texte + champ a une page | `page_numero`, `label`, `vue`, `champ`, `alias` |
| `add-column` | Ajoute champ_tableau a un tableau | `page_numero`, `titre`, `vue`, `champ`, `alias` |
| `add-page` | Ajoute une page avec onglet_page | `numero`, `libelle`, `onglet_nom`, `onglet_libelle` |
| `add-groupbox` | Englobe des champs existants dans un `[groupbox]` (MVP wrapper-only) | `page_numero`, `texte`, `champs` (liste d'ids) |
| `validate` | Lecture seule : valide le layout groupbox/bornes grille (sans modifier) | `{}` (pas de parametre) |

Chaque action met a jour automatiquement `dernier_id` et le timestamp.

**`add-groupbox` (mode wrapper-only)** : calcule la bounding box des
champs cibles + marges (`margin_top=16` pour la reserve titre, `margin_x=5`,
`margin_bottom=6`) puis insere le bloc `[groupbox]` avant le 1er champ cible.
Les champs ne sont **pas** repositionnes (restent comme freres dans la page,
visuellement a l'interieur du groupbox). Le mode "repositionnement
automatique" (champs deviennent children, espacement 14 / offset 16 normes
graphiques) reste un chantier dedie a ouvrir si necessaire.

**Validation automatique post-modification** : apres chaque action modifiante (`add-field` / `add-column` / `add-page` / `add-groupbox`), le script re-parse le fichier et execute `validate_groupbox_layout()`. Le resultat est inclus dans le JSON de retour sous la cle `post_validation`. Idem pour `dhsf_add_fk.py`.

5 regles issues de `reference/normes-graphiques.md` section 5 :

| Regle | Severite | Formule |
|-------|----------|---------|
| R1 | error | `taille_groupbox >= NbLignes * espacement + 18` (borne min : espacement=10) |
| R2 | warning | `Y(premier enfant) - Y(groupbox) >= 15` (reserve titre) |
| R3 | warning | Entre deux groupbox consecutives sur meme X : gap >= 8 |
| R4 | error | `max_X(obj) <= nb_col * 4` (saturation largeur, cause "clip grille") |
| R5 | error | `max_Y(obj) <= nb_lig * 14` (saturation hauteur) |

Format du `post_validation` :

```json
{
  "valid": true,
  "violations": [{"rule": "R1", "severity": "error", "page": 2, "id": 42, "type": "groupbox", "detail": "..."}],
  "stats": {"total": 1, "errors": 1, "warnings": 0}
}
```

L'orchestrateur (humain ou `creating-diva-entity`) DOIT lire ce `post_validation` apres chaque modification. Les erreurs (R1/R4/R5) indiquent un layout casse qui echouera a la compilation xwin7 (erreur "Objet en dehors de la clip grille" pour R4/R5). Les warnings (R2/R3) indiquent un ecart vis-a-vis de la charte graphique -- souvent correctible mais parfois accepte en production.

### 4. dhsf_add_fk.py -- Binding "FK par zoom standard"

Entree : un `.dhsf` existant + une ou plusieurs FK a declarer.
Sortie : le `.dhsf` est modifie en place (ISO-8859-1 + CRLF) pour ajouter
les 3 couches du binding FK (cf. skill [`binding-zoom-to-field`](../binding-zoom-to-field/SKILL.md) et son `reference/fk-pattern.md`).

```
py scripts/dhsf_add_fk.py --path <fichier.dhsf> \
    --src-table RACECHIEN \
    --fk RacPays:T013:9053 --fk RacDev:T007:9047
```

Pour chaque FK, le script :
1. Localise le bloc `[champ]` dont `donnee=...,<champ>,...` match (case-insensitive)
2. Enrichit les sous-sections du bloc :
   - `[param_saisie]` : `table_associee=oui`
   - `[touches]` : `f8=<zoom>`
   - `[traitements]` : `diva_apres="Champ_<CHAMP>_<id>_Ap"`
   - `[boutons]` : entry `"zoom"`
3. Injecte la procedure callback `Champ_<CHAMP>_<id>_Ap` dans la section `[diva]`
   avant `[/diva]`, appelant `Check_<SRC_TABLE>_Field_<CHAMP>_Lib`

Le `<id>` est un **compteur sequentiel global** alloue parmi les procedures
`Champ_*_Ap` du fichier (pas l'id widget DOM). Si le bloc `[champ]` pour un
champ FK n'est pas trouve, un warning est emis et le callback est quand meme
genere dans `[diva]` (pour que l'utilisateur complete manuellement le
bloc `[champ]` apres).

Ce script fonctionne avec `generating-objet-metier --fk` (FK-02) pour livrer
les 3 couches solidaires : Module Check (dhsp) + masque structurel (dhsf [champ])
+ callback applicatif (dhsf [diva]).

### Contrainte sur add-field : attributs de page obligatoires

L'action `add-field` exige que la page cible possede les 5 attributs
obligatoires : `numero`, `nb_lig`, `nb_col`, `offset_lig`, `offset_col`.
Si un attribut manque, l'action est refusee avec un message explicite
(ne cree pas un bloc invalide).

Dans un **masque zoom** (template `zoom`) :
- **Page 1** : page principale zoom (generalement liste) -- attributs en place
- **Page 11** : **page fiche** -- c'est la page a cibler pour ajouter des
  champs metier (detail d'un enregistrement)
- Autres pages (2-10, 12+) : popup, saisie cle, etc. -- usage specifique

Regle generale : pour ajouter un champ de donnee dans un zoom, utiliser
`page_numero=11`.

## Workflow typique

1. **Generer** le masque depuis un template : `dhsf_template.py --template zoom`
2. **Valider** la structure : `dhsf_parser.py --summary`
3. **Modifier** incrementalement : `dhsf_modify.py --action add-field`
4. **Re-valider** : `dhsf_parser.py --summary`
5. **Verifier l'encodage** : `writing-diva-files` skill (verify_encoding.py)
