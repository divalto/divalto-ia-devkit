# Pattern "FK par zoom standard" -- Fragment de reference

> Source canonique : `docs/FK-ZOOM-BINDING.md` (workspace) + `docs/ZOOMS-STANDARDS-CATALOGUE.md` tables B et C. Ce fragment donne le strict minimum pour appliquer le pattern.

## Sommaire

1. Pattern 3 couches
2. Cardinalite 1:1 (la seule supportee en V1)
3. Mapping cible -> module (table B resumee)
4. Taxonomie suffixes predicteurs (table C resumee)
5. Naming des callbacks
6. Liens anti-patterns et regles linter

## 1. Pattern 3 couches

Une foreign key "par zoom standard" se declare via 3 couches solidaires :

| Couche | Fichier | Contenu |
|--------|---------|---------|
| **Module Check** | `.dhsp` (objet metier) | `Module "Gttmchk<cible>.dhop"` + `Check_<SRC>_Field_<CHAMP>` + `Check_<SRC>_Field_<CHAMP>_Lib` |
| **Masque structurel** | `.dhsf` section `[champ]` | `[param_saisie] table_associee=oui` + `[touches] f8=<numero_zoom>` + `[traitements] diva_apres="Champ_<CHAMP>_<id>_Ap"` + `[boutons] "zoom"` |
| **Masque callback** | `.dhsf` section `[diva]` | procedure `Champ_<CHAMP>_<id>_Ap` qui appelle `Check_<SRC>_Field_<CHAMP>_Lib` |

Les 3 couches doivent exister ensemble. Une couche orpheline = bug silencieux (zoom non declenche, ou symbole non resolu a la compilation).

## 2. Cardinalite 1:1 (V1)

Un champ source pointe vers une cle unique dans une table cible. 1 455 cas sur 2 408 procedures `Check_*_Field_*` dans X.13 (60 %).

Format CLI : `--fk <CHAMP>:<TARGET>[:<ZOOM>]`.
Ex : `--fk RacPays:T013:9053` (champ RacPays -> table pays T013 via zoom 9053).

Cardinalites **non supportees en V1** (chantiers futurs) :
- **Composee** : N champs -> 1 cle composee. 318 cas X.13.
- **Filtre borne** : 2 champs d/f -> meme cible (plage). 982 paires X.13.
- **Polymorphique** : 1 champ -> N cibles via `Zoom_Call(C_ZOOM_*)` dynamique. 610 cas X.13.

## 3. Mapping cible -> module (table B resumee)

349 cibles FK distinctes en X.13. Les plus courantes :

| Cible | Module Check | Domaine |
|-------|--------------|---------|
| `T013` | `Gttmchkt013.dhop` | Pays |
| `T007` | `Gttmchkt007.dhop` | Devises |
| `T017` | `Gttmchkt017.dhop` | Depots |
| `T014` | `Gttmchkt014.dhop` | Zones geographiques |
| `T027` | `Gttmchkt027.dhop` | Conditions de reglement |

Pattern general : `Gttmchk<cible-en-minuscules>.dhop` (~280 / 349 cibles suivent ce pattern).

Les fonctions exposees par le module cible : `Find_<CIBLE>(cle)`, `Find_<CIBLE>_Lib(cle)`, `Check_<CIBLE>_Exists(cle)`. Voir `docs/ZOOMS-STANDARDS-CATALOGUE.md` table B pour le catalogue complet (utilisation build-time uniquement).

## 4. Taxonomie des suffixes predicteurs (table C resumee)

40+ suffixes de champ sont predictifs a >= 90 % du type de cible FK. Les plus fiables :

| Suffixe champ | Cible pressentie | Fiabilite X.13 | Zoom |
|---------------|------------------|----------------|------|
| `Pay` / `Pays` | T013 (Pays) | 98 % | 9053 |
| `Dev` | T007 (Devises) | 96 % | 9047 |
| `Depo` | T017 (Depots) | 95 % | 9057 |
| `Cpt` | T027 (Conditions de reglement) | 94 % | 9067 |
| `TiCod` | Tiers (partage gtfdd) | 92 % | 9000 |
| `Art` | Article | 91 % | 9000 |

Usage : lors de la detection automatique FK (ex: etape CP1bis de `creating-diva-entity`), scanner les suffixes des champs metier pressentis et proposer au developpeur les FK candidates. **Toujours valider** avec le developpeur -- la fiabilite n'est pas 100 %.

## 5. Naming des callbacks `Champ_<CHAMP>_<id>_Ap`

Dans `[diva]` du masque, chaque callback FK est nomme :

```
Champ_<nom_champ_lower>_<id>_Ap
```

Ou `<id>` est un **compteur sequentiel global** alloue parmi les procedures `Champ_*_Ap` du fichier (pas l'id widget DOM). 17 740 procedures `Champ_*_Ap` recensees dans les masques X.13.

Corps type :

```diva
Procedure Champ_RacPays_1_Ap()
  Check_RACECHIEN_Field_RacPays_Lib(ent.RacPays)
EndP
```

## 6. Liens anti-patterns linter

| Anti-pattern | Cible | Automatise ? |
|--------------|-------|--------------|
| **Z14** | Champ avec suffixe FK predicteur mais aucune procedure `Check_<SRC>_Field_<Champ>` | Partiellement (suffixes catalogues) |
| **Z15** | Procedure `Check_<SRC>_Field_<Champ>` sans import `Module "Gttmchk<cible>.dhop"` (orpheline) | Oui (regex + cross-file) |

Le skill `linting-diva-code` implemente ces regles (FK-06). Voir la description des anti-patterns dans son `reference/rules-architecture.md`.

## 7. Voir aussi (dans ce skill)

- `scripts/dhsp_add_fk.py` : application de la couche 1 (Module Check)
- Le skill `manipulating-dhsf-screens` fournit `dhsf_add_fk.py` pour les couches 2 + 3 (masque structurel + callback).
- Le skill `generating-objet-metier` integre ce pattern via son flag `--fk` (mode creation).
