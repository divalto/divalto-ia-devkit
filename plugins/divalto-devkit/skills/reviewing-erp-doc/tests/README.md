# Tests — `reviewing-erp-doc`

Tests **exécutables** des détecteurs du skill. **Aucun ERP, aucune base SQL, aucune
dépendance externe** : les quatre détecteurs consomment un IR en JSON, et la fixture en
fournit un vrai.

## Lancer

```
py .claude/skills/reviewing-erp-doc/tests/run_all.py
```

…ou une suite à la fois :

```
py .claude/skills/reviewing-erp-doc/tests/test_detecteurs.py
py .claude/skills/reviewing-erp-doc/tests/test_e4_heuristiques.py
```

## Les deux suites

| Suite | Cas | Ce qu'elle mesure |
|-------|-----|-------------------|
| `test_detecteurs.py` | 8 | E1, E3, E4 et le batch E2 sur le **cas d'exemple livré** en entier |
| `test_e4_heuristiques.py` | 9 | chaque règle de E4 séparément, sur l'entrée minimale qui la déclenche |

## La fixture

`fixtures/ir-fixture-simple.json` est le **vrai IR** produit par `ingest_deliverable.py`
sur `test_fixtures/fixture-simple`, récupéré de l'historique du dépôt. Deux champs ont
été neutralisés : `deliverable_root` (qui portait un chemin de poste) et `generated_at`.

Les valeurs attendues des assertions ont été **mesurées** en lançant les détecteurs, pas
déduites de ce que les règles devraient trouver. La distinction a payé : la page
`reference/exemple-de-cas.md` affirmait que `OKK.yaml` était « l'entité conforme : aucune
détection attendue ». Mesure : E3 en signale deux et E4 un. La page a été corrigée.

## Ce que le cas d'exemple démontre réellement

| | `BAD.yaml` | `OKK.yaml` |
|---|---|---|
| **E1** affirmations non sourcées | **6 erreurs** | 0 |
| **E3** omissions structurelles | 1 info (aucun `.dhsd` ne lui correspond) | **2 erreurs** (un champ et un index déclarés dans `Gttokk.dhsd`, absents du livrable) |
| **E4** contradictions | 0 | **1 warning** (`AnnulFl` déclaré `C20` pour un suffixe `Fl`) |
| **batch E2** | — | 6 citations, 5 résolues, 1 source absente |

La leçon que les assertions gardent : **un livrable peut satisfaire la règle de citation
et rester structurellement incomplet.** `OKK` est muet sur E1 et parle sur E3 et E4.

## Ce qui n'est pas couvert, et pourquoi

`ingest_deliverable.py` exige **`pyyaml`**, et ce skill ne le déclarait pas — alors que
`documenting-erp`, le producteur du livrable qu'il relit, le déclare depuis toujours dans
sa section `## Dependances`. C'était le consommateur qui taisait la dépendance du
producteur. Corrigé dans les prérequis du `SKILL.md` et dans l'environnement du
workspace. Le script s'arrête à l'import avec un message explicite ; les cinq autres CLI
sont en bibliothèque standard et sont couvertes ici.

Couvrir l'ingestion demande donc `py -m pip install pyyaml`, et ce serait la suite
naturelle de ce lot : c'est le premier maillon du pipeline, et le seul à lire le livrable.
