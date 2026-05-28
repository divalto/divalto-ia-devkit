---
name: coding-diva-advanced
description: >
  Reference des patterns avances du langage DIVA : HTTP/REST, JSON/XML, integration .NET,
  surcharge (OverWrite), module table (mtab), RecordSql avance (Reader, Collate, Paging),
  tunnels inter-modules (Ping/Pong), evenements Harmony.
  A consulter pour generer du code DIVA utilisant des fonctionnalites au-dela de la syntaxe de base.
---

# coding-diva-advanced

## Contenu

- Quand utiliser ce skill
- Domaines couverts (8)
- Anti-patterns avances
- References

---

## Quand utiliser ce skill

Ce skill est une **reference**, pas un generateur. Le consulter quand :
- L'utilisateur demande un appel HTTP/REST depuis DIVA
- L'utilisateur veut parser du JSON ou XML
- L'utilisateur veut integrer une DLL .NET
- L'utilisateur veut surcharger un module standard (OverWrite)
- L'utilisateur veut creer un module table (mtab) avec controles
- L'utilisateur veut utiliser Reader, Collate, ou Paging sur un RecordSql
- L'utilisateur veut communiquer entre modules (tunnels Ping/Pong)
- L'utilisateur veut gerer des evenements clavier/souris dans un Zoom (Harmony)

Ce skill ne couvre PAS la syntaxe de base (types, procedures, fonctions, boucles, chaines) : elle est implicite dans les autres skills de generation.

---

## Domaines couverts

| # | Domaine | Cas d'usage | Reference |
|---|---------|-------------|-----------|
| 1 | HTTP/REST | Appel API externe, WebRequest, WebServiceDiva | [http-rest.md](reference/http-rest.md) |
| 2 | JSON/XML | Parsing JSON (JsonOpen), lecture XML (XmlRead), HMP | [json-xml.md](reference/json-xml.md) |
| 3 | Integration .NET | Appel DLL .NET (AssemblyLoad/Invoke) | [dotnet-integration.md](reference/dotnet-integration.md) |
| 4 | Surcharge | OverWrittenBy/OverWrite, convention nommage U/UU, codes retour hooks Zoom* | [overwrite-pattern.md](reference/overwrite-pattern.md), [zoom-hooks-reference.md](reference/zoom-hooks-reference.md) |
| 5 | Module table (mtab) | Controles en cascade Switch TRUE, initialisation defauts | [module-table.md](reference/module-table.md) |
| 6 | RecordSql avance | Reader, Collate, Paging, Where fluent, RecordSqlPtr | [recordsql-advanced.md](reference/recordsql-advanced.md) |
| 7 | Tunnels | Ping/Pong, PingLocal, ProgramCall | [tunnels.md](reference/tunnels.md) |
| 8 | Harmony | Record Harmony, codes touches, timer, ZoomArret | [harmony-events.md](reference/harmony-events.md) |

---

## Anti-patterns avances

**NE JAMAIS generer :**
- `+` pour concatener → utiliser `&`
- `ForEach` → DIVA n'en a pas, utiliser `ListBegin/ListNext/ListEnd` ou Reader
- `Try/Catch` → DIVA n'a pas d'exceptions, utiliser codes retour + `ErrorFatal`/`ErrorWarning`
- `Class` → DIVA n'a pas d'OOP, utiliser les modules mchk
- Threads → utiliser `ProgramCall` pour l'execution parallele
- Oublier `WebRequestClose(ticket)` apres un appel HTTP (fuite)
- Oublier `JsonClose(ticket)` apres parsing JSON
- `GG_*` pour un module DAV → utiliser `GT_*`
- `GT_*` pour un module Production → utiliser `GG_*`

---

## References

- [HTTP/REST](reference/http-rest.md) -- WebRequest API, WebServiceDiva
- [JSON/XML](reference/json-xml.md) -- JsonOpen/Parse, XmlOpen/Read, HMP
- [Integration .NET](reference/dotnet-integration.md) -- AssemblyLoad, codes erreur
- [Surcharge](reference/overwrite-pattern.md) -- OverWrittenBy/OverWrite, convention U, pattern canonique de procedure surchargee
- [Hooks Zoom*](reference/zoom-hooks-reference.md) -- grille de codes retour O/N/I/C, couverture validee, pattern d'utilisation
- [Module table](reference/module-table.md) -- mtab, Switch TRUE, controles
- [RecordSql avance](reference/recordsql-advanced.md) -- Reader, Collate, Paging, Direct, Transactions, Performance, Callbacks
- [Tunnels](reference/tunnels.md) -- Ping/Pong, PingLocal, ProgramCall
- [Harmony](reference/harmony-events.md) -- Evenements, codes touches, timer
