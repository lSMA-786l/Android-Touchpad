import 'package:flutter/material.dart';

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
