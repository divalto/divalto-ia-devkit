# Modules ERP Divalto X.13 -- resume

Fragment local au skill (autonome, distribuable). Utilise au CP1 par Claude
pour cadrer le module cible avec le collaborateur (prefixe, dictionnaire,
chemin source). Ne pas confondre avec les chemins absolus sur le poste :
les chemins ci-dessous sont relatifs a `{CHEMIN_ERP_STANDARD}`.

## 16 modules standards

| Module              | Chemin source relatif                | Dictionnaire              | Prefixe code |
|---------------------|--------------------------------------|---------------------------|--------------|
| Achat-Vente         | `Achat-Vente/source/`                | `gtfdd.dhsd` / `rtlfdd.dhsd` / `ggfdd.dhsd` / `wmsfdd.dhsd` | GT_ / RT_ / GG_ / WMS_ |
| Framework A5        | `A5/source/`                         | `a5dd.dhsd`               | A5 |
| Comptabilite        | `Comptabilite/source/`               | `ccfdd.dhsd`              | CC_ |
| Reglements          | `Reglement/source/`                  | `rcfdd.dhsd`              | RC_ |
| Paie                | `Paie/source/`                       | `ppfdd.dhsd`              | PP_ |
| Affaires            | `Affaires/source/`                   | `gafdd.dhsd`              | GA_ |
| Controle de gestion | `Controle/source/`                   | `cofdd.dhsd`              | CO_ |
| Outils              | `Outils/source/`                     | --                        | -- |
| GRM                 | `Gestion Ressources Materiels/source/` | `gmfdd.dhsd`            | GM_ |
| Point de vente      | `Point de vente/source/`             | `pvfdd.dhsd`              | PV_ |
| Qualite             | `Qualite/source/`                    | `qufdd.dhsd`              | QU_ |
| Relation-Tiers      | `Relation-Tiers/source/`             | `grfdd.dhsd`              | GR_ |
| Documentation       | `Documentation/source/`              | `dofdd.dhsd`              | DO_ |
| Processus           | `Processus/source/`                  | `spfdd.dhsd`              | SP_ |
| Mobilite            | `Mobilite/source/`                   | `mofdd.dhsd`              | MO_ |
| Decisionnel         | `Decisionnel/source/`                | --                        | -- |

## Sous-modules Achat-Vente

Achat-Vente est subdivise en 5 sous-modules qui partagent plusieurs
dictionnaires :

| Sous-module | Chemin relatif                   | Dictionnaire       | Prefixe | Domaine fonctionnel    |
|-------------|----------------------------------|--------------------|---------|------------------------|
| Dav         | `Achat-Vente/source/Dav/`        | `gtfdd.dhsd`       | GT_     | Gestion commerciale    |
| Retail      | `Achat-Vente/source/Retail/`     | `rtlfdd.dhsd`      | RT_     | Retail / Point de vente|
| Prod        | `Achat-Vente/source/Prod/`       | `ggfdd.dhsd`       | GG_     | Production             |
| Atelier     | `Achat-Vente/source/Atelier/`    | `ggfdd.dhsd`       | GG_     | Atelier / Fabrication  |
| Wms         | `Achat-Vente/source/Wms/`        | `wmsfdd.dhsd`      | WMS_    | Gestion de stock       |

## Prefixes de base par dictionnaire

| Dictionnaire    | Prefixe base SQL | Tables principales (exemples)              |
|-----------------|------------------|--------------------------------------------|
| `a5dd.dhsd`     | `a5f`            | MZ, XQ, XT, MUSER, A5ChkData               |
| `ccfdd.dhsd`    | `ccf`            | C3, C4, C5                                 |
| `gtfdd.dhsd`    | `gtf`            | SOC, CLI, ART, ETS, T006, FOU, VRP, PRO    |
| `rtlfdd.dhsd`   | `rtl`            | RtlTypRglt, RtlFamRglt, RtlMagasin         |
| `grfdd.dhsd`    | `grf`            | GR1 (tiers mere)                           |

## Usage au CP1

Quand le collaborateur donne un nom de module (ex: `DAV`), le skill peut
consulter ce fragment pour :
- Retrouver le chemin source relatif a `{CHEMIN_ERP_STANDARD}`
- Retrouver le nom du dictionnaire `.dhsd` a parser
- Retrouver le prefixe de code (GT_, CC_...) utilise dans la convention
  de nommage des programmes (cf. `generating-zoom-sql/reference/` pour
  la convention canonique de nommage)
