# Classification standard / specifique des chemins

Ce document detaille **R-14** -- le protocole de session-opening qui produit une classification validee des chemins du workspace.

## R-14 -- Classification standard / specifique des chemins : validation utilisateur obligatoire en debut de session

> **Regle de comportement** -- s'execute **au demarrage** de toute session sur un workspace integrateur, juste apres R-1 et R-2 (et apres R-15 si applicable), AVANT toute operation qui depend de cette classification.

- **Question** : Pour chaque chemin filesystem resolu du fichier implicite, comment savoir s'il pointe vers du source **standard** (ERP livre par Divalto), du source **specifique** (workspace integrateur, fichiers ecrits/modifies par l'integrateur), du **runtime**, ou autre ?

- **Constat fondamental** : il n'existe **pas de mecanisme formel d'auto-classification universelle** dans Divalto. Les signaux structurels disponibles, par ordre de robustesse :

  - **(a) L'alias `divalto`** -> designe sans ambiguite le runtime (R-5).
  - **(b) Les champs `repobjet` / `repobjetsurcharge` / `repbrowse` / `repbrowsesurcharge` du `[profil]` du `.dhpt`** -> classification **formelle typee** posee explicitement par l'integrateur dans la configuration du projet (cf. R-15, [profile.md](profile.md)). C'est le signal le plus precis quand il est disponible : il dit non seulement "standard vs specifique" mais aussi le type d'artefact concerne (objets compiles / browse). **Conditionnel** : ce signal n'existe que si le workspace contient deja au moins un `.dhpt` de surcharge (en-tete `xwin-s-projet`). Sur un workspace en cours d'initialisation, tomber sur (c) et les signaux suivants.
  - **(c) La position dans le fichier implicite** -> convention "specifique en tete, standard en queue" (cf. semantique d'ordre de R-6). Convention seulement.

  Tous les autres signaux que je peux deduire (presence du nom du workspace dans `/specifs/<X>/`, segment de version `v<YEAR>_erpX<N>_<patch>`, etc.) sont des **conventions specifiques au partenaire integrateur** -- elles peuvent etre differentes chez d'autres partenaires. Aucun champ tag/type n'existe dans `divaltopath.cfg`, `divaltoserver.cfg` ou `fconfig`.

- **Indice content-based supplementaire** : un dossier qui contient massivement des fichiers prefixes par les **codes 2 caracteres des modules ERP** (`gt`, `cc`, `a5`, `gg`, `gr`, `ga`, `gm`, `pp`, `pv`, `rc`, `co`, `do`, `mo`, `sp`, `qu`, `tpv`) est tres probablement un dossier standard ERP. Plus robuste que la position ou le nommage du dossier, parce qu'il regarde le contenu.

### Conventions de separation -- a distinguer en deux niveaux

  1. **Axe ORIGINE (standard vs specifique)** -- convention **forte, en general respectee chez tous les integrateurs** : un dossier qui contient des sources standard n'en contient PAS de specifiques, et inversement. Idem pour les objets compiles, idem pour le browse. C'est ce qui rend le test content-based fiable : la presence d'un seul fichier avec suffixe `u` (ou `_base`) marque le dossier comme SPECIFIQUE pour son entierete ; la presence d'un seul fichier `<2-char-module><nom>.<ext>` sans `u` le marque comme STANDARD.

  2. **Axe TYPE D'ARTEFACT (projets vs sources vs fichiers vs objets vs ...)** -- convention **propre au partenaire**, **NON universelle**. Certains partenaires separent les types d'artefacts en sous-dossiers (`projets/`, `sources/`, `fichiers/`, `objets/`, `navigation/` distincts). D'autres peuvent **regrouper** projets et sources (ou d'autres combinaisons) dans un meme dossier. **Ne pas faire de presomption** sur ce point.

  **Conclusion operationnelle** : le test content-based s'appuie sur le **suffixe `u`** (et `_base` pour les compagnons), pas sur le type d'artefact. Cette mecanique fonctionne sur tout type DIVA (`.dhpt`, `.dhsf`, `.dhsd`, `.dhsq`, `.dhsp`, ...). Donc meme dans un dossier qui melange projets et sources, le test reste fiable tant que l'axe origine est respecte. Si je rencontre un dossier qui melange standard ET specifique (violation de l'axe 1, cas non observe mais theoriquement possible), il faut **demander au collaborateur** (P-A) -- ne pas trancher heuristiquement.

### Tableau des patterns content-based

