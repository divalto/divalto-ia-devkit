# Le référentiel que E4 confronte au livrable

E4 cherche les affirmations du livrable qui contredisent une règle connue du référentiel
DIVA. **Ses deux sources sont livrées avec le devkit** : aucune heuristique n'exige un
document que vous n'auriez pas, et E4 tourne donc toujours, sans option à passer.

C'est un changement par rapport à la version précédente, qui attendait une racine
`docs/` en argument obligatoire. Cette racine n'était pas distribuée : E4 était en
pratique inopérant. L'argument `--docs-root` n'existe plus.

## Sommaire

- [H1 -- Nature d'un champ contre son suffixe](#h1----nature-dun-champ-contre-son-suffixe)
- [H5 -- Préfixe du fichier cité contre le domaine déclaré](#h5----préfixe-du-fichier-cité-contre-le-domaine-déclaré)
- [Ce que E4 ne fait pas](#ce-que-e4-ne-fait-pas)
- [Schéma de sortie des détections E4](#schéma-de-sortie-des-détections-e4)

---

## H1 -- Nature d'un champ contre son suffixe

**La règle.** Certains suffixes de nom de champ DIVA prédisent la Nature attendue avec
une corrélation forte. `CdeDh` est un timestamp, `CdeDt` une date, `AnnulFl` un flag.

**La source, livrée.** Le skill `managing-diva-dictionaries`, page
`reference/taxonomie-suffixes.md`, bande « corrélation forte (>= 85 %) ». Elle concorde
avec `SUFFIX_TAXONOMY` de son `scripts/suggest_nature.py`. La table est **recopiée** dans
`detect_doc_contradictions.py` (`SUFFIX_TO_NATURE`) : la règle de vendoring interdit à un
script d'aller lire la page d'un autre skill.

| Suffixe | Nature attendue | Corrélation |
|---------|-----------------|-------------|
| `Dh` | `DH` -- timestamp 14 octets | 98 % |
| `Fl` | commence par `1,` -- flag booléen | 95 % |
| `Dt` | `D8` -- date AAAAMMJJ | 93 % |

**Ce que H1 ne couvre volontairement pas.** `Mt` (65 %) et `Qte` (72 %) sont dans la
bande « proposer + demander confirmation » de la page source, pas dans celle qu'on
affirme. Ils étaient dans la table et **produisaient des faux positifs** : elle annonçait
`8,N` alors que les deux sources donnent `16,D0` et `12,D2`. Un livrable déclarant la
bonne Nature était signalé comme contradiction. Ils sont retirés. `Flg` (99 %) et `He`
(97 %) sont dans la bonne bande et pourraient être ajoutés ; ils ne le sont pas encore.

**Limite de forme, mesurée.** Le suffixe est extrait en **fin de nom** (`([A-Z][a-z]+)$`).
`LotQte` porte le suffixe `Qte`, mais `QteCde` porte `Cde` : un champ dont le token typé
est en tête échappe à H1. Ce n'est pas un bug, c'est la portée de l'heuristique.

---

## H5 -- Préfixe du fichier cité contre le domaine déclaré

**La règle.** Les fichiers source d'un domaine portent le préfixe module de ce domaine.
Une entité déclarée dans `DAV` cite des fichiers `gtt*`.

**La source, livrée.** [prefixes-domaine.md](prefixes-domaine.md), copie locale de
`naming-diva-entities/reference/domain-prefixes.md`. H5 lit la colonne **« Préfixe
module »** (`gtt`) -- pas la colonne « Préfixe code » (`GT_`), que la version précédente
comparait à `gttcli` et qui ne concordait que par accident de troncature.

**La vérification.** Pour chaque citation `fichier:ligne` d'une affirmation, si le nom de
fichier ne commence pas par le préfixe module du domaine déclaré, un `warning` est posé.

**Règle de précédence.** Si le domaine de l'entité n'est pas déclaré, ou ne figure pas
dans la table, H5 **se tait**. Mieux vaut une détection muette qu'un faux positif.

**Limite, mesurée.** La colonne « Domaine » de la page d'origine mélange des codes
(`DAV`, `GRM`) et des noms de module (`Retail`, `Comptabilite`). H5 ne se déclenche que
si le champ `module` du livrable correspond à une valeur de cette colonne.

---

## Ce que E4 ne fait pas

Quatre heuristiques ont été **documentées sans jamais être implémentées**. Elles sont
nommées ici pour que la page cesse de les promettre :

| Heuristique annoncée | État |
|----------------------|------|
| Nature non documentée (une Nature du livrable absente de la table des Natures) | non implémentée |
| Pattern 3 fichiers (naming `Gttmchk*.dhop`) | non implémentée -- les formules vivent dans `naming-diva-entities/reference/naming-formulas.md` |
| Instances et naming (`Mcli` pour Module CLI) | non implémentée -- heuristique jugée trop faible, les noms d'instances apparaissent rarement en clair |
| Anti-patterns `Zxx` connus | non implémentée -- les règles `Z` ciblent du code source, pas un livrable de doc ; elles vivent dans `linting-diva-code/reference/rules-architecture.md` |

Hors périmètre par nature, et pourquoi :

- les patterns de langage avancé (HTTP/REST/JSON) -- utiles pour `coding-diva-advanced`,
  pas pour un livrable de doc
- l'intégration des zooms -- cible de la fonctionnalité zoom, non structurante pour un
  livrable
- les formats de fichiers -- technique d'encodage, non structurante pour la sémantique du
  livrable

---

## Schéma de sortie des détections E4

Chaque item suit le schéma général des détections (voir `SKILL.md`), avec ces
particularités :

- `source_ref` = la page qui porte la règle (ex : `reference/prefixes-domaine.md`)
- `excerpt_source` = extrait textuel de la règle (max 200 caractères)
- `challenge` = une à deux lignes contrastant livrable et référentiel

Les items E4 ne sont **jamais** de sévérité `erreur` -- au maximum `warning`. Une
corrélation statistique n'est pas une règle, et le référentiel peut être en retard sur le
standard.
