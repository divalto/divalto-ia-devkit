# Patterns de structure JSON — divalto-page-ui

> **Les exemples ci-dessous illustrent uniquement la hiérarchie d'imbrication.**
> Pour connaître les propriétés valides de chaque composant, appeler systématiquement :
>
> - `list_components()` — liste les types disponibles
> - `get_component_properties({ component })` — propriétés et contraintes d'un type
>
> Ne jamais utiliser une propriété sans l'avoir vérifiée via ces outils MCP.

---

## Pattern 1 — Page de liste (grid + filtres)

> **MUST — `filters` a deux parties distinctes.** `Filters` (avec un `s` majuscule) est une **map déclarative** de la logique de filtrage, indexée par `<datasourceName>` puis `<filterName>` ; chaque feuille porte `Operator` (enum `FilterOperator` : `Equal`, `Contains`, `Greater`, …) et `FieldName` (nom de la colonne SQL). `Children` contient les **composants UI** (textbox, list, …) qui matchent par clé avec les filtres déclarés dans `Filters` — ces composants n'ont **ni `Operator` ni `DataField`** (la liaison se fait par le nom).

```json
{
  "Type": "page",
  "Title": "Liste des clients",
  "Children": {
    "filterPanel": {
      "Type": "filters",
      "Filters": {
        "customer.grid": {
          "nameFilter": {
            "Operator": "Contains",
            "FieldName": "customerName"
          },
          "statusFilter": {
            "Operator": "Equal",
            "FieldName": "status"
          }
        }
      },
      "Children": {
        "nameFilter": {
          "Type": "textbox",
          "Label": "Nom"
        },
        "statusFilter": {
          "Type": "list",
          "Label": "Statut",
          "DataSource": "status.listSource"
        }
      }
    },
    "mainGrid": {
      "Type": "grid",
      "DataSource": "customer.grid",
      "Exportable": {
        "ExportExcel": true
      },
      "Columns": {
        "customerName": {
          "type": "string",
          "title": "Nom",
          "primary": true,
          "sortable": true
        },
        "status": {
          "type": "string",
          "title": "Statut",
          "sortable": true
        },
        "outstanding": {
          "type": "decimal",
          "title": "Encours",
          "sum": true
        }
      }
    }
  }
}
```

---

## Pattern 2 — Fiche CRUD avec onglets

> **MUST — invariant d'imbrication d'une fiche CRUD.** Le composant `crud` **enveloppe** la totalité du contenu de la fiche, y compris les onglets. Le pattern canonique est `page > crud > tabs > tab > group (+ champs)` pour la fiche elle-même, et `page > crud > tabs > tab > grid` pour un onglet de liste rattaché à la fiche courante.
>
> - ❌ `page > tabs > tab > crud (+ grid en sibling tab)` — structure inversée : le save/cancel du CRUD ne couvre qu'un seul onglet ; les autres onglets ne partagent pas la session d'édition.
> - ✅ `page > crud > tabs > tab > group (champs) + tab > grid (sous-liste)`
>
> **MUST — un `crud` enveloppant une fiche a toujours des `Children` non vides.** Un `crud` qui contient les onglets de la fiche doit binder des champs (typiquement via `group > textbox/email/…` dans le 1er onglet) sinon la fiche s'affiche **vide** à l'exécution.
>
> - ❌ `"myCrud": { "Type": "crud", "DataSource": "...", "Children": { … tabs vides … } }` — fiche blanche.
> - ❌ `"myCrud": { "Type": "crud", "DataSource": "..." }` (sans `Children` du tout) — même problème.
> - ✅ Au minimum un onglet contient un `group` avec des `textbox`/`email`/… liés via `DataField` aux colonnes de la source du CRUD.

```json
{
  "Type": "page",
  "Title": "Fiche client",
  "Children": {
    "myCrud": {
      "Type": "crud",
      "DataSource": "customer.id.crud",
      "CanInsert": true,
      "CanUpdate": true,
      "CanDelete": true,
      "Events": {
        "BeforeInsert": { "Script": "customer.beforeInsert" },
        "AfterInsert": { "Script": "customer.afterInsert" },
        "AfterUpdate": { "Script": "customer.afterUpdate" }
      },
      "Children": {
        "myTabs": {
          "Type": "tabs",
          "StaticChildren": {
            "tabGeneral": {
              "Type": "tab",
              "Title": "Informations générales",
              "Children": {
                "generalGroup": {
                  "Type": "group",
                  "Title": "Général",
                  "WithBorder": true,
                  "Children": {
                    "nameField": {
                      "Type": "textbox",
                      "Label": "Nom",
                      "ScriptId": "script_nameField"
                    }
                  }
                }
              }
            },
            "tabContacts": {
              "Type": "tab",
              "Title": "Contacts",
              "Children": {}
            }
          }
        }
      }
    }
  }
}
```

