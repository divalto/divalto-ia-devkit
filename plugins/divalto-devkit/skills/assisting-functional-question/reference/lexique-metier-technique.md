# Lexique metier -> technique DIVA / ERP Divalto Infinity

## Sommaire

- Principe
- Parametrage dossier (SOC.EntCodN, Soc_Gerer_*)
- Entites et tables (Client, Tiers, Etablissement, Dossier)
- Zooms SQL (grez002, a5rsrub, etc.)
- Modules Check (creation / controle / init des tiers)
- Reglement / Comptabilite
- DAV (devis / commande / facture / contremarque)
- Contexte utilisateur (MZ.*, Give_ETS, fourchettes)
- Symptomes courants et pistes
- Comment enrichir ce lexique

---

Traduction des termes conversationnels (ceux qu'emploient les collaborateurs
en chat) vers les symboles techniques a grep dans X.13. Ce lexique alimente
l'etape 2 du skill `assisting-functional-question`.

---

## Principe

Le collaborateur dit ce qu'il **voit** ou ce qu'il **fait** dans l'ERP
("j'active l'option", "je cree un client", "le zoom...").
Claude doit traduire chaque formulation en symboles DIVA grep-ables pour
localiser le code source responsable.

Une entree du lexique = un concept (gauche) + un ou plusieurs symboles techniques
(droite) + un fichier de reference ou le grep commence.

---

## Parametrage dossier

| Concept conversationnel | Symboles techniques | Commentaire |
|-------------------------|---------------------|-------------|
| "option dans le dossier" | `SOC.EntCodN(N) = 2` | Codage standard DIVA : EntCodN est un tableau de flags booleans (1 = non, 2 = oui) sur la table SOC |
| "confidentialite des enregistrements" | `SOC.ConfEnr(N) = Oui` | Gestion de la confidentialite, active = Oui |
| "gestion des etablissements" | `Soc_Gerer_Etablissements` -> `SOC.EntCodN(22) = 2` | Prerequis de toutes les sous-options par etablissement |
| "gestion des tiers par etablissement" | `Soc_Gerer_Tiers_Etablissement` -> `SOC.EntCodN(24) = 2` | Prerequis : `EntCodN(22) = 2` |
| "gestion des commerciaux par etablissement" | `Soc_Gerer_Commerciaux_InterEtablissement` -> `SOC.EntCodN(48) = 2` | Prerequis : `EntCodN(22) = 2` |
| "gestion des autres tiers par etablissement" | `Soc_Gerer_AutreTiers_InterEtablissement` -> `SOC.EntCodN(49) = 2` | Prerequis : `EntCodN(22) = 2` |
| "etablissement gere comme une societe (compta)" | `SOC.EntCodN(97) = 2` | Paramétrage comptable |
| "inter-agences" | `Soc_Gerer_InterAgence` | Voir `cctm000.dhsp:1340` |

---

## Entites et tables

| Concept | Table SQL | DObj DIVA | Commentaire |
|---------|-----------|-----------|-------------|
| "client" | `CLIENT` | `CLI`, `Client` (RecordSql) | Type de tiers Ce1='3' |
| "prospect" | `PROSPECT` | `PRO` | Ce1='2' |
| "fournisseur" | `FOURNISSEUR` | `FOU` | Ce1='4' |
| "commercial" / "VRP" / "representant" | `TIERS` avec Ce1='5' | `VRP` | |
| "autre tiers" | `TIERS` avec Ce1='6' | `TIA` | |
| "individu" / "contact" | `TIERS` avec Ce1='7' | | Pas de gestion par etab |
| "etablissement" | `ETS` | `ETS`, `Etab`, `Etab_loc` | Table maitre des etablissements |
| "societe" / "dossier" | `SOC` | `SOC`, `Soc` | Table maitre du parametrage dossier |
| "contexte utilisateur" | n/a | `MZ.Dos`, `MZ.Etb`, `MZ.DosCpt` | Globales systemes |

---

## Zooms SQL

| Concept | Fichier X.13 | Symboles |
|---------|--------------|----------|
| "zoom client" / "zoom tiers" | `Relation-Tiers/source/grez002_sql.dhsf` + `grtz002_sql.dhsp` | `ZoomDebut`, `Check_Condition_Tiers` |
| "rubriques zoom partagees A5" | `A5/source/a5rsrub.dhsq` | `CLI_Equal_Etb`, `CLI_Between_Etb`, `CLI_Like_Etb`, equivalents pour Fournisseur/Prospect |
| "zoom etablissement" | `Relation-Tiers/source/grez185_sql.dhsf` | |
| "zoom famille de reglement" | `Reglement/source/rcez*.dhsf` | |
| "zoom inter-societe" | `Achat-Vente/source/Dav/gtez021_sql.dhsf` | |

