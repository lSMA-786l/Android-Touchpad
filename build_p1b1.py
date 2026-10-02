#!/usr/bin/env python3
"""
P1-B1: TPad protocol spec + shared Dart codec package.

What it does:
  Creates the `tpad/` project root and the pure-Dart `tpad_protocol`
  package inside it (no Flutter dependency). This package is the message
  contract that BOTH the Windows receiver app and the Android controller
  app will import. Everything else in Phase 1 builds on this.

Run (via Antigravity on SMA's machine):
  python build_p1b1.py [--dir tpad]

Output tree:
  tpad/
    README.md                <- project readme (what/why/how to run)
    rules.md                 <- project rules: read before writing any code
    design.md                <- system design: components, flows, screens
    packages/tpad_protocol/
      pubspec.yaml
      README.md
      PROTOCOL.md            <- the full protocol spec, read this first
      lib/tpad_protocol.dart
      lib/src/consts.dart
      lib/src/actions.dart
      lib/src/messages.dart
      lib/src/tcp_frame.dart
      lib/src/udp_packet.dart
      test/codec_test.dart

Next step after running: `cd tpad/packages/tpad_protocol && dart pub get && dart test`
(requires the Flutter/Dart toolchain on this machine).
"""

import argparse
import os
import sys

# ---------------------------------------------------------------- files ---

PUBSPEC = r'''name: tpad_protocol
description: Shared protocol codec for the TPad phone-as-touchpad project (pure Dart, no Flutter).
version: 0.1.0

environment:
  sdk: ^3.4.0

dependencies:
  crypto: ^3.0.3

dev_dependencies:
  test: ^1.24.0
'''

PKG_README = r'''# tpad_protocol

Pure-Dart protocol codec shared by the TPad Windows receiver and the
Android controller. No Flutter dependency — import it from both apps.

Contents:
- `PROTOCOL.md` — the full wire spec (ports, pairing, packet layouts,
  message types, security rules). Read this before touching the code.
- `lib/src/consts.dart` — ports, protocol version, limits.
- `lib/src/actions.dart` — closed action set (string tags, mouse buttons,
  media/presenter commands). The receiver ONLY executes these.
- `lib/src/messages.dart` — `ControlMessage` envelope + factories.
- `lib/src/tcp_frame.dart` — length-prefixed framing + stream decoder.
- `lib/src/udp_packet.dart` — 40-byte binary pointer packet + HMAC.
- `test/codec_test.dart` — round-trip tests. Run with `dart test`.
'''

CONSTS = r'''/// Shared constants for the TPad protocol v1.
library;

/// Protocol version negotiated in `hello`.
const int kProtocolVersion = 1;

/// TCP control channel (TLS) port.
const int kTcpPort = 47900;

/// UDP pointer-stream port.
const int kUdpPort = 47901;

/// mDNS service name advertised by the receiver (optional discovery).
const String kMdnsService = '_tpad._tcp';

/// How long a pairing PIN stays valid (seconds).
const int kPairPinTtlSeconds = 120;

/// Max failed PIN attempts before the PIN is regenerated.
const int kPairPinMaxAttempts = 3;

/// Largest TCP frame the receiver will accept (bytes). Bigger -> dropped.
const int kMaxTcpFrameBytes = 4 * 1024 * 1024;

/// Keepalive ping interval (seconds) and silence timeout (seconds).
const int kKeepaliveSeconds = 15;
const int kSilenceTimeoutSeconds = 45;

/// Max UDP pointer packets per second accepted from one device.
const int kMaxUdpPerSecond = 240;

/// Max TCP control messages per second accepted from one device.
const int kMaxTcpPerSecond = 60;

/// Max allowed |now - ts| on a control message envelope (milliseconds).
const int kMaxClockSkewMs = 60000;
'''

