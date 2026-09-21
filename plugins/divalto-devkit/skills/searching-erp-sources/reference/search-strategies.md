# search-strategies.md

Strategies de recherche appliquees par `verify_x13.py` pour explorer l'ERP X.13 (~7000 fichiers `.dhsp`).

## Objectif : maitriser la volumetrie

Un grep naif sur la racine ERP peut retourner 1000+ matches en 30+ secondes. Les bornes et le cadrage reduisent ce bruit.

## Strategie 1 -- Cadrage par domaine (prefere)

Le parseur (phase 1) identifie `domaine_pressenti` via mots-cles ("Retail", "facture", "reglement"...).
`verify_x13.py --domain-scope auto` utilise cette information pour restreindre la recherche aux sous-repertoires pertinents.

| `domaine_pressenti` | Sous-repertoires explores |
|---------------------|---------------------------|
| `RT_` | `Achat-Vente/source/Retail/` |
| `GT_` | `Achat-Vente/source/Dav/` puis `Achat-Vente/source/` |
| `GG_` | `Achat-Vente/source/Prod/`, `Achat-Vente/source/Atelier/` |
| `CC_` | `Comptabilite/source/` |
| `RC_` | `Reglement/source/` |
| ... | cf. `MODULE_DIRS` dans `verify_x13.py` |

Si `domain_scope=all` ou que le domaine est inconnu, la racine ERP est scannee entierement (avec bornes).

## Strategie 1bis -- Cartographie de nommage des sources standard

Avant de conclure « pas de source standard », viser le bon **prefixe de fichier**. Chercher
`gti*` au lieu de `gtt*` fait rater le traitement et mene a une conclusion fausse. Le
nom d'une source suit le schema **`PP` `T` `NNN`** (sans espaces) :

```
c c u t 0 5 0 . dhsp
|-| | |  |-|
 |  | |   +--- identifiant numerique du programme
 |  | +------- type d'objet (position 3)
 |  +--------- surcharge eventuelle (voir plus bas)
 +------------ prefixe module (positions 1-2)
```

**Positions 1-2 -- prefixe module** :

| Module | Prefixe |
|--------|---------|
| Achat-Vente (DAV / Prod / Retail / Atelier / WMS) | `gt` |
| A5 (transverse / outils) | `a5` |
| Reglement | `rc` |
| Comptabilite | `cc` |
| Paie | `pp` |
| Affaires (GPA) | `ga` |
| Controle | `co` |
| Gestion Ressources Materiels | `gm` |
| Point de Vente | `pv` |
| Qualite | `qu` |
| Relation-Tiers (CRM) | `gr` |
| Documentation | `do` |
| Processus | `sp` |
| Mobilite | `mo` |

**Position 3 -- type d'objet** :

