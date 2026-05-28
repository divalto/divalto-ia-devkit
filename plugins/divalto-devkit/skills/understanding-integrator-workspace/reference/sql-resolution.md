# Resolution SQL -- modele deux portes

Ce document detaille **R-7** a **R-12** -- les regles qui resolvent la base SQL d'un workspace, par les **deux portes** independantes par lesquelles xwin7 accede a une base SQL Divalto.

## Modele "deux portes vers la meme base SQL"

A une base SQL Divalto, on accede par **deux portes** independantes l'une de l'autre. La coherence entre les deux est **une discipline de configuration**, pas une jointure enforcee par xwin7.

| Porte | Chaine de resolution | Consommateurs typiques |
|-------|----------------------|------------------------|
| **HARMONY** | `<implicite>.txt` URL `//host/db` → `divaltoserver.cfg` puis `fconfig` cle B → chemin SQL → `fhsql.dhfi/.dhfd` cle C → DSN ODBC → registre Windows ODBC | Acces file-based natif Divalto (mecanique Harmony / `.dhfi` multi-base via ODBC) |
| **ADO.NET** | `<implicite>.xml` → `connexions.xml` → chaine ADO.NET | **RecordSql** (`.dhsq`/`.dhoq`) |

Les deux portes doivent pointer sur la **meme base SQL** (meme Server + meme Database). Sinon : configuration cassee. xwin7 ne verifie pas, c'est a l'admin/dev de tenir la coherence.

---

## Porte HARMONY -- chaine de resolution

### Precedence de resolution des serveurs

Parallele a la precedence pour les chemins (`divaltopath.cfg` -> `fconfig` cle E) :

| Etape | Source consultee | Regle | Si trouve | Si absent |
|-------|------------------|-------|-----------|-----------|
| 1 | `<DIVA_ROOT>/sys/divaltoserver.cfg` | R-7 | retourner `<SQLPATH>` | passer a l'etape 2 |
| 2 | `<DIVA_ROOT>/sys/fconfig.dhfi` (cle B = "table des serveurs") | R-8 | retourner `<SQLPATH>` | P-A : demander |

`divaltoserver.cfg` fait foi en priorite. `fconfig` consulte uniquement si l'alias serveur est absent du `.cfg`. Si les deux divergeaient, `divaltoserver.cfg` l'emporte mais signaler le conflit (P-B).

---

### R-7 -- Resoudre le chemin SQL via `divaltoserver.cfg`

- **Question** : A partir d'une ligne URL SQL `//host/db` du fichier implicite, quel est le **chemin SQL** associe a ce serveur (point d'entree de la porte Harmony) ?
- **Entree** : Le `<db>` extrait de la ligne URL SQL (la cle de lookup est le `<db>`, pas le `<host>` -- le `<host>` est utilise seulement quand la machine est distante) + `<DIVA_ROOT>` connu (R-5).
- **Procedure** :
  1. Localiser `<DIVA_ROOT>/sys/divaltoserver.cfg`.
  2. Lire le fichier -- une entree par ligne, grammaire :
     ```
     <NAME>nom_serveur<ADDRESS>adresse<SQLPATH>chemin<COMMENT>libelle<TYPE>type<OS>os<PORT>port
     ```
     `<TYPE>` observes : `WINDOWS` (entrees de drives), `SQL` (bases SQL), `XLAN` (serveurs xlan). `<SQLPATH>` peut etre vide.
  3. Chercher l'entree dont `<NAME>` matche `<db>` (insensible a la casse).
  4. Extraire `<SQLPATH>`.
  5. **Cas particulier** : si `<SQLPATH>` est vide -> appliquer la regle de fallback : chemin SQL = `<DIVA_ROOT>/<db>/` (PAS `<DIVA_ROOT>` tout seul -- piege a documenter, le sous-dossier nomme comme la base est obligatoire).
  6. Si aucune entree ne matche -> R-8 (fallback fconfig).
- **Sortie** : Le chemin SQL (chemin Windows absolu) -- dossier qui doit contenir au moins `fhsql.dhfi` + `fhsql.dhfd`.
- **Garde-fou** :
  - **P-A** si pas de `.cfg` ou alias absent et fconfig inaccessible.
  - **P-B** pour confirmation du chemin avant utilisation.