ACTIONS = r'''/// Closed action set for the TPad protocol.
///
/// The receiver ONLY executes the message types listed here. There is
/// deliberately NO "run arbitrary command" action — see PROTOCOL.md §6.
library;

/// Message type tags for the TCP control channel.
class MsgType {
  MsgType._();
  static const hello = 'hello';
  static const helloAck = 'hello_ack';
  static const pairRequest = 'pair_request';
  static const pairConfirm = 'pair_confirm';
  static const click = 'click';
  static const key = 'key';
  static const macroFire = 'macro_fire';
  static const media = 'media';
  static const presenter = 'presenter';
  static const ping = 'ping';
  static const pong = 'pong';
  static const error = 'error';
}

/// Mouse buttons for [MsgType.click] (`data.button`).
class MouseButton {
  MouseButton._();
  static const left = 'left';
  static const right = 'right';
  static const middle = 'middle';
}

/// Click actions for [MsgType.click] (`data.action`).
class ClickAction {
  ClickAction._();
  static const down = 'down';
  static const up = 'up';

  /// Atomic down+up, for taps.
  static const tap = 'tap';
}

/// Media commands for [MsgType.media] (`data.command`).
class MediaCmd {
  MediaCmd._();
  static const playPause = 'play_pause';
  static const next = 'next';
  static const prev = 'prev';
  static const volUp = 'vol_up';
  static const volDown = 'vol_down';
  static const mute = 'mute';
}

/// Presenter commands for [MsgType.presenter] (`data.command`).
class PresenterCmd {
  PresenterCmd._();
  static const next = 'next';
  static const prev = 'prev';
  static const blank = 'blank';
}

/// Key actions for [MsgType.key] (`data.action`).
/// `data.vk` is a Windows virtual-key code (int).
class KeyAction {
  KeyAction._();
  static const down = 'down';
  static const up = 'up';
  static const press = 'press';
}

/// Error codes for [MsgType.error] (`data.code`).
class ErrorCode {
  ErrorCode._();
  static const badToken = 'bad_token';
  static const badPin = 'bad_pin';
  static const replay = 'replay';
  static const rateLimited = 'rate_limited';
  static const unknownType = 'unknown_type';
  static const unsupportedProtocol = 'unsupported_protocol';
  static const badFrame = 'bad_frame';
}
'''

MESSAGES = r'''import 'dart:convert';
import 'dart:math';

import 'actions.dart';
import 'consts.dart';

/// One JSON control message on the TCP+TLS channel.
///
/// The envelope (type/seq/ts/nonce) is what the receiver uses for replay
/// protection: `seq` must be strictly increasing per device, and `ts`
/// must be within [kMaxClockSkewMs] of the receiver clock. The payload
/// lives in [data].
class ControlMessage {
  final String type;
  final int seq;
  final int ts;
  final String nonce;
  final Map<String, dynamic> data;

  ControlMessage({
    required this.type,
    required this.seq,
    Map<String, dynamic>? data,
    int? ts,
    String? nonce,
  })  : data = data ?? {},
        ts = ts ?? DateTime.now().millisecondsSinceEpoch,
        nonce = nonce ?? _newNonce();

  static String _newNonce() {
    final r = Random.secure();
    final b = List<int>.generate(8, (_) => r.nextInt(256));
    return b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  }

  Map<String, dynamic> toJson() => {
        'type': type,
        'seq': seq,
        'ts': ts,
        'nonce': nonce,
        'data': data,
      };

  String encode() => jsonEncode(toJson());

  factory ControlMessage.decode(String raw) {
    final m = jsonDecode(raw) as Map<String, dynamic>;
    return ControlMessage(
      type: m['type'] as String,
      seq: (m['seq'] as num).toInt(),
      ts: (m['ts'] as num).toInt(),
      nonce: m['nonce'] as String,
      data: Map<String, dynamic>.from(m['data'] as Map? ?? const {}),
    );
  }

  // ------------------------- convenience factories -------------------------

  factory ControlMessage.hello({
    required int seq,
    required String deviceId,
    required String deviceName,
    required String tokenHex,
  }) =>
      ControlMessage(type: MsgType.hello, seq: seq, data: {
        'deviceId': deviceId,
        'deviceName': deviceName,
        'token': tokenHex,
        'protocol': kProtocolVersion,
      });

  factory ControlMessage.helloAck({
    required int seq,
    required bool ok,
    String? reason,
    String? serverName,
  }) =>
      ControlMessage(type: MsgType.helloAck, seq: seq, data: {
        'ok': ok,
        if (reason != null) 'reason': reason,
        if (serverName != null) 'serverName': serverName,
      });

  factory ControlMessage.pairRequest({
    required int seq,
    required String deviceId,
    required String deviceName,
    required String pin,
  }) =>
      ControlMessage(type: MsgType.pairRequest, seq: seq, data: {
        'deviceId': deviceId,
        'deviceName': deviceName,
        'pin': pin,
      });

  factory ControlMessage.click({
    required int seq,
    required String button,
    required String action,
  }) =>
      ControlMessage(type: MsgType.click, seq: seq, data: {
        'button': button,
        'action': action,
      });

  factory ControlMessage.media({required int seq, required String command}) =>
      ControlMessage(type: MsgType.media, seq: seq, data: {
        'command': command,
      });

  factory ControlMessage.presenter({required int seq, required String command}) =>
      ControlMessage(type: MsgType.presenter, seq: seq, data: {
        'command': command,
      });

  factory ControlMessage.macroFire({required int seq, required String macroId}) =>
      ControlMessage(type: MsgType.macroFire, seq: seq, data: {
        'macroId': macroId,
      });

  factory ControlMessage.ping({required int seq}) =>
      ControlMessage(type: MsgType.ping, seq: seq);

  factory ControlMessage.pong({required int seq}) =>
      ControlMessage(type: MsgType.pong, seq: seq);

  factory ControlMessage.error({
    required int seq,
    required String code,
    String? message,
  }) =>
      ControlMessage(type: MsgType.error, seq: seq, data: {
        'code': code,
        if (message != null) 'message': message,
      });
}
'''

