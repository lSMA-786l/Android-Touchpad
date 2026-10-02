# tpad_theme

Shared design system for TPad. Both the Windows receiver and the Android
controller import this — one source of truth for color, type, spacing,
and the 5 core widgets. Follows the primitive -> semantic -> component
token model.

## Token model

| Layer | What | Example |
|---|---|---|
| 01 · Primitive | the raw value | `TPadBrown.c500` = `#B07338` |
| 02 · Semantic | what it means | dark `colorScheme.primary` = `TPadBrown.c400` |
| 03 · Component | where it lives | `TPadButton` primary bg = `colorScheme.primary` |

Rebrand = swap one primitive. Dark/light mode = remap the semantic
layer in `TPadTheme`. Components never change.

**Rule: zero raw hex inside widgets.** Primitives live in
`src/primitives.dart`; widgets only touch the theme / semantic tokens.

## Foundations

- Color: brown ramp (dark primary), cyan ramp (light primary),
  warm neutrals for dark, clean neutrals for light.
- Type scale: 12 / 14 / 16 / 20 / 24 / 32.
- Spacing: 4pt grid (4, 8, 16, 24, 32, 48). Radius: 4 / 8 / 16 / full.
- Dark theme: black + brown. Light theme: white + cyan.

## Fonts (OFL 1.1, researched 2026-10-02)

- Display: **Bricolage Grotesque** (variable) — expressive headings.
- Body: **Manrope** (variable) — UI text.
- Mono: **JetBrains Mono** (variable) — PIN, log lines.

Bundled under `assets/fonts/` (variable TTFs) so the app works fully
offline — no runtime font fetching on a LAN-only app. If a file is
missing, `TPadFonts` falls back to the system font; the builder script
prints the download URLs.

## Core widgets (5 — not 50)

- `TPadButton` — primary / secondary / ghost x sm / md / lg
- `TPadCard` — padded surface card
- `TPadInput` — labeled text field
- `TPadSectionHeader` — small-caps section label
- `TPadLogLine` — mono log line
