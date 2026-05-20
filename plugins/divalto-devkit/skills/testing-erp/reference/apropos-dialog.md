# Dialog F1 "A propos du Zoom"

## Contenu

- Role
- Format de la dialog
- Exemples captures
- Workflow Playwright
- Mapping vers les tokens de generation
- Diagnostic en cas d'ecart

---


> Reference : `docs/NAVIGATION-ERP.md` section 3.4

## Role

Dialog accessible par **F1** (ou menu Aide > "A propos du Zoom") dans un zoom ouvert.
Affiche les metadonnees techniques du zoom reellement charge : RecordSQL, Table SQL,
Masque, Module, Base, Power Search.

Sert de **checkpoint de coherence technique** (CP3) apres creation d'entite :
comparer les valeurs observees avec les valeurs attendues cote generation.

---

## Format de la dialog

Texte fixe (standardise sur tous les zooms SQL observes -- Article, Client) :

```
Zoom SQL version 2025 (13/06/2024)
Copyright (C) Divalto 2024

RecordSQL    : <nom du RecordSQL>
ZoomOptimize : Oui/Non
ZoomPaginate : Oui/Non
Base donnees : <nom base SQL>
Table        : <nom table SQL>
Masque       : <fichier .dhof>
Module       : <fichier .dhop>
Imprimante   : <vide ou nom>
Version module : <version ERP>
Numero de tache : <no tache>

Power Search
Dictionnaire : <nom dictionnaire>
Reference    : <nom reference>
```

---

## Exemples captures

### Zoom Article (9000)

```
RecordSQL      : Article
ZoomOptimize   : Oui
ZoomPaginate   : Oui
Base donnees   : BaseXrpX13
Table          : ART
Masque         : gtez000_sql.dhof
Module         : gttz000_sql.dhop
Version module : 10.13 Service Pack b
Numero tache   : 40

Power Search
Dictionnaire   : Dico_Document_DAV
Reference      : Article
```

### Zoom Client (9021)

```
RecordSQL      : Client
ZoomOptimize   : Oui
ZoomPaginate   : Oui
Base donnees   : BaseXrpX13
Table          : CLI
Masque         : GTEZ021_sql.dhof
Module         : GTTZ021_sql.dhop
Version module : 10.13 Service Pack b
Numero tache   : 40

Power Search
Dictionnaire   : Dico_Document_DAV
Reference      : Client
```

---

## Workflow Playwright

1. S'assurer d'etre sur l'onglet du zoom ouvert (pas l'onglet ERP principal).
2. Appuyer sur **F1** : `browser_press_key` avec `F1`.
   - Alternative : `browser_click` sur le menu Aide puis "A propos du Zoom".
3. Capturer la dialog :
   - `browser_take_screenshot` pour conserver une trace visuelle (recommande pour CP3).
   - `browser_snapshot` pour extraire les valeurs structurellement (si snapshot disponible).
4. Extraire les 12 champs listes ci-dessus.
5. Fermer la dialog : `browser_click` sur le bouton "OK".

---

## Mapping vers les tokens de generation

Reference : `naming-diva-entities` fournit les tokens utilises a la generation.

| Champ F1 | Source attendue | Comment verifier |
|----------|----------------|------------------|
| **RecordSQL** | Token `recordsql` | Doit egaler le nom d'entite -- ex `Livre` |
| **Table** | Parametre `--table` | Nom exact de la table SQL -- ex `LIVRE` |
| **Masque** | Token `fichier_masque` + `.dhof` | Fichier compile (.dhsf -> .dhof) |
| **Module** | Token `fichier_zoom` + `.dhop` | Fichier compile (.dhsp -> .dhop) |
| **Base donnees** | Environnement dev standard | `BaseXrpX13` en developpement |
| **Power Search Reference** | Token `entite` | Nom d'entite -- ex `Livre`. Aucune action requise a la generation : Power Search est un moteur de recherche integre de l'ERP |

`Power Search` n'a pas a etre genere par les skills. C'est un mecanisme
de recherche ERP qui fonctionne independamment. Ce champ sert uniquement de controle.

---

## Diagnostic en cas d'ecart

| Ecart observe | Cause probable | Action |
|---------------|----------------|--------|
| RecordSQL differe | Mauvais nom calcule ou mchk errone | Relire le mchk genere, verifier le token |
| Table differe | Dictionnaire .dhsd non synchronise ou mauvais --table | Relancer synchro SQL, verifier les sources |
| Masque .dhof non trouve | manipulating-dhsf-screens n'a pas produit au bon emplacement, ou compilation echouee | Verifier la sortie .dhof, relancer compilation |
| Module .dhop non trouve | .dhsp absent du sous-projet, ou echec compilation | Verifier les sources dans le .dhps, relancer compilation |
| Base != BaseXrpX13 | Dossier incorrect ou session pointee ailleurs | Verifier le profil / dossier a la connexion |
| Version module ancienne | L'ERP n'a pas ete relance apres recompilation | **Fermer l'ERP (`browser_close`) et reconnecter** |

> **Version module ancienne** est un piege classique : les objets compiles (.dhof/.dhop)
> sont **charges au demarrage de la session ERP**. Apres une recompilation, si on ne
> ferme pas / reouvre pas l'ERP, F1 continue d'afficher l'ancienne version.
