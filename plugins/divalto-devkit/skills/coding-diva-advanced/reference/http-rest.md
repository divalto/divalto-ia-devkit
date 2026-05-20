# HTTP/REST -- WebRequest API

## WebRequest -- client HTTP complet

```
1   ticket      L
1   statusCode  L = 0
1   response    S

ticket = WebRequestNew()
WebRequestSetUrl(ticket, "https://api.example.com/data")
WebRequestSetMethod(ticket, "GET", -1)    ; -1 = timeout par defaut
WebRequestSetHeader(ticket, "Content-Type", "application/json")
WebRequestSetHeader(ticket, "Authorization", "Bearer " & token)

st = WebRequestSend(ticket, "", response, statusCode)
If st = 0 And statusCode = 200
    ; Traiter la reponse
EndIf
WebRequestClose(ticket)
```

### Fonctions WebRequest

| Fonction | Role |
|----------|------|
| `WebRequestNew()` | Cree un ticket HTTP, retourne identifiant |
| `WebRequestSetUrl(ticket, url)` | Definit l'URL cible |
| `WebRequestSetMethod(ticket, method, timeout)` | Methode HTTP (GET, POST, PUT, DELETE), timeout en ms (-1 = defaut) |
| `WebRequestSetHeader(ticket, name, value)` | Ajoute un header HTTP |
| `WebRequestSend(ticket, body, &response, &statusCode)` | Envoie la requete, retourne 0=OK |
| `WebRequestClose(ticket)` | **OBLIGATOIRE** -- libere les ressources |

### Anti-pattern

**Ne jamais oublier `WebRequestClose(ticket)`** -- provoque une fuite de ressources.

### Pattern POST avec body JSON

```
ticket = WebRequestNew()
WebRequestSetUrl(ticket, url)
WebRequestSetMethod(ticket, "POST", 30000)   ; timeout 30s
WebRequestSetHeader(ticket, "Content-Type", "application/json")

body = '{"ref":"' & MonRS.Code & '","qty":' & ToString(MonRS.Quantite) & '}'
st = WebRequestSend(ticket, body, response, statusCode)
WebRequestClose(ticket)
```

## WebServiceDivaExecute -- appel de service Diva

```
st = WebServiceDivaExecute(URL, "<action>MONACTION", params, retour)
If st = 0
    ; Traiter retour
EndIf
```

Appel synchrone a un service web Divalto. Les parametres et retours utilisent le format HMP (voir json-xml.md).
