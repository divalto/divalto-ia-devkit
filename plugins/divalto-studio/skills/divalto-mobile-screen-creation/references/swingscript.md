# Reference du langage SwingScript — Divalto Weavy Mobile

SwingScript est le langage de script proprietaire Divalto pour la logique metier des applications mobiles. C'est un langage procedural avec gestion de variables scopees, execution SQL inline et APIs de manipulation UI.

> **Decouvrir les fonctions disponibles** : utiliser l'outil MCP `get_swingscript_reference` pour chercher des fonctions par nom ou par groupe. Ne jamais inventer un nom de fonction sans l'avoir verifie.

---

## Syntaxe fondamentale

### Variables et affectation

```swing
// Affectation simple
myVariable = "valeur"
myVariable = TRANSLATE( "valeur interpolee <varscript>arg1</varscript>" )

// Resultat d'une fonction
result = CALL_SCRIPT( "Func_MyFunction", arg1, arg2 )
result = VARGET_DBSQL( "SELECT name FROM sw_data_customer WHERE customer_ID = '123'" )
```

Toutes les valeurs sont des chaines en interne. Pas de typage explicite.

### Regles syntaxiques importantes

- **Pas de point-virgule** : ne jamais terminer une ligne par `;`. SwingScript est oriente ligne.
- **Pas d'appels imbriques** : les appels de fonction ne peuvent pas etre utilises comme arguments d'une autre fonction. Stocker le resultat dans une variable d'abord.

```swing
// INTERDIT — appel imbrique
IF ( EQUALS( CONTROL_ENABLE( "myCtrl" ), "1" ) ) THEN

// CORRECT — variable intermediaire
enabled = CONTROL_ENABLE( "myCtrl" )
IF ( EQUALS( enabled, "1" ) ) THEN
```

### Interpolation de variables

| Syntaxe                           | Contexte                                 | Exemple                                            |
| --------------------------------- | ---------------------------------------- | -------------------------------------------------- |
| `<var>name\|Group</var>`          | Variable shell (groupe)                  | `<var>customer_ID\|Customer</var>`                 |
| `<varscript>name</varscript>`     | Variable de script locale                | `<varscript>arg1</varscript>`                      |
| `<ctrl>name</ctrl>`               | Valeur d'un controle UI                  | `<ctrl>tbName</ctrl>`                              |
| `<sql>SELECT ...</sql>`           | Execution SQL inline (retourne scalaire) | `<sql>SELECT COUNT(*) FROM sw_data_customer</sql>` |
| `<lng>Key</lng>`                  | Cle de traduction                        | `<lng>Gen_Customer</lng>`                          |
| `<msk>value\|format</msk>`        | Formatage                                | `<msk>%now%\|d</msk>` (date courte)                |
| `<row>field</row>`                | Champ ligne courante (FOREACH)           | `<row>name</row>`                                  |
| `%variable%`                      | Variable systeme                         | `%baseuser_ID%`, `%now%`, `%gps_fix%`              |
| `<ifempty>val\|default</ifempty>` | Valeur par defaut si vide                | `<ifempty><var>x\|G</var>\|0</ifempty>`            |
| `<calc>expr</calc>`               | Calcul arithmetique                      | `<calc>quantity * price</calc>`                    |

### Formats de masque (`<msk>`)

| Format     | Resultat           | Exemple            |
| ---------- | ------------------ | ------------------ |
| `d`        | Date courte        | `15/01/2024`       |
| `g`        | Date generale      | `15/01/2024 14:30` |
| `HH:mm:ss` | Heure              | `14:30:00`         |
| `0`        | Entier             | `42`               |
| `0.00`     | Decimal 2 chiffres | `42.50`            |

---

## Flux de controle

### Conditions

```swing
IF ( condition ) THEN
  // instructions
ENDIF

IF ( condition ) THEN
  // instructions
ELSE
  // instructions
ENDIF

// Conditions imbriquees
IF ( EQUALS( action, "edit" ) ) THEN
  // ...
ELSE
  IF ( EQUALS( action, "view" ) ) THEN
    // ...
  ENDIF
ENDIF
```

### Operateurs de comparaison

```swing
EQUALS( str1, str2 )          // Egalite de chaines (retourne "1" ou "0")
LEN( str )                    // Longueur de chaine
value1 > value2               // Comparaison numerique
value1 < value2
value1 >= value2
value1 == value2               // Egalite numerique
value1 != value2               // Difference numerique
```

### Operateurs logiques

```swing
( cond1 ) && ( cond2 )        // ET logique
( cond1 ) || ( cond2 )        // OU logique
EQUALS( x, y ) == 0           // Negation (NON EGAL)
```

### Boucles (ancres + GOTO)

SwingScript n'a pas de `while` ou `for`. Les boucles utilisent des ancres :

```swing
#StartLoop:
  elapsedTime = DATEDIFF( startTime, "%now%", "sec" )

  IF ( elapsedTime < maxTime ) THEN
    PAUSE( "0.5" )
    GOTO StartLoop
  ENDIF
```

### Iteration sur lignes SQL

