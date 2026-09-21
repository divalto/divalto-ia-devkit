# Prefixes de domaine -- copie locale pour E4

Copie locale de la table des prefixes de domaine, utilisee par l'heuristique **H5**
de `detect_doc_contradictions.py`. La regle de vendoring du devkit interdit a un
script d'aller lire la page d'un autre skill : la table est donc dupliquee ici.

**Autorite** : la version qui fait foi vit dans le skill `naming-diva-entities`,
page `reference/domain-prefixes.md`, avec ses colonnes completes (prefixe de
surcharge, prefixe DB, dictionnaire, module ficsql). Si les deux divergent, c'est
celle-la qui a raison.

H5 compare le prefixe du **nom de fichier** cite dans le livrable a la colonne
« Prefixe module » : `gttcli.dhop` doit commencer par `gtt` pour une entite dont le
domaine declare est `DAV`.

| Domaine | Prefixe code | Prefixe module |
|---------|--------------|----------------|
| DAV | `GT_` | `gtt` |
| Retail | `RT_` | `rtt` |
| Production | `GG_` | `ggt` |
| Atelier | `GG_` | `ggt` |
| Comptabilite | `CC_` | `cct` |
| Affaires | `GA_` | `gat` |
| Reglements | `RC_` | `rct` |
| Relation-Tiers | `GR_` | `grt` |
| Paie | `PP_` | `ppt` |
| Point de vente | `PV_` | `pvt` |
| Qualite | `QU_` | `qut` |
| Controle | `CO_` | `cot` |
| Processus | `SP_` | `spt` |
| Mobilite | `MO_` | `mot` |
| GRM | `GM_` | `gmt` |

> **Portee de H5.** La colonne « Domaine » melange des codes (`DAV`, `GRM`) et des
> noms de module (`Retail`, `Comptabilite`) -- c'est ainsi dans la page d'origine.
> H5 ne se declenche que si le champ `module` du livrable correspond a une valeur de
> cette colonne. Sinon elle se tait, ce qui est le comportement voulu : mieux vaut
> une detection muette qu'un faux positif.

