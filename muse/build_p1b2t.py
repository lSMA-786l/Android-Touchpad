#!/usr/bin/env python3
"""
P1-B2T: TPad shared design system (tpad_theme) + receiver retrofit.

What it does (run via Antigravity on SMA's machine):
  1. Requires P1-B1 + P1-B2 output — fails loudly otherwise.
  2. Creates packages/tpad_theme: primitives (brown/cyan/neutral ramps),
     4pt spacing, radius, typography (Bricolage Grotesk / Manrope /
     JetBrains Mono), semantic dark (black+brown) + light (white+cyan)
     themes, and the 5 core widgets (TPadButton, TPadCard, TPadInput,
     TPadSectionHeader, TPadLogLine).
  3. Checks the 3 bundled font files; prints loud download instructions
     when missing (fonts fall back to system until added).
  4. Retrofits the receiver app: adds the tpad_theme path dependency,
     switches app.dart to TPadTheme.dark(), rewrites the 4 screens to
     use tokens/widgets only (zero raw hex in widgets).
  5. Adds the UI-token rule to rules.md and the P1-B2T row to the root
     README batch table.
  6. Runs `flutter pub get` + `flutter analyze` in the receiver app.
  7. VERIFY: files exist, anchors present, no redactor damage.

Design decisions (agreed with SMA 2026-10-02):
  - Dark first: black + brown. Light: white + cyan (tokens defined,
    polish later).
  - Fonts (OFL 1.1, researched 2026-10-02): Bricolage Grotesque for
    display, Manrope for body, JetBrains Mono for PIN/log. Bundled as
    variable TTFs under packages/tpad_theme/assets/fonts/ (no runtime
    download — the app is LAN-only).

Run:
  python build_p1b2t.py [--dir tpad] [--no-flutter]
"""

import argparse
import os
import subprocess
import sys

# ------------------------------------------------------------------ files ---

THEME_PUBSPEC = r'''name: tpad_theme
description: Shared design tokens + core widgets for TPad apps (black/brown dark, white/cyan light).
version: 0.1.0

environment:
  sdk: ^3.4.0
  flutter: ">=3.22.0"

dependencies:
  flutter:
    sdk: flutter

flutter:
  fonts:
    - family: BricolageGrotesque
      fonts:
        - asset: assets/fonts/BricolageGrotesk-Variable.ttf
    - family: Manrope
      fonts:
        - asset: assets/fonts/Manrope-Variable.ttf
    - family: JetBrainsMono
      fonts:
        - asset: assets/fonts/JetBrainsMono-Variable.ttf
'''

THEME_README = r'''# tpad_theme

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
'''

BARREL = r'''/// TPad shared design tokens + core widgets.
library tpad_theme;

export 'src/primitives.dart';
export 'src/spacing.dart';
export 'src/typography.dart';
export 'src/theme.dart';
export 'src/widgets.dart';
'''

PRIMITIVES = r'''import 'package:flutter/material.dart';

/// Primitive color ramps — raw values. NEVER use these directly in
/// widgets; reference them through the semantic theme in theme.dart.
/// (Token layer 01: primitive.)
class TPadBrown {
  static const c50 = Color(0xFFFBF7F1);
  static const c100 = Color(0xFFF3E8D7);
  static const c200 = Color(0xFFE7CFA9);
  static const c300 = Color(0xFFD9AC77);
  static const c400 = Color(0xFFC98F52);
  static const c500 = Color(0xFFB07338);
  static const c600 = Color(0xFF8F5C2E);
  static const c700 = Color(0xFF734825);
  static const c800 = Color(0xFF57341C);
  static const c900 = Color(0xFF3D2413);
}

class TPadCyan {
  static const c50 = Color(0xFFECFEFF);
  static const c100 = Color(0xFFCFFAFE);
  static const c200 = Color(0xFFA5F3FC);
  static const c300 = Color(0xFF67E8F9);
  static const c400 = Color(0xFF22D3EE);
  static const c500 = Color(0xFF06B6D4);
  static const c600 = Color(0xFF0891B2);
  static const c700 = Color(0xFF0E7490);
  static const c800 = Color(0xFF155E75);
  static const c900 = Color(0xFF164E63);
}

/// Warm neutrals for the black+brown dark theme.
class TPadNeutralDark {
  static const bg = Color(0xFF100D0A);
  static const surface = Color(0xFF171310);
  static const container = Color(0xFF211B16);
  static const outline = Color(0xFF3A322B);
  static const text = Color(0xFFEFE9DD);
  static const textDim = Color(0xFFA89C8D);
}

/// Clean neutrals for the white+cyan light theme.
class TPadNeutralLight {
  static const bg = Color(0xFFFFFFFF);
  static const surface = Color(0xFFF7F7F5);
  static const container = Color(0xFFECECE8);
  static const outline = Color(0xFFD8D8D2);
  static const text = Color(0xFF1B1B19);
  static const textDim = Color(0xFF5C5C57);
}

/// Functional colors shared by both modes.
class TPadFunctional {
  static const warning = Color(0xFFE8A33D);
  static const danger = Color(0xFFE57373);
  static const success = Color(0xFF7BC47F);
}
'''

