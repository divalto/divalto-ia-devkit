# Integration .NET (Assembly)

Permet d'appeler des DLL .NET depuis DIVA.

## Pattern d'appel

```
1   assembly    L
1   method      L
1   result      S

assembly = AssemblyLoad("MonAssembly.dll")
method = AssemblyGetMethod(assembly, "MaMethode")
st = AssemblyMethodInvoke(assembly, method, params, result)
If st <> 0
    errMsg = AssemblyGetError()
EndIf
```

## Fonctions Assembly

| Fonction | Role |
|----------|------|
| `AssemblyLoad(path)` | Charge une DLL .NET, retourne identifiant |
| `AssemblyGetMethod(assembly, name)` | Obtient une reference de methode |
| `AssemblyMethodInvoke(assembly, method, params, &result)` | Execute la methode |
| `AssemblyGetError()` | Retourne le message d'erreur de la derniere invocation |

## Contrainte de signature .NET

Les methodes appelees depuis DIVA doivent respecter la signature :

```csharp
public static string Method(string hmp)
```

- **public static** : obligatoire
- **string** en entree : parametres au format HMP (voir json-xml.md)
- **string** en retour : resultat au format HMP

## Codes d'erreur

| Code | Description |
|------|-------------|
| `0x167c` | Method not found |
| `0x167d` | Incorrect assembly identifier |
| `0x167e` | Incorrect method identifier |
| `0x167f` | Class not found |
| `0x1680` | Exception dans la methode .NET |
| `0x1681` | Assembly not found (DLL introuvable) |