TCP_FRAME = r'''import 'dart:convert';
import 'dart:typed_data';

import 'consts.dart';

/// Length-prefixed framing for the TCP control channel:
/// `[4-byte big-endian length][UTF-8 JSON payload]`.
abstract class TcpFrame {
  static Uint8List encode(String jsonPayload) {
    final body = utf8.encode(jsonPayload);
    final out = Uint8List(4 + body.length);
    final view = ByteData.sublistView(out);
    view.setUint32(0, body.length, Endian.big);
    out.setRange(4, 4 + body.length, body);
    return out;
  }

  static Uint8List encodeMessageJson(Map<String, dynamic> json) =>
      encode(jsonEncode(json));
}

/// Incremental decoder for a TCP byte stream. Feed chunks with [add],
/// pull complete JSON payloads with [drain].
class TcpFrameDecoder {
  final List<int> _buf = <int>[];

  void add(List<int> chunk) => _buf.addAll(chunk);

  List<String> drain() {
    final out = <String>[];
    while (_buf.length >= 4) {
      final len = ByteData.sublistView(
        Uint8List.fromList(_buf.sublist(0, 4)),
      ).getUint32(0, Endian.big);
      if (len > kMaxTcpFrameBytes) {
        throw const FormatException('frame exceeds kMaxTcpFrameBytes');
      }
      if (_buf.length < 4 + len) break; // wait for more data
      final body = _buf.sublist(4, 4 + len);
      _buf.removeRange(0, 4 + len);
      out.add(utf8.decode(body));
    }
    return out;
  }

  int get bufferedBytes => _buf.length;
}
'''

UDP_PACKET = r'''import 'dart:typed_data';

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
'''

BARREL = r'''/// TPad shared protocol codec (pure Dart, no Flutter).
library tpad_protocol;

export 'src/actions.dart';
export 'src/consts.dart';
export 'src/messages.dart';
export 'src/tcp_frame.dart';
export 'src/udp_packet.dart';
'''

