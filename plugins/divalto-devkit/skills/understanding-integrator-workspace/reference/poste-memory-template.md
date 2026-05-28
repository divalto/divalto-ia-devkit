# Memoire des conventions du poste integrateur (R-16)

Ce document detaille **R-16** -- la capture et la relecture des conventions du poste integrateur dans la **memoire de session** Claude Code (`~/.claude/projects/<workspace>/memory/`). Capitalise les decouvertes faites pendant l'audit initial du workspace (R-1 a R-15) pour les sessions ulterieures, sans avoir a re-poser les memes questions au collaborateur a chaque demarrage.

## Motivation -- pourquoi capitaliser

Sur un poste integrateur mature, plusieurs conventions sont **stables dans le temps** mais **specifiques au poste** :

- Quel implicite est actif (local au workspace ? partage runtime `c:\divalto\sys\impltmp.txt` ?)
- Comment est declare `cheminbases` (relatif avec `flagrelatif=1` ? absolu ? Vers sources ou objets ?)
- Quelle convention de casse pour les noms de version ERP (`v2026_erpx13_p223a` lowercase ? `v2026_erpX13_p223a` mixte ?)
- Quelles cles `[general]` sont obligatoires pour les `.dhpt` de surcharge du poste (`f5compile`, `typetransport`, ...)
- Quel(s) profil(s) sont actifs

Ces 5 questions sont posees lors de l'**audit initial** du workspace (R-1 a R-15). Une fois repondues, elles peuvent etre **stockees une fois pour toutes** en memoire et **relues** au demarrage de chaque session ulterieure sur le meme workspace.

Sans cette capitalisation, Claude re-decouvre les conventions a chaque session, perd du temps et risque de derive (interpretation differente d'une fois sur l'autre).

> **Cadre conceptuel** : `R-1` a `R-15` produisent la **carte du workspace** (search path, profil typé, classification standard/specifique). `R-16` ecrit cette carte dans la memoire de session pour que la prochaine ouverture demarre informee, pas a froid.

---

## Localisation de la memoire

Claude Code maintient une memoire de session par workspace dans :

```
~/.claude/projects/<workspace>/memory/
```

Le `<workspace>` correspond au chemin du dossier ouvert dans Claude Code (encode avec des slashs remplaces par des tirets, cf. convention Claude Code).

