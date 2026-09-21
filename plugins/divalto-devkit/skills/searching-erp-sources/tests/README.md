# Tests du skill searching-erp-sources

```
py .claude/skills/searching-erp-sources/tests/run_all.py
```

Aucun poste Divalto requis : chaque cas fabrique une petite arborescence de sources en
ISO-8859-1 + CRLF dans un repertoire temporaire, nettoye en `finally`.

---

## test_honnetete_sortie.py

Les cinq defauts corriges sur `verify_x13.py` partagent **une seule cause** :
la sortie affirmait plus que le travail reellement accompli. Un rapport qui en dit trop
est plus dangereux qu'un rapport vide -- le developpeur conclut « ca n'existe pas dans mes
sources » alors que la recherche n'a pas eu lieu.

| Defaut | Ce que la sortie disait | Ce qui se passait |
|--------|-------------------------|-------------------|
| **#327** | « recherche effectuee » | seuls les **5 premiers** mots-cles etaient cherches, en silence. Le 6e n'apparaissait nulle part |
| **#328** | 50 correspondances | un mot de 2 lettres (`AB`) matchait **a l'interieur** d'autres mots (`MABSENT`, `TABLEAU`) et saturait son quota sur un seul fichier de dictionnaire, gaspillant 1 des 5 emplacements de recherche |
| **#329** | cadrage par domaine | le cadrage avait **echoue** (sous-repertoires absents) et la recherche portait sur **tout** `erp_root` |
| **#329 bis** | aide CLI : `auto\|all\|<prefix>` | un **prefixe** de module (`GT_`) etait traite comme un nom de repertoire litteral, donc jamais resolu : `--domain-scope GT_` retombait **toujours** sur tout l'ERP, meme la ou `GT_` est une cle valide |
| **version** | `CONFIRME X.13` | le script lit la racine qu'on lui donne : elle peut contenir **n'importe quelle version**. Le skill appelant `analyzing-diva-request` dit lui-meme que « le defaut X.13 n'est PAS forcement la cible » |

Plus un compteur qui melangeait deux unites : `files_examined` additionnait des fichiers
sondes **et** des correspondances trouvees. Il affichait `0` alors que 20 fichiers avaient
ete lus.

### Les deux decors

| Decor | Ce qu'il represente |
|-------|---------------------|
| `specifique/` **plat** | un specifique partenaire : des `alg_*.dhsp` et des surcharges `gt*u.dhsp` a la racine, **aucun** sous-repertoire de domaine. C'est le cas ou le cadrage echoue -- et celui ou le grep est le **seul** outil, puisque le graphe `diva-mcp` ne couvre que le standard |
| `standard/` | l'arborescence du standard livre : `Achat-Vente/source/Dav/...`. Le cadrage doit y fonctionner |

### Ce que les cas verifient

- **#327** : les mots cherches, les mots **ecartes** (nommes), et le drapeau
  `couverture_keywords_complete` -- vrai quand tout a ete cherche, faux sinon.
- **#328** : `AB` ne ramene plus rien sur un decor qui contient `MABSENT` et `TABLEAU`,
  **et** un mot entier legitime est toujours trouve (la correction ne casse pas la
  recherche).
- **#329** : repli signale avec sa raison sur l'arborescence plate ; **pas** de repli en
  mode `auto` sur le standard ; `--domain-scope GT_` resout desormais le prefixe ; et si
  le prefixe est connu mais que ses repertoires manquent, la raison le dit precisement.
- **version** : `--version` rapportee dans `scope.version_verifiee`, statuts **neutres**
  (`NOUVEAU`, sans numero), et `null` sans l'option -- **rien n'est affirme**.
- **compteurs** : `files_examined` et `matches_total` sont deux champs distincts.

> **Pourquoi les statuts ne portent pas la version** : le consommateur aval
> (`build_facts.py`) teste `X.12` **avant** `CONFIRME` dans sa normalisation. Un statut
> `CONFIRME X.12` serait donc retrograde en simple piste advisory `X.12` et **la
> confirmation sur disque serait perdue**. Verifie par execution. Ne pas remettre la
> version dans le statut.

**Verification de discrimination** : jouee contre la version anterieure des scripts, la
suite tombe sur **15 cas** sur 18 -- les 3 gardes restants sont ceux qui doivent passer
dans les deux versions.

---

## Note sur `_structural_parser.py`

Le correctif #332 (le parseur capturait le **type de retour** au lieu du nom pour
`Public function <type> <nom>`) vit dans le module **canonique** de `linting-diva-code`,
re-vendore a l'identique ici et dans `reviewing-erp-doc`. Ses tests sont dans
`linting-diva-code/tests/`. Mesure du correctif : sur ~1200 fichiers du standard,
**18 284 noms de fonctions faux sur 18 320 -> 0**.