TEST_FILE = r'''import 'package:tpad_protocol/tpad_protocol.dart';
import 'package:test/test.dart';

void main() {
  group('udp packet', () {
    final key = List<int>.generate(32, (i) => i);

    test('round-trip preserves values', () {
      final p = UdpPointerPacket.fromPixels(
        seq: 42,
        dx: 12.34,
        dy: -5.0,
        flags: UdpPointerPacket.flagLeftDown,
      );
      final raw = p.encode(key);
      expect(raw.length, UdpPointerPacket.size);

      final back = UdpPointerPacket.decode(raw, key);
      expect(back, isNotNull);
      expect(back!.seq, 42);
      expect(back.dxPx, closeTo(12.34, 0.005));
      expect(back.dyPx, closeTo(-5.0, 0.005));
      expect(back.leftDown, isTrue);
      expect(back.rightDown, isFalse);
    });

    test('rejects tampered bytes', () {
      final raw = const UdpPointerPacket(seq: 1, timestampMs: 2).encode(key);
      raw[30] ^= 0xFF; // inside the HMAC region
      expect(UdpPointerPacket.decode(raw, key), isNull);
    });

    test('rejects wrong key', () {
      final raw = const UdpPointerPacket(seq: 1, timestampMs: 2).encode(key);
      final other = List<int>.generate(32, (i) => 255 - i);
      expect(UdpPointerPacket.decode(raw, other), isNull);
    });
  });

  group('tcp framing', () {
    test('round-trip one message', () {
      final msg = ControlMessage(type: MsgType.ping, seq: 7);
      final frame = TcpFrame.encode(msg.encode());
      final dec = TcpFrameDecoder()..add(frame);
      final out = dec.drain();
      expect(out, hasLength(1));
      final back = ControlMessage.decode(out.first);
      expect(back.type, MsgType.ping);
      expect(back.seq, 7);
      expect(back.nonce, hasLength(16));
    });

    test('handles split chunks and back-to-back frames', () {
      final a = ControlMessage.media(seq: 3, command: MediaCmd.playPause);
      final b = ControlMessage.presenter(seq: 4, command: PresenterCmd.next);
      final bytes = [...TcpFrame.encode(a.encode()), ...TcpFrame.encode(b.encode())];
      final dec = TcpFrameDecoder();
      dec.add(bytes.sublist(0, 5));
      expect(dec.drain(), isEmpty);
      dec.add(bytes.sublist(5));
      final out = dec.drain();
      expect(out, hasLength(2));
      expect(ControlMessage.decode(out[0]).data['command'], MediaCmd.playPause);
      expect(ControlMessage.decode(out[1]).data['command'], PresenterCmd.next);
    });

    test('factories build correct envelopes', () {
      final m = ControlMessage.hello(
        seq: 1,
        deviceId: 'd1',
        deviceName: 'Redmi',
        tokenHex: 'ab' * 32,
      );
      expect(m.type, MsgType.hello);
      expect(m.data['protocol'], kProtocolVersion);
      final back = ControlMessage.decode(m.encode());
      expect(back.data['deviceName'], 'Redmi');
    });
  });
}
'''

RULES_MD = r'''# TPad Project Rules

Read this file before writing any code or docs for TPad. Ordered by
importance: scope, security, code, workflow. Nothing here is optional.

## 1. Scope (frozen — changes need SMA's explicit approval)

Phase 1 ships ONLY:
- Touchpad: relative mode, minimal gestures (1-finger move; tap = click;
  2-finger tap = right-click; 3-finger tap = middle-click;
  2-finger drag = scroll; double-tap-hold = drag; pinch = zoom).
  No 3/4-finger OS gestures.
- Haptics on tap/click: fired locally and instantly, never gated on
  the network. No per-move vibration.
- Media keys: play/pause, next, previous, volume up/down, mute.
- Presentation clicker: next/previous slide (+ blank toggle if trivial).
- Macros: dedicated phone tab; combos defined once in the receiver app
  (e.g. Ctrl+Shift+T = "Reopen tab", Win+L = "Lock PC").

NEVER build — do not re-propose without asking SMA first:
- App launcher, clipboard sync, arbitrary remote command execution,
  screen mirroring, gamepad mode. Wake-on-LAN is parked.

Phase 2 (separate planning, do not build now): full keyboard,
multi-monitor picker, per-app volume mixer.

## 2. Security (non-negotiable)

1. TLS on the control channel with TOFU cert pinning (fingerprint
   check, fail closed). Self-signed RSA/ECDSA only — never Ed25519
   (BoringSSL rejects it).
2. Per-device 256-bit token issued at pairing; stored in secure storage.
3. HMAC-SHA256 (truncated to 16 bytes) on every UDP packet.
4. Replay protection: per-device strictly increasing `seq` — reject
   `seq <= lastSeq`; reject `|now - ts| > 60000`.
5. Auth is enforced SERVER-SIDE on EVERY packet. Never trust the client.
6. Closed action set only (PROTOCOL.md section 5). Unknown types get
   `error`/`unknown_type`; repeated abuse gets disconnected. No shell,
   no process spawning from phone-supplied strings. Ever.
7. Rate limits: 240 UDP packets/s and 60 TCP messages/s per device.
   Exceed -> drop; repeated -> disconnect.
8. No tokens, PINs, keys, or private keys in logs, errors, or commits.

## 3. Code

- Dart must be null-safe and const-safe. Never access instance members
  from a `const` context.
- `tpad_protocol` stays pure Dart — no Flutter imports. Both apps import
  it; never duplicate packet/message code.
- Minimal diffs. Do not reformat unrelated code.
- Every network boundary validates: magic, version, HMAC, seq, ts,
  frame size (max 4 MiB). Malformed input is dropped, never crashes.
- Handle disconnects and reconnects gracefully on both sides.

## 4. Workflow (how batches work)

- Each batch is a re-runnable Python builder script that Antigravity
  executes on SMA's machine. Scripts print every file they write and end
  with a VERIFY step checking file existence + anchors. A missed anchor
  is reported as "ANCHOR NOT FOUND" — never as "already-present".
- Batches are DELIVERED, never COMPLETE, until `flutter analyze` is
  clean and the feature is tap-tested on real hardware (Redmi + laptop).
- Secrets stay on SMA's machine. Scripts read them from local files and
  mask them in output. Never print, log, or commit them.
- Ask SMA before expanding scope, adding a dependency (check its license
  — no GPL without his explicit approval), or changing the protocol.
'''

