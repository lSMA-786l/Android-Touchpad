import 'package:flutter/material.dart';

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
