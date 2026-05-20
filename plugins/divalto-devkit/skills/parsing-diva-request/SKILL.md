---
name: parsing-diva-request
description: >
  Structure une demande DIVA en texte libre (user story + criteres d'acceptation, ou ticket
  myService d'anomalie) en JSON canonique : type de demande, titre, resume, acteurs, donnees
  manipulees, domaine ERP pressenti, keywords techniques et metier, CA detectes, message
  d'erreur. Le parseur est deterministe (regex + heuristiques), le LLM raffine la sortie au
  checkpoint CP1 de l'orchestrateur. A utiliser quand une demande est livree en texte libre
  et qu'il faut produire un JSON structure exploitable par les phases suivantes d'analyse.
---

# Parsing DIVA Request

## Contenu

- Utilisation rapide
- Parametres d'entree
- Sortie : JSON canonique
- Type de demande detecte
- Domaines ERP reconnus
- Cas d'ambiguite (needs_clarification)
- Scripts disponibles
- References

---

## Utilisation rapide

Via stdin (recommande pour coller un texte long) :

```
echo "En tant que gestionnaire reglement, je veux saisir la famille de reglement sur la fiche client. CA : le zoom est accessible depuis le menu Retail." | \
  py .claude/skills/parsing-diva-request/scripts/parse_request.py
```

Via fichier :

```
py .claude/skills/parsing-diva-request/scripts/parse_request.py --input demande.txt
```

Sortie JSON sur stdout, conforme au schema `scripts/templates/request.schema.json`.

---

## Parametres d'entree

| Parametre | Format | Obligatoire | Defaut |
|-----------|--------|-------------|--------|
| `--input` | Chemin fichier texte (UTF-8) | Non | stdin |
| `--type` | `auto` / `feature` / `ticket` | Non | `auto` (detection) |

Un seul parametre a la fois : si `--input` est absent, la commande lit `stdin` jusqu'a EOF.

---

## Sortie : JSON canonique

```json
{
  "type": "feature|ticket|unknown",
  "titre": "<titre court, <= 80 car>",
  "resume": "<1-3 phrases, <= 400 car>",
  "acteurs": ["<role metier>"],
  "donnees": ["<nom PascalCase ou MAJUSCULE>"],
  "domaine_pressenti": "RT_|GT_|CC_|...|null",
  "keywords_techniques": ["<PascalCase, fichier.dhsp, fonction>"],
  "keywords_metier": ["<mot substantif 5+ car>"],
  "ca_detectes": ["<texte CA>"],
  "message_erreur": "<si ticket, citation>",
  "needs_clarification": false
}
```

Reference du schema : `scripts/templates/request.schema.json`.

---

## Type de demande detecte

Heuristique multi-signaux :

| Type | Patterns declencheurs |
|------|----------------------|
| `feature` | `En tant que` / `Je veux` / `Afin de` / `Etant donne` / `Quand...Alors` / section `Criteres d'acceptation` ou `CA` avec bullets |
| `ticket` | `anomalie` / `bug` / `erreur` / `plante` / `cassé` / `ne fonctionne pas` / stack trace / message entre quotes |
| `unknown` | Aucun signal -- declenche `needs_clarification: true` |

Detail dans `reference/patterns-features.md` et `reference/patterns-tickets.md`.

---

## Domaines ERP reconnus

Liste canonique :

| Prefixe | Module | Mots-cles declencheurs |
|---------|--------|------------------------|
| `GT_` | Achat-Vente / Dav | gestion commerciale, facture, client, article, commande, vente |
| `RT_` | Retail | retail, caisse, ticket, point de vente, magasin |
| `GG_` | Prod / Atelier | production, atelier, fabrication, OF, nomenclature |
| `CC_` | Comptabilite | compta, ecriture, journal, bilan, TVA |
| `RC_` | Reglements | reglement, banque, paiement, relance |
| `PP_` | Paie | paie, salaire, bulletin, cotisation |
| `GA_` | Affaires | affaire, chantier, analytique |
| `QU_` | Qualite | qualite, controle qualite, non-conformite |
| `GR_` | Relation-Tiers | CRM, contact, prospect, tiers |
| `A5` | Framework A5 | framework, menu, dossier, utilisateur, securite |

La detection est informative (hint pour le CP2 de l'orchestrateur). Si aucun domaine ne matche, `domaine_pressenti: null`.

---

## Cas d'ambiguite (needs_clarification)

Le flag `needs_clarification: true` est leve quand :

- Le type est `unknown` (aucun signal feature ni ticket)
- Type = `feature` mais aucun acteur extrait (pas de `En tant que`)
- Type = `ticket` mais aucun message d'erreur ni stack trace identifie

Dans ces cas, l'orchestrateur LLM doit demander au developpeur de clarifier au CP1 avant de poursuivre. Le parseur n'invente pas -- c'est la responsabilite du LLM.

---

## Scripts disponibles

```
scripts/parse_request.py        # Parseur principal
scripts/templates/
  request.schema.json           # Schema JSON canonique de la sortie
```

---

## References

- `reference/patterns-features.md` -- detail des patterns de detection feature (BDD, CA, gerondif)
- `reference/patterns-tickets.md` -- detail des patterns ticket (messages d'erreur, stack traces, anomalies)