---

## Modules Check (creation / controle / init)

| Concept | Fichier X.13 | Symboles |
|---------|--------------|----------|
| "creer un client" | `Achat-Vente/source/Dav/gttmchkcli.dhsp` | `Init_Client_Record`, `Check_Client_Field_*` |
| "creer un prospect" | `Achat-Vente/source/Dav/gttmchkpro.dhsp` | `Init_Pro_Record`, `Check_Pro_Field_*` |
| "creer un fournisseur" | `Achat-Vente/source/Dav/gttmchkfou.dhsp` | `Init_Fou_Record`, `Check_Fou_Field_*` |
| "creer un etablissement" | `Achat-Vente/source/Dav/gttmchkets.dhsp` | `Init_Ets_Record` |
| "creer un commercial" | `Achat-Vente/source/Dav/gttmchkvrp.dhsp` | `Init_Vrp_Record` |
| "creer un autre tiers" | `Achat-Vente/source/Dav/gttmchktia.dhsp` | `Init_Tia_Record` |

---

## Reglement / Comptabilite

| Concept | Fichier X.13 | Symboles |
|---------|--------------|----------|
| "reglement" / "encaissement" | `Reglement/source/rctm000.dhsp`, `rcpm000.dhsp` | |
| "famille de reglement" | `Reglement/source/rctmrecouvrement.dhsp` | `RCTFAMREG` (table) |
| "ecriture comptable" | `Comptabilite/source/cctmecr.dhsp` | `EnteteDHb`, `DHBENT` |
| "lettrage" | `Comptabilite/source/cctmletr.dhsp` | |

---

## DAV (devis / commande / facture)

| Concept | Fichier X.13 | Symboles |
|---------|--------------|----------|
| "entete piece" | `Achat-Vente/source/Dav/gttmdhb000.dhsp` | `DHBENT`, `DHBChamp(*)`, `DHB_CHAMP_ETB` |
| "contremarque" | `Achat-Vente/source/Dav/gtppctm*.dhsp` | `Supprimer_LienContremarque`, `ActionERP_Contremarque_*` |
| "livraison" | `Achat-Vente/source/Dav/gttmliv*.dhsp` | |
| "tarif" | `Achat-Vente/source/Dav/gttmtar*.dhsp` | |

---

## Contexte utilisateur

| Concept | Symbole | Fichier de reference |
|---------|---------|----------------------|
| "l'utilisateur connecte" | `System.User`, `Utilisateur` | `Relation-Tiers/source/divaltouserdrt_sql.dhsp` |
| "dossier courant" | `MZ.Dos` | Initialise dans `DOS_1_Ap` |
| "etablissement courant" | `MZ.Etb` | Initialise dans `DOS_1_Ap` via `Find_Ets_Premier` |
| "dossier comptable courant" | `MZ.DosCpt` | Initialise dans `DOS_1_Ap` |
| "commercial associe a l'utilisateur" | `Util.ReprUser`, `Commercial.SalCod` | |
| "autorisation sur etablissement" | `Give_ETS(Etab, code_etb)`, `G3_Protection(Conf)` | `Achat-Vente/source/Dav/gttmchkets.dhsp` |
| "fourchettes de tiers par etab" | `ETS.Tiers1(1..3)`, `ETS.Tiers2(1..3)` | Charges dans `grtz002_sql.dhsp:247` |

---

## Symptomes courants et pistes

| Symptome conversationnel | Pistes immediates |
|--------------------------|-------------------|
| "je ne vois plus les X dans le zoom" | Filtrage par contexte utilisateur (`MZ.Etb`, `MZ.Dos`), reprise des donnees existantes |
| "X ne fonctionne plus comme avant, j'ai change une option" | Prerequis de l'option (chaine `SOC.EntCodN(N)` + `ConfEnr(N)`) |
| "X ne s'enregistre pas" | Module check : la validation rejette silencieusement (`Check_*_Field_*` avec `Message_*`) |
| "impossible de creer Y" | Module check `Init_Y_Record` + conditions `Field_*` |
| "l'option est activee mais rien ne change" | Restart de tache requis ? Recompilation ? Ordre d'init dans `DOS_1_Ap` ? |
| "acces refuse / confidentialite" | `SOC.ConfEnr(N)`, `G3_Protection`, droits utilisateur |

---

## Comment enrichir ce lexique

Apres chaque nouveau cas UC-110 traite avec succes :
1. Noter le **concept conversationnel** utilise par le collaborateur
2. Noter le **symbole technique** qui a permis de debloquer
3. Ajouter une entree dans la table appropriee ci-dessus
4. Si le concept n'entre dans aucune table existante, creer une nouvelle section

Objectif : couvrir les 80% des questions recurrentes en < 50 concepts.