---

## Pattern 3 — Page de dashboard standalone (sans CRUD)

> Scénario : page de tableau de bord en **lecture seule**, sans cycle d'édition. Les onglets sont enfants directs de `page` (pas de `crud` wrapper). Pour une **fiche** avec un onglet dashboard (édition + KPI), voir **Pattern 6** ci-dessous — c'est le cas le plus courant et le `metric` doit aller dans un onglet du `crud`, jamais en sibling de `crud` au niveau `page`.

```json
{
  "Type": "page",
  "Title": "Tableau de bord client",
  "Children": {
    "mainTabs": {
      "Type": "tabs",
      "StaticChildren": {
        "listTab": {
          "Type": "tab",
          "Title": "Liste",
          "Children": {
            "subFilters": {
              "Type": "filters",
              "Filters": {
                "customer.grid": {
                  "search": {
                    "Operator": "Contains",
                    "FieldName": "customerName"
                  }
                }
              },
              "Children": {
                "search": {
                  "Type": "textbox",
                  "Label": "Recherche"
                }
              }
            },
            "subGrid": {
              "Type": "grid",
              "DataSource": "customer.grid",
              "Columns": {
                "customerName": { "type": "string", "title": "Nom" }
              }
            }
          }
        },
        "dashboardTab": {
          "Type": "tab",
          "Title": "Tableau de bord",
          "Children": {
            "totalMetric": {
              "Type": "metric",
              "DataSource": "customer.outstanding.metricSource",
              "Title": "Encours total"
            }
          }
        }
      }
    }
  }
}
```

---

## Pattern 4 — Titre de page dynamique avec lien retour

> **MUST — `Mode` et la page cible sont sur `Link`, pas sur `link`.** Le composant `link` (classe `LinkConfig`) expose `Label`, `Url` (URL externe), `Target` (enum `LinkTargetEnum` : `Self`/`Blank`/`Parent`/`Top` — sémantique HTML, pas page Divalto) et `Link: LinkDataConfig`. C'est le sous-objet `Link` qui porte la redirection interne : `Target` (nom de la page cible) et `Mode` (enum `LinkMode` : `Back`/`Popin`/`Redirect`/`NewWindow`/…).

```json
{
  "Type": "page",
  "Title": {
    "Label": "Fiche client",
    "Children": {
      "backButton": {
        "Type": "link",
        "Label": "← Retour",
        "Link": {
          "Target": "customer",
          "Mode": "Back"
        }
      }
    }
  },
  "Children": {}
}
```

---

## Pattern 5 — Grille avec GroupBy et styles conditionnels

> **MUST — `StyleRules` est une propriété du `grid`, pas de la colonne.** La colonne porte un `Style: string` simple (statique). Pour un style **conditionnel**, déclarer `StyleRules.ColumnStylesRules` au niveau du grid et référencer la colonne via `ColumnKey`. Les conditions sont des objets `{ Operator, Value }` (enum `FilterOperator` : `Equal`, `NotEqual`, `Contains`, `Greater`, …), pas des expressions textuelles. Le `Style` est une valeur d'enum (`SemanticWarning`/`SemanticDanger`/`SemanticSuccess`/`SemanticInfo` ou `ColorRed`/`ColorOrange`/…), pas un nom libre.

```json
{
  "Type": "grid",
  "DataSource": "stock.table",
  "GroupBy": "category",
  "Exportable": {
    "ExportExcel": true
  },
  "TextWrap": false,
  "Columns": {
    "label": {
      "type": "string",
      "title": "Produit",
      "primary": true
    },
    "qty": {
      "type": "int",
      "title": "Qté",
      "width": 80,
      "sum": true
    },
    "status": {
      "type": "string",
      "title": "Statut"
    }
  },
  "StyleRules": {
    "ColumnStylesRules": [
      {
        "ColumnKey": "status",
        "Style": "SemanticWarning",
        "Rules": [
          { "Operator": "Equal", "Value": "LOW" }
        ]
      },
      {
        "ColumnKey": "status",
        "Style": "SemanticDanger",
        "Rules": [
          { "Operator": "Equal", "Value": "OUT" }
        ]
      }
    ]
  }
}
```

