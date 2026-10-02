import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:tpad_protocol/tpad_protocol.dart';

/// Owns the pairing PIN lifecycle and builds the QR payload.
///
/// NOTE (P1-B4): TLS certificate generation + fingerprint land here next;
/// [certFingerprint] is a placeholder until then.
class PairingService extends ChangeNotifier {
  String _pin = '';
  DateTime _expiresAt = DateTime.now();
  String _lanIp = '';
  Timer? _ticker;

  String get pin => _pin;
  String get lanIp => _lanIp;

  /// Placeholder until P1-B4 wires real TLS cert pinning.
  String get certFingerprint => 'PENDING-P1-B4';

  int get secondsLeft {
    final d = _expiresAt.difference(DateTime.now()).inSeconds;
    return d < 0 ? 0 : d;
  }

  bool get expired => secondsLeft == 0;

  /// QR payload scanned by the phone (see PROTOCOL.md section 2).
  String get qrPayload {
    final name = Uri.encodeComponent('TPad Receiver');
    return 'TPAD://$_lanIp:$kTcpPort'
        '?fp=$certFingerprint&pin=$_pin&name=$name';
  }

  Future<void> refresh() async {
    _lanIp = await _findLanIp();
    _newPin();
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (expired) _newPin(); // auto-rotate on expiry
      notifyListeners(); // tick the countdown
    });
    notifyListeners();
  }

  void regenerate() => _newPin();

  void _newPin() {
    _pin = (Random.secure().nextInt(900000) + 100000).toString();
    _expiresAt =
        DateTime.now().add(const Duration(seconds: kPairPinTtlSeconds));
    notifyListeners();
  }

  Future<String> _findLanIp() async {
    try {
      final ifs = await NetworkInterface.list(
        includeLoopback: false,
        type: InternetAddressType.IPv4,
      );
      for (final i in ifs) {
        for (final a in i.addresses) {
          if (!a.isLoopback) return a.address;
        }
      }
    } catch (_) {
      // fall through to loopback
    }
    return '127.0.0.1';
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }
}