Cette memoire est :
- **Persistante** entre sessions (relue automatiquement par Claude Code au demarrage)
- **Locale au poste** (pas partagee entre integrateurs -- ce qui est ce qu'on veut : les conventions sont specifiques au poste)
- **Versionnable** independamment (option : si le partenaire veut sauvegarder ses conventions, il peut les inclure dans son SVN/Git ailleurs ; pas obligatoire)

---

## Template a 5 sections -- `poste-conventions.md`

Fichier a creer/maintenir : `~/.claude/projects/<workspace>/memory/poste-conventions.md`.

Structure recommandee :

```markdown
# Conventions du poste integrateur -- <nom_workspace>

Capturees lors de l'audit initial (R-1 a R-15) le <date> par <session>.
Reapplicables a toutes les surcharges futures sur ce poste.

## 1. Implicite actif

- **Chemin** : `<chemin_absolu>` (ex: `c:\Divalto\sys\impltmp.txt`)
- **Type** : `local workspace` | `partage runtime` | `autre`
- **Compagnon XML** : `<chemin_xml>` (typiquement meme repertoire, meme basename, ext `.xml`)
- **Confirme par** : <collaborateur> le <date>

## 2. Convention `cheminbases`

- **Mode** : `relatif` | `absolu`
- **`flagrelatif=`** : `1` (relatif) | `0` ou absent (absolu)
- **Pointe sur** : `sources standard` (typique) | `objets compiles` (rare/erreur)
- **Exemple terrain** : `"/../../../sources/v2026_erpx13_p223a"`
- **Notes** : <details specifiques observes>

## 3. Convention de casse pour la version ERP

- **Format** : `v<annee>_erp<x>_p<patch>`
- **Casse** : `lowercase` (recommande, observe sur ce poste) | `mixte` | `uppercase`
- **Exemple terrain** : `v2026_erpx13_p223a`
- **Notes** : si une RETEX a confirme qu'une variante de casse cause une erreur sur ce poste, mentionner ici.

## 4. Cles `[general]` obligatoires pour les `.dhpt` de surcharge du poste

Liste des cles qui doivent etre presentes dans `[general]` d'un `.dhpt` de surcharge fonctionnel sur ce poste (au-dela des cles standard documentees dans `managing-diva-projects/reference/dhpt-structure.md`) :

| Cle | Valeur observee | Notes |
|-----|------------------|-------|
| `cheminbases` | <valeur> | obligatoire (cf. section 2) |
| `flagrelatif` | <valeur> | (cf. section 2) |
| `f5compile` | `1` | compilation incrementale F5 active |
| `typetransport` | `3` | observe sur les surcharges fonctionnelles |
| `projetstandard` | `0` | projet partenaire |
| <autre> | <valeur> | <raison> |

## 5. Profil(s) actif(s)

- **Profil principal** : `<nom>` (ex: `developpement` -- attention encodage `\xe9` ISO-8859-1)
- **Encodage** : `accent ISO-8859-1` | `sans accent`
- **`repobjet`** : `<chemin>` (objets compiles STANDARD)
- **`repobjetsurcharge`** : `<chemin>` (objets compiles SURCHARGE)
- **`repbrowse`** : `<chemin>`
- **`repbrowsesurcharge`** : `<chemin>`
- **`versioncible`** : `<X.NN>`
- **Profils secondaires** : <liste si plusieurs>

---

## Notes additionnelles

Toute particularite observee qui ne rentre pas dans les 5 sections ci-dessus mais qui meriterait d'etre reapplique aux sessions futures. Exemple : *« le compagnon ADO.NET `connexions.xml` est partage via `\\srv-prod\divalto\sys\` au lieu du `c:\Divalto\sys\` local »*.

---

## Sources de verite -- ou ces conventions ont ete trouvees

Pour traceabilite :
- Implicite : confirme par <collaborateur> le <date>
- `cheminbases` : `<chemin>/divalto achat-venteu.dhpt` ligne X
- Casse version : `<chemin>/divalto achat-venteu.dhpt` ligne Y
- ...
```

---

## Procedure de capture (audit initial)

A executer **a la 1ere session** sur un workspace nouveau, apres avoir applique R-1 a R-15 :

1. **R-1 a R-15** -- audit complet du workspace (implicite + profil + classification). Voir les regles correspondantes.
2. **Verifier l'existence** de `~/.claude/projects/<workspace>/memory/poste-conventions.md`. Si present -> appliquer la procedure de relecture (section suivante) au lieu de capture.
3. **Presenter au collaborateur les 5 conventions observees** dans un format synthetique, en demandant explicitement : *« je vais les capturer dans la memoire du workspace pour les sessions futures -- une convention manquante ou erronee ? »*.
4. **Sur OK** : creer le fichier en suivant le template ci-dessus, remplir les sections avec les valeurs observees + les sources de verite. Encodage **UTF-8 + LF** (memoire Claude Code, pas un fichier DIVA).
5. **Sur correction** : appliquer les corrections du collaborateur avant ecriture. Re-presenter pour confirmation finale.
6. **Mentionner** au collaborateur que la memoire est **locale au poste** -- si plusieurs integrateurs travaillent sur le meme workspace via SVN, chacun doit faire son audit initial.

> **P-B applicable** : ne JAMAIS ecrire la memoire sans confirmation explicite du collaborateur. Les conventions deduites de l'audit sont des hypotheses jusqu'a validation.

---

## Procedure de relecture (sessions ulterieures)

A executer **a chaque demarrage** d'une session sur un workspace deja audite :

1. **Lire** `~/.claude/projects/<workspace>/memory/poste-conventions.md` en premier (avant tout audit R-1 a R-15).
2. **Presenter au collaborateur les conventions stockees** (resume synthetique des 5 sections + date de derniere capture).
3. **Demander confirmation** : *« les conventions du poste tiennent-elles toujours ? Une mise a jour necessaire (nouveau profil, changement d'implicite, evolution du standard) ? »*.
4. **Sur confirmation "OK, inchange"** : utiliser les conventions stockees pour la session, sans re-poser les questions R-1 a R-15.
5. **Sur indication d'evolution** : re-executer l'audit (R-1 a R-15) sur les parties concernees, puis **mettre a jour** `poste-conventions.md` (toujours apres confirmation -- P-B). Ne JAMAIS modifier en silence.

---

## Limites et garde-fous

- **Memoire locale au poste** : les conventions stockees ne sont pas transposables d'un poste a l'autre. Si un meme integrateur change de machine, refaire l'audit initial. Le partenaire peut s'inspirer d'une memoire d'un poste voisin **comme reference**, jamais comme verite par defaut.
- **Conventions evoluent** : versions ERP, profils, structures de workspace bougent. La memoire **doit etre relue et re-validee** a chaque session -- elle accelere l'audit, elle ne le supprime pas.
- **Pas de mecanisme automatique** : ce template documente une **bonne pratique** -- Claude la suit explicitement, il n'y a pas de hook Claude Code qui force la capture. Si une session se termine sans capture, ce n'est pas bloquant ; la prochaine session refera juste l'audit complet.
- **Pas de SC futur sans datapoint** : si une convention se revele systematiquement valable cross-postes (typique : *« sur tous les postes integrateurs Divalto, `flagrelatif=1` est la convention »*), elle peut etre promue vers la doc generale du skill (`dhpt-structure.md`). Le canal est la RETEX -- pas de generalisation prematuree avant accumulation de datapoints terrain.

---

## Lien avec les autres regles

- **R-1 a R-15** : produisent les donnees a stocker dans `poste-conventions.md`. R-16 est la **persistance** de ces decouvertes.
- **SC-002 (batch 2026-05-27)** : enrichit la doc generale `dhpt-structure.md` avec les conventions terrain (cheminbases, flagrelatif, casse lowercase, cles `[general]`). Le template ci-dessus reference ces conventions comme valeurs **typiques** -- les valeurs **effectives** du poste vivent dans la memoire.
- **Principes transverses P-A / P-B / P-C** : la capture et la relecture sont soumises a P-B (jamais sans confirmation explicite) et P-C (la memoire vit dans `memory/`, jamais dans le registre Windows).
