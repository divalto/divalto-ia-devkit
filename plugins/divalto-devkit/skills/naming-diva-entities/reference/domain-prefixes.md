# Prefixes par domaine

Table exhaustive des prefixes utilises pour le nommage des fichiers et instances DIVA.

Source : `docs/CONVENTIONS.md` (section Prefixes domaine complets) et `docs/MODULES-ERP.md` (section 4).

---

## Table des prefixes

| Domaine | Prefixe code | Prefixe module | Prefixe surcharge | Prefixe DB | Domaine 2L | Dictionnaire | Module ficsql |
|---------|-------------|---------------|-------------------|-----------|-----------|-------------|---------------|
| DAV | `GT_` | `gtt` | `gtu` | `gtf` | `gt` | `GTFDD` | `gtpmficsql.dhop` |
| Retail | `RT_` | `rtt` | `rtu` | `rtl` | `rt` | `RTLFDD` | `rtpmficsql.dhop` |
| Production | `GG_` | `ggt` | `ggu` | `ggf` | `gg` | `GGFDD` | `ggpmficsql.dhop` |
| Atelier | `GG_` | `ggt` | `ggu` | `ggf` | `gg` | `GGFDD` | `ggpmficsql.dhop` |
| Comptabilite | `CC_` | `cct` | `ccu` | `ccf` | `cc` | `CCFDD` | `ccpmficsql.dhop` |
| Affaires | `GA_` | `gat` | `gau` | `gaf` | `ga` | `GAFDD` | `gapmficsql.dhop` |
| Reglements | `RC_` | `rct` | `rcu` | `rcf` | `rc` | `RCFDD` | `rcpmficsql.dhop` |
| Relation-Tiers | `GR_` | `grt` | `gru` | `grf` | `gr` | `GRFDD` | `grpmficsql.dhop` |
| Paie | `PP_` | `ppt` | `ppu` | `ppf` | `pp` | `PPFDD` | `pppmficsql.dhop` |
| Point de vente | `PV_` | `pvt` | `pvu` | `pvf` | `pv` | `PVFDD` | `pvpmficsql.dhop` |
| Qualite | `QU_` | `qut` | `quu` | `quf` | `qu` | `QUFDD` | `qupmficsql.dhop` |
| Controle | `CO_` | `cot` | `cou` | `cof` | `co` | `COFDD` | `copmficsql.dhop` |
| Processus | `SP_` | `spt` | `spu` | `spf` | `sp` | `SPFDD` | `sppmficsql.dhop` |
| Mobilite | `MO_` | `mot` | `mou` | `mof` | `mo` | `MOFDD` | `mopmficsql.dhop` |
| GRM | `GM_` | `gmt` | `gmu` | `gmf` | `gm` | `GMFDD` | `gmpmficsql.dhop` |

---

## Conventions de derivation

- **Prefixe module** = `{domaine_2l}t` (ex: `rt` + `t` = `rtt`)
- **Prefixe surcharge** = `{domaine_2l}u` (ex: `rt` + `u` = `rtu`)
- **Prefixe DB** = 3 lettres, souvent `{domaine_2l}` + lettre supplementaire (ex: `rtl`)
- **Dictionnaire** = `{PREFIX_DB_MAJ}FDD` (ex: `RTLFDD`)

**Exceptions notables :**
- Production et Atelier partagent les memes prefixes (`GG_`, `ggt`, `ggf`)
- Le prefixe DB n'est pas toujours `{domaine_2l}` + 1 lettre (ex: DAV = `gtf`, pas `dav`)