| Lettre | Type |
|--------|------|
| `t` | Traitement / programme |
| `e` | Ecran / masque |
| `i` | Include (bloc d'impression, sous-ecran) |
| `z` | Zoom |
| `r` | RecordSql |
| `f` | Fichier / dictionnaire (ex: `ccfdd`) |
| `p` | Module de procedures / fonctions |

**Surcharge partenaire** : la 3e lettre est remplacee par `u` pour les **programmes / zoom**
(`cctt050` -> `ccut050`, `cctz030` -> `ccuz030`). Pour les **masques / includes / recordsql /
dictionnaires**, le `u` est ajoute en **fin de basename** (`ccee032.dhsf` -> `ccee032u.dhsf`,
`ccrsdos.dhsq` -> `ccrsdosu.dhsq`, `ccfdd.dhsd` -> `ccfddu.dhsd`).

**Extensions** : `.dhs*` = source texte editable (ISO-8859-1 + CRLF), `.dho*` = objet compile
binaire ; la derniere lettre reprend le type (`.dhsp`/`.dhop` programme, `.dhsf`/`.dhof` masque,
`.dhsi`/`.dhoi` include, `.dhsq`/`.dhoq` recordsql, `.dhsd`/`.dhfd` dictionnaire).

> **Discipline** : viser module (pos 1-2) **+** type (pos 3). En cas de doute sur le
> type, **grep large** sur le prefixe module (`gt*`, `cc*`) plutot que sur un seul prefixe ; ne
> **jamais** conclure « pas de source » sur un seul prefixe rate. Cette convention est **stable**
> -- documentee ici pour fonctionner **meme `diva-mcp` indisponible** (mode degrade).
>
> **`diva-mcp` confirme / etend** : pour l'inventaire exhaustif par module, un module recent ou un
> detail specifique de version, interroger `diva-mcp` (`search_documentation`) -- c'est la source
> la plus a jour. La convention ci-dessus, elle, est invariante.

## Strategie 2 -- Verification d'existence (glob)

Pour chaque program candidat de `candidates_x12.json` :

```python
for path in base_dir.rglob(f"{program_name}.dhsp"):
    # trouve -> CONFIRME X.13
```

C'est rapide (10-100 ms par candidat dans un sous-repertoire) car glob utilise l'index filesystem.

## Strategie 3 -- Grep textuel borne

Pour chaque keyword technique de `request.json` :

```python
pattern = re.compile(re.escape(keyword), re.IGNORECASE)
# Parcours avec limites
```

Bornes appliquees :
- `max_files=20` -- arret apres 20 fichiers scannes
- `max_matches=50` -- arret apres 50 matches globaux
- `timeout=60s` -- deadline globale

Si un match est dans un fichier deja `CONFIRME X.13` (program candidat retrouve), on l'ignore (doublon inutile). Sinon, statut `NOUVEAU X.13`.

## Strategie 4 -- Extract contextuel

Pour chaque match ou program confirme, `extract_context_for(path, line_no)` :
1. Lit le fichier (ISO-8859-1)
2. Parse la structure via `_structural_parser.py` (vendored)
3. Identifie la procedure/fonction englobante
4. Extrait un snippet de 30 lignes (ou le bloc entier si < 30 lignes)

## Strategie 5 -- Impact analysis (callers)

Pour chaque fonction candidate (provenance Neo4j), regex ciblee :

```
\b(?:Call|Execute)\s+["']?<function_name>["']?
| \b<function_name>\s*\(
```

Limites : `max_matches=20` par fonction, pour rester tractable.

Voir `x13-impact-patterns.md` pour le detail des patterns de detection.

## Cascade si pas assez de resultats

Actuellement : pas de cascade automatique. Si le scope domaine retourne < 5 confirmes, le LLM orchestrateur peut relancer manuellement, a son checkpoint de perimetre, avec `--domain-scope all`.

Amelioration future (non MVP) : cascade automatique. Inscrit.

## Pourquoi pas ripgrep ?

`rg` serait beaucoup plus rapide mais :
- Disponibilite pas garantie sur le poste du collaborateur
- L'encodage ISO-8859-1 DIVA demande un parsing manuel pour les accents
- Le parser structurel DIVA est en Python (coherence)

Pour le MVP, Python suffit avec les bornes imposees.

## Verifier une clause existante avant de developper (filtre TRA)

Pour une demande de type « ajouter un filtre dans un TRA / un zoom », chercher d'abord si la
**clause existe deja** dans le `.dhsq` standard (ex. une case `<Champ>_Equal_<X>`) avant de
conclure a un developpement. Le mecanisme de filtrage (cote masque / `.dhsp`) consomme la clause
via `UseClause` : une `UseClause` a **un seul parametre** est compatible avec un `Equal` mais
**pas** avec un `Between` (qui en exige deux). Selon les cas : aucun developpement (clause deja
exposee) ou simple surcharge. Mecanique des clauses RecordSql : cf. `generating-recordsql`.

## Graphe de code en retard : toujours verifier en local

Le graphe `diva-mcp` (`search_code`, `get_call_graph`) indexe une **revision donnee** du standard
et peut **retarder** sur les ouvertures recentes : un service pack peut introduire une procedure
**absente du graphe**, sans avertissement. Un `search_code` qui retourne `[]` sur un programme
existant ne prouve **pas** l'absence -- verifier dans les sources locales (`grep` du `.dhsp`,
strategie 3) avant de conclure. C'est precisement le role de ce skill : le filet de verification
X.13 **locale**. (Avertissement detaille cote `querying-diva-graph`.)

> A ne pas confondre avec la **cartographie de nommage** (strategie 1bis) : celle-ci est une
> convention **stable** et fiable cote MCP ; c'est le **graphe de code** qui retarde, pas la doc.