DESIGN_MD = r'''# TPad System Design

## 1. Goals

1. Feels like the laptop's own trackpad: sub-perceptual latency on
   5 GHz WiFi, smooth motion, no jitter, no post-liftoff sliding.
2. LAN-only. No cloud, no accounts, no internet.
3. Secure by construction (rules.md section 2): a compromised phone can
   move the mouse and fire allowlisted actions — nothing more.

## 2. Components

```
Android controller                  Windows receiver
+------------------+                +---------------------------+
| TouchpadScreen   |                | TrayApp (tray_manager)    |
| MacrosTab        |                | PairingScreen (QR)        |
| MediaTab         |                | DeviceListScreen          |
| ClickerTab       |                | MacroEditorScreen         |
| PairingScreen    |                | SettingsScreen            |
| SettingsScreen   |                | ActionLogScreen           |
+------------------+                +---------------------------+
| GesturePipeline  |                | PairingService            |
|  (coalesce       |                |  (PIN, cert, QR)          |
|   60-120 Hz)     |                | NetServer                 |
+------------------+                |  (UDP listener,           |
| NetClient        |    UDP / TCP   |   TLS server)             |
|  (UDP sender,    | <------------> | SecurityGate              |
|   TLS channel,   |                |  (token/HMAC/replay/      |
|   pairing)       |                |   rate-limit)             |
+------------------+                | InputEngine               |
                                    |  (One Euro smoothing,    |
        +------------------+        |   SendInput batching)     |
        | tpad_protocol    | <-----> | ActionRouter              |
        | (shared codec)   |        |  (click/key/macro/        |
        +------------------+        |   media/presenter)        |
                                    | Store (SQLite)            |
                                    |  devices/macros/settings  |
                                    +---------------------------+
```

## 3. Data flow: one finger move

1. Android gesture layer reports pointer deltas at 120-240 Hz.
2. `GesturePipeline` coalesces MOVE events and flushes at 60-120 Hz as
   `UdpPointerPacket` (dx/dy in hundredths of a logical pixel).
3. UDP datagram -> receiver. `SecurityGate` checks HMAC, seq freshness,
   and rate. Any failure -> drop silently (and count it).
4. `InputEngine`: One Euro filter + rest deadzone, then the
   sensitivity/acceleration curve; batches into ONE `SendInput` call
   per network tick.
5. Cursor moves. Budget: single-digit milliseconds on LAN.

Taps, clicks, keys, macros, and media take the TCP+TLS path as JSON
control messages — sent immediately, never coalesced.

## 4. Screens

Controller (phone): Pairing (QR scan / manual IP), Touchpad
(full-screen pad + click-button row), Macros (button grid), Media
(transport + volume), Clicker (prev/next/blank), Settings (sensitivity
slider, acceleration curve, remembered devices, disconnect).

Receiver (tray app; window opens on demand): Pairing (QR + PIN +
approve), Devices (list, per-device permissions, kick), Macros
(define/edit combos), Settings (ports, autostart, log level),
Log (recent actions).

## 5. Connection state machine

disconnected -> discovering -> pairing -> connecting -> connected.
Any failure -> disconnected (with reason) -> user retries.
`connected` + 45 s of silence -> disconnected (timeout).
Closing the phone app ends the session; the receiver locks the channel
until the next connect.

## 6. Storage

Phone: `flutter_secure_storage` holds the per-laptop device token;
`shared_preferences` holds sensitivity, acceleration, remembered devices.
Laptop: SQLite holds `devices(id, name, token_hash, permissions,
last_seen)`, `macros(id, name, vk_sequence)`, `settings(key, value)`.
The TLS private key lives in Windows Credential Manager / a DPAPI
protected file — never in the repo.

## 7. UI/UX principles

- Dark UI on the phone, big touch targets, full-screen pad.
- Every tap gets instant LOCAL feedback (haptic + visual). Never wait
  for the network to acknowledge a gesture.
- Minimal gestures only (rules.md section 1). Discoverability beats power.
- The receiver UI is plain and functional: it is a control panel, not
  a showcase.
'''

