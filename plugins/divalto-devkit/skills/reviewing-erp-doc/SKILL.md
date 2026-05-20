---
name: reviewing-erp-doc
description: Relit la documentation technique produite par documenting-erp et la challenge contre les sources X.13 et le referentiel DIVA. Detecte 4 categories d'erreurs d'interpretation LLM -- E1 (affirmation narrative non sourcee), E2 (desalignement entre narratif et source citee), E3 (omission structurelle champ/index/FK), E4 (contradiction avec le referentiel DIVA). Produit un rapport classe par severite (erreur/warning/info) en lecture seule stricte sur le livrable et sur le referentiel. Seconde voix independante du producteur. A utiliser apres une execution de documenting-erp pour challenger le livrable avant publication.
---

# reviewing-erp-doc -- Relire et challenger une documentation technique generee

## Role

Seconde voix independante qui relit la documentation technique produite par `documenting-erp` (UC-200) et challenge son contenu contre la connaissance produit vivante : sources X.13 + referentiel DIVA du workspace. Detecte les erreurs d'interpretation LLM que le producteur n'a pas su identifier comme incertaines (au-dela des items `[A VERIFIER]` deja presents dans le livrable).

Le relecteur signale, il ne corrige pas. Le collaborateur arbitre en aval.

## Principe

Ce skill est cable pour etre **independant par conception** du producteur :

- Aucun import vers `documenting-erp/scripts/`
- Connait uniquement la structure YAML stable du livrable
- Re-consulte les memes sources (X.13, schema SQL, referentiel) depuis zero
- Aucune modification du livrable ni du referentiel : lecture seule stricte

Ce qui legitimement peut apparaitre dans un livrable UC-200 mais meriter d'etre challenge :

