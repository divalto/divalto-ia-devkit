# Corpus `docs/` cible pour E4

Liste figee des fichiers du referentiel DIVA confrontes au livrable par `detect_doc_contradictions.py`.

Le corpus est volontairement restreint a 4 fichiers pour garder la detection rapide et previsible. Enrichissement ulterieur possible (chantier separe) si de nouvelles heuristiques sont valides.

## Sommaire

- [Fichiers du corpus](#fichiers-du-corpus)
- [H1 -- Nature vs suffixe typee](#h1----nature-vs-suffixe-typee)
- [H2 -- Nature non documentee](#h2----nature-non-documentee)
- [H3 -- Pattern 3 fichiers respecte](#h3----pattern-3-fichiers-respecte)
- [H4 -- Instances et naming](#h4----instances-et-naming)
- [H5 -- Domaine coherent avec prefixe](#h5----domaine-coherent-avec-prefixe)
- [H6 -- Anti-patterns connus](#h6----anti-patterns-connus)
- [Ce qui N'EST PAS dans le corpus](#ce-qui-nest-pas-dans-le-corpus)
- [Schema de sortie des detections E4](#schema-de-sortie-des-detections-e4)

---

## Fichiers du corpus

| Fichier (attendu sous `{RACINE_DOCS}`) | Role dans E4 | Heuristiques derivees |
|----------------------------------------|--------------|------------------------|
| `DICTIONNAIRE-DHSD.md` (section 2 "Mapping Nature -> Taille en octets") | Table des Natures DIVA + suffixes typees | H1, H2 |
| `ARCHITECTURE-ENTITE.md` | Pattern 3 fichiers (`.dhsq`/`.dhop`/`.dhsp`), naming des instances | H3, H4 |
| `MODULES-ERP.md` | Liste des domaines ERP + prefixes attendus | H5 |
| `ANTI-PATTERNS.md` | Regles `Z01`-`Zxx` (anti-patterns connus) | H6 |

Si un fichier du corpus est absent chez le collaborateur (cas peu probable sur un workspace DIVA, mais possible en distribution), l'heuristique correspondante est sautee avec un warning global dans `.detect_e4.json`.

---

## H1 -- Nature vs suffixe typee

**Regle referentiel** : `docs/DICTIONNAIRE-DHSD.md` documente une table de suffixes de nom de champ qui induisent une Nature attendue. Ex : suffixe `Dt` -> Nature `D8` (date), suffixe `Dh` -> Nature `DH` (datetime), suffixe `Fl` -> Nature flottante.

**Verification** : pour chaque champ du livrable (`entity.technical.fields[]`), extraire le suffixe typee du nom. Si le suffixe est liste dans la table referentiel et que la Nature declaree ne matche pas la Nature attendue -> contradiction.

**Extraction heuristique de la table** (dans `detect_doc_contradictions.py`) :
```
regex sur DICTIONNAIRE-DHSD.md : lignes `| <suffixe> | <Nature> | ...` dans les tableaux Markdown
-> dict { suffixe: Nature_attendue }
```

**Exemple de contradiction** :

Livrable :
```yaml
technical:
  fields:
    - { nom: "CLI.DateDernierAchat", nature: "Ch10" }
```

Referentiel (`DICTIONNAIRE-DHSD.md` (section 2 "Mapping Nature -> Taille en octets")) :
```
| Dt | D8 | Date sur 8 octets |
```

Rapport :
```
[E4 warning] CLI / technical.fields
Extrait livrable : "CLI.DateDernierAchat = Ch10"
Extrait referentiel (DICTIONNAIRE-DHSD.md) : "suffixe Dt -> Nature D8"
Challenge : suffixe "Dt" attendu en Nature D8, livrable declare Ch10.
```

---

## H2 -- Nature non documentee

**Regle referentiel** : la table des Natures de `DICTIONNAIRE-DHSD.md` (section 2 "Mapping Nature -> Taille en octets") est exhaustive des Natures acceptees en DIVA.

**Verification** : pour chaque Nature declaree dans le livrable, verifier qu'elle figure dans la liste documentee. Une Nature inconnue -> contradiction.

**Limites** : risque de faux positif si le referentiel est en retard sur une Nature recemment ajoutee. Severite `warning` oblige.

---

## H3 -- Pattern 3 fichiers respecte

**Regle referentiel** : `docs/ARCHITECTURE-ENTITE.md` documente que chaque entite metier est implementee par 3 fichiers avec naming strict :
- `.dhsq` (RecordSql) : fichier `Gtt<entite>.dhsq`
- `.dhop` (Module Check) : fichier `Gttmchk<entite>.dhop` ou equivalent selon domaine
- `.dhsp` (Zoom SQL) : fichier `Gttzoom<entite>.dhsp` ou equivalent

**Verification** : pour chaque citation dans le livrable pointant un `.dhop`, verifier le naming. Si le nom ne commence pas par `Gttmchk` (ou pattern equivalent pour autres domaines) -> contradiction.

**Tolerance** : d'autres prefixes sont acceptes selon le domaine (`Gfc` pour COMPTA, `Gab` pour DAFF, etc.). La liste complete provient de `MODULES-ERP.md` section 4 (cross-heuristique avec H5).

---

## H4 -- Instances et naming

**Regle referentiel** : `ARCHITECTURE-ENTITE.md` documente les conventions de nommage des instances (ex: `Mcli` pour Module CLI, `Tcli` pour Table CLI, etc.).

**Verification** : parser les noms d'instances cites dans le narratif (si detectables). Comparer au pattern attendu. Ecart -> contradiction.

**Limites** : heuristique faible (les noms d'instances apparaissent rarement en clair dans le narratif). Candidat a etre desactive par defaut si trop de bruit.

---

## H5 -- Domaine coherent avec prefixe

**Regle referentiel** : `docs/MODULES-ERP.md` section 4 liste les domaines ERP (DAV, COMPTA, DAFF, GS, ...) avec leur(s) prefixe(s) attendu(s) pour les fichiers sources.

**Verification** : pour chaque entite du livrable, extraire le domaine declare (`module.yaml -> domain`, ou inference depuis les citations). Comparer au prefixe des fichiers cites. Incoherence -> contradiction.

**Exemple de contradiction** :

Livrable :
```yaml
# module.yaml
domain: "COMPTA"
```

Mais `entity/ECR.yaml` cite :
```yaml
technical:
  source: "Gttecr.dhsq:1"  # Prefixe Gtt attendu en DAV, pas COMPTA
```

Rapport :
```
[E4 warning] ECR / technical.source
Extrait livrable : citation "Gttecr.dhsq"
Extrait referentiel (MODULES-ERP.md) : "Domaine COMPTA -> prefixe Gfc"
Challenge : domaine declare COMPTA mais prefixe de fichier Gtt (attendu Gfc).
```

**Regle de precedence** : en cas de doute sur le domaine (pas declare, inference multiple possible), ne pas remonter (mieux vaut un faux negatif qu'un faux positif sur une entite trans-domaine).

---

## H6 -- Anti-patterns connus

**Regle referentiel** : `docs/ANTI-PATTERNS.md` documente ~20 regles `Zxx` chacune avec un pattern detectable.

**Verification** : pour chaque entite, appliquer les regles applicables au livrable (certaines regles ciblent du code DIVA, pas un livrable de doc -- filtrage necessaire).

Regles applicables a un livrable UC-200 :
- Z14/Z15 : FK sans zoom -- verifiable si le livrable declare des FK
- Z16 : masque zoom sans `f8` -- verifiable si le livrable liste des zooms
- D01-D14 : regles dictionnaire -- verifiables via re-parse (cross-heuristique avec E3)

**Limites** : la plupart des regles Z ciblent du code source, pas un livrable de doc. H6 reste utile pour detecter des citations vers des fichiers qui violent les regles Z (ex: le livrable affiche un extrait de `.dhsf` qui viole Z16 -- signaler comme warning que la source pointee est elle-meme problematique).

---

## Ce qui N'EST PAS dans le corpus

Hors scope v1 :
- `docs/LANGAGE-AVANCE.md` (patterns HTTP/REST/JSON) -- utile pour `coding-diva-advanced`, pas pour un livrable de doc
- `docs/ZOOM-INTEGRATION.md` -- cible de la fonctionnalite zoom, non structurante pour un livrable
- `docs/FORMATS-FICHIERS.md` -- reference technique encodage, non structurante pour la semantique du livrable
- Tout `docs/*.md` non liste ci-dessus

Enrichissement possible si de nouvelles heuristiques sont proposees dans un chantier ulterieur (pas dans scope UC-201 v1).

---

## Schema de sortie des detections E4

Chaque item remonte suit le schema general des detections (voir SKILL.md), avec la particularite suivante :

- `source_ref` = `<fichier_referentiel>:<section>` (ex: `DICTIONNAIRE-DHSD.md:section 2`)
- `excerpt_source` = extrait textuel du referentiel (max 200 caracteres)
- `challenge` = phrase de 1-2 lignes contrastant livrable et referentiel

Les items E4 ne sont JAMAIS severite `erreur` (maximum `warning`).
