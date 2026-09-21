---
name: migrating-erp-downgrade
description: A utiliser lors de la migration du specifique d'un client d'une version ERP Divalto a une autre (rebase sur un nouveau Service Pack / version X.N), ou pour arbitrer ce qu'un downgrade conserve, rebase ou abandonne | Guide la migration de pack : ordre de compilation (bases standard d'abord, surcharges overWrite ensuite -- recompiler un standard apres sa surcharge efface les procedures fusionnees), contournement deux passes quand des dependances inter-projets ne sont pas declarees dans les .dhps, arbitrage des sources downgrade (un SP ne livre qu'un sous-ensemble des sources : croiser diff textuel, existence de l'objet compile et couplage au dictionnaire downgrade -- jamais 'supprimable' sur la seule absence de source standard), verification post-migration de l'integrite des surcharges. Complete les references downgrade de managing-diva-dictionaries et la compilation de managing-diva-projects / compiling-diva-projects.
---

# migrating-erp-downgrade -- Migration / rebase de pack et arbitrage downgrade

## Contenu

- Quand l'utiliser
- Carte du processus de migration
- Ordre de compilation (les deux pieges)
- Verifier l'integrite des surcharges (script)
- Arbitrer les sources d'un downgrade
- Monter une surcharge de version (Service Pack)
- References

---

## Quand l'utiliser

- **Migrer le specifique d'un client** d'une version ERP Divalto a une autre (rebase
  d'un projet downgrade sur un nouveau Service Pack ou une version X.N).
- **Arbitrer un downgrade** : decider, source par source, quoi conserver + rebaser, quoi
  abandonner, au passage d'un SP.
- **Diagnostiquer** un comportement « redevenu standard » apres un rebase (surcharge
  silencieusement effacee).

**Ne pas utiliser** pour :
- **Compiler** un projet (boucle de developpement) -> `compiling-diva-projects`.
- **Creer / structurer** un `.dhpt` / `.dhps` -> `managing-diva-projects`.
- **Modifier / surcharger un dictionnaire** ou diffuser ses 3 couches -> `managing-diva-dictionaries`.
- Preparer une **livraison / quitus** -> skill de livraison dedie.

---

## Carte du processus de migration

```
Nouveau pack standard (SP cible)
   │
   ▼
1. Arbitrer les sources downgrade   ── croiser 3 signaux (diff / objet / couplage)
   │                                   → reference/downgrade-source-arbitration.md
   ▼
2. Rebaser le specifique a conserver  ── (dico : managing-diva-dictionaries)
   │
   ▼
3. Compiler DANS LE BON ORDRE         ── bases standard d'abord, surcharges overWrite ensuite
   │                                   → reference/migration-build-order.md
   ▼
4. Verifier l'integrite des surcharges ── check_overwrite_order.py (date + symbole)
   │
   ▼
Pack migre, surcharges intactes
```

---

## Ordre de compilation -- les deux pieges

Detail complet : [reference/migration-build-order.md](reference/migration-build-order.md).

1. **Piege overWrite** -- `OverWrite <base>.dhop` **fusionne** ses procedures
   dans `<base>.dhop`. Recompiler le standard `<base>` **apres** sa surcharge regenere
   l'objet **propre** et **efface** la surcharge (0 erreur de compil ; bug silencieux au
   runtime). **Regle d'or : bases standard d'abord, surcharges ENSUITE.**
2. **Dependances `.dhps` non declarees** -- en `buildall`, un mauvais ordre
   provoque « Erreur dictionnaire ... recompiler les dictionnaires » sur des `.dhoq`
   standard. **Contournement : 2e passe** en mode `build`. **Correctif durable** :
   declarer les dependances dans les `.dhps` (cf. `managing-diva-projects`).

---

## Verifier l'integrite des surcharges -- `check_overwrite_order.py`