SPACING = r'''/// 4pt grid. If a number isn't divisible by 4, it doesn't ship.
class TPadSpacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;
}

class TPadRadius {
  static const double sm = 4;
  static const double md = 8;
  static const double lg = 16;
  static const double full = 999;
}
'''

TYPOGRAPHY = r'''import 'package:flutter/material.dart';

/// Font families (bundled variable TTFs, OFL 1.1).
class TPadFonts {
  static const display = 'BricolageGrotesque';
  static const body = 'Manrope';
  static const mono = 'JetBrainsMono';
}

/// Type scale: 12 / 14 / 16 / 20 / 24 / 32. System font is the fallback
/// when a bundled file is missing.
class TPadText {
  static const display = TextStyle(
    fontFamily: TPadFonts.display,
    fontSize: 32,
    fontWeight: FontWeight.w700,
    height: 1.1,
  );
  static const heading = TextStyle(
    fontFamily: TPadFonts.display,
    fontSize: 20,
    fontWeight: FontWeight.w600,
    height: 1.2,
  );
  static const body = TextStyle(
    fontFamily: TPadFonts.body,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.4,
  );
  static const caption = TextStyle(
    fontFamily: TPadFonts.body,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 1.3,
  );
  static const mono = TextStyle(
    fontFamily: TPadFonts.mono,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 1.4,
  );
  static const pin = TextStyle(
    fontFamily: TPadFonts.mono,
    fontSize: 32,
    fontWeight: FontWeight.w600,
    letterSpacing: 4,
    height: 1.2,
  );
}
'''

THEME = r'''import 'package:flutter/material.dart';

import 'primitives.dart';
import 'typography.dart';

/// Semantic theme (token layer 02). Dark = black + brown,
/// light = white + cyan. Components only ever touch this layer.
class TPadTheme {
  static ThemeData dark() {
    final scheme = ColorScheme.dark(
      primary: TPadBrown.c400,
      onPrimary: TPadNeutralDark.bg,
      secondary: TPadBrown.c300,
      onSecondary: TPadNeutralDark.bg,
      surface: TPadNeutralDark.surface,
      onSurface: TPadNeutralDark.text,
      onSurfaceVariant: TPadNeutralDark.textDim,
      surfaceContainerHighest: TPadNeutralDark.container,
      outline: TPadNeutralDark.outline,
      error: TPadFunctional.danger,
    );
    return ThemeData(
      colorScheme: scheme,
      scaffoldBackgroundColor: TPadNeutralDark.bg,
      useMaterial3: true,
      fontFamily: TPadFonts.body,
      textTheme: const TextTheme(
        displayLarge: TPadText.display,
        titleLarge: TPadText.heading,
        bodyMedium: TPadText.body,
        bodySmall: TPadText.caption,
      ),
    );
  }

  static ThemeData light() {
    final scheme = ColorScheme.light(
      primary: TPadCyan.c600,
      onPrimary: TPadNeutralLight.bg,
      secondary: TPadCyan.c500,
      onSecondary: TPadNeutralLight.bg,
      surface: TPadNeutralLight.surface,
      onSurface: TPadNeutralLight.text,
      onSurfaceVariant: TPadNeutralLight.textDim,
      surfaceContainerHighest: TPadNeutralLight.container,
      outline: TPadNeutralLight.outline,
      error: TPadFunctional.danger,
    );
    return ThemeData(
      colorScheme: scheme,
      scaffoldBackgroundColor: TPadNeutralLight.bg,
      useMaterial3: true,
      fontFamily: TPadFonts.body,
      textTheme: const TextTheme(
        displayLarge: TPadText.display,
        titleLarge: TPadText.heading,
        bodyMedium: TPadText.body,
        bodySmall: TPadText.caption,
      ),
    );
  }
}
'''

