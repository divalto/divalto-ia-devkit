---
name: searching-erp-sources
description: >
  Verifie l'existence des candidats Neo4j (candidates_x12.json) dans le code source X.13
  standard ({CHEMIN_ERP_STANDARD}) et extrait le contexte
  precis (fichier:ligne, procedure englobante, snippet 10-30 lignes). Source de verite :
  promouvoit les candidats [X.12] en [CONFIRME X.13], [DISPARU X.13] ou ajoute des
  decouvertes [NOUVEAU X.13]. Applique des bornes strictes (--max-matches, --max-files,
  --timeout) pour gerer la volumetrie ERP (~7000 fichiers). A utiliser apres
  querying-diva-graph (mode hybride) ou en mode direct si diva-mcp indispo.
---

# Searching ERP Sources

## Contenu

- Utilisation rapide
- Workflow verify + extract
- Parametres d'entree
- Sortie : evidence_x13.json
- Strategies de recherche et bornes
- Mode direct (Neo4j indispo)
- Scripts disponibles
- References

---

## Utilisation rapide

Workflow type (apres querying-diva-graph) :

```
py .claude/skills/searching-erp-sources/scripts/verify_x13.py \
    --candidates output/candidates_x12.json \
    --request output/request.json \
    --erp-root "C:/Developpements harmony/Standard/Version X.13" \
    --domain-scope auto \
    --max-matches 50 --max-files 20 --timeout 60
```

Sortie : `evidence_x13.json` (format decrit dans [reference/search-strategies.md](reference/search-strategies.md)).

Pour extraire le contexte d'un fichier precis a une ligne donnee :

```
py .claude/skills/searching-erp-sources/scripts/extract_context.py \
    --file "<path>" --line 42 --window 30
```

---

## Workflow verify + extract

```
candidates_x12.json  -->  verify_x13.py  -->  evidence_x13.json
                                |
                                | Pour chaque program candidat :
                                |   1. Glob dans ERP (scope domaine)
                                |   2. Si trouve  -> status = "CONFIRME X.13"
                                |   3. Si absent  -> status = "DISPARU X.13"
                                |
                                | Pour chaque keyword technique :
                                |   4. Grep dans ERP
                                |   5. Si match hors candidates  -> status = "NOUVEAU X.13"
                                |
                                | Pour chaque program retenu :
                                |   6. extract_context.py (snippet + fonction englobante)
                                |
                                | Impact analysis :
                                |   7. Grep des patterns "Call X" / "Execute X"
                                |      pour les fonctions candidates
```

---

## Parametres d'entree

| Parametre | Format | Obligatoire | Defaut |
|-----------|--------|-------------|--------|
| `--candidates` | Chemin `candidates_x12.json` | Oui (sauf mode direct) | -- |
| `--request` | Chemin `request.json` | Oui | -- |
| `--erp-root` | Chemin racine ERP X.13 | Non | `C:/Developpements harmony/Standard/Version X.13` |
| `--domain-scope` | `auto` / `<prefix>` / `all` | Non | `auto` (suit `request.domaine_pressenti`) |
| `--max-matches` | Plafond matches par keyword | Non | `50` |
| `--max-files` | Plafond fichiers examines | Non | `20` |
| `--timeout` | Timeout global en secondes | Non | `60` |

**Portabilite** : `--erp-root` est passe en parametre -- pas de chemin en dur dans le script. Le placeholder pour la distribution est `{CHEMIN_ERP_STANDARD}` (voir `.claude/skills/README.md`).

---

## Sortie : evidence_x13.json

```json
{
  "scope": {
    "erp_root": "C:/Developpements harmony/Standard/Version X.13",
    "domains_searched": ["Achat-Vente/source/Retail"],
    "files_examined": 42,
    "matches_truncated": false,
    "duration_seconds": 4.2
  },
  "confirmed": [
    {
      "from_x12": "rttzfamrglt_sql",
      "file_path": "C:\\...\\Retail\\rttzfamrglt_sql.dhsp",
      "line_range": [1, 303],
      "status": "CONFIRME X.13",
      "context_sample": {
        "line": 37,
        "enclosing_block": {"kind": "procedure", "name": "Construire_ConditionSelection"},
        "snippet": "Public Procedure Construire_ConditionSelection(...)\n..."
      }
    }
  ],
  "disappeared": [
    {"from_x12": "rttzoldlegacy_sql", "status": "DISPARU X.13",
     "reason_hypothesis": "non_trouve_via_glob"}
  ],
  "new_findings": [
    {"file_path": "...", "line_range": [...], "pattern": "...",
     "status": "NOUVEAU X.13"}
  ],
  "impact": {
    "callers": [
      {"file_path": "...", "line": 42, "callee": "Construire_ConditionSelection",
       "status": "CONFIRME X.13"}
    ]
  }
}
```

Format canonique : detail dans [reference/search-strategies.md](reference/search-strategies.md).

---

## Strategies de recherche et bornes

Voir `reference/search-strategies.md` pour le detail. En bref :

1. **Cadrage par domaine** (auto) : si `domaine_pressenti = RT_`, le script cherche d'abord dans `Achat-Vente/source/Retail/`. Si moins de 5 matches, elargit a l'ERP complet.
2. **Glob** pour l'existence de programs (rapide).
3. **Grep** regex pour les keywords techniques et les callers.
4. **Bornes strictes** `--max-matches 50 --max-files 20 --timeout 60` pour eviter le deluge.
5. **Extract contextuel** via `_structural_parser.py` (vendore) : pour chaque ligne cible, recuperer la procedure englobante + snippet.

---

## Mode direct (Neo4j indispo)

Si `candidates_x12.json` a `neo4j_status: "unavailable"`, le script bascule en mode "recherche X.13 directe" :

- Ignore la liste de candidats (vide)
- Utilise uniquement `request.keywords_techniques` et `request.keywords_metier` pour la recherche
- Marque tous les findings comme `[NOUVEAU X.13]` (puisqu'il n'y a pas de reference X.12)
- Ajoute un disclaimer : "Recherche directe X.13, sans orientation Neo4j"

Le rapport final (phase 4) indique alors "Couverture Neo4j : absente".

---

## Scripts disponibles

```
scripts/verify_x13.py            # Verification + impact + extraction
scripts/extract_context.py       # Wrapper de _structural_parser.py (snippet autour d'une ligne)
scripts/_structural_parser.py    # Vendored from linting-diva-code (parse structurel DIVA)
```

**Vendoring** : `_structural_parser.py` est une copie de `.claude/skills/linting-diva-code/scripts/_structural_parser.py`. Procedure de mise a jour : modifier le canonique, copier dans ce skill, verifier `md5sum` identique.

---

## References

- `reference/search-strategies.md` -- strategies de recherche, cadrage, bornes, cascade, format des JSON intermediaires
- `reference/x13-impact-patterns.md` -- regex pour detecter les callers (Call, Execute, Module, HFileVersion)
