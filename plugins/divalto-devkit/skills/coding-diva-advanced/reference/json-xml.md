# JSON, XML et HMP

## Lecture JSON

```
1   ticketj     L
1   valeur      S

ticketj = JsonOpen()
JsonParse(ticketj, jsonString)
JsonGetValue(ticketj, "article.ref", valeur)        ; Acces par chemin
JsonGetValue(ticketj, "[0].title", valeur)          ; Acces tableau
JsonGetLength(ticketj, "items", nbItems)            ; Nombre d'elements
JsonClose(ticketj)
```

### Fonctions JSON

| Fonction | Role |
|----------|------|
| `JsonOpen()` | Cree un ticket JSON |
| `JsonParse(ticket, string)` | Parse la chaine JSON |
| `JsonGetValue(ticket, path, &value)` | Lit une valeur par chemin (dot notation) |
| `JsonGetLength(ticket, path, &count)` | Nombre d'elements dans un tableau |
| `JsonClose(ticket)` | **OBLIGATOIRE** -- libere les ressources |

### Anti-pattern

**Ne jamais oublier `JsonClose(ticket)`** apres parsing JSON.

---

## Lecture XML

```
1   ticketx     L
1   tag         S
1   value       S

ticketx = XmlOpen(xmlString)
Loop XmlRead(ticketx, tag, value) <> XML_EOF
    Switch2 tag
        Case XML_BEGINTAG    ; Debut de balise
        Case XML_ENDTAG      ; Fin de balise
        Case XML_ATTRIBUT    ; Attribut
        Case XML_TEXTVALUE   ; Valeur texte
    EndSwitch
EndLoop
XmlClose(ticketx)
```

### Constantes XML

| Constante | Signification |
|-----------|---------------|
| `XML_EOF` | Fin du document |
| `XML_BEGINTAG` | Debut de balise ouvrante |
| `XML_ENDTAG` | Fin de balise (fermante) |
| `XML_ATTRIBUT` | Attribut de balise |
| `XML_TEXTVALUE` | Valeur texte entre balises |

---

## HMP -- Harmony Markup Parameters

Format d'echange cle-valeur proprietaire Divalto : `<param1>value1<param2>value2`

```
HmpSeek(hmpString, "param1", valeur)     ; Recherche par cle
HmpRead(hmpString, tag, valeur)          ; Lecture sequentielle
HmpEncode(valeur)                        ; Echappement des < >
```

Utilise dans les WebServiceDiva et les tunnels Ping/Pong pour transmettre des donnees structurees.
