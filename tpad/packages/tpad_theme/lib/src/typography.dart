import 'package:flutter/material.dart';

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
