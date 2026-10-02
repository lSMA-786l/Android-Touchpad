import 'dart:typed_data';

import 'package:crypto/crypto.dart';

/// Binary pointer packet sent over UDP. Exactly [size] bytes, big-endian.
///
/// Layout:
///   0-1 : magic 0x5450 ("TP")
///   2   : version 0x01
///   3   : flags (bit0 leftDown, bit1 rightDown, bit2 middleDown)
///   4-7 : seq uint32 (per-device, strictly increasing)
///   8-15: timestampMs uint64 (sender epoch millis)
///   16-17: dx int16 — hundredths of a logical pixel, signed
///   18-19: dy int16
///   20-21: scrollDx int16 (two-finger scroll; 0 otherwise)
///   22-23: scrollDy int16
///   24-39: HMAC-SHA256(deviceKey, bytes 0..23), truncated to 16 bytes
///
/// Deltas are RELATIVE and device-independent: the phone sends raw logical
/// pixels (x100) and the RECEIVER applies sensitivity/acceleration/smoothing.
/// The receiver must drop packets with stale seq (<= last seen per device).
class UdpPointerPacket {
  static const int size = 40;
  static const int headerSize = 24;
  static const int magic = 0x5450;
  static const int version = 0x01;

  static const int flagLeftDown = 0x01;
  static const int flagRightDown = 0x02;
  static const int flagMiddleDown = 0x04;

  final int seq;
  final int timestampMs;
  final int flags;
  final int dx;
  final int dy;
  final int scrollDx;
  final int scrollDy;

  const UdpPointerPacket({
    required this.seq,
    required this.timestampMs,
    this.flags = 0,
    this.dx = 0,
    this.dy = 0,
    this.scrollDx = 0,
    this.scrollDy = 0,
  });

  /// Build from logical-pixel doubles; values are quantized to
  /// hundredths and clamped to int16 range.
  factory UdpPointerPacket.fromPixels({
    required int seq,
    int? timestampMs,
    int flags = 0,
    double dx = 0,
    double dy = 0,
    double scrollDx = 0,
    double scrollDy = 0,
  }) {
    int q(double v) => (v * 100).round().clamp(-32768, 32767);
    return UdpPointerPacket(
      seq: seq,
      timestampMs: timestampMs ?? DateTime.now().millisecondsSinceEpoch,
      flags: flags,
      dx: q(dx),
      dy: q(dy),
      scrollDx: q(scrollDx),
      scrollDy: q(scrollDy),
    );
  }

  /// Encode to 40 bytes. [deviceKey] is the 32 raw bytes of the pairing
  /// token (hex-decoded on both sides).
  Uint8List encode(List<int> deviceKey) {
    final out = Uint8List(size);
    final w = ByteData.sublistView(out, 0, headerSize);
    w.setUint16(0, magic, Endian.big);
    w.setUint8(2, version);
    w.setUint8(3, flags);
    w.setUint32(4, seq, Endian.big);
    w.setUint64(8, timestampMs, Endian.big);
    w.setInt16(16, dx, Endian.big);
    w.setInt16(18, dy, Endian.big);
    w.setInt16(20, scrollDx, Endian.big);
    w.setInt16(22, scrollDy, Endian.big);
    final mac = Hmac(sha256, deviceKey).convert(out.sublist(0, headerSize)).bytes;
    out.setRange(headerSize, size, mac.sublist(0, 16));
    return out;
  }

  /// Decode and verify. Returns null on bad length, magic, version,
  /// or HMAC mismatch. Callers must ALSO enforce seq freshness.
  static UdpPointerPacket? decode(Uint8List raw, List<int> deviceKey) {
    if (raw.length != size) return null;
    final r = ByteData.sublistView(raw, 0, headerSize);
    if (r.getUint16(0, Endian.big) != magic) return null;
    if (r.getUint8(2) != version) return null;
    final mac =
        Hmac(sha256, deviceKey).convert(raw.sublist(0, headerSize)).bytes;
    var ok = 0;
    for (var i = 0; i < 16; i++) {
      ok |= raw[headerSize + i] ^ mac[i];
    }
    if (ok != 0) return null;
    return UdpPointerPacket(
      seq: r.getUint32(4, Endian.big),
      timestampMs: r.getUint64(8, Endian.big),
      flags: r.getUint8(3),
      dx: r.getInt16(16, Endian.big),
      dy: r.getInt16(18, Endian.big),
      scrollDx: r.getInt16(20, Endian.big),
      scrollDy: r.getInt16(22, Endian.big),
    );
  }

  double get dxPx => dx / 100.0;
  double get dyPx => dy / 100.0;
  double get scrollDxPx => scrollDx / 100.0;
  double get scrollDyPx => scrollDy / 100.0;

  bool get leftDown => (flags & flagLeftDown) != 0;
  bool get rightDown => (flags & flagRightDown) != 0;
  bool get middleDown => (flags & flagMiddleDown) != 0;
}