### R-8 -- Resoudre le chemin SQL via `fconfig` cle B (fallback)

> **Pre-requis strict** : R-8 ne s'execute QUE si R-7 a echoue. Parallele exact de la precedence R-3 -> R-4 pour les chemins.

- **Question** : Quand R-7 ne trouve pas l'alias dans `divaltoserver.cfg`, comment combler le trou ?
- **Entree** : `<db>` recherche + chemin de `fconfig.dhfi` (via R-5 `CheminFpartd` du registre).
- **Procedure** :
  1. Ouvrir `fconfig.dhfi` en parcours sequentiel sur **cle B** (table des serveurs).
  2. Le skill `reading-isam-files` est le bon outil. Limitation actuelle : pas de `structure_fconfig.json` pour la cle B. A defaut, lecture brute du `.dhfd` (les enregistrements serveur portent un prefixe `C 5XX` dans les bytes observes).
  3. Chercher l'enregistrement dont le `NAME` matche `<db>`.
  4. Extraire le `SQLPATH` (et appliquer la meme regle de fallback "vide -> `<DIVA_ROOT>/<db>/`" qu'en R-7).
- **Sortie** : chemin SQL comme R-7.
- **Garde-fou** : P-A si absent des deux sources.

---

### R-9 -- Extraire la connection string ODBC depuis `fhsql.dhfi` cle C

- **Question** : Le chemin SQL trouve en R-7/R-8 contient `fhsql.dhfi/.dhfd`. Que faire de ce fichier ?

- **Entree** : Chemin SQL resolu (sortie R-7 ou R-8).

- **Mecanique reelle** : le ou les enregistrements de `fhsql.dhfi/.dhfd` contiennent une **connection string ODBC complete**, pas juste un nom DSN. La forme observee est :

  ```
  BCONNECT DSN=<nom>;Description=<desc>;Trusted_Connection=<Yes|No>;APP=<app>;WSID=<host>;DATABASE=<base>;Encrypt=<Yes|No>;TrustServerCertificate=<Yes|No>;
  ```

  Les paires `cle=valeur` sont separees par `;` et **chacune peut overrider** la valeur correspondante du DSN dans le registre Windows (cf. R-10). Le `BCONNECT` est donc l'autorite primaire cote Divalto : ce qui est dans cette chaine prime sur le registre.

- **Cles typiques observees** :

  | Cle | Role |
  |-----|------|
  | `DSN` | Nom du Data Source ODBC configure cote Windows -- cle d'entree pour R-10 |
  | `Description` | Libelle informatif |
  | `Trusted_Connection` | `Yes` = Windows integrated auth, `No` = SQL auth (credentials hors string) |
  | `APP` | Identifiant applicatif client (ex: `Divalto Infinity`) |
  | `WSID` | Workstation ID (typiquement nom de machine) |
  | **`DATABASE`** | **Base SQL effectivement consultee** -- override le registre |
  | `Encrypt` | `Yes/No` -- chiffrement TLS de la connexion -- override le registre |
  | `TrustServerCertificate` | `Yes/No` -- acceptation cert auto-signe -- override le registre |

  D'autres cles sont possibles (ex: `Server`, `Port`, `Database`, etc.) -- la liste ci-dessus n'est PAS exhaustive. Le principe d'override de R-10 s'applique a toute cle presente dans le BCONNECT.

- **Procedure** :

  1. Lire `fhsql.dhfi` en parcours sur **cle C** via le skill `reading-isam-files`.
  2. Le contenu est une chaine `BCONNECT ...` -- extraire la **chaine complete**, pas juste le `DSN=`.
  3. Limitation actuelle : pas de `structure_fhsql.json` dans le skill. A defaut, lecture brute du `.dhfd` -- la chaine `BCONNECT [\x20-\x7E]+` est suffisamment textuelle pour etre trouvee par regex.
  4. Parser la chaine en paires `cle=valeur` (split sur `;`, trim, decoder).
  5. Conserver **la chaine complete + le dict de paires** pour R-10 (qui appliquera la regle d'override).

- **Sortie** : Le `<nom_dsn>` ET le dict des paires de la connection string complete (`{DSN, Description, Trusted_Connection, ..., DATABASE, Encrypt, TrustServerCertificate, ...}`).

- **Garde-fou** :
  - **P-A** : si le pattern `BCONNECT` est introuvable ou si plusieurs `BCONNECT` distincts apparaissent sans logique evidente, demander au collaborateur.
  - **Erreur classique** : extraire **uniquement** le `DSN=` et oublier le reste de la chaine -> conduit a un faux diagnostic d'incoherence 32-bit/64-bit (R-10). Toujours conserver la connection string complete.

---

### R-10 -- Lire la configuration d'un DSN ODBC dans le registre Windows

- **Question** : Le DSN extrait en R-9 est un alias systeme Windows. Ou trouver le driver, le serveur SQL, la base, le mode d'authentification ?
- **Entree** : Le nom du DSN (sortie R-9).
- **Procedure** : Les DSN ODBC vivent dans la base de registre Windows. Quatre emplacements possibles, a tester dans l'ordre :

  | # | Cle de registre | Type de DSN |
  |---|-----------------|-------------|
  | 1 | `HKLM\SOFTWARE\WOW6432Node\ODBC\ODBC.INI\<DSN>` | System DSN, vue 32-bit (utilise par Divalto 32-bit) |
  | 2 | `HKLM\SOFTWARE\ODBC\ODBC.INI\<DSN>` | System DSN, vue 64-bit |
  | 3 | `HKCU\SOFTWARE\WOW6432Node\ODBC\ODBC.INI\<DSN>` | User DSN, vue 32-bit |
  | 4 | `HKCU\SOFTWARE\ODBC\ODBC.INI\<DSN>` | User DSN, vue 64-bit |

  Commande : `reg query "<cle>\<DSN>"`.

  Champs typiquement presents :

  | Champ | Role |
  |-------|------|
  | `Driver` | Chemin absolu du DLL du pilote ODBC (ex: `C:\WINDOWS\SysWOW64\msodbcsql17.dll`) |
  | `Server` | Hote + instance SQL (ex: `localhost\<instance>`) |
  | `Database` | Nom de la base par defaut |
  | `Trusted_Connection` | `Yes` (Windows integrated auth) ou `No` (SQL auth -- credentials gerees hors DSN) |
  | `Encrypt`, `TrustServerCertificate` | Options TLS de la connexion |

  La liste des DSN connus de la machine se lit a `HKLM\SOFTWARE\WOW6432Node\ODBC\ODBC.INI\ODBC Data Sources`.

- **Sortie** : Driver + Server + Database + mode auth (valeurs **brutes** du registre, avant override BCONNECT).
- **Garde-fou** :
  - **P-A** : si le DSN n'est dans aucune des 4 cles, ne pas l'inventer. Demander.
  - **P-C (liste blanche registre)** : seules les valeurs sous la cle DSN ciblee `\ODBC\ODBC.INI\<DSN>` sont autorisees -- valeurs typiques `Driver`, `Server`, `Database`, `Trusted_Connection`, `Encrypt`, `TrustServerCertificate` et autres champs ODBC standard qui appartiennent a la cle DSN. Le listing `\ODBC\ODBC.INI\ODBC Data Sources` est tolere **uniquement** si necessaire pour resoudre un DSN ambigu (pas par precaution). **Interdit** : explorer les autres branches de `\ODBC\` (drivers ODBC tiers, configurations de pools), lire les sous-cles `\ODBC\ODBCINST.INI`, faire un `reg query /s` sur `\ODBC\`. Si le DSN est absent des 4 vues -> P-A, pas exploration. Cf. SKILL.md section *Principes transverses -- P-C*.
  - **Hygiene credentials** : si `Trusted_Connection=No` et qu'un mot de passe SQL est present dans le DSN (champ `PWD` ou similaire), redaction systematique (cf. regle d'or de R-11).

### Semantique d'override : connection string BCONNECT prime sur le registre

> **Cle critique** : ce qui est dans la chaine `BCONNECT` de R-9 **override** la valeur correspondante du registre. xwin7 utilise la valeur effective = `BCONNECT.cle` si presente, sinon `registre.cle`. **Ne pas comparer aveuglement le registre 32-bit et 64-bit sans tenir compte du BCONNECT.**

**Procedure de comparaison correcte** :

1. Lire la connection string BCONNECT (R-9) -> dict `bconnect = {DSN, DATABASE, Encrypt, TrustServerCertificate, ...}`
2. Lire le DSN dans le registre 32-bit -> dict `reg32 = {Driver, Server, Database, Encrypt, TrustServerCertificate, ...}`
3. Lire le DSN dans le registre 64-bit -> dict `reg64 = {Driver, Server, Database, Encrypt, TrustServerCertificate, ...}`
4. Pour chaque champ, calculer la **valeur effective** :

   ```
   effective_32[champ] = bconnect[champ] si present, sinon reg32[champ]
   effective_64[champ] = bconnect[champ] si present, sinon reg64[champ]
   ```

5. Comparer `effective_32` vs `effective_64` -- **pas** `reg32` vs `reg64` bruts.

**Champs typiquement overrides** (presents dans le BCONNECT, prime sur le registre) :

- `DATABASE` (le plus important -- determine la base reellement consultee)
- `Encrypt`
- `TrustServerCertificate`
- `Trusted_Connection` (parfois)
- `APP`, `WSID` (informatifs)

**Champs typiquement NON overrides** (uniquement dans le registre, doivent etre cross-checkes 32/64) :

- `Server` (le BCONNECT ne le redefinit generalement pas)
- `Driver` (chemin du DLL ODBC -- toujours dans le registre)

### Exemple concret

Cas observe sur un workspace integrateur :

| Source | DATABASE | Encrypt | TrustServerCertificate | Server |
|--------|----------|---------|------------------------|--------|
| `BCONNECT` (R-9) | `DIVALTO_EXPLOINTEGRATION_VX13` | `Yes` | `Yes` | _(non present)_ |
| Registre 32-bit | `DIVALTO_EXPLOINTEGRATION_VX13` | `Yes` | `Yes` | `localhost\divaltoerp` |
| Registre 64-bit | `DIVALTO_CLAUDEINTEGRATION_VX13` | `No` | `No` | `localhost\divaltoerp` |

**Diagnostic naif** (comparer registre brut) : *"32-bit et 64-bit divergent sur DATABASE / Encrypt / TrustServerCertificate -- piege 32/64 !"* → **FAUX**.

**Diagnostic correct** (appliquer override BCONNECT) :

- `effective_32.DATABASE` = `BCONNECT.DATABASE` = `DIVALTO_EXPLOINTEGRATION_VX13`
- `effective_64.DATABASE` = `BCONNECT.DATABASE` = `DIVALTO_EXPLOINTEGRATION_VX13`
- → **identiques** : pas de piege 32/64 sur ces 3 champs (overrides BCONNECT).
- `effective_32.Server` = `effective_64.Server` = `localhost\divaltoerp` → identiques.
- **Verdict reel : porte Harmony coherente bout en bout.**

### Garde-fou supplementaire pour R-10

- **Ne JAMAIS conclure a une incoherence 32/64 sans avoir applique l'override BCONNECT.** Un audit naif produit des faux positifs sur tous les champs presents dans le BCONNECT.
- Les vrais pieges 32/64 sont sur les champs **non overrides** : `Server`, `Driver`. Ce sont eux qui doivent etre cross-checkes apres application de l'override.

---

## Porte ADO.NET -- chaine de resolution

### R-11 -- Resoudre via `<implicite>.xml` -> `connexions.xml`

> **Cette chaine est totalement independante de R-7..R-10**. Elle n'utilise PAS la ligne URL SQL de l'implicite.

- **Question** : Comment retrouver la chaine de connexion ADO.NET utilisee par les RecordSql (`.dhsq`/`.dhoq`) -- la voie effective qu'emprunte le code DIVA pour interroger la base ?
- **Entree** : Le chemin du fichier implicite confirme (R-1) + `<DIVA_ROOT>` (R-5).
- **Procedure** :
  1. **Localiser le compagnon XML** : a cote du fichier implicite (meme repertoire, meme basename, extension `.xml`). Ex: `<implicite>.txt` -> `<implicite>.xml`.
  2. **Lire le mapping alias-applicatif -> connexion-logique** :
     ```xml
     <implicites xmlns="urn:implicites-schema">
        <implicite nom="<alias_applicatif>" connexion="<nom_connexion_logique>" />
     </implicites>
     ```
     - `nom` = alias utilise dans le code RecordSql (`Default` par convention).
     - `connexion` = nom de la connexion logique dont la definition reelle est dans `connexions.xml`.
  3. **Lire `<DIVA_ROOT>/sys/connexions.xml`** et trouver l'entree `<connexion nom="<nom_connexion_logique>">` :
     ```xml
     <connexion nom="<NOM>">
        <type><code></type>                          <!-- 5 observe = SQL Server natif -->
        <nomBase><nom_base></nomBase>
        <chaineDeConnexion>...</chaineDeConnexion>   <!-- chaine ADO.NET complete -->
        <harmonyShareServer>...</harmonyShareServer>
        <logSql>...</logSql>
     </connexion>
     ```
- **Sortie** : La chaine ADO.NET complete (Data Source, Database, auth, options).
- **Garde-fou** :
  - **P-A** : si le `.xml` compagnon est absent, ou si le `nom` de connexion declare n'existe pas dans `connexions.xml`, ne pas inventer. Demander.
  - **P-B** : presenter au collaborateur la chaine resolue avant utilisation.
  - **Credentials -- regle d'or** : si la `<chaineDeConnexion>` contient `Password=`, `pwd=`, `User Id=`, `uid=`, **NE JAMAIS ressortir ces valeurs en clair** (reponse, log, commit, artefact). Redaction systematique : `Password=<REDACTED>`. La chaine reste utilisable en passant la valeur originelle directement au client SQL sans l'exposer.
  - **Cas Trusted_Connection** : pas de credential -> pas de risque d'exfiltration. Verifier que le user Windows a les droits SQL voulus.

---

## Coherence transverse entre les deux portes

> **Regle critique** : la comparaison entre les portes Harmony et ADO.NET ne peut pas se faire en regardant le registre brut. Il faut d'abord calculer la **`base_effective`** de chaque porte en appliquant la regle d'override BCONNECT (R-10), puis comparer les `base_effective`. Un audit naif (comparaison registre brut) produit des faux positifs.

### Formules de `base_effective` par porte

```
base_effective_Harmony   = FHSQL[DATABASE] || ODBC_registry[Database]
base_effective_ADO_NET   = ADO_NET_connection_string[Database]   # extrait de connexions.xml (R-11)
```

- Pour la porte Harmony : si `FHSQL[DATABASE]` est present dans la connection string BCONNECT (R-9), il **prime** sur la valeur `Database` du registre ODBC (R-10). Sinon, c'est le registre qui fait foi.
- Pour la porte ADO.NET : la chaine ADO.NET de `connexions.xml` (R-11) est autoritative -- pas d'override registre.

### Tableau des sources et valeurs effectives

| Source | Server / Data Source | Database (brut) | Override applique |
|--------|----------------------|------------------|---------------------|
| `<implicite>.txt` URL SQL (porte Harmony, declaration) | `<host>` (informatif si local) | `<db>` | - |
| **R-9 -- BCONNECT** (chaine dans `fhsql.dhfd`) | (rarement present) | `FHSQL[DATABASE]` | **Source d'override** |
| **R-10 -- registre ODBC** du DSN trouve en R-9 (32-bit) | `Server` | `Database` | Overrideable par R-9 |
| **R-10 -- registre ODBC** du DSN trouve en R-9 (64-bit) | `Server` | `Database` | Overrideable par R-9 |
| **R-11 -- chaine ADO.NET** de `connexions.xml` | Data Source de la `<chaineDeConnexion>` | Database de la chaine + `<nomBase>` | - (autoritative) |

### 2 cas P-B distincts a produire en finding

**Cas A -- divergence registre 32/64 mais override BCONNECT identique** → **warning**

Scenario : BCONNECT contient `DATABASE=X`, registre 32-bit `Database=X`, registre 64-bit `Database=Y`.
- `base_effective_Harmony_32` = `BCONNECT[DATABASE]` = `X`
- `base_effective_Harmony_64` = `BCONNECT[DATABASE]` = `X`
- Verdict : les deux bitness pointent en realite sur **la meme base** (l'override BCONNECT prime). Configuration **fonctionnelle mais inhabituelle** -- le registre 64-bit est divergent mais ignore au runtime. **Warning** (signaler au collaborateur que c'est suspect), **pas error** (ca fonctionne).

**Cas B -- vraie incoherence inter-portes** → **error**

Scenario : `base_effective_Harmony` ≠ `base_effective_ADO_NET`.
- Exemple : `base_effective_Harmony` = `X` (via BCONNECT), `base_effective_ADO_NET` = `Y` (via connexions.xml).
- Verdict : les deux portes pointent **vraiment** sur des bases differentes. Une operation Harmony lit/ecrit dans X, une operation ADO.NET (RecordSql) lit/ecrit dans Y. **Vraie incoherence** -- bug latent qui se revelera au moment ou un workflow utilise les deux portes (typique : creation entite via Harmony puis lecture via RecordSql). **Error**.

### Tableau de decision -- recapitulatif

| `base_effective_Harmony_32` | `base_effective_Harmony_64` | `base_effective_ADO_NET` | Finding |
|------------------------------|------------------------------|----------------------------|---------|
| `X` | `X` | `X` | (aucun -- coherent) |
| `X` | `X` | `Y` | **error** (Cas B -- Harmony vs ADO.NET divergent) |
| `X` | `Y` | `X` | **error** (Cas B -- Harmony 64 vs ADO.NET divergent) |
| `X` | `Y` (override BCONNECT identique) | `X` | **warning** (Cas A -- registre divergent mais override identique) |

### Garde-fous

- **Ne JAMAIS comparer les `Database` registre 32/64 sans avoir d'abord applique l'override BCONNECT.** Un audit naif sur le registre brut produit le faux positif Cas A (qui n'est pas une vraie incoherence).
- **Server est generalement pas override par BCONNECT** -- comparer les `Server` registre 32 vs 64 est legitime (cf. R-10).
- **Si BCONNECT absent ou non parsable** : tomber sur le registre brut, signaler P-A (le diagnostic est de moindre confiance).
- **Si connexions.xml absent ou si la connexion declaree dans `<implicite>.xml` n'y existe pas** : P-A, ne pas inventer une `base_effective_ADO_NET` plausible.

---

## R-12 -- Verifier la joignabilite SQL (regle conditionnelle de delegation)

- **Question** : Comment confirmer que la base SQL declaree dans le fichier implicite est joignable ?

- **Entree** : La chaine de connexion ADO.NET extraite par R-11. Tester la porte ADO.NET suffit puisque la coherence transverse garantit que les deux portes pointent sur la meme base.

- **Niveau cible** : niveau **(d)** -- une requete `SELECT 1` (ou `SELECT @@SERVERNAME, DB_NAME(), GETDATE()`) reussit. C'est la seule confirmation complete que tout fonctionne bout en bout (host joignable + instance SQL repond + base existe + droits OK).

- **Posture par defaut -- delegation au collaborateur** : Claude **ne lance pas** la requete spontanement. Il documente la commande, la transmet au collaborateur, et **attend** son retour. La base est traitee comme une **ressource du collaborateur**, pas comme une cible operable par defaut.

- **Exception -- consentement explicite + contexte sur** : Claude **peut** executer `sqlcmd` lui-meme **si et seulement si** les 3 conditions suivantes sont **toutes** reunies dans la session courante :

  | Condition | Detail |
  |-----------|--------|
  | **1. Consentement explicite** | Le collaborateur a explicitement demande l'execution dans cette session (ex: "essaie de joindre la base", "lance la requete de test", "verifie la connexion"). Le simple fait que la verification soit utile **ne suffit pas** -- l'execution doit etre demandee. |
  | **2. Contexte sur** | Tous les criteres suivants sont remplis : (a) `localhost` ou hote interne approuve par le collaborateur, (b) `Trusted_Connection=Yes` OU credentials gerees par le collaborateur, (c) requete strictement **read-only** (`SELECT 1`, `SELECT @@SERVERNAME`, `SELECT DB_NAME()`, `SELECT GETDATE()` ou equivalent), (d) **aucun effet de bord** possible sur la base. |
  | **3. Timeout court** | `-l 5` (5s) en local ; `-l 15` (15s) maximum pour hote distant. **Jamais** sans timeout. |

  Si l'une des 3 conditions n'est pas reunie : retomber sur la posture par defaut (delegation au collaborateur).

### Deux voies pour confirmer la joignabilite (par ordre de preference)

**Voie A -- indirecte, via les operations Divalto normales (recommandee)** :

La joignabilite SQL est **implicitement testee** lors de toute operation Divalto qui touche la base : `xwin7 -action synchroauto`, certaines compilations qui valident un `.dhsq`, etc. Si ces operations passent avec succes (`Erreur(s)=0`), la base est joignable -- pas besoin de test additionnel.

Pratiquement : si dans la session courante le collaborateur vient de lancer un `synchroauto` reussi, la joignabilite est confirmee comme effet de bord. R-12 est satisfaite implicitement.

**Voie B -- directe, via `sqlcmd`, mais executee par le collaborateur** :

Si la voie A n'est pas applicable, Claude **fournit la recette** mais **ne l'execute pas**. Le collaborateur copie/lance la commande lui-meme.

Format de la commande, en deduisant les parametres de la `<chaineDeConnexion>` extraite par R-11 :

```bash
# Cas Trusted_Connection=Yes (Windows integrated auth)
sqlcmd -S "<Data Source>" -d "<Database>" -E -Q "SELECT 1" -l <timeout_secondes>

# Cas SQL Server Auth (User Id + Password dans la chaine)
sqlcmd -S "<Data Source>" -d "<Database>" -U "<User Id>" -P "<Password>" -Q "SELECT 1" -l <timeout_secondes>
```

- `-l <timeout>` : **timeout de login OBLIGATOIRE**. Valeur recommandee : `5` secondes en local (`localhost\...`), `15` secondes pour un serveur distant. Sans timeout, `sqlcmd` peut bloquer indefiniment sur un host injoignable.
- Si l'auth est SQL native, Claude affiche la commande avec `<Password>` litteral plutot que la valeur reelle, et **demande au collaborateur de substituer** lui-meme. Toujours pas de credentials en clair dans une reponse / log / fichier.

### Garde-fou

- **Posture par defaut = delegation** : Claude ne lance pas `sqlcmd` (ni autre client SQL) spontanement. Il documente la commande et la transmet au collaborateur.
- **Execution autorisee sous conditions strictes** : les 3 conditions ci-dessus (consentement explicite + contexte sur + timeout court) doivent **toutes** etre remplies. Si Claude execute la commande, il doit signaler explicitement dans sa reponse que les 3 conditions sont reunies (forme courte : *"Conditions reunies pour execution directe (consentement + localhost+Trusted + read-only) -- requete `SELECT 1` lancee."*).
- **Refus quand non rempli** : si une condition manque, expliquer brievement laquelle et demander au collaborateur d'executer lui-meme. Ne pas etre bureaucratique -- un refus motive en 1 phrase suffit.
- **Non-bloquant** : si la voie A est utilisable (`synchroauto` reussi recemment, par exemple), ne pas demander au collaborateur de faire un test additionnel -- juste signaler "joignabilite confirmee implicitement par <operation>".
- **Timeout obligatoire** : ne pas omettre `-l <timeout>`.
- **Cas distant** : si le `<Data Source>` n'est pas `localhost\...` mais un hote distant, prevenir explicitement le collaborateur que (a) le timeout devient critique, (b) un firewall / segmentation reseau peut bloquer alors que tout est par ailleurs correct.
- **Hygiene credentials** : si l'auth est SQL native (User Id + Password), **Claude ne logue jamais le mot de passe en clair** (ni dans la commande presentee, ni dans le retour). Si le collaborateur execute lui-meme : OK. Si Claude execute via consentement explicite : le mot de passe doit etre fourni par le collaborateur en tant qu'argument runtime, **pas** reproduit dans la reponse.

### Localisation des credentials -- synthese

| Mode d'authentification | Ou vivent les credentials | Hygiene |
|-------------------------|---------------------------|---------|
| `Trusted_Connection=Yes` (Windows integrated) | Aucun credential a manipuler. La connexion utilise le user Windows qui execute le client. Verifier que ce user a les droits SQL voulus. | N/A |
| SQL Server Auth (porte ADO.NET) | Directement dans la `<chaineDeConnexion>` de `connexions.xml` (R-11). Source unique pour cette porte. | Regle d'or de R-11 -- redaction systematique des `Password=`, `User Id=`. |
| SQL Server Auth (porte Harmony / DSN ODBC) | Generalement HORS du DSN (les drivers modernes les demandent au runtime). Si exceptionnellement dans le registre (champ `PWD`), meme regle d'hygiene. | Voir R-10 garde-fou. |
