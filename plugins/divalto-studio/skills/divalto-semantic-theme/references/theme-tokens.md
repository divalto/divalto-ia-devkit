# Clés de token du thème

Les clés que peut nommer une couleur de config — voir [SKILL.md](../SKILL.md#nommer-un-token-dans-une-couleur-de-config)
pour la règle. **Ce qui s'écrit, c'est la clé**, jamais la valeur : les deux colonnes ci-dessous sont
les valeurs *par défaut* en clair et en sombre, données pour reconnaître une couleur, pas pour la
recopier. Un thème de projet re-seede ses familles, donc la valeur change et la clé reste.

Une clé absente de cette liste ne se résout pas : le player laisse alors la couleur à son défaut,
**sans rien signaler**. Ne jamais fabriquer une clé par analogie — la lire ici.

Liste générée depuis `resources/mobile/theme-preview-spec.json` (224 clés), l'asset que l'extension
livre déjà pour l'onglet Couleurs. La regénérer quand cet asset change.

## `calendar`

| Clé | clair | sombre |
|---|---|---|
| `calendar.allday-bg` | `FF9C0028` | `FF9C0028` |
| `calendar.selected-slot` | `FF9C0055` | `FF9C0055` |
| `calendar.special-slot` | `E6C9EBB3` | `140516B3` |

## `color-base`

| Clé | clair | sombre |
|---|---|---|
| `color-base.active` | `BDC4CB` | `5C636A` |
| `color-base.base` | `FFFFFF` | `495057` |
| `color-base.emphasis` | `00000057` | `E9ECEF2B` |
| `color-base.hover` | `CED4DA` | `596169` |
| `color-base.on-base` | `343A40` | `DEE2E6` |
| `color-base.on-subtle` | `343A40` | `DEE2E6` |
| `color-base.on-surface` | `343A40` | `DEE2E6` |
| `color-base.opacity.opacity-active` | `00000029` | `E9ECEF29` |
| `color-base.opacity.opacity-focus` | `0000001F` | `E9ECEF1F` |
| `color-base.opacity.opacity-hover` | `00000014` | `E9ECEF0F` |
| `color-base.subtle` | `F8F9FA` | `41464B` |
| `color-base.subtle-active` | `CED4DA` | `596169` |
| `color-base.subtle-hover` | `DEE2E6` | `495057` |

## `color-dark`

| Clé | clair | sombre |
|---|---|---|
| `color-dark.active` | `2B2F32` | `212529` |
| `color-dark.dark` | `000000` | `1A1D20` |
| `color-dark.emphasis` | `00000066` | `343A40` |
| `color-dark.hover` | `495057` | `212529` |
| `color-dark.on-dark` | `FFFFFF` | `FFFFFF` |
| `color-dark.on-subtle` | `495057` | `DEE2E6` |
| `color-dark.on-surface` | `343A40` | `2B2F32` |
| `color-dark.opacity.opacity-active` | `00000029` | `00000029` |
| `color-dark.opacity.opacity-focus` | `0000001F` | `0000001F` |
| `color-dark.opacity.opacity-hover` | `00000014` | `00000014` |
| `color-dark.subtle` | `CED4DA` | `1A1D20` |
| `color-dark.subtle-active` | `ADB5BD` | `2B2F32` |
| `color-dark.subtle-hover` | `BDC4CB` | `212529` |

## `color-error` — famille re-seedable par le thème du projet

| Clé | clair | sombre |
|---|---|---|
| `color-error.active` | `A62001` | `A62001` |
| `color-error.emphasis` | `DD2B0166` | `DD2B0199` |
| `color-error.error.opacity-active` | `DD2B0129` | `DD2B0129` |
| `color-error.error.opacity-focus` | `DD2B011F` | `DD2B011F` |
| `color-error.error.opacity-hover` | `DD2B0114` | `DD2B0114` |
| `color-error.hover` | `C12601` | `C12601` |
| `color-error.on-error` | `FFFFFF` | `FFFFFF` |
| `color-error.on-subtle` | `531000` | `E66041` |
| `color-error.on-surface` | `DD2B01` | `DD2B01` |
| `color-error.subtle` | `F7CAC0` | `1C0500` |
| `color-error.subtle-active` | `EE9580` | `531000` |
| `color-error.subtle-hover` | `F2B0A0` | `370B00` |

## `color-filetypes`

| Clé | clair | sombre |
|---|---|---|
| `color-filetypes.document.blue` | `0070DB` | `0070DB` |
| `color-filetypes.document.bold` | `0A58CA` | `80B8ED` |
| `color-filetypes.document.bolder` | `052C65` | `9FC9F2` |
| `color-filetypes.document.subtle` | `80B8ED` | `002A52` |
| `color-filetypes.document.subtler` | `BFDBF6` | `001C37` |
| `color-filetypes.pdf.bold` | `A62001` | `EE9580` |
| `color-filetypes.pdf.bolder` | `531000` | `F2B0A0` |
| `color-filetypes.pdf.red` | `DD2B01` | `DD2B01` |
| `color-filetypes.pdf.subtle` | `EE9580` | `531000` |
| `color-filetypes.pdf.subtler` | `F7CAC0` | `370B00` |
| `color-filetypes.presentation.bold` | `BF7500` | `FFCE80` |
| `color-filetypes.presentation.bolder` | `603B00` | `FFDA9F` |
| `color-filetypes.presentation.orange` | `FF9C00` | `FF9C00` |
| `color-filetypes.presentation.subtle` | `FFCE80` | `603B00` |
| `color-filetypes.presentation.subtler` | `FFE6BF` | `402700` |
| `color-filetypes.spreadsheet.bold` | `39833C` | `A6D7A8` |
| `color-filetypes.spreadsheet.bolder` | `1D421E` | `BCE1BD` |
| `color-filetypes.spreadsheet.green` | `4CAF50` | `4CAF50` |
| `color-filetypes.spreadsheet.subtle` | `A6D7A8` | `1D421E` |
| `color-filetypes.spreadsheet.subtler` | `D2EBD3` | `132C14` |

## `color-info` — famille re-seedable par le thème du projet

| Clé | clair | sombre |
|---|---|---|
| `color-info.active` | `78D4EC` | `78D4EC` |
| `color-info.emphasis` | `4BC6E566` | `4BC6E599` |
| `color-info.hover` | `62CDE8` | `62CDE8` |
| `color-info.info` | `4BC6E5` | `4BC6E5` |
| `color-info.on-info` | `133239` | `133239` |
| `color-info.on-subtle` | `1C4A56` | `8FDBEF` |
| `color-info.on-surface` | `4BC6E5` | `4BC6E5` |
| `color-info.opacity.opacity-active` | `4BC6E529` | `4BC6E529` |
| `color-info.opacity.opacity-focus` | `4BC6E51F` | `4BC6E51F` |
| `color-info.opacity.opacity-hover` | `4BC6E514` | `4BC6E514` |
| `color-info.subtle` | `D2F1F9` | `09191D` |
| `color-info.subtle-active` | `A5E3F2` | `1C4A56` |
| `color-info.subtle-hover` | `BCEAF5` | `133239` |

## `color-inverse`

| Clé | clair | sombre |
|---|---|---|
| `color-inverse.active` | `495057` | `DEE2E6` |
| `color-inverse.emphasis` | `00000066` | `495057` |
| `color-inverse.hover` | `343A40` | `E9ECEF` |
| `color-inverse.inverse` | `212529` | `F8F9FA` |
| `color-inverse.on-inverse` | `FFFFFF` | `000000` |
| `color-inverse.on-subtle` | `FFFFFF` | `F8F9FA` |
| `color-inverse.on-surface` | `343A40` | `F8F9FA` |
| `color-inverse.opacity.opacity-active` | `00000029` | `F8F9FA29` |
| `color-inverse.opacity.opacity-focus` | `0000001F` | `F8F9FA1F` |
| `color-inverse.opacity.opacity-hover` | `00000014` | `F8F9FA14` |
| `color-inverse.subtle` | `495057` | `343A40` |
| `color-inverse.subtle-active` | `5C636A` | `596169` |
| `color-inverse.subtle-hover` | `565E64` | `495057` |

## `color-light`

| Clé | clair | sombre |
|---|---|---|
| `color-light.active` | `C6C7C8` | `4D5154` |
| `color-light.emphasis` | `0000001A` | `4D5154` |
| `color-light.hover` | `D3D4D5` | `424649` |
| `color-light.light` | `FCFCFD` | `FCFCFD` |
| `color-light.on-light` | `424649` | `424649` |
| `color-light.on-subtle` | `4D5154` | `FCFCFD` |
| `color-light.on-surface` | `FCFCFD` | `FCFCFD` |
| `color-light.opacity.opacity-active` | `FCFCFD29` | `FCFCFD29` |
| `color-light.opacity.opacity-focus` | `FCFCFD1F` | `FCFCFD1F` |
| `color-light.opacity.opacity-hover` | `FCFCFD14` | `FCFCFD14` |
| `color-light.subtle` | `FCFCFD` | `4D5154` |
| `color-light.subtle-active` | `ECECEC` | `939597` |
| `color-light.subtle-hover` | `ECECEC` | `727577` |

## `color-primary` — famille re-seedable par le thème du projet

| Clé | clair | sombre |
|---|---|---|
| `color-primary.active` | `BF7500` | `BF7500` |
| `color-primary.emphasis` | `FF9C0066` | `FF9C0099` |
| `color-primary.hover` | `DF8900` | `DF8900` |
| `color-primary.on-primary` | `FFFFFF` | `FFFFFF` |
| `color-primary.on-subtle` | `603B00` | `FFB540` |
| `color-primary.on-surface` | `FF9C00` | `FF9C00` |
| `color-primary.opacity.fab-focus-ring` | `FF9C0080` | `FF9C0080` |
| `color-primary.opacity.fab-focus-ring 2` | `FF9C0080` | `FF9C0080` |
| `color-primary.opacity.fab-focus-ring 3` | `FF9C0080` | `FF9C0080` |
| `color-primary.opacity.grid-selected-bg` | `FF9C0040` | `FF9C0080` |
| `color-primary.opacity.opacity-active` | `FF9C0029` | `FF9C0029` |
| `color-primary.opacity.opacity-focus` | `FF9C001F` | `FF9C001F` |
| `color-primary.opacity.opacity-hover` | `FF9C0014` | `FF9C0014` |
| `color-primary.primary` | `FF9C00` | `FF9C00` |
| `color-primary.subtle` | `FFE6BF` | `201400` |
| `color-primary.subtle-active` | `FFCE80` | `603B00` |
| `color-primary.subtle-hover` | `FFDA9F` | `402700` |

## `color-secondary` — famille re-seedable par le thème du projet

| Clé | clair | sombre |
|---|---|---|
| `color-secondary.active` | `565E64` | `596169` |
| `color-secondary.emphasis` | `6C757D66` | `6C757D99` |
| `color-secondary.hover` | `5C636A` | `5C636A` |
| `color-secondary.on-secondary` | `FFFFFF` | `FFFFFF` |
| `color-secondary.on-subtle` | `2B2F32` | `A7ACB1` |
| `color-secondary.on-surface` | `5C636A` | `6C757D` |
| `color-secondary.opacity.opacity-active` | `6C757D29` | `6C757D29` |
| `color-secondary.opacity.opacity-focus` | `6C757D1F` | `6C757D1F` |
| `color-secondary.opacity.opacity-hover` | `6C757D14` | `6C757D14` |
| `color-secondary.secondary` | `6C757D` | `6C757D` |
| `color-secondary.subtle` | `DEE2E6` | `F8F9FA` |
| `color-secondary.subtle-active` | `BDC4CB` | `DEE2E6` |
| `color-secondary.subtle-hover` | `CED4DA` | `E9ECEF` |

## `color-series-a`

| Clé | clair | sombre |
|---|---|---|
| `color-series-a.bold` | `0A58CA` | `2082E0` |
| `color-series-a.bolder` | `052C65` | `60A6E9` |
| `color-series-a.series-a` | `0070DB` | `0070DB` |
| `color-series-a.subtle` | `2082E0` | `0054A4` |
| `color-series-a.subtler` | `60A6E9` | `002A52` |

## `color-series-b`

| Clé | clair | sombre |
|---|---|---|
| `color-series-b.bold` | `6219B0` | `A842BA` |
| `color-series-b.bolder` | `411175` | `C178CE` |
| `color-series-b.series-b` | `8221EA` | `9C27B0` |
| `color-series-b.subtle` | `923DED` | `751D84` |
| `color-series-b.subtler` | `B174F2` | `4E1458` |

## `color-series-c`

| Clé | clair | sombre |
|---|---|---|
| `color-series-c.bold` | `306D32` | `2ACA90` |
| `color-series-c.bolder` | `1D421E` | `86E1C0` |
| `color-series-c.series-c` | `4CAF50` | `0CC280` |
| `color-series-c.subtle` | `79C37C` | `087950` |
| `color-series-c.subtler` | `A6D7A8` | `054930` |

## `color-series-d`

| Clé | clair | sombre |
|---|---|---|
| `color-series-d.bold` | `066140` | `4CAF50` |
| `color-series-d.bolder` | `033120` | `8FCD92` |
| `color-series-d.series-d` | `099260` | `39833C` |
| `color-series-d.subtle` | `0CC280` | `265828` |
| `color-series-d.subtler` | `67D9B0` | `132C14` |

## `color-series-e`

| Clé | clair | sombre |
|---|---|---|
| `color-series-e.bold` | `BF3F00` | `E14621` |
| `color-series-e.bolder` | `802A00` | `EE9580` |
| `color-series-e.series-e` | `FF5400` | `DD2B01` |
| `color-series-e.subtle` | `FF6920` | `A62001` |
| `color-series-e.subtler` | `FFAA80` | `6F1601` |

## `color-series-f`

| Clé | clair | sombre |
|---|---|---|
| `color-series-f.bold` | `BF7500` | `FFC927` |
| `color-series-f.bolder` | `804E00` | `FFD865` |
| `color-series-f.series-f` | `FF9C00` | `FFC108` |
| `color-series-f.subtle` | `FFA820` | `BF9106` |
| `color-series-f.subtler` | `FFC160` | `806104` |

## `color-success` — famille re-seedable par le thème du projet

| Clé | clair | sombre |
|---|---|---|
| `color-success.active` | `265828` | `265828` |
| `color-success.emphasis` | `4CAF5066` | `4CAF5099` |
| `color-success.hover` | `306D32` | `306D32` |
| `color-success.on-subtle` | `132C14` | `79C37C` |
| `color-success.on-success` | `FFFFFF` | `FFFFFF` |
| `color-success.on-surface` | `39833C` | `39833C` |
| `color-success.opacity.opacity-active` | `4CAF5029` | `4CAF5029` |
| `color-success.opacity.opacity-focus` | `4CAF501F` | `4CAF501F` |
| `color-success.opacity.opacity-hover` | `4CAF5014` | `4CAF5014` |
| `color-success.subtle` | `D2EBD3` | `0A160A` |
| `color-success.subtle-active` | `A6D7A8` | `1D421E` |
| `color-success.subtle-hover` | `BCE1BD` | `132C14` |
| `color-success.success` | `39833C` | `39833C` |

## `color-tertiary` — famille re-seedable par le thème du projet

| Clé | clair | sombre |
|---|---|---|
| `color-tertiary.active` | `A842BA` | `A842BA` |
| `color-tertiary.emphasis` | `9C27B066` | `9C27B099` |
| `color-tertiary.hover` | `9C27B0` | `9C27B0` |
| `color-tertiary.on-subtle` | `62186E` | `B55DC4` |
| `color-tertiary.on-surface` | `9C27B0` | `89229A` |
| `color-tertiary.on-tertiary` | `FFFFFF` | `FFFFFF` |
| `color-tertiary.opacity.opacity-active` | `9C27B029` | `9C27B029` |
| `color-tertiary.opacity.opacity-focus` | `9C27B01F` | `9C27B01F` |
| `color-tertiary.opacity.opacity-hover` | `9C27B014` | `9C27B014` |
| `color-tertiary.subtle` | `E6C9EB` | `140516` |
| `color-tertiary.subtle-active` | `CE93D8` | `3B0F42` |
| `color-tertiary.subtle-hover` | `DAAEE1` | `270A2C` |
| `color-tertiary.tertiary` | `89229A` | `89229A` |

## `color-warning` — famille re-seedable par le thème du projet

| Clé | clair | sombre |
|---|---|---|
| `color-warning.active` | `FFD146` | `FFB540` |
| `color-warning.emphasis` | `FFC10866` | `FF9C0099` |
| `color-warning.hover` | `FFC927` | `FFA820` |
| `color-warning.on-subtle` | `604803` | `FFC160` |
| `color-warning.on-surface` | `FFC108` | `FF9C00` |
| `color-warning.on-warning` | `403002` | `402700` |
| `color-warning.opacity.opacity-active` | `FFC10829` | `FF9C0029` |
| `color-warning.opacity.opacity-focus` | `FFC1081F` | `FF9C001F` |
| `color-warning.opacity.opacity-hover` | `FFC10814` | `FF9C0014` |
| `color-warning.subtle` | `FFF0C1` | `201400` |
| `color-warning.subtle-active` | `FFE084` | `603B00` |
| `color-warning.subtle-hover` | `FFE8A2` | `402700` |
| `color-warning.warning` | `FFC108` | `FF9C00` |

## `color`

| Clé | clair | sombre |
|---|---|---|
| `color.app-surface` | `FFFFFF` | `1A1D20` |
| `color.border` | `00000040` | `E9ECEF26` |
| `color.border-alt` | `00000080` | `E9ECEF4D` |
| `color.on-app-surface` | `000000` | `CED4DA` |
| `color.opacity.SegmentedControl.segmentedcontrol-opacity-focus` | `00000059` | `E9ECEF59` |
| `color.opacity.disabled-foreground` | `0000005C` | `E9ECEF33` |
| `color.opacity.flat-hover-bg` | `00000014` | `E9ECEF0F` |
| `color.opacity.grid-hover-bg` | `00000017` | `E9ECEF2E` |
| `color.opacity.grid-sorted-bg` | `00000005` | `E9ECEF0A` |
| `color.opacity.link-hover-text` | `FFFFFF1A` | `0000001A` |
| `color.opacity.outline-border` | `00000080` | `E9ECEF80` |
| `color.opacity.overlay` | `FFFFFFCC` | `00000080` |
| `color.opacity.overlay-dark` | `000000B2` | `00000080` |
| `color.opacity.table-alt-row-bg` | `0000000D` | `E9ECEF1A` |
| `color.opacity.transparent` | `FFFFFF00` | `FFFFFF00` |
| `color.subtle` | `565E64` | `6C757D` |
| `color.surface` | `E9ECEF` | `212529` |
| `color.surface-alt` | `FFFFFF` | `1A1D20` |

## `maps`

| Clé | clair | sombre |
|---|---|---|
| `maps.callout-bg` | `E9ECEFCC` | `212529CC` |
| `maps.callout-separator` | `00000033` | `CED4DA33` |
| `maps.location-pin` | `5E9DC8FF` | `5E9DC8FF` |
| `maps.polygon-fill` | `DD2B0130` | `DD2B0130` |
| `maps.polygon-stroke` | `DD2B01FF` | `DD2B01FF` |
| `maps.route` | `FF9C00FF` | `FF9C00FF` |

## `survey`

| Clé | clair | sombre |
|---|---|---|
| `survey.pen` | `FF9C00FF` | `FF9C00FF` |

