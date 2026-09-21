# Le cas d'exemple livre avec ce skill

`test_fixtures/fixture-simple/` contient un **module minimal complet** : deux entites
documentees, l'une conforme, l'autre volontairement fautive, plus les sources ERP qui
permettent de rejouer la detection. Il sert a voir ce que le skill trouve avant de le
lancer sur un vrai livrable.

## Ce que contient le cas

| Fichier | Role |
|---------|------|
| `module.yaml` | l'en-tete du module : `code: TST`, `prefix: Gtt`, `status: stable` |
| `entity/OKK.yaml` | l'entite **bien sourcee** -- mais pas exempte de detections |
| `entity/BAD.yaml` | l'entite **infondee** : chaque affirmation metier y est sans source |
| `erp-root/Gttokk.dhsd` | le dictionnaire de `OKK` -- la source de verite structurelle |
| `erp-root/Gttokk.dhsq` | le RecordSql de `OKK` -- la source de verite des citations |

## Ce que les detecteurs trouvent reellement

Les chiffres ci-dessous sont **mesures** en lancant les detecteurs sur ce cas, et
asservis par `tests/test_detecteurs.py`. Une premiere version de cette page annoncait
« `OKK.yaml` : aucune detection attendue » -- c'etait faux, et rien ne le confrontait.

| | `BAD.yaml` | `OKK.yaml` |
|---|---|---|
| **E1** affirmations non sourcees | **6 erreurs** | 0 |
| **E3** omissions structurelles | 1 info | **2 erreurs** |
| **E4** contradictions | 0 | **1 warning** |
| **batch E2** citations a juger | -- | 6, dont 5 resolues |

**La lecon du cas, et c'est elle qui le rend utile** : un livrable peut satisfaire la
regle de citation et rester structurellement incomplet. `OKK` est irreprochable sur E1
et parle sur E3 et E4.

### Le detail, detecteur par detecteur

- **E1 sur `BAD`** -- 0 `Citation:`, 0 `[A VERIFIER]`, `meta.a_verifier` vide, pour six
  affirmations : `business.role`, les deux `business_rules`,
  `technical.performance_notes` et les deux `business_note` de champs. Chacune remonte en
  erreur. `BAD` a la **meme forme** que `OKK` : c'est ce qui rend le cas interessant, un
  livrable peut etre parfaitement structure et entierement infonde.
- **E1 sur `OKK`** -- muet, et c'est merite : 5 `Citation:`, 2 `[A VERIFIER]` inline, et
  une entree `meta.a_verifier` pour la seule assertion qui reste a confirmer.
- **E3 sur `OKK`** -- deux **erreurs** : le champ `Telephone` et l'index `IdxTel` sont
  declares dans `Gttokk.dhsd` et absents du livrable, sans justification dans
  `meta.a_verifier`. C'est le seul endroit du cas ou la source de verite contredit le
  livrable sur du structurel.
- **E3 sur `BAD`** -- une **info**, pas une erreur : aucun `.dhsd` ne correspond a la
  table `BAD` sous `erp-root/`, donc E3 ne peut rien confronter et le dit. `BAD` declare
  `dictionary_source: Gttbad.dhsd`, un fichier absent -- delibere, la reaction du skill
  a une source introuvable fait partie du cas.
- **E4 sur `OKK`** -- un **warning** : `AnnulFl` est declare en Nature `C20`, alors que
  le suffixe `Fl` predit `1,0` a 95 %. Un drapeau booleen sur 20 octets.

## Rejouer le cas

Depuis la racine du cas, en pointant les chemins du pipeline dessus :

```bash
py scripts/ingest_deliverable.py --deliverable test_fixtures/fixture-simple --out .ir.json
py scripts/detect_unsourced.py --ir .ir.json --out .detect_e1.json
```

puis les etapes 3 a 8 du pipeline decrit dans le `SKILL.md`. Les sorties (`.ir.json`,
`.detect_*.json`, `review.md`, `review.json`) sont des **produits d'execution** : elles
s'ecrivent la ou vous les demandez et ne sont pas livrees avec le skill.