| Pattern de fichier | Classification probable |
|--------------------|--------------------------|
| `<2-char-module><nom>.<ext>` (sans `u` final, sans `_base`) | **STANDARD** (livre par Divalto) |
| `<2-char-module><nom>u.<ext>` (suffixe `u` avant l'extension) | **SPECIFIQUE** -- surcharge d'un fichier standard |
| `<2-char-module><nom>_base.<ext>` (ou `<2-char-module><nom>_sql_base.<ext>`) | **SPECIFIQUE** -- compagnon AGL d'une surcharge masque |
| Prefixe custom (`mi`, `dgs`, ou autre code partenaire), sans 2-char-module | **SPECIFIQUE** -- fichier custom invente par l'integrateur |
| Aucun fichier avec ces patterns / dossier vide / fichiers d'outils (`.exe`, `.dll`, `.cfg`) | **RUNTIME** ou **autre** -- pas un dossier de sources ERP |

### Procedure obligatoire au demarrage de session

1. **Appliquer R-1 + R-2** pour obtenir la liste ordonnee des chemins du workspace.
2. **Produire une classification draft** : pour chaque ligne du fichier implicite, marquer un type pressenti parmi `STANDARD`, `SPECIFIQUE`, `RUNTIME`, `URL SQL`, `?`.

   **Pre-check sur l'etat du workspace** : detecter si le workspace contient au moins un `.dhpt` de surcharge (chercher recursivement `*.dhpt` puis filtrer ceux avec en-tete `xwin-s-projet 2.0`). Cela conditionne l'usage de R-15 :
   - **Workspace deja initie** (>=1 `.dhpt` de surcharge) -> **invoquer R-15 d'abord** pour chaque `.dhpt` de surcharge present. Les paths types extraits donnent le signal formel le plus fort. La classification R-14 confronte ensuite le contenu de l'implicite a ces paths types.
   - **Workspace en cours d'initialisation** (aucun `.dhpt` de surcharge encore) -> R-15 ne s'applique pas. R-14 enchaine directement sur les signaux suivants.

   Indices a utiliser, par ordre de robustesse :
   - **Alias `divalto`** -> `RUNTIME` (signal formel R-5).
   - **(Conditionnel) Match avec un champ `repobjet*` / `repbrowse*` du profil du `.dhpt`** (R-15) -> classification formelle typee : si le chemin resolu de la ligne matche `repobjet` ou `repbrowse`, c'est `STANDARD` ; s'il matche `repobjetsurcharge` ou `repbrowsesurcharge`, c'est `SPECIFIQUE`. **Signal le plus fort apres l'alias `divalto`** -- pose explicitement par l'integrateur. **Disponible seulement si le pre-check a trouve au moins un `.dhpt` de surcharge.**
   - **Contenu du dossier resolu** (test content-based) : `ls` du dossier puis classification par prevalence des patterns du tableau ci-dessus.
   - **Position dans le fichier implicite** (D1 de R-6) -> convention complementaire : tete = `SPECIFIQUE`, queue = `STANDARD`. Sert de second avis.
   - **Conventions de nommage du dossier** (segment de version, nom workspace dans le path) -> indice faible, valable uniquement comme corroboration.

3. **Presenter la classification draft au collaborateur explicitement** sous forme de tableau :
   ```
   | # | Ligne brute | Chemin resolu | Type pressenti | Confiance |
   ```
4. **Demander validation ligne par ligne** : le collaborateur valide, corrige, ou complete. Le silence ne vaut pas approbation.
5. **Stocker la classification validee** comme reference de la session. Elle alimente toutes les operations ulterieures (notamment R-13, et toute decision "ou copier / ou lire / ne pas toucher").

### Sortie

Classification validee de chaque ligne du fichier implicite, utilisable pour la suite de la session.

### Garde-fou

- **P-A renforce** : ne JAMAIS presumer la classification d'un chemin sans validation, meme si les heuristiques sont fortes. Le silence ne vaut pas approbation.
- **P-B applique a la classification** : si le collaborateur corrige une classification que mes heuristiques avaient mal predite, le noter en RETEX (categorie `SUGGESTION` ou `BUG-SKILL`) -- ce peut etre le signe d'une convention de nommage propre a ce partenaire que le skill devra apprendre.
- **Position dans le workflow** : R-14 est un **checkpoint d'entree** de session sur un workspace integrateur. AUCUNE operation qui depend de la distinction standard/specifique (R-13, surcharges, modifications, copies) ne doit etre executee avant que R-14 ait produit une classification validee.

### Format attendu de la demande au collaborateur

Apres avoir produit la classification draft, presenter au collaborateur :

```
Voici ma classification draft pour les <N> lignes du fichier implicite :

| # | Ligne brute | Chemin resolu | Type pressenti | Confiance |
|---|-------------|---------------|----------------|-----------|
| 1 | /specifs/<workspace>/fichiers/ | <chemin_resolu>  | SPECIFIQUE | Haute (profil repobjetsurcharge) |
| 2 | /specifs/<workspace>/projets/ | ...              | SPECIFIQUE | Haute (position + content-based) |
...

Confiance "Haute" partout sauf [RUNTIME] qui est certain. Tu valides ligne par ligne,
ou tu corriges si une convention t'est propre ?
```
