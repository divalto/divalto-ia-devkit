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

Actuellement : pas de cascade automatique. Si le scope domaine retourne < 5 confirmes, le LLM orchestrateur peut relancer manuellement au CP4 avec `--domain-scope all`.

Amelioration future (non MVP) : cascade automatique. Inscrit au BACKLOG.

## Pourquoi pas ripgrep ?

`rg` serait beaucoup plus rapide mais :
- Disponibilite pas garantie sur le poste du collaborateur
- L'encodage ISO-8859-1 DIVA demande un parsing manuel pour les accents
- Le parser structurel DIVA est en Python (coherence)

Pour le MVP, Python suffit avec les bornes imposees.