PROTOCOL_MD = r'''# TPad Protocol v1

Wire spec for the TPad phone-as-touchpad system. Both the Windows receiver
and the Android controller implement this exactly. The Dart codec lives in
`lib/`; this file is the contract.

## 1. Overview

Two channels, phone -> laptop:

| Channel | Transport | Carries |
|---|---|---|
| Pointer stream | UDP datagrams | Relative mouse movement, scroll (binary, 40-byte packets) |
| Control channel | TCP + TLS | Clicks, keys, macros, media, presenter, pairing, keepalive (length-prefixed JSON) |

Default ports: **TCP 47900**, **UDP 47901**. Optional mDNS advertisement:
`_tpad._tcp` (with QR + manual-IP fallback always available).

Design rule: the phone sends *raw, device-independent* input; the receiver
applies sensitivity, acceleration, and smoothing. Tuning lives in one place.

## 2. Pairing (QR + PIN, trust-on-first-use)

1. Receiver generates a 6-digit PIN (TTL 120 s, single-use, regenerated
   after 3 failed attempts) and a self-signed TLS certificate
   (RSA or ECDSA — **not Ed25519**, BoringSSL rejects it).
2. Receiver displays a QR encoding:
   `TPAD://<ip>:47900?fp=<certSha256Hex>&pin=<6digits>&name=<urlencoded>`
3. Phone scans the QR, opens TLS to `ip:47900`, and checks the server
   certificate fingerprint against `fp`. Mismatch -> abort (fail closed).
4. Over TLS, phone sends `pair_request` {deviceId (uuid), deviceName, pin}.
5. Receiver validates the PIN -> responds `pair_confirm` {ok, token}.
   `token` is 32 random bytes, hex-encoded (64 chars).
6. Phone stores the token in secure storage. The raw 32 bytes (hex-decoded)
   are the `deviceKey` used for UDP HMAC.

Nothing listens on the network until the receiver app is running, and
pairing requires physical access to the laptop screen.

## 3. Session

1. Phone opens TLS to the receiver and sends `hello`
   {deviceId, deviceName, token, protocol: 1}.
2. Receiver validates the token -> `hello_ack` {ok: true, serverName}
   or {ok: false, reason}.
3. UDP pointer packets and control messages flow.
4. `ping`/`pong` keepalive every 15 s; receiver drops clients silent
   for 45 s.

## 4. UDP pointer packet — 40 bytes, big-endian

```
 0-1 : magic 0x5450 ("TP")
 2   : version 0x01
 3   : flags (bit0 leftDown, bit1 rightDown, bit2 middleDown)
 4-7 : seq uint32 (per-device, strictly increasing)
 8-15: timestampMs uint64 (sender epoch millis)
16-17: dx int16 — hundredths of a logical pixel, signed
18-19: dy int16
20-21: scrollDx int16 (two-finger scroll; 0 otherwise)
22-23: scrollDy int16
24-39: HMAC-SHA256(deviceKey, bytes 0..23), truncated to 16 bytes
```

Receiver rules: drop on bad magic/version/HMAC; drop when
`seq <= lastSeq` for that device (stale/replay); drop when the per-device
rate exceeds 240 pkt/s.

## 5. TCP control channel

Frame: `[4-byte big-endian length][UTF-8 JSON]`. Max frame 4 MiB —
the receiver must drop anything larger.

Envelope (every message):

```json
{ "type": "click", "seq": 12, "ts": 1759280000000, "nonce": "9f2c...",
  "data": { "button": "left", "action": "tap" } }
```

- `seq`: per-device strictly increasing. Receiver keeps `lastSeq` per
  device and rejects `seq <= lastSeq` with `error`/`replay`.
- `ts`: sender epoch millis. Reject when `|now - ts| > 60000`.
- `nonce`: 8 random bytes as 16 hex chars (defense in depth).

Message types (`data` fields):

| type | data |
|---|---|
| `hello` | deviceId, deviceName, token, protocol |
| `hello_ack` | ok, reason?, serverName? |
| `pair_request` | deviceId, deviceName, pin |
| `pair_confirm` | ok, token? |
| `click` | button: left/right/middle, action: down/up/tap |
| `key` | vk (Windows virtual-key int), action: down/up/press |
| `macro_fire` | macroId |
| `media` | command: play_pause/next/prev/vol_up/vol_down/mute |
| `presenter` | command: next/prev/blank |
| `ping` / `pong` | — |
| `error` | code, message? |

`click` with `action: tap` is atomic down+up (for taps).
DOWN/UP/click/key messages are sent immediately — never coalesced.

## 6. Security rules (non-negotiable)

1. TLS on the control channel, cert pinning via TOFU fingerprint check.
2. HMAC on every UDP packet (see §4).
3. Auth enforced **server-side on every packet** — never trust the client.
4. **Closed action set**: the receiver implements exactly the types in §5.
   Unknown types -> `error`/`unknown_type`; repeated abuse -> disconnect.
   There is deliberately no "run arbitrary command" action.
5. Rate limits: 240 UDP pkt/s, 60 TCP msg/s per device. Exceed -> drop;
   repeated -> disconnect.
6. No tokens, PINs, keys, or cert private keys in logs.

## 7. Versioning

`protocol` integer in `hello` (currently 1). The receiver rejects unknown
versions with `hello_ack` {ok: false, reason: "unsupported-protocol"}.
Packet/message layouts are versioned independently of app versions.
'''

