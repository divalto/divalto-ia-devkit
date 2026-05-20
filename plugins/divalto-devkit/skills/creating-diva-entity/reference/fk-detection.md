# Detection et validation des foreign keys (FK) -- Etape 1bis

> Fragment de reference pour l'etape 1bis de `creating-diva-entity`. Voir le skill [`binding-zoom-to-field`](../../binding-zoom-to-field/SKILL.md) et son `reference/fk-pattern.md` pour le pattern 3 couches complet.

## Objectif

Avant de generer les sources (etapes 2-5bis), l'orchestrateur detecte les **foreign keys candidates** parmi les champs metier pressentis, pour les propager aux generateurs via `--fk`.

## Sous-etapes

**Etape 1bis.a -- Collecte des noms de champs pressentis** : demander a l'utilisateur une premiere liste de noms PascalCase pour les champs metier, meme partielle. Exemples : `RacPays`, `RacDev`, `RacDepo`, `RacRefArt`.

**Etape 1bis.b -- Appel `suggest_nature.py` pour chaque champ** pour extraire `fk_target` :

```
py .claude/skills/managing-diva-dictionaries/scripts/suggest_nature.py \
    --name "{nom_champ}"
# Retourne : {nature, fk_target: {target, kind, zoom_num, module_dhop, find_fn, get_lib_fn, confidence} | null, fk_note, ...}
```

**Etape 1bis.c -- Classification des FK** :
- `fk_target` non null **ET** `fk_target.confidence >= 0.90` -> **proposition automatique** a l'utilisateur (ex : `RacPays -> T013 (zoom 9053, 100% fiable)`)
- `fk_target` null **ET** `fk_note` present -> **ambiguite signalee** (ex : `RacRefArt -> suffixe Ref ambigu (ART ? 43%), demander au collaborateur`)
- `fk_target` null **ET** `fk_note` null -> pas de FK deduite (champ metier simple)

**Etape 1bis.d -- Collaborateur valide / enrichit la liste FK** : il peut aussi declarer manuellement une FK qui n'a pas ete detectee (ex : un champ `RacElveur` qui doit pointer vers `ELEVEUR` sans que le suffixe soit reconnu).

## Checkpoint CP1bis -- Foreign keys detectees

Presenter au collaborateur :
- Les FK detectees automatiquement (fiabilite >= 90 %) avec format `CHAMP -> CIBLE (zoom N, X%)`
- Les FK ambigues a clarifier (fiabilite < 90 % ou suffixes `Ref`, `Cod`, `Lib`)
- Les champs metier non-FK (simples)
- L'option d'ajouter manuellement des FK non detectees

Attendre validation explicite de la liste finale de FK avant de lancer les generations.

## Propagation aux etapes suivantes

La liste des FK validees est memorisee pour etre propagee :
- Etape 3 (`generating-objet-metier`) : parametre `--fk CHAMP:TARGET[:ZOOM]` repetable (cf. FK-02)
- Etape 5ter (`dhsf_add_fk.py`) : memes `--fk` pour enrichir le masque (cf. FK-03)

Si aucune FK n'est detectee ni declaree, passer directement a l'etape 2 (generation sans FK -- retrocompat pre-FK-02).