WIDGETS = r'''import 'package:flutter/material.dart';

import 'spacing.dart';
import 'typography.dart';

/// The 5 core widgets (token layer 03). Everything in both apps is
/// built from these — no one-off styled widgets, no raw hex.

enum TPadButtonType { primary, secondary, ghost }

enum TPadButtonSize { sm, md, lg }

class TPadButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final TPadButtonType type;
  final TPadButtonSize size;

  const TPadButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
    this.type = TPadButtonType.primary,
    this.size = TPadButtonSize.md,
  });

  @override
  Widget build(BuildContext context) {
    final height = switch (size) {
      TPadButtonSize.sm => 36.0,
      TPadButtonSize.md => 48.0,
      TPadButtonSize.lg => 56.0,
    };
    final hPad = switch (size) {
      TPadButtonSize.sm => 16.0,
      TPadButtonSize.md => 24.0,
      TPadButtonSize.lg => 32.0,
    };
    final style = ButtonStyle(
      minimumSize: WidgetStatePropertyAll(Size(hPad * 2, height)),
      padding: WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: hPad)),
      shape: WidgetStatePropertyAll(
        RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(TPadRadius.md),
        ),
      ),
      textStyle: const WidgetStatePropertyAll(TPadText.body),
    );
    final child = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[
          Icon(icon, size: 20),
          const SizedBox(width: TPadSpacing.xs),
        ],
        Text(label),
      ],
    );
    switch (type) {
      case TPadButtonType.primary:
        return FilledButton(
            onPressed: onPressed, style: style, child: child);
      case TPadButtonType.secondary:
        return OutlinedButton(
            onPressed: onPressed, style: style, child: child);
      case TPadButtonType.ghost:
        return TextButton(
            onPressed: onPressed, style: style, child: child);
    }
  }
}

class TPadCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const TPadCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(TPadSpacing.md),
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(TPadRadius.lg),
      ),
      margin: EdgeInsets.zero,
      child: Padding(padding: padding, child: child),
    );
  }
}

class TPadInput extends StatelessWidget {
  final String? label;
  final String? hint;
  final TextEditingController? controller;
  final bool obscure;
  final TextInputType keyboard;

  const TPadInput({
    super.key,
    this.label,
    this.hint,
    this.controller,
    this.obscure = false,
    this.keyboard = TextInputType.text,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return TextField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboard,
      style: TPadText.body.copyWith(color: scheme.onSurface),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(TPadRadius.md),
        ),
      ),
    );
  }
}

class TPadSectionHeader extends StatelessWidget {
  final String title;

  const TPadSectionHeader(this.title, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: TPadSpacing.sm),
      child: Text(
        title.toUpperCase(),
        style: TPadText.caption.copyWith(
          color: Theme.of(context).colorScheme.onSurfaceVariant,
          letterSpacing: 1.2,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class TPadLogLine extends StatelessWidget {
  final String line;

  const TPadLogLine(this.line, {super.key});

  @override
  Widget build(BuildContext context) {
    return SelectableText(
      line,
      style: TPadText.mono
          .copyWith(color: Theme.of(context).colorScheme.onSurface),
    );
  }
}
'''

# --- receiver retrofit: full-file rewrites (themed, zero raw hex) ---

