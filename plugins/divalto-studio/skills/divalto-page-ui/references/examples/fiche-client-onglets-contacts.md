# Fiche client avec onglet contacts

## Quand l'utiliser

Afficher la fiche d'un client (coordonnées principales) avec un onglet listant ses contacts liés, accessible depuis la page de liste des clients par sélection d'un ID.

## Composants

- `crud` — formulaire principal de la fiche client
- `tabs` — conteneur d'onglets (Informations, Contacts)
- `tab` — un onglet
- `group` — regroupement des champs avec encadré
- `textbox`, `email` — saisies
- `grid` — liste des contacts liés

## Fichiers

```text
DeviceTypes/Default/customer/id/
├── customer.id.page.json
├── customer.id.crud.datasource.json
├── customercontact.grid.datasource.json
└── customercontact.grid.sql.sql
```

## JSON + SQL

### `customer.id.page.json`

```json
{
  "Type": "page",
  "Title": "Fiche client",
  "Children": {
    "customerCrud": {
      "Type": "crud",
      "DataSource": "customer.id.crud",
      "CanInsert": true,
      "CanUpdate": true,
      "CanDelete": true,
      "Children": {
        "mainTabs": {
          "Type": "tabs",
          "StaticChildren": {
            "infoTab": {
              "Type": "tab",
              "Title": "Informations",
              "Children": {
                "infoGroup": {
                  "Type": "group",
                  "Title": "Coordonnées",
                  "WithBorder": true,
                  "Children": {
                    "codeField": {
                      "Type": "textbox",
                      "Label": "Code",
                      "DataField": "codeCustomer"
                    },
                    "nameField": {
                      "Type": "textbox",
                      "Label": "Nom",
                      "DataField": "customerName"
                    },
                    "emailField": {
                      "Type": "emailbox",
                      "Label": "Email",
                      "DataField": "email"
                    },
                    "phoneField": {
                      "Type": "textbox",
                      "Label": "Téléphone",
                      "DataField": "phone"
                    }
                  }
                }
              }
            },
            "contactsTab": {
              "Type": "tab",
              "Title": "Contacts",
              "Children": {
                "contactsGrid": {
                  "Type": "grid",
                  "DataSource": "customercontact.grid",
                  "Exportable": {
                    "ExportExcel": true
                  },
                  "Columns": {
                    "firstName": {
                      "type": "string",
                      "title": "Prénom",
                      "sortable": true
                    },
                    "lastName": {
                      "type": "string",
                      "title": "Nom",
                      "primary": true,
                      "sortable": true
                    },
                    "email": {
                      "type": "string",
                      "title": "Email"
                    },
                    "phone": {
                      "type": "string",
                      "title": "Téléphone"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### `customer.id.crud.datasource.json`

```json
{
  "Type": "table",
  "TableName": "customer",
  "PrimaryKey": "customer_ID",
  "ContextFields": [
    { "DatabaseFieldName": "customer_ID" }
  ]
}
```

### `customercontact.grid.datasource.json`

```json
{
  "Type": "sql",
  "SelectQueryName": "customercontact.grid",
  "TableName": "customercontact",
  "PrimaryKey": "customercontact_ID_primaryKey"
}
```

### `customercontact.grid.sql.sql`

```sql
SELECT
  cc.customercontact_ID AS customercontact_ID_primaryKey,
  cc.firstName,
  cc.lastName,
  cc.email,
  cc.phone
FROM {{TABLE(customercontact, cc)}}
WHERE cc.customer_ID = {{id}}
  AND {{FILTERS}}
ORDER BY cc.lastName, cc.firstName
```

## Pièges

1. ❌ `Children` à l'intérieur d'un `tabs` → ✅ utiliser `StaticChildren` (les onglets statiques d'une fiche ne sont pas dynamiques).
2. ❌ Champs `textbox`/`email` placés directement dans le `tab` → ✅ toujours envelopper dans un `group`.
3. ❌ `ExportExcel: true` directement sur le `grid` → ✅ utiliser `Exportable: { ExportExcel: true }` ; l'écriture directe est obsolète.
4. ❌ Référencer `customercontact.grid` sans créer les deux fichiers compagnons (`.datasource.json` **et** `.sql.sql`) → ✅ tout `SelectQueryName` a son `.sql.sql` voisin.
5. ❌ Faire `FROM sw_data_customercontact AS cc` directement → ✅ `FROM {{TABLE(customercontact, cc)}}` pour appliquer automatiquement le contrôle d'accès ligne.
6. ❌ Oublier `{{FILTERS}}` dans la requête de contacts → ✅ combiner le filtre métier avec `AND {{FILTERS}}` ; sans lui, un futur panneau `filters` ajouté à la grille serait inerte.
7. ❌ Mettre `AfterLoad` comme événement de la `grid` → ✅ `AfterLoad` n'existe pas sur `grid` ; pour réagir au chargement, utiliser `AfterChildrenLoad` au niveau de la `page`.
