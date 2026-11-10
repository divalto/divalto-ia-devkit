# Divalto Studio — working rules

Rules that decide what you are allowed to write, and in what order. Everything
descriptive about the platform — layers, workspace layout, UI/TypeScript/C#
patterns — lives in the `divalto-studio-platform` skill; load it when you need
the background rather than a rule.

## File editing permission

Read this before writing any file.

**You MUST NOT decide from filesystem permissions whether you may edit a file.**
A file being writable by the OS — or living under the user's home directory —
does not mean you are allowed to change it. The workspace marks files you may not
edit as read-only (`files.readonlyInclude`). In Divalto, the standard layer is
read-only while the active edit perimeter is the project (`spe`).

- ❌ `Write` / shell redirection into a read-only file because the OS allows it.
- ✅ Propose the change as a project override at the same relative path in the
  active perimeter, or stop and ask.

The lock is logical — editor plus server sync — not OS permissions. A shell write
can succeed on disk and still be illegitimate: it will not sync. "The write did
not error" is not proof it was allowed.

## Project overrides

Enriching or customizing a standard entity (Contact, Customer…) with data absent
from the standard is done through a project override: an override of the page
(form and list) plus a `.scriptlibrary.ts` for the computation, written at the
same relative path in the active perimeter.

**You MUST create every override file with the `specialize_file` MCP tool.** Call
`specialize_file({ path })` with the absolute path of the standard file, then edit
the returned `spePath`.

- ❌ Creating the override by hand, with `Write`, or with a shell `cp` — these
  bypass the deterministic Specialize command and do not sync server-side.
- ✅ `specialize_file` first, then edit `spePath`. For a `.scriptlibrary.ts` the
  tool generates an `extends Standard` stub: override only the methods you need,
  never duplicate the standard file.

This rule is unconditional and does not depend on any skill being loaded. If the
`divalto-crm-overload` skill does not activate, still follow this mechanism — do
not improvise an alternative.

There is no "custom column" or `Custom.*` mechanism, and no way to add a custom
field to the dictionary of a standard entity. Never propose it; it does not exist
in Divalto. Never assume a Divalto mechanism absent from the `divalto-studio` MCP
tools.

## Translation keys

`search_translation_keys` and `get_translation_key` are the ONLY source of a
project's translation keys and labels.

**You MUST NOT source a key from anywhere else** — not the catalog files, not the
configurations or scripts, not the `.divalto-original` SCM baseline, not another
project, not a skill example. A key found in a `"Label"` or a
`getTranslationAsync('…')` proves that the key exists; it says nothing about the
label being asked for.

- ❌ Searching the files because the tool errored, is not started, or is absent.
- ✅ Report what the tool said — or that it is unavailable — and stop. Never
  guess a key, never create one to work around the refusal.

An unloaded catalog is not an empty catalog: without it, the company-wide
uniqueness of a key cannot be checked, so anything you return is a guess.

## Writing Divalto TypeScript (`.scriptlibrary.ts`)

Any time you write or modify Divalto TypeScript — a `.scriptlibrary.ts` file, or
any call to an SDK service (`$component`, `$database`, `$notify`…) — use the
`divalto-scriptlibrary` skill, whatever the size of the change, even one line. It
checks the real SDK signatures and component properties through MCP before the
code is written; "the snippet is small" and "I already know the API" are not
reasons to skip it. Page structure and event placement stay with
`divalto-page-ui`.

## Before writing a `.component.json` or a `.page.json`

Components have a strict, schema-defined set of properties. You have no reliable
prior on what exists — only the MCP tools do.

1. `list_components` → the exact set of valid component types.
2. `get_component_properties(component)` for every component you intend to use →
   the exhaustive list of allowed properties.
3. Generate the JSON using only the properties returned at step 2.
4. `validate_divalto_file('component', content)` → fix every error.
5. Write the file.

**`get_component_properties` is the single source of truth for which properties
exist.** `validate_divalto_file` is a guard, not an oracle: the underlying schema
is permissive and may accept properties that do not exist on the component. Never
use validation success to confirm a property absent from
`get_component_properties`. Never transpose properties from other frameworks — no
`Style.*`, no `css.*`, no HTML attributes.

When a property carries an `enum`, only those values are acceptable. The schema
may also accept arbitrary strings as a fallback for dynamic bindings, but the
enum is the intended set. If the user asks for a value outside it, refuse and
propose a valid one.

## Before writing any other JSON file

1. Generate the JSON.
2. `validate_divalto_file(type, content)` → fix every error.
3. Write the file to the correct path.

`Schema not found for type '<type>'` means the type is not covered — `menu` is one
of them. It is not a defect in your file: keep the content, write it, and say the
file went out unvalidated.

## File naming and uniqueness

Every Divalto file follows `<basename>.<type>.<ext>` (`customer.component.json`,
`customer.scriptlibrary.ts`). Check for an existing file of the same basename in
the relevant type family **before** creating one — if it exists, edit it.

- No duplicate basename within a type family: two `*.component.json` with the
  same basename in different folders collide, and the platform cannot
  disambiguate them.
- `component` and `page` are two shapes of the same `ConfigType.Component` and
  share one namespace: `customer.component.json` blocks `customer.page.json`
  anywhere in the project. Renaming one into the other does not resolve the
  conflict. `.component.json` is deprecated — prefer `.page.json` for new files.
- Code-behind mirrors its JSON counterpart: `myPage.page.json` ↔
  `myPage.scriptlibrary.ts`.
- Other types are independent namespaces: `customer.entity.json` and
  `customer.datasource.json` may coexist.

## Deprecated components

Some components are kept for backward compatibility only. `list_components` and
`get_component_properties` surface a `deprecated` field naming the modern
replacement — there is no static list to keep in sync.

**When proposing a component, you MUST NOT name a deprecated alternative — not
even by negation.**

- ❌ "Utilise `info` (et non `infoMail`, qui est obsolète) configuré pour email."
- ✅ "Utilise `info` avec `InfoConfig` configuré pour email."

Name it only when the user asked about it explicitly, or is editing code that
already uses it — and then migrate the usage to the modern replacement in the
same pass. Never write a new `.component.json` / `.page.json` referencing a
deprecated component type; if asked for one, refuse and explain the replacement.

Exception for file-level deprecations: when the deprecation implies a file rename
(an existing `customer.component.json` while `.page.json` is the modern shape),
only mention it. Do not rename the file — a dedicated migration skill handles it.

The same preference applies to TypeScript helpers and C# methods: rely on the
language services and explicit `[Obsolete]` attributes.