APP_DART_THEMED = r'''import 'dart:async';

import 'package:flutter/material.dart';
import 'package:tpad_theme/tpad_theme.dart';

import 'screens/devices_screen.dart';
import 'screens/log_screen.dart';
import 'screens/pairing_screen.dart';
import 'screens/settings_screen.dart';
import 'services/log_service.dart';
import 'services/net_server.dart';
import 'services/pairing_service.dart';

/// Service singletons for the receiver app.
class ReceiverServices {
  static final log = LogService();
  static final pairing = PairingService();
  static final net = NetServer(log: log);
}

class TPadApp extends StatefulWidget {
  const TPadApp({super.key});

  @override
  State<TPadApp> createState() => _TPadAppState();
}

class _TPadAppState extends State<TPadApp> {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(ReceiverServices.net.start());
      unawaited(ReceiverServices.pairing.refresh());
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TPad Receiver',
      debugShowCheckedModeBanner: false,
      theme: TPadTheme.dark(),
      home: Scaffold(
        appBar: AppBar(title: const Text('TPad Receiver')),
        body: IndexedStack(
          index: _tab,
          children: const [
            PairingScreen(),
            DevicesScreen(),
            LogScreen(),
            SettingsScreen(),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _tab,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.qr_code_2), label: 'Pair'),
            NavigationDestination(icon: Icon(Icons.devices), label: 'Devices'),
            NavigationDestination(icon: Icon(Icons.terminal), label: 'Log'),
            NavigationDestination(
                icon: Icon(Icons.settings), label: 'Settings'),
          ],
        ),
      ),
    );
  }
}
'''

PAIRING_SCREEN_THEMED = r'''import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:tpad_theme/tpad_theme.dart';

import '../app.dart';

class PairingScreen extends StatelessWidget {
  const PairingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final pairing = ReceiverServices.pairing;
    final scheme = Theme.of(context).colorScheme;
    return ListenableBuilder(
      listenable: pairing,
      builder: (context, _) {
        return Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(TPadSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Scan with the TPad phone app',
                    style: TPadText.heading),
                const SizedBox(height: TPadSpacing.md),
                // White card behind the QR: scanners need contrast.
                Container(
                  padding: const EdgeInsets.all(TPadSpacing.sm),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius:
                        BorderRadius.circular(TPadRadius.lg),
                  ),
                  child: QrImageView(
                    data: pairing.qrPayload,
                    version: QrVersions.auto,
                    size: 220,
                  ),
                ),
                const SizedBox(height: TPadSpacing.md),
                Text('PIN  ${pairing.pin}',
                    style: TPadText.pin
                        .copyWith(color: scheme.primary)),
                Text('expires in ${pairing.secondsLeft}s',
                    style: TPadText.caption.copyWith(
                        color: scheme.onSurfaceVariant)),
                const SizedBox(height: TPadSpacing.sm),
                TPadButton(
                  label: 'New PIN',
                  icon: Icons.refresh,
                  type: TPadButtonType.secondary,
                  onPressed: pairing.regenerate,
                ),
                const SizedBox(height: TPadSpacing.sm),
                Text('Listening on ${pairing.lanIp}',
                    style: TPadText.caption.copyWith(
                        color: scheme.onSurfaceVariant)),
                Text('TLS fingerprint arrives in P1-B4',
                    style: TPadText.caption
                        .copyWith(color: TPadFunctional.warning)),
              ],
            ),
          ),
        );
      },
    );
  }
}
'''

DEVICES_SCREEN_THEMED = r'''import 'package:flutter/material.dart';
import 'package:tpad_theme/tpad_theme.dart';

import '../app.dart';

/// Placeholder: device approval, per-device permissions, and kick
/// arrive in P1-B4.
class DevicesScreen extends StatelessWidget {
  const DevicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final net = ReceiverServices.net;
    final scheme = Theme.of(context).colorScheme;
    return ListenableBuilder(
      listenable: net,
      builder: (context, _) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.devices,
                  size: 48, color: scheme.onSurfaceVariant),
              const SizedBox(height: TPadSpacing.sm),
              Text('${net.clientCount} connected client(s)',
                  style: TPadText.heading),
              const SizedBox(height: TPadSpacing.xs),
              Text(
                'Device approval, per-device permissions,\nand kick arrive in P1-B4.',
                textAlign: TextAlign.center,
                style: TPadText.caption
                    .copyWith(color: scheme.onSurfaceVariant),
              ),
            ],
          ),
        );
      },
    );
  }
}
'''