```swing
query = "SELECT id, name FROM sw_data_customer WHERE active = 1"
EXECUTE_SCRIPT_FOREACH_ROW( "Func_ProcessCustomer", "sql", query )
// Dans Func_ProcessCustomer, les colonnes sont accessibles via <row>id</row>, <row>name</row>
```

---

## Gestion des variables

### Variables shell (scopees par groupe)

```swing
// Ecriture / Lecture
VARSET_SHELL( "customer_ID", "123", "Customer" )
value = VARGET_SHELL( "customer_ID", "Customer" )
// Ou via interpolation : <var>customer_ID|Customer</var>

// Suppression
VARDEL_SHELL( "customer_ID", "Customer" )
VARDELGROUP_SHELL( "Customer" )

// Initialisation depuis SQL
VARSET_SHELL_BYSQL( "SELECT customer_ID AS id, name FROM sw_data_customer WHERE ...", "Customer" )
```

**Groupes courants :** `Options`, `User`, `Customer`, `Order`, `Intervention`, `GPS`, `Selection`, `Tag`, `ViewPicture`

### Variables de script

```swing
// Les arguments de CALL_SCRIPT sont accessibles via arg1, arg2, etc.
customer_ID = TRANSLATE( "<varscript>arg1</varscript>" )

// Initialiser des variables locales depuis SQL
VARINITIALIZE_SCRIPT_BYSQL( "SELECT name, codeCustomer FROM sw_data_customer WHERE customer_ID = '123'" )
// Cree les variables locales : name, codeCustomer
```

---

## Appels de scripts

```swing
// Appel avec arguments et retour
result = CALL_SCRIPT( "Func_GetCustomerInfo", customer_ID )

// Appel sans retour
CALL_SCRIPT( "FuncOrder_SetDisplayMode" )

// Inclure un script (partage les variables du scope courant, pas de nouveau scope)
INCLUDE( "FuncCustomer_RefreshDisplay" )

// Iteration sur lignes SQL
EXECUTE_SCRIPT_FOREACH_ROW( "Func_ProcessCustomer", "sql", query )

// Retourner une valeur
RETURN( result )
RETURN( "cancel" )  // Annuler un formulaire
```

---

## Operations base de donnees

> **Base de donnees : MariaDB (syntaxe MySQL).** Toutes les requetes SQL doivent utiliser la syntaxe MariaDB.
>
> **Avant d'ecrire du SQL, toujours utiliser les outils MCP :**
>
> - `get_entities()` — lister toutes les tables `sw_data_*`
> - `get_entity_properties("sw_data_customer")` — obtenir les colonnes exactes
> - `get_swingscript_reference( search="VAR" )` — trouver les fonctions DB disponibles

### Patterns courants

```swing
// Lecture scalaire
name = VARGET_DBSQL( "SELECT name FROM sw_data_customer WHERE customer_ID = '123'" )

// Champ par ID
name = VARGET_DBFIELD_BYID( "sw_data_customer", "name", "123" )

// Initialiser plusieurs variables locales depuis SQL
VARINITIALIZE_SCRIPT_BYSQL( "SELECT name, codeCustomer, city FROM sw_data_customer WHERE customer_ID = '123'" )

// Insertion (retourne le nouvel ID)
newId = VARADD_DB( "sw_data_customer", "name=John;codeCustomer=CLI001;city=Paris" )

// Mise a jour par ID
VARUPDATE_DB_BYID( "sw_data_customer", customerId, "name=Jane;city=Lyon" )

// Suppression par ID
VARDEL_DB_BYID( "sw_data_customer", customerId )

// SQL brut
EXECUTESQL( "UPDATE sw_data_customer SET lastSync = NOW() WHERE customer_ID = '123'" )
```

---

## Syntaxe MariaDB — aide-memoire

```sql
-- Concatenation (pas de || comme en SQLite/PostgreSQL)
SELECT CONCAT(firstName, ' ', lastName) FROM sw_data_baseuser

-- Null coalescing
SELECT IFNULL(city, 'N/A'), COALESCE(phone, mobile, 'Aucun')

-- Date courante
SELECT NOW(), CURDATE(), CURTIME()

-- Formatage date
SELECT DATE_FORMAT(startDate, '%d/%m/%Y %H:%i')

-- LIKE (insensible a la casse par defaut en MariaDB)
SELECT * FROM sw_data_customer WHERE name LIKE '%dupont%'

-- Limite et pagination
SELECT * FROM sw_data_customer LIMIT 10 OFFSET 20

-- GROUP_CONCAT
SELECT GROUP_CONCAT(name SEPARATOR ', ') FROM sw_data_baseuser
```

**Differences avec SQLite (piege courant) :**

| Operation     | SQLite            | MariaDB        |
| ------------- | ----------------- | -------------- |
| Concatenation | `a \|\| b`        | `CONCAT(a, b)` |
| Date courante | `datetime('now')` | `NOW()`        |
| Booleen       | `true` / `false`  | `1` / `0`      |

---

## Patterns de scripts courants

### Script form_open (initialisation)