ROOT_README = r'''# TPad — phone-as-touchpad

Turn an old Android phone into a wireless touchpad + remote for a
Windows 10/11 laptop. The phone acts as a touchpad **only while the
companion app is open** — close it and it's a normal phone again.

Local network only. No cloud, no accounts, no internet needed.
Security-first: a compromised phone can move the mouse and fire
allowlisted actions — nothing more.

## Features (Phase 1)

- Laptop-like touchpad: 1-finger move, tap = click,
  2-finger tap = right-click, 3-finger tap = middle-click,
  2-finger drag = scroll, double-tap-hold = drag, pinch = zoom
- Instant local haptics; sensitivity slider + acceleration curve
- Media keys, presentation clicker, macro buttons
  (combos defined once on the laptop)

Explicitly out of scope: app launcher, clipboard sync, Wake-on-LAN
(parked), arbitrary remote commands (never).

## Layout

- `packages/tpad_protocol/` — shared wire-protocol codec (pure Dart).
  Start with its `PROTOCOL.md`.
- `apps/tpad_receiver/` — Windows receiver app (tray app).
- `apps/tpad_controller/` — Android controller app.
- `rules.md` — project rules. **Read before writing any code.**
- `design.md` — system design: components, data flows, screens.

## Prerequisites (SMA's machine)

- Flutter SDK (stable), Visual Studio 2022 with "Desktop development
  with C++", Android SDK, Git
- Laptop + Redmi Note 7 Pro on the same WiFi; USB debugging on the phone

## Quickstart

1. `python <batch>.py` — each Phase-1 batch is a builder script that
   Antigravity runs; scripts print what they write and end with VERIFY.
2. `cd packages/tpad_protocol && dart pub get && dart test`
3. Later batches scaffold the two Flutter apps, which import
   `tpad_protocol` as a path dependency.
4. `flutter analyze` must be clean and features tap-tested on real
   hardware before a batch counts as done.

## Batch log (Phase 1)

| Batch | Status | Contents |
|---|---|---|
| P1-B1 | DELIVERED | Protocol spec + shared Dart codec + project docs |
| P1-B2 | planned | Windows scaffold: tray app, QR pairing screen, listeners |
| P1-B3 | planned | Windows input engine: SendInput pipeline, smoothing |
| P1-B4 | planned | Security: TLS, tokens, replay window, HMAC, approve/kick |
| P1-B5 | planned | Android scaffold: QR scan pairing, connection state |
| P1-B6 | planned | Android touchpad: gesture pipeline, haptics, settings |
| P1-B7 | planned | Macros: receiver definitions + phone macros tab |
| P1-B8 | planned | Media keys + presentation clicker |

Batches are DELIVERED, never COMPLETE, until analyzed + tap-tested.

## Security model

QR + PIN pairing with TOFU cert pinning, TLS control channel, HMAC'd
UDP pointer stream, per-device tokens, replay window, rate limits,
closed action set. Full spec: `packages/tpad_protocol/PROTOCOL.md`.

## Database

None hosted. Local SQLite for devices/macros/settings; secure storage
for tokens. No server to pay for.
'''