LOG_SCREEN_THEMED = r'''import 'package:flutter/material.dart';
import 'package:tpad_theme/tpad_theme.dart';

import '../app.dart';

class LogScreen extends StatelessWidget {
  const LogScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final log = ReceiverServices.log;
    return ListenableBuilder(
      listenable: log,
      builder: (context, _) {
        final lines = log.lines;
        return Column(
          children: [
            Expanded(
              child: lines.isEmpty
                  ? Center(
                      child: Text('No events yet.',
                          style: TPadText.caption.copyWith(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant)))
                  : ListView.builder(
                      padding:
                          const EdgeInsets.all(TPadSpacing.sm),
                      itemCount: lines.length,
                      itemBuilder: (context, i) =>
                          TPadLogLine(lines[i]),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(TPadSpacing.xs),
              child: TPadButton(
                label: 'Clear',
                icon: Icons.delete_outline,
                type: TPadButtonType.ghost,
                size: TPadButtonSize.sm,
                onPressed: log.clear,
              ),
            ),
          ],
        );
      },
    );
  }
}
'''

SETTINGS_SCREEN_THEMED = r'''import 'package:flutter/material.dart';
import 'package:tpad_protocol/tpad_protocol.dart';
import 'package:tpad_theme/tpad_theme.dart';

import '../app.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final net = ReceiverServices.net;
    return ListenableBuilder(
      listenable: net,
      builder: (context, _) {
        return ListView(
          padding: const EdgeInsets.all(TPadSpacing.md),
          children: [
            const TPadSectionHeader('Network'),
            ListTile(
              title: const Text('TCP port'),
              subtitle:
                  Text('$kTcpPort (TLS lands in P1-B4)'),
              leading: const Icon(Icons.security),
            ),
            ListTile(
              title: const Text('UDP port'),
              subtitle: Text('$kUdpPort'),
              leading: const Icon(Icons.speed),
            ),
            SwitchListTile(
              title: const Text('Listeners running'),
              value: net.running,
              onChanged: (v) => v ? net.start() : net.stop(),
            ),
            const Divider(),
            const TPadSectionHeader('System'),
            const ListTile(
              title: Text('Start with Windows'),
              subtitle:
                  Text('Arrives in a later batch (registry entry).'),
              leading: Icon(Icons.power_settings_new),
            ),
          ],
        );
      },
    );
  }
}
'''

RECEIVER_PUBSPEC = r'''name: tpad_receiver
description: TPad Windows receiver — tray app turning phone touch input into mouse/keyboard actions.
publish_to: "none"
version: 0.1.0

environment:
  sdk: ^3.4.0

dependencies:
  flutter:
    sdk: flutter
  tpad_protocol:
    path: ../../packages/tpad_protocol
  tpad_theme:
    path: ../../packages/tpad_theme
  tray_manager: ^0.5.0
  window_manager: ^0.4.0
  qr_flutter: ^4.1.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0

flutter:
  uses-material-design: true
  assets:
    - assets/tray_icon.png
'''

FILES = {
    # --- tpad_theme package ---
    "packages/tpad_theme/pubspec.yaml": THEME_PUBSPEC,
    "packages/tpad_theme/README.md": THEME_README,
    "packages/tpad_theme/lib/tpad_theme.dart": BARREL,
    "packages/tpad_theme/lib/src/primitives.dart": PRIMITIVES,
    "packages/tpad_theme/lib/src/spacing.dart": SPACING,
    "packages/tpad_theme/lib/src/typography.dart": TYPOGRAPHY,
    "packages/tpad_theme/lib/src/theme.dart": THEME,
    "packages/tpad_theme/lib/src/widgets.dart": WIDGETS,
    # --- receiver retrofit (themed rewrites) ---
    "apps/tpad_receiver/pubspec.yaml": RECEIVER_PUBSPEC,
    "apps/tpad_receiver/lib/app.dart": APP_DART_THEMED,
    "apps/tpad_receiver/lib/screens/pairing_screen.dart":
        PAIRING_SCREEN_THEMED,
    "apps/tpad_receiver/lib/screens/devices_screen.dart":
        DEVICES_SCREEN_THEMED,
    "apps/tpad_receiver/lib/screens/log_screen.dart": LOG_SCREEN_THEMED,
    "apps/tpad_receiver/lib/screens/settings_screen.dart":
        SETTINGS_SCREEN_THEMED,
}