- Citation correcte mais paraphrase derivant du code cite (contresens sur Mchk, inversion d'une contrainte)
- Affirmation qui echappe a la regle de citation CA4 de UC-200
- Champ, index ou FK present dans la source mais absent du livrable
- Formulation qui contredit le referentiel DIVA (Nature, prefixe, pattern 3 fichiers, anti-patterns)

## Categories d'erreurs detectees

| Cat | Nom | Severite par defaut | Deterministe ? | Etape |
|-----|-----|---------------------|----------------|-------|
| E1  | Affirmation non sourcee | erreur | Oui (regex) | 2 |
| E3  | Omission structurelle | erreur | Oui (diff sources vs YAML) | 3 |
| E4  | Contradiction avec referentiel DIVA | warning | Oui (heuristiques) | 4 |
| E2  | Desalignement narratif vs citation | warning | Non (jugement LLM) | 5-6 |

Definitions detaillees + exemples : voir [reference/categories-erreurs.md](reference/categories-erreurs.md).

Strategie de cross-check par categorie : voir [reference/cross-check-strategy.md](reference/cross-check-strategy.md).

## Prerequis

- Un livrable UC-200 existe sous `{REPERTOIRE_SORTIE}/doc-erp/{MODULE}/` (produit par `documenting-erp`)
- Acces en lecture aux sources X.13 (`{CHEMIN_ERP_STANDARD}`)
- Acces en lecture a l'export JSON du schema SQL (`{CHEMIN_SCHEMA_SQL}`)
- Acces en lecture a la racine du referentiel DIVA du workspace (`{RACINE_DOCS}`) -- optionnel (skip E4 si absent)

## Pipeline

> **CHECKPOINT CP-Entree -- Cadrage des inputs**
> Presenter au collaborateur :
> - Chemin du livrable UC-200 : `{REPERTOIRE_SORTIE}/doc-erp/{MODULE}/`
> - Chemin `{CHEMIN_ERP_STANDARD}`
> - Chemin `{CHEMIN_SCHEMA_SQL}`
> - Racine `{RACINE_DOCS}` (ou `skip` pour desactiver E4)
> - Entites a relire : `all` par defaut, ou liste explicite (ex: `CLI,FOU,ART`)
> Attendre validation avant execution.

---

### Etape 1 : Ingestion du livrable

```
py scripts/ingest_deliverable.py \
  --deliverable {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/ \
  --entities all \
  --out-ir {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.review_ir.json
```

Lit `module.yaml`, `entity/*.yaml`, `relation/*.yaml`, `glossary.yaml` et le rendu `{MODULE}.md`. Produit un IR unifie :

- Par entite : liste des **affirmations** (texte, champ YAML source, citations detectees, items `meta.a_verifier` couvrant l'affirmation)
- Par entite : liste des **structures declarees** (fields, indexes, primary_key, relations)

Sortie interne, pas presentee au collaborateur.

### Etape 2 : Detection E1 -- affirmations non sourcees

```
py scripts/detect_unsourced.py \
  --ir {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.review_ir.json \
  --out {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.detect_e1.json
```

Scan regex : toute affirmation non vide dans `business.*`, `schema.*`, `technical.*` doit avoir soit une citation `fichier:ligne`, soit etre couverte par un item `meta.a_verifier`. Affirmations orphelines remontees en `erreur`.

Deterministe, zero LLM.

### Etape 3 : Detection E3 -- omissions structurelles

```
py scripts/detect_omissions.py \
  --ir {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.review_ir.json \
  --erp-root {CHEMIN_ERP_STANDARD} \
  --schema-sql {CHEMIN_SCHEMA_SQL} \
  --out {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.detect_e3.json
```

Re-parse `.dhsd` (via `_dhsd_parser.py` vendore), `.dhsf` (via `_dhsf_parser.py` vendore) et schema SQL. Diff avec les structures declarees dans l'IR. Un element present en source mais absent du livrable, non justifie par un `meta.a_verifier`, remonte en `erreur`.

Deterministe.

### Etape 4 : Detection E4 -- contradictions avec le referentiel DIVA

```
py scripts/detect_doc_contradictions.py \
  --ir {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.review_ir.json \
  --docs-root {RACINE_DOCS} \
  --out {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.detect_e4.json
```

Corpus cible et regles d'extraction : voir [reference/docs-corpus.md](reference/docs-corpus.md). Si `{RACINE_DOCS}` vaut `skip`, l'etape est sautee et un warning global `E4 non verifie (docs-root skip)` est pose dans le rapport final.

Deterministe (regex + heuristiques).

### Etape 5 : Preparation du batch E2

```
py scripts/prepare_misalign_batch.py \
  --ir {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.review_ir.json \
  --erp-root {CHEMIN_ERP_STANDARD} \
  --context-lines 20 \
  --out {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/.batch_e2.json
```

Pour chaque affirmation sourcee (citation `fichier:ligne` detectee par `ingest_deliverable.py`), extrait via `_x13_context.py` un contexte de 20 lignes autour de la citation. Produit un batch :

```json
[
  {
    "entity": "CLI",
    "yaml_path": "business.role",
    "narratif": "<extrait narratif livrable>",
    "citation": "Gttmchkcli.dhop:142",
    "context_source": "<20 lignes autour de la ligne 142>"
  },
  ...
]
```

Deterministe.

### Etape 6 : Evaluation semantique E2 (LLM)

Claude boucle sur le batch, **une entite a la fois**. Pour chaque paire `{narratif, context_source}` :

1. Lire strictement le `context_source` fourni (ne PAS aller chercher d'autres extraits X.13)
2. Evaluer si le narratif est une paraphrase fidele du contexte :
   - `align: oui` -- le narratif dit bien ce que dit le contexte
   - `align: non` -- le narratif affirme l'inverse ou introduit une information non presente dans le contexte
   - `align: douteux` -- le contexte est trop court ou ambigu pour trancher
3. Si `non` ou `douteux` : fournir une `explication` de 1-2 phrases + un `extrait_contradictoire` (fragment du contexte qui contredit le narratif) quand il existe
4. JAMAIS proposer de correction du narratif

Ecrire le resultat dans `.detect_e2.json` (un objet par paire du batch). Severite : `non` -> `warning`, `douteux` -> `info`, `oui` -> pas d'item.

Regles strictes de cette etape :
- Ne pas inventer un extrait source -- si ce n'est pas dans `context_source`, ne pas le mentionner
- Ne pas deborder sur d'autres categories (E1, E3, E4 sont traitees par les detecteurs deterministes)
- En cas de batch vide (aucune citation detectee a l'etape 1) : ecrire un `.detect_e2.json` vide avec statut `no_citations_in_deliverable` (cas cible dans le scenario 3 de UC-201)

### Etape 7 : Synthese editoriale (LLM)

Avant l'assemblage machine, Claude lit les 4 `.detect_eN.json` + l'IR + les stats
agregees et redige une **synthese editoriale** de 200-400 mots en voix de relecteur
humain. Objectif : sortir du format liste pour donner une vraie lecture du livrable.

Le texte doit :
- Ouvrir par un verdict pondere (publiable / corrections / regression) avec une raison concrete
- Distinguer ce qui est solide (structure) de ce qui cloche (narratif, omissions, contradictions)
- Pointer les entites les plus critiques et ce qui les caracterise
- Signaler le ratio de couverture du producteur et son implication (le producteur a-t-il reconnu ses incertitudes ?)
- Se terminer par une recommandation d'action concrete (ex: cabler tel extracteur, re-enrichir telle entite)

Regles strictes :
- Ne pas inventer un extrait ou un challenge -- s'appuyer uniquement sur les detections
- Ne pas repeter les compteurs bruts ("131 erreurs E1") sans les mettre en sens
- Ton direct, premiere personne ("j'ai relu...", "je recommande..."), pas de formules corporate
- Ecrire en markdown, sans titre H2 (la section `## Retour du relecteur` est ajoutee par le template)

Ecrire le texte dans `{REPERTOIRE_SORTIE}/doc-erp/{MODULE}/review.editorial.md`. Ce fichier sera consomme par l'etape 8 via `--editorial`.

### Etape 8 : Assemblage du rapport

```
py scripts/build_review.py \
  --deliverable {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/ \
  --detections .detect_e1.json,.detect_e2.json,.detect_e3.json,.detect_e4.json \
  --template templates/review.md.j2 \
  --editorial {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/review.editorial.md \
  --out-md {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/review.md \
  --out-json {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/review.json \
  --out-stats {REPERTOIRE_SORTIE}/doc-erp/{MODULE}/review.stats.json
```

Agrege les 4 detections. Tri deterministe :
- Par entite (ordre alphabetique)
- Par categorie (E1 -> E3 -> E4 -> E2)
- Par severite (erreur -> warning -> info)
- Par ligne source (pour stabilite du diff)

Timestamps exclus du diff pour garantir l'idempotence (CA13 de UC-201).

Calcule egalement le **ratio de couverture du producteur** = `nb items [A VERIFIER] deja presents dans meta.a_verifier / (nb items [A VERIFIER] + nb items detectes par le relecteur)`. 100% = producteur a tout signale. < 50% = le producteur rate plus de la moitie des points incertains.

---

> **CHECKPOINT CP-Rapport-Final -- Livraison du rapport de relecture**
> Presenter au collaborateur :
> - Fichiers produits : `review.md`, `review.json`, `review.stats.json`
> - Resume executif : nb erreurs / warnings / infos par categorie (tableau E1/E2/E3/E4), nb entites touchees
> - Ratio de couverture du producteur
> - Verdict : `publiable en l'etat` (0 erreur, warnings acceptables) | `corrections necessaires avant publication` (>=1 erreur) | `regression CA4 UC-200` (E1 massif)
> - Entites les plus critiques (top 3 par nb d'erreurs)
> Attendre validation.

---

## Invariants

1. **Lecture seule stricte sur le livrable** -- aucun YAML, aucun MD, aucun JSON du livrable UC-200 n'est modifie
2. **Lecture seule stricte sur le referentiel DIVA** -- signalement uniquement ; jamais de proposition de modification du referentiel
3. **Independance producteur** -- aucun import vers `documenting-erp/scripts/` ; connait uniquement la structure YAML stable
4. **Pas d'invention** -- chaque item du rapport est trace au livrable (chemin YAML + champ) ou a la source X.13 (fichier:ligne). Jamais d'affirmation sans ancre.
5. **Idempotence** -- deux passes sur les memes inputs produisent des rapports identiques (hors timestamps exclus du diff)
6. **Pas de cross-contamination entre categories** -- un item ne doit appartenir qu'a une seule categorie E1/E2/E3/E4. En cas de doublon potentiel (ex: une affirmation non sourcee ET en omission structurelle), E1 prime.

## Convention de severite

| Severite | Sens | Action attendue |
|----------|------|-----------------|
| `erreur` | Viole un CA de UC-200 ou omet une structure declaree en source | Corriger avant publication |
| `warning` | Desalignement ou contradiction a verifier | Recommande de corriger avant publication |
| `info` | Observation, point d'attention, cas `douteux` | Laisse au jugement du collaborateur |

## Vendoring

Strategie : vendoring **selectif** quand le canonique est reutilisable en l'etat (copie fidele + mention de l'origine), **mini-parseur dedie** quand le canonique est overkill ou inclut des dependances non necessaires.

| Fichier local | Strategie | Source de reference | Role |
|---------------|-----------|----------------------|------|
| `scripts/_x13_context.py` | Copie fidele | `searching-erp-sources/scripts/extract_context.py` | Extraction de contexte autour d'une ligne X.13 |
| `scripts/_structural_parser.py` | Copie fidele | `searching-erp-sources/scripts/_structural_parser.py` (requis par `_x13_context.py`) | Parser de blocs Procedure/Function |
| `scripts/_dhsd_parser.py` | Extraction chirurgicale | `managing-diva-dictionaries/scripts/validate_dhsd.py` (fonction `parse_dhsd_table` + ajout parser d'index) | Extraction fields + indexes d'un `.dhsd` |
| `scripts/_dhsf_parser.py` | Mini-parseur dedie | -- (50 lignes pour scanner les `f8=<code>` par champ) | Extraction des zooms f8 d'un `.dhsf` |

Procedure de mise a jour pour les copies fideles : modifier le canonique dans le skill source, puis re-copier dans `reviewing-erp-doc/scripts/`. Pour les extractions chirurgicales et mini-parseurs : ajuster manuellement a chaque evolution du format source, la derive est acceptable tant que la fonction cible reste stable.

## Schema des detections

Chaque fichier `.detect_eN.json` suit le meme schema :

```json
{
  "category": "E1" | "E2" | "E3" | "E4",
  "generated_at": "<timestamp ISO>",
  "items": [
    {
      "entity": "CLI",
      "severity": "erreur" | "warning" | "info",
      "title": "<titre court>",
      "yaml_path": "<chemin dans le YAML, ex: business.role>",
      "excerpt_deliverable": "<extrait livrable>",
      "excerpt_source": "<extrait source ou corpus>",
      "source_ref": "<fichier:ligne>",
      "challenge": "<1-2 phrases : la source dit X, le livrable affirme Y>"
    }
  ]
}
```
