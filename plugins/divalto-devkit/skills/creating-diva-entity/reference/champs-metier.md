# Definition des champs metier -- Etape 7bis

> Fragment de reference pour l'etape 7bis de `creating-diva-entity` (definition collaborative des champs metier de la table avant generation dictionnaire).

## Objectif

Collecter avec le collaborateur la liste des champs metier de la table, avec pour chacun : nom PascalCase, Nature DIVA, description semantique.

## Sous-etapes

1. **Description semantique** : le collaborateur fournit une description en langage naturel ("date de livraison prevue", "flag annulation", "montant HT").

2. **Proposition nom PascalCase** : l'orchestrateur propose un nom qui respecte la taxonomie de suffixes DIVA (detail : [reference/suffix-taxonomy.md](suffix-taxonomy.md)).

3. **Appel `suggest_nature.py`** pour deduire la Nature automatiquement :

```
py .claude/skills/managing-diva-dictionaries/scripts/suggest_nature.py \
    --name "{nom_champ}"
# Retourne : { "nature": "...", "confidence": 0.xx, "rule": "...", "alternatives": [...], "note": "..." }
```

4. **Regle de decision** :
   - `confidence >= 0.85` -> proposer la Nature directement, demander confirmation simple.
   - `0.5 <= confidence < 0.85` -> proposer la Nature principale + les alternatives, demander confirmation.
   - `confidence < 0.5` -> demander explicitement la Nature au collaborateur avec les alternatives les plus frequentes comme options.

5. **Socle audit canonique** : ajoute automatiquement par `generate_dhsd_block.py`, ne pas les redemander : `Ce1`, `Dos`, `UserCr`, `UserMo`, `UserCrDh`, `UserMoDh`.

6. **A ne pas proposer** : ni `UserTrace` (obsolete, 0 occurrence X.13), ni duplicate d'un champ canonique.

## Checkpoint CP3bis -- Definition des champs metier

Presenter au collaborateur :
- Liste complete des champs metier proposes avec : nom, Nature, taille, description, regle de deduction (suffixe/prefixe/canonique), confiance.
- Champs canoniques qui seront ajoutes automatiquement.
- Champ `U<Table>` (reserve distributeur) dont la taille est libre (100/200/500).

Attendre validation explicite avant de generer les blocs dictionnaire.