# (path, anchor that must be present)
ANCHORS = [
    ("packages/tpad_theme/pubspec.yaml", "name: tpad_theme"),
    ("packages/tpad_theme/README.md", "TPadBrown"),
    ("packages/tpad_theme/lib/tpad_theme.dart", "export 'src/widgets.dart'"),
    ("packages/tpad_theme/lib/src/primitives.dart", "class TPadBrown"),
    ("packages/tpad_theme/lib/src/primitives.dart", "class TPadCyan"),
    ("packages/tpad_theme/lib/src/spacing.dart", "class TPadSpacing"),
    ("packages/tpad_theme/lib/src/typography.dart", "BricolageGrotesque"),
    ("packages/tpad_theme/lib/src/theme.dart", "static ThemeData dark()"),
    ("packages/tpad_theme/lib/src/theme.dart", "static ThemeData light()"),
    ("packages/tpad_theme/lib/src/widgets.dart", "class TPadButton"),
    ("packages/tpad_theme/lib/src/widgets.dart", "class TPadLogLine"),
    ("apps/tpad_receiver/pubspec.yaml", "tpad_theme:"),
    ("apps/tpad_receiver/pubspec.yaml",
     "path: ../../packages/tpad_theme"),
    ("apps/tpad_receiver/lib/app.dart", "TPadTheme.dark()"),
    ("apps/tpad_receiver/lib/screens/pairing_screen.dart", "TPadButton"),
    ("apps/tpad_receiver/lib/screens/log_screen.dart", "TPadLogLine"),
]

# (rel path under packages/tpad_theme, download URL) — OFL 1.1 variable TTFs.
FONTS = {
    "assets/fonts/BricolageGrotesk-Variable.ttf":
        "https://github.com/google/fonts/raw/main/ofl/bricolagegrotesque/"
        "BricolageGrotesque%5Bopsz%2Cwght%5D.ttf",
    "assets/fonts/Manrope-Variable.ttf":
        "https://github.com/google/fonts/raw/main/ofl/manrope/"
        "Manrope%5Bwght%5D.ttf",
    "assets/fonts/JetBrainsMono-Variable.ttf":
        "https://github.com/google/fonts/raw/main/ofl/jetbrainsmono/"
        "JetBrainsMono%5Bwght%5D.ttf",
}

# README batch-table row inserted after the P1-B2 row.
README_ROW_ANCHOR = \
    "| P1-B2 | DELIVERED | Windows scaffold: tray app, QR pairing screen, listeners |"
README_ROW_INSERT = \
    "| P1-B2T | DELIVERED | Shared theme package (tokens + 5 widgets) + receiver retrofit |"

# rules.md gets the UI-token rule appended to the code section.
RULES_ANCHOR = "- Minimal diffs. Do not reformat unrelated code."
RULES_ADDITION = (
    "- Minimal diffs. Do not reformat unrelated code.\n"
    "- UI: tokens only — zero raw hex/colors in widgets. Primitives live in\n"
    "  tpad_theme; widgets reference semantic tokens (see tpad_theme/README.md)."
)


