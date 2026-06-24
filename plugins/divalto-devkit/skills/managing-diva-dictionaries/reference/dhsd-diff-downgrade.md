# Diff de dictionnaire et arbitrage de downgrade -- methodologie

> **Statut** : methodologie documentee, **sans outil dedie** dans cette version
> (le diff structurel 3-voies est un chantier separe -- SC-031). Cette page sert
> de garde-fou : tout diff de `.dhsd`, manuel ou outille, DOIT respecter les
> regles ci-dessous, sous peine de conclusions fausses (cas reels R-026, R-027).

## Contenu

- Pourquoi un diff de dictionnaire est piegeux
- Regle 1 -- couvrir les 3 couches (CHAMP / CHAMPS / CHAMPL)
- Regle 2 -- arbitrage downgrade en 3 voies (CUSTOM / ROLLBACK / GEL)
- Lien avec `modify_field_nature.py`

---

## Pourquoi un diff de dictionnaire est piegeux

Comparer deux `.dhsd` (deux versions, ou un downgrade vs son standard) sert a
decider quoi conserver, rebaser ou supprimer lors d'une migration ou d'un
changement de Service Pack. Deux pieges recurrents rendent une analyse
automatique naive **fausse** :

1. ne regarder qu'une seule couche du dictionnaire (R-027) ;
2. comparer le downgrade a une seule version de reference (R-026).

---

## Regle 1 -- couvrir les 3 couches (R-027)

Un `.dhsd` porte les customisations sur **trois** couches distinctes. Un diff
qui n'en regarde qu'une est **aveugle** au reste :

| Couche | Bloc | Contenu | Risque si ignoree |
|--------|------|---------|-------------------|
| Globale | `[CHAMP]` | Definition des champs (Nature, flags) | rate les champs ajoutes/modifies globalement |
| Table physique | `[TABLE]` / `[CHAMPS]` | Placement des champs dans les tables physiques | -- (couche habituellement regardee) |
| **Record relationnel** | **`[CHAMPL]`** | Records logiques utilises par les **RecordSQL**, vues, selections | **angle mort** : rate les champs custom references par les WHERE |

**Cas reel (R-027)** : conclusion automatique « ce downgrade est identique au SP
d'origine, gel pur supprimable » -- **FAUSSE**. Deux champs custom etaient en plus
dans le downgrade, mais **uniquement sur un record relationnel `[CHAMPL]`** (ex. un
record de selection a 147 champs en downgrade vs 145 cote standard) -- couche ignoree
par un parser `[TABLE]`/`[CHAMPS]`. Ces champs sont exactement ceux references par
les clauses WHERE des RecordSQL associes. Le downgrade est donc une **vraie
surcharge, NON supprimable**.

> **C'est la couche `[CHAMPL]` qui est la plus pertinente pour l'arbitrage
> RecordSQL** -- un RecordSQL se compile contre un record relationnel.

**Parsing correct** : ne PAS utiliser une regex englobante `\[CHAMPR\](.*?)\[/CHAMPR\]`
-- un `[CHAMPR]` peut envelopper **plusieurs** records. Parser chaque paire
`nom=<NomRecord>` + `[CHAMPL]...[/CHAMPL]` individuellement. Distinguer aussi les
overlays `u` (`[CHAMPR]`/`[TABLEU]`, purement **additifs**) des dictionnaires
complets (qui peuvent porter des **rollbacks**, cf. regle 2).

---

## Regle 2 -- arbitrage downgrade en 3 voies (R-026)

Pour decider si un downgrade de dictionnaire a encore lieu d'etre au passage d'un
Service Pack (ex. 217E -> 217F), comparer le downgrade au **seul** standard cible
(217F) est insuffisant : on voit les ecarts, **pas leur nature**. Il faut une
comparaison **3-voies** :

- (a) downgrade **vs** standard d'**ORIGINE** (217E)
- (b) downgrade **vs** standard **CIBLE** (217F)

La position de chaque ecart dans les 3 versions le classe :

| Classe | Condition | Signification | Action |
|--------|-----------|---------------|--------|
| **CUSTOM** | present downgrade, absent 217E **ET** 217F | vraie surcharge distributeur | **conserver + rebaser** sur la cible |
| **ROLLBACK** | present 217E/217F, absent downgrade (retire volontairement) | le downgrade annule une evolution standard | decision : maintenir le rollback ou adopter le standard |
| **GEL DE BASELINE** | downgrade **==** 217E a l'identique, aucun custom | le downgrade ne fait que **bloquer** les evolutions du SP | suppression = adoption du standard cible (**decision fonctionnelle**) |

**Le gel pur est le signal le plus important** : un downgrade dont la suppression
n'est qu'une decision d'adoption du standard -- souvent un reliquat. **Mais** ne
conclure « gel pur » qu'apres avoir verifie les **3 couches** (regle 1) -- c'est
precisement la combinaison des deux regles qui a manque dans le cas CCFDD.

**Cas reels (R-026)** :
- un downgrade == SP d'origine exactement cote `[CHAMPS]` (apparence de gel pur,
  bloquant des evolutions reglementaires du SP cible) -- mais l'analyse 3 couches a
  revele un custom sur `[CHAMPL]` -> finalement **CUSTOM**, non supprimable ;
- un autre downgrade == SP d'origine + quelques customs (une table custom + plusieurs
  champs custom) -> **conserver + rebaser**.

---

## Lien avec `modify_field_nature.py`

Le script `modify_field_nature.py` (modification de Nature + recalcul des
positions) re-propage les couches **physiques** `[TABLE]/[CHAMPS]` et
`[INDEX]/[CHAMPS]`. Il **ne touche pas** a la couche `[CHAMPL]` : si le champ
modifie figure dans un record relationnel, le script emet un **warning**
(`champ present dans N record(s) [CHAMPL]`) et laisse la re-propagation
relationnelle a la charge de l'integrateur. C'est l'application directe de la
regle 1 : la couche `[CHAMPL]` reste un point de vigilance manuel tant que
l'outillage de diff/arbitrage 3-voies (SC-031) n'existe pas.

---

## Voir aussi

Cette page couvre l'arbitrage au niveau **dictionnaire** (structure `.dhsd`, 3 couches).
Pour le processus de **migration de pack** dans son ensemble -- arbitrage des **sources**
(un SP ne livre qu'un sous-ensemble des sources), **ordre de compilation** (piege overWrite,
deux passes) et **verification post-migration** des surcharges -- voir le skill
[`migrating-erp-downgrade`](../../migrating-erp-downgrade/SKILL.md).