Apres un rebase, controler que chaque surcharge `overWrite` a bien survecu (deux
signaux : **date** de l'objet de base vs overlay, **presence du symbole** de surcharge
dans l'objet de base).

```
# Paire explicite (fiable) -- on fournit les procedures de surcharge a controler
py .claude/skills/migrating-erp-downgrade/scripts/check_overwrite_order.py \
    --base "objets/<base>.dhop" --overlay "objets/<overlay>.dhop" \
    --symbols "<ProcSurcharge1>,<ProcSurcharge2>"

# Scan d'un repertoire (heuristique de nommage u<->t, symboles candidats auto)
py .claude/skills/migrating-erp-downgrade/scripts/check_overwrite_order.py \
    --objets "objets/"
```

Sortie JSON : par paire, `date_inversion` (base plus recent que l'overlay = suspect),
et par symbole `in_base` / `in_overlay` / `lost` (present overlay, absent base = surcharge
effacee). `anomaly=true` et **exit 1** si un signal est leve. Voir
[reference/migration-build-order.md](reference/migration-build-order.md) section
« Verifier l'integrite ».

> **Portee** : le moteur (recherche de symbole dans le `.dhop`, comparaison de dates) est
> fiable. La detection suppose de pointer le script sur les objets reels du projet (bases
> **et** overlays). Le mode `--objets` couple par nommage (heuristique) ; le mode explicite
> est sans ambiguite.

---

## Arbitrer les sources d'un downgrade

Detail complet : [reference/downgrade-source-arbitration.md](reference/downgrade-source-arbitration.md).

Un Service Pack ne livre qu'un **sous-ensemble** des sources standard ; le reste n'existe
qu'en **objet compile**. **Ne jamais conclure « supprimable » sur la seule absence de
source standard.** Croiser **3 signaux** :

1. **diff textuel** (si la source standard est livree) ;
2. **existence de l'objet standard** (indexer aussi `objets/`) -> source absente + objet
   present = standard recompile en contexte downgrade, pas un custom ;
3. **couplage** au dictionnaire / RecordSQL downgrade (raisonner par dependance).

L'arbitrage des RecordSQL se joue sur le record relationnel `[CHAMPL]` du dictionnaire --
voir le diff 3 couches / 3 voies de
[managing-diva-dictionaries](../managing-diva-dictionaries/reference/dhsd-diff-downgrade.md).

---

## Monter une surcharge de version (Service Pack)

Deux actions `xwin7` reportent une surcharge sur un nouveau standard :
`creerprojetsurcharge` (cree la surcharge N depuis N-1) et `mettreAJourMasquesSurcharge`
(reporte les pages du masque d'origine).

**Trois pieges, tous verifiables :**

| Piege | Ce qu'il faut savoir |
|---|---|
| `-Base_N` | designe le standard **CIBLE**, pas celui d'ou l'on part |
| `-Base_Nm1` | **n'existe pas** -- l'inventer par symetrie avec `-OverLoad_Nm1` est le reflexe a bloquer |
| Le resultat | tombe dans `FUpgrade.log`, **pas** sur `-output` ; le code de sortie 1 est cosmetique |

Toujours commencer par **`-AnalyzeOnly`** (n'ecrit rien) avec **`-ClearFUpgrade`** (sinon on
lit le journal du run precedent), et **un run par `.dhpt`** : un projet ne couvre qu'un
sous-ensemble des masques.

Detail des parametres, forme reelle du journal et **niveau de preuve de chaque affirmation**
dans [reference/montee-version-surcharge.md](reference/montee-version-surcharge.md).

---

## References

- [reference/migration-build-order.md](reference/migration-build-order.md) -- ordre overWrite, deux passes, verificateur
- [reference/downgrade-source-arbitration.md](reference/downgrade-source-arbitration.md) -- 3 signaux d'arbitrage source
- Skills lies : `compiling-diva-projects` (compilation), `managing-diva-projects` (structure `.dhpt`/`.dhps`), `managing-diva-dictionaries` (dico, diff 3 couches/3 voies)