```swing
CONTROL_SET_VALUE( "lbTitle", "<sql>SELECT name FROM sw_data_customer WHERE customer_ID = '<var>customer_ID|Customer</var>'</sql>" )
CONTROL_SETIMAGE( "pbLogo", "sql", "SELECT picture FROM sw_data_companyinfo LIMIT 1" )

CALL_SCRIPT( "Func_LoadPermissions" )

IF ( EQUALS( "<var>isReadOnly|MyEntity</var>", "1" ) ) THEN
  CONTROL_ENABLE( "tbName", "0" )
  CONTROL_VISIBLE( "btDelete", "0" )
ENDIF

DISPLAY_TITLE( "<lng>Gen_Customer</lng>" )
```

### Script form_close (nettoyage)

```swing
IF ( EQUALS( "%form_useraction%", "validate" ) ) THEN
  IF ( LEN( "<var>row_ID|Selection</var>" ) == 0 ) THEN
    MSGBOX( "<lng>Msg_NoItemSelected</lng>" )
    RETURN( "cancel" )
  ENDIF
  VARSET_SHELL( "action", "validate", "Selection" )
ENDIF

VARDELGROUP_SHELL( "MyEntity" )
```

### Script valuechanged (reaction a la saisie)

```swing
product_ID = UNISEARCH_SELECTEDID( "usProducts" )

IF ( LEN( product_ID ) > 0 ) THEN
  VARSET_SHELL( "product_ID", product_ID, "Order" )
  CALL_SCRIPT( "FuncOrder_UpdateTotal" )
  UNISEARCH_REFRESH( "usOrderLines" )
ENDIF
```

### Script click (action bouton)

```swing
url = VARGET_DBFIELD_BYID( "sw_data_customer", "website", "<var>customer_ID|Customer</var>" )
IF ( LEN( url ) > 0 ) THEN
  OPEN_URL( url )
ENDIF
```

### Fonction utilitaire (reutilisable)

```swing
// @description  Obtenir les informations du client
// @param1       customer_ID
// @return       Label du client (nom + code)

customer_ID = TRANSLATE( "<varscript>arg1</varscript>" )
customerInfo = ""

IF ( LEN( customer_ID ) > 0 ) THEN
  VARINITIALIZE_SCRIPT_BYSQL( "SELECT name, codeCustomer FROM sw_data_customer WHERE customer_ID = '<varscript>customer_ID</varscript>'" )

  IF ( LEN( "<varscript>name</varscript>" ) > 0 ) THEN
    customerInfo = TRANSLATE( "<varscript>name</varscript> (<varscript>codeCustomer</varscript>)" )
  ENDIF
ENDIF

RETURN( customerInfo )
```

### Pattern GPS complet

```swing
reqPrecision = TRANSLATE( "<varscript>arg1</varscript>" )
searchTime = TRANSLATE( "<varscript>arg2</varscript>" )
result = "0"

IF ( LEN( reqPrecision ) == 0 ) THEN
  reqPrecision = "100"
ENDIF
IF ( LEN( searchTime ) == 0 ) THEN
  searchTime = "10"
ENDIF

GPS_START()
startTime = TRANSLATE( "%now%" )

#WaitForGPS:
  elapsedTime = DATEDIFF( startTime, "%now%", "sec" )
  precision = TRANSLATE( "%gps_precision%" )

  IF ( ( elapsedTime < searchTime ) && ( ( precision > reqPrecision ) || ( precision == -1 ) ) ) THEN
    PAUSE( "0.25" )
    GOTO WaitForGPS
  ENDIF

IF ( EQUALS( "%gps_fix%", "1" ) ) THEN
  latitude = GPS_GETLATITUDE()
  longitude = GPS_GETLONGITUDE()
  VARSET_SHELL( "gpsLatitude", latitude, "GPS" )
  VARSET_SHELL( "gpsLongitude", longitude, "GPS" )
  result = "1"
ENDIF

GPS_STOP()
RETURN( result )
```

---

## Tables de donnees courantes

> **Cette liste est indicative.** Pour obtenir la liste exhaustive et les colonnes de chaque table, utiliser les outils MCP :
>
> - `get_entities()` — liste complete des tables
> - `get_entity_properties("sw_data_customer")` — colonnes, types et cles d'une table

| Table                     | Entite                          |
| ------------------------- | ------------------------------- |
| `sw_data_customer`        | Client                          |
| `sw_data_customercontact` | Contact client                  |
| `sw_data_customeraddress` | Adresse client                  |
| `sw_data_intervention`    | Intervention                    |
| `sw_data_orderheader`     | En-tete commande                |
| `sw_data_orderdetail`     | Ligne commande                  |
| `sw_data_product`         | Produit                         |
| `sw_data_equipment`       | Equipement                      |
| `sw_data_contract`        | Contrat                         |
| `sw_data_task`            | Tache                           |
| `sw_data_baseuser`        | Utilisateur                     |
| `sw_data_generictype`     | Types generiques (enumerations) |
| `sw_data_translation`     | Traductions                     |
| `sw_data_feature`         | Feature flags                   |
| `sw_data_companyinfo`     | Informations societe            |