FILES = {
    "README.md": ROOT_README,
    "rules.md": RULES_MD,
    "design.md": DESIGN_MD,
    "packages/tpad_protocol/pubspec.yaml": PUBSPEC,
    "packages/tpad_protocol/README.md": PKG_README,
    "packages/tpad_protocol/PROTOCOL.md": PROTOCOL_MD,
    "packages/tpad_protocol/lib/tpad_protocol.dart": BARREL,
    "packages/tpad_protocol/lib/src/consts.dart": CONSTS,
    "packages/tpad_protocol/lib/src/actions.dart": ACTIONS,
    "packages/tpad_protocol/lib/src/messages.dart": MESSAGES,
    "packages/tpad_protocol/lib/src/tcp_frame.dart": TCP_FRAME,
    "packages/tpad_protocol/lib/src/udp_packet.dart": UDP_PACKET,
    "packages/tpad_protocol/test/codec_test.dart": TEST_FILE,
}

# (path, anchor that must be present)
ANCHORS = [
    ("packages/tpad_protocol/pubspec.yaml", "name: tpad_protocol"),
    ("packages/tpad_protocol/PROTOCOL.md", "# TPad Protocol v1"),
    ("packages/tpad_protocol/lib/tpad_protocol.dart", "export 'src/udp_packet.dart'"),
    ("packages/tpad_protocol/lib/src/consts.dart", "kTcpPort = 47900"),
    ("packages/tpad_protocol/lib/src/actions.dart", "class MsgType"),
    ("packages/tpad_protocol/lib/src/messages.dart", "class ControlMessage"),
    ("packages/tpad_protocol/lib/src/tcp_frame.dart", "class TcpFrameDecoder"),
    ("packages/tpad_protocol/lib/src/udp_packet.dart", "class UdpPointerPacket"),
    ("packages/tpad_protocol/lib/src/udp_packet.dart", "static const int size = 40"),
    ("packages/tpad_protocol/test/codec_test.dart", "rejects tampered bytes"),
    ("README.md", "P1-B1"),
    ("README.md", "## Quickstart"),
    ("rules.md", "# TPad Project Rules"),
    ("rules.md", "non-negotiable"),
    ("design.md", "# TPad System Design"),
    ("design.md", "SecurityGate"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="P1-B1 builder: protocol spec + codec")
    ap.add_argument("--dir", default="tpad", help="project root to create")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)

    print("== P1-B1: writing tpad_protocol package ==")
    for rel, content in FILES.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("  wrote %-55s %6d bytes" % (rel, len(content.encode("utf-8"))))

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

    print("VERIFY OK — %d files, all anchors present, no redactor damage" % len(FILES))
    print()
    print("Next: cd %s && dart pub get && dart test" % os.path.join(root, "packages", "tpad_protocol"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