Pour styliser une ligne entière selon une condition : utiliser `StyleRules.RowStyleRules` (mêmes objets `Rules` à l'intérieur).

---

## Pattern 6 — Fiche CRUD avec onglet dashboard (KPI / metric)

> **MUST — placement du `metric` sur une fiche.** Un widget `metric` (encadré KPI, badge synthétique) s'ajoute à une fiche **comme un onglet dédié du `crud`** (typiquement nommé « Dashboard », « Tableau de bord », « Indicateurs »). Le `metric` est enfant d'une `tab`, jamais sibling de `crud` au niveau `page`.
>
> - ❌ `page > metric + crud > tabs > tab > group + tab > grid` — metric à côté de crud au niveau page, n'apparaît pas dans le code de référence Divalto et casse la cohérence de la fiche.
> - ✅ `page > crud > tabs > tab "Dashboard" > metric + tab "Fiche" > group + tab "Listes" > grid` — le KPI est un onglet de la fiche au même titre que les autres.
>
> Cas alternatif (info concise dans l'entête, **pas** un widget) : `crud.Header > infolines` — slot prévu pour les badges/indicateurs synthétiques de l'entête, à ne pas confondre avec un widget `metric`. Pour un **bouton d'action** dans l'entête, voir Pattern 7.

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
        "customerTabs": {
          "Type": "tabs",
          "StaticChildren": {
            "dashboardTab": {
              "Type": "tab",
              "Title": "Tableau de bord",
              "Children": {
                "outstandingMetric": {
                  "Type": "metric",
                  "DataSource": "orderheader.customeroutstanding.metricSource",
                  "MetricType": "Indicator",
                  "Title": "Encours total",
                  "Weight": 12
                }
              }
            },
            "infoTab": {
              "Type": "tab",
              "Title": "Informations",
              "Children": {
                "infoGroup": {
                  "Type": "group",
                  "Children": {
                    "codeField": { "Type": "textbox", "Label": "Code", "DataField": "codeCustomer" },
                    "nameField": { "Type": "textbox", "Label": "Nom",  "DataField": "customerName" }
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
                  "Columns": {
                    "lastName": { "type": "string", "title": "Nom", "primary": true }
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

---

## Pattern 7 — Header de CRUD avec bouton d'action

> Le `Header` d'un `crud` porte les actions **supplémentaires** (créer une entité liée, commande, navigation). Les boutons Enregistrer / Modifier / Supprimer ne s'y mettent pas : ils viennent de `CanInsert` / `CanUpdate` / `CanDelete`.
>
> La cible du lien suit les règles de [`navigation.md`](./navigation.md) : pas de segment `page`/`entity`/`activity` écrit à la main, et identifiant `new` pour ouvrir une fiche en création.

```json
{
  "Type": "page",
  "Title": "Fiche concurrent",
  "Children": {
    "competitorCrud": {
      "Type": "crud",
      "DataSource": "competitor.id.crud",
      "CanUpdate": true,
      "CanDelete": true,
      "Header": {
        "Actions": {
          "newProduct": {
            "Type": "button",
            "Label": "Gen_CompetitorProduct",
            "Icon": "plus",
            "Link": {
              "Target": "competitorProduct/new",
              "Params": {
                "competitor_ID": "#=id#"
              }
            }
          }
        }
      },
      "Children": {
        "mainGroup": {
          "Type": "group",
          "Title": "Identification",
          "Children": {
            "codeField": { "Type": "textbox", "Label": "Code", "DataField": "codecompetitor" },
            "nameField": { "Type": "textbox", "Label": "Nom",  "DataField": "name" }
          }
        }
      }
    }
  }
}
```

Datasource compagnon — `competitor.id.crud.datasource.json` (type `table`, cf. `datasources.md`) :

```json
{
  "Type": "table",
  "TableName": "competitor"
}
```

---

## Pattern 8 — Liste principale d'une entité → vue d'entité (skill dédié)

> La **liste principale autonome d'une entité standard** (« page de liste des clients », « lister les articles ») n'est **pas** un `grid` SQL fait main : c'est une **vue d'entité** `entityViews` / `entityList`, pilotée par le schéma, déclarée dans le `.entity.json`. Sa création est possédée par le skill [`divalto-entity-list`](../../divalto-entity-list/SKILL.md) — déléguer.
>
> Le `grid` (Patterns 1, 5) reste pour : une **sous-liste imbriquée** dans une fiche (enregistrements liés dans un onglet d'un `crud`, ex. « sur la fiche d'un tiers, ses devis en cours ») et des **données ad-hoc** (résultat calculé, jointures, agrégat). Cf. règle de l'étape 1 de `SKILL.md`.

---

## Anti-patterns à éviter

| Erreur                                                  | Correction                                                                                                |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Liste principale d'une entité standard générée comme `grid` + datasource SQL fait main (« page de liste des clients » → `customer.grid` + SQL) | C'est une **vue d'entité** (`entityViews` / `entityList`), possédée par le skill [`divalto-entity-list`](../../divalto-entity-list/SKILL.md) — déléguer. Le `grid` SQL reste pour les sous-listes imbriquées et les données ad-hoc (cf. Pattern 8 + étape 1 de `SKILL.md`). |
| `Children` pour les colonnes d'un `grid`                | Utiliser `Columns` — clé spécifique au grid                                                               |
| `Children` à l'intérieur d'un `tabs`                    | Utiliser `StaticChildren` — les onglets ne sont pas dynamiques                                            |
| Champs de saisie placés directement dans un `tab`       | Toujours envelopper dans un `group`                                                                       |
| Fiche avec structure `page > tabs > tab > crud` (CRUD imbriqué dans un onglet) | `page > crud > tabs > tab > group + tab > grid` — le `crud` enveloppe les onglets, jamais l'inverse (cf. Pattern 2) |
| `crud` enveloppant une fiche **sans `Children`** (ou avec onglets vides) | Au minimum un onglet avec `group > textbox/email/…` binding les champs de la source (cf. Pattern 2) — sans cela la fiche est vide à l'exécution |
| Casing minuscule sur une propriété de composant (`Type`, `Title`, `DataSource`, `Children`, `Columns`…) | Les propriétés d'un composant sont en **PascalCase**. Le `Type` en PascalCase d'un nœud est **toujours** le discriminant de composant (`grid`, `crud`, `textbox`…). |
| Une propriété de colonne en PascalCase **dans un sous-objet de `Columns`** (`Type`, `Title`, `Width`, `ColumnTemplate`, `Format`, `Style`…) | **Toutes** les propriétés d'une colonne (`BaseColumnConfig` / `ColumnConfig`) s'écrivent **première lettre en minuscule**, sans exception : `type`, `title`, `width`, `columnTemplate`, `format`, `style`, `primary`, `sortable`, `sum`… ❌ `{ "Type": "string", "Width": 120, "ColumnTemplate": "..." }` → ✅ `{ "type": "string", "width": 120, "columnTemplate": "..." }`. En prime, un `Type` PascalCase y est interprété comme le **discriminant de composant** et casse silencieusement la colonne. Même règle pour une colonne calculée / de comptage ajoutée à une grille existante. |
| `metric` (ou widget KPI) en sibling de `crud` au niveau `page` (`page > metric + crud > …`) | Ajouter le `metric` comme onglet dédié du `crud` (cf. Pattern 6) : `page > crud > tabs > tab "Dashboard" > metric`. Pour une info concise dans l'entête : `crud.Header > infolines`. |
| `ExportExcel: true` directement sur le grid             | Obsolète — utiliser `Exportable: { ExportExcel: true }`                                                   |
| `AfterLoad` comme événement de grille                   | N'existe pas sur grid. Pour réagir au chargement de la page, utiliser `AfterChildrenLoad` au niveau page. |
| `StyleRules` placé **dans une colonne** du grid (`Columns.<col>.StyleRules: [...]`) avec une syntaxe `{ Condition, Style }` | `StyleRules` est une propriété du **grid**, pas de la colonne. Utiliser `StyleRules.ColumnStylesRules: [{ ColumnKey, Style, Rules: [{ Operator, Value }] }]` (cf. Pattern 5). Au niveau colonne, seul `Style: string` statique existe. |
| `filters > Children > textbox/list` portant `Operator` / `DataField` | La logique de filtrage vit dans `Filters` (map `<datasource> > <name> > { Operator, FieldName }`). `Children` contient seulement les composants UI (`textbox`, `list`) ; ils s'apparient avec les filtres par leur **clé**, sans `Operator` ni `DataField` (cf. Pattern 1). |
| `link.Target: "<page>"` + `link.Mode: "Back"` au niveau racine du composant `link` | `Target`/`Mode` pour une redirection interne vivent dans le sous-objet `Link: { Target, Mode }` (`LinkDataConfig`). Sur `link` lui-même, `Target` est l'enum HTML `LinkTargetEnum` (`Self`/`Blank`/`Parent`/`Top`) — pas une page (cf. Pattern 4). |
| `Link.Target` préfixé à la main (`"page/customer/42"`, `"entity/orderheader"`) | Le moteur ajoute le premier segment d'après `Category`, sans vérifier s'il est déjà là : `"page/customer/42"` devient `page/page/customer/42` et tombe sur la page d'erreur. Écrire `"customer/42"` (cf. [`navigation.md`](./navigation.md)). |
| Identifiant de création inventé (`"Target": "customer/create"`, `"customer/0"`) | Le mode création se cible par l'identifiant littéral `new` — toute autre valeur est traitée comme l'identifiant d'un enregistrement à ouvrir (cf. [`navigation.md`](./navigation.md)). |
| `grid.LoadDataOnInit: true` | Propriété inventée — n'existe pas sur `GridConfig`. Le grid charge automatiquement quand sa datasource est prête ; si tu veux différer, regarder `Events.AfterChildrenLoad` au niveau page. |
| Inventer une propriété pour caler avec un autre framework | Toujours vérifier via `get_component_properties({ component })`                                            |