def run(cmd, cwd, timeout=600):
    print("  $ " + " ".join(cmd))
    try:
        p = subprocess.run(
            cmd, cwd=cwd, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
    except FileNotFoundError:
        return None, "command not found: " + cmd[0]
    except subprocess.TimeoutExpired:
        return None, "timed out after %ds" % timeout
    return p.returncode, p.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description="P1-B2T builder: theme + retrofit")
    ap.add_argument("--dir", default="tpad", help="project root (B1+B2)")
    ap.add_argument("--no-flutter", action="store_true",
                    help="only write files; skip flutter pub/analyze")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)
    app_dir = os.path.join(root, "apps", "tpad_receiver")

    # --- 0. B1 + B2 must have run ---
    for need in (os.path.join(root, "packages", "tpad_protocol",
                              "pubspec.yaml"),
                 os.path.join(app_dir, "pubspec.yaml")):
        if not os.path.isfile(need):
            print("!! Missing: " + need)
            print("!! Run build_p1b1.py then build_p1b2.py first.")
            return 1

    # --- 1. write files ---
    print("== P1-B2T: writing tpad_theme + retrofit ==")
    for rel, content in FILES.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("  wrote %-58s %6d bytes" % (rel, len(content.encode("utf-8"))))

    # --- 2. fonts check (loud instructions, not fatal) ---
    print("== fonts ==")
    theme_dir = os.path.join(root, "packages", "tpad_theme")
    for rel, url in FONTS.items():
        p = os.path.join(theme_dir, rel)
        if os.path.isfile(p) and os.path.getsize(p) > 1024:
            print("  ok   " + rel)
        else:
            print("  !! FONT MISSING: " + rel)
            print("     download (OFL 1.1, free): " + url)
            print("     save it to: " + p)
            print("     (UI falls back to system fonts until added)")

    # --- 3. root README batch row ---
    readme = os.path.join(root, "README.md")
    if os.path.isfile(readme):
        with open(readme, "r", encoding="utf-8") as f:
            text = f.read()
        if README_ROW_ANCHOR in text and "P1-B2T" not in text:
            text = text.replace(
                README_ROW_ANCHOR,
                README_ROW_ANCHOR + "\n" + README_ROW_INSERT)
            with open(readme, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            print("  batch table: P1-B2T row added")
        elif "P1-B2T" in text:
            print("  batch table: P1-B2T row already present")
        else:
            print("  !! ANCHOR NOT FOUND: P1-B2 row in README.md")
    else:
        print("  !! ANCHOR NOT FOUND: tpad/README.md missing")

    # --- 4. rules.md UI-token rule ---
    rules = os.path.join(root, "rules.md")
    if os.path.isfile(rules):
        with open(rules, "r", encoding="utf-8") as f:
            text = f.read()
        if "zero raw hex" in text:
            print("  rules.md: UI-token rule already present")
        elif RULES_ANCHOR in text:
            text = text.replace(RULES_ANCHOR, RULES_ADDITION)
            with open(rules, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            print("  rules.md: UI-token rule added")
        else:
            print("  !! ANCHOR NOT FOUND: code-rule line in rules.md")
    else:
        print("  !! ANCHOR NOT FOUND: tpad/rules.md missing")

    # --- 5. pub get + analyze (real toolchain only) ---
    if not args.no_flutter:
        print("== flutter pub get ==")
        rc, out = run(["flutter", "pub", "get"], cwd=app_dir, timeout=600)
        print(out[-3000:] if out else "")
        if rc != 0:
            print("!! flutter pub get failed — send the output back.")
            return 1
        print("== flutter analyze ==")
        rc, out = run(["flutter", "analyze"], cwd=app_dir, timeout=600)
        print(out[-4000:] if out else "")
        if "No issues found!" in (out or ""):
            print("ANALYZE: clean")
        else:
            print("ANALYZE: has findings — review above (DELIVERED, not "
                  "COMPLETE, until clean + tap-tested)")

    # --- 6. VERIFY ---
    print("== VERIFY ==")
    failures = []
    for rel, anchor in ANCHORS:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            failures.append("MISSING FILE: " + rel)
            continue
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        if "<redacted>" in text:
            failures.append("REDACTOR DAMAGE in " + rel)
        if anchor not in text:
            failures.append("ANCHOR NOT FOUND in %s: %r" % (rel, anchor))

    if failures:
        print("VERIFY FAILED:")
        for fl in failures:
            print("  !! " + fl)
        return 1

    print("VERIFY OK — %d files, all anchors present, no redactor damage"
          % len(FILES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
