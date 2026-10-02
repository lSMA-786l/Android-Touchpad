#!/usr/bin/env python3
"""
P1-B2: TPad Windows receiver scaffold.

What it does (run via Antigravity on SMA's machine):
  1. Requires P1-B1 output (tpad/packages/tpad_protocol) — fails loudly otherwise.
  2. Requires the Flutter toolchain — fails loudly with setup hints otherwise.
  3. Runs `flutter create --platforms=windows` for apps/tpad_receiver (skipped
     if the project already exists).
  4. Overlays our Dart code: tray app shell, pairing screen (QR+PIN),
     device/log/settings screens, UDP+TCP listeners, in-memory log service.
  5. Generates a placeholder tray icon PNG (pure stdlib, no Pillow).
  6. Runs `flutter pub get` + `flutter analyze`, prints the result.
  7. VERIFY: files exist, anchors present, no redactor damage.

What this batch is NOT (by design):
  - Input injection (SendInput) -> P1-B3.
  - TLS, tokens, HMAC, replay window, approve/kick -> P1-B4.
  The TCP listener here is a PLAINTEXT scaffold so pairing/traffic flow can
  be smoke-tested; P1-B4 upgrades it. Upgrade points are marked "P1-B4".

Run:
  python build_p1b2.py [--dir tpad] [--no-flutter]

  --no-flutter: only write files (used to test this script where the
  Flutter SDK is unavailable). On SMA's machine run WITHOUT it.
"""

import argparse
import os
import struct
import subprocess
import sys
import zlib

# ------------------------------------------------------------------ files ---

PUBSPEC = r'''name: tpad_receiver
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

APP_README = r'''# tpad_receiver (P1-B2 scaffold)

Windows receiver for TPad. System-tray app: shows pairing QR/PIN, lists
devices, keeps an action log. Listens on TCP 47900 + UDP 47901.

## This batch (P1-B2)

- Tray app shell (`tray_manager` + `window_manager`, hide-to-tray)
- Pairing screen: QR payload + auto-rotating PIN
- Devices / Log / Settings screens (Devices approval lands in P1-B4)
- UDP + TCP listeners (plaintext scaffold — TLS arrives in P1-B4)
- In-memory timestamped log service

## Not yet (later batches)

- P1-B3: SendInput pipeline (mouse/keyboard injection) + smoothing
- P1-B4: TLS, per-device tokens, HMAC, replay window, approve/kick

## Run

  flutter pub get
  flutter run -d windows
'''

MAIN_DART = r'''import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';

import 'app.dart';
import 'services/tray_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await windowManager.ensureInitialized();

  const windowOptions = WindowOptions(
    size: Size(520, 680),
    minimumSize: Size(420, 560),
    center: true,
    title: 'TPad Receiver',
  );
  await windowManager.waitUntilReadyToShow(windowOptions, () async {
    await windowManager.show();
    await windowManager.focus();
  });

  await TrayService.init();
  runApp(const TPadApp());
}
'''

APP_DART = r'''import 'dart:async';

import 'package:flutter/material.dart';

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
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.teal,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
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

LOG_SERVICE = r'''import 'package:flutter/foundation.dart';

/// Timestamped, capped in-memory log shown on the Log tab.
class LogService extends ChangeNotifier {
  static const int _cap = 300;
  final List<String> _lines = [];

  List<String> get lines => List.unmodifiable(_lines);

  void add(String message) {
    final ts = DateTime.now();
    final stamp = '${ts.hour.toString().padLeft(2, '0')}:'
        '${ts.minute.toString().padLeft(2, '0')}:'
        '${ts.second.toString().padLeft(2, '0')}';
    _lines.add('[$stamp] $message');
    if (_lines.length > _cap) {
      _lines.removeRange(0, _lines.length - _cap);
    }
    notifyListeners();
  }

  void clear() {
    _lines.clear();
    notifyListeners();
  }
}
'''

PAIRING_SERVICE = r'''import 'dart:async';
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
'''

NET_SERVER = r'''import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:tpad_protocol/tpad_protocol.dart';

import 'log_service.dart';

/// Binds the UDP pointer listener and the TCP control listener.
///
/// SCAFFOLD (P1-B2): plaintext TCP, logs traffic, answers unhandled types
/// with error/unknown_type. P1-B4 upgrades this to TLS + SecurityGate
/// (token / HMAC / replay / rate-limit) — see the P1-B4 markers below.
class NetServer extends ChangeNotifier {
  final LogService log;
  NetServer({required this.log});

  RawDatagramSocket? _udp;
  ServerSocket? _tcp;
  final Map<String, Socket> _clients = {};
  bool _running = false;

  bool get running => _running;
  int get clientCount => _clients.length;

  Future<void> start() async {
    if (_running) return;
    try {
      _udp = await RawDatagramSocket.bind(InternetAddress.anyIPv4, kUdpPort);
      _udp!.listen(_onUdpEvent);
      log.add('UDP listening on port $kUdpPort');

      _tcp = await ServerSocket.bind(InternetAddress.anyIPv4, kTcpPort);
      _tcp!.listen(_onTcpClient);
      log.add(
          'TCP listening on port $kTcpPort (plaintext scaffold — TLS in P1-B4)');

      _running = true;
    } catch (e) {
      log.add('FAILED to bind listeners: $e');
    }
    notifyListeners();
  }

  void _onUdpEvent(RawSocketEvent event) {
    if (event != RawSocketEvent.read) return;
    final dg = _udp?.receive();
    if (dg == null) return;
    // P1-B4: decode + verify via UdpPointerPacket.decode(dg.data, deviceKey).
    log.add('UDP ${dg.data.length}B from ${dg.address.address}:${dg.port}');
  }

  void _onTcpClient(Socket client) {
    final id = '${client.remoteAddress.address}:${client.remotePort}';
    _clients[id] = client;
    log.add('TCP client connected: $id');
    notifyListeners();

    final decoder = TcpFrameDecoder();
    client.listen(
      (chunk) {
        decoder.add(chunk);
        for (final raw in decoder.drain()) {
          _onControlMessage(id, client, raw);
        }
      },
      onError: (Object e) {
        log.add('TCP client error $id: $e');
        _dropClient(id);
      },
      onDone: () {
        log.add('TCP client disconnected: $id');
        _dropClient(id);
      },
    );
  }

  void _onControlMessage(String id, Socket client, String raw) {
    final ControlMessage msg;
    try {
      msg = ControlMessage.decode(raw);
    } catch (e) {
      log.add('bad frame from $id: $e');
      return;
    }
    // P1-B4: SecurityGate.check(msg) — token, seq freshness, ts skew, rate.
    log.add('TCP $id -> ${msg.type} (seq ${msg.seq})');
    if (msg.type == MsgType.ping) {
      final pong = ControlMessage.pong(seq: 0);
      client.add(TcpFrame.encode(pong.encode()));
      return;
    }
    // Scaffold behavior: pairing + actions arrive in P1-B3/P1-B4.
    final err = ControlMessage.error(
      seq: 0,
      code: ErrorCode.unknownType,
      message: 'scaffold: ${msg.type} not handled until P1-B3/P1-B4',
    );
    client.add(TcpFrame.encode(err.encode()));
  }

  void _dropClient(String id) {
    _clients.remove(id)?.destroy();
    notifyListeners();
  }

  Future<void> stop() async {
    for (final id in _clients.keys.toList()) {
      _dropClient(id);
    }
    _udp?.close();
    await _tcp?.close();
    _running = false;
    notifyListeners();
  }
}
'''

TRAY_SERVICE = r'''import 'package:flutter/foundation.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:window_manager/window_manager.dart';

/// System-tray integration: icon, tooltip, menu, click-to-show.
class TrayService with TrayListener {
  TrayService._();

  static Future<void> init() async {
    final svc = TrayService._();
    await trayManager.setIcon('assets/tray_icon.png');
    await trayManager.setToolTip('TPad Receiver');
    await trayManager.setContextMenu(
      Menu(items: [
        MenuItem(key: 'show', label: 'Show TPad Receiver'),
        MenuItem.separator(),
        MenuItem(key: 'quit', label: 'Quit'),
      ]),
    );
    trayManager.addListener(svc);
    debugPrint('tray initialized');
  }

  @override
  void onTrayIconMouseDown() {
    windowManager.show();
    windowManager.focus();
  }

  @override
  void onTrayMenuItemClick(MenuItem menuItem) {
    switch (menuItem.key) {
      case 'show':
        windowManager.show();
        windowManager.focus();
      case 'quit':
        windowManager.close();
    }
  }
}
'''

PAIRING_SCREEN = r'''import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../app.dart';

class PairingScreen extends StatelessWidget {
  const PairingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final pairing = ReceiverServices.pairing;
    return ListenableBuilder(
      listenable: pairing,
      builder: (context, _) {
        return Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Scan with the TPad phone app',
                    style: TextStyle(fontSize: 16)),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: QrImageView(
                    data: pairing.qrPayload,
                    version: QrVersions.auto,
                    size: 220,
                  ),
                ),
                const SizedBox(height: 16),
                Text('PIN  ${pairing.pin}',
                    style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 4)),
                Text('expires in ${pairing.secondsLeft}s',
                    style: TextStyle(color: Colors.grey[400])),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: pairing.regenerate,
                  icon: const Icon(Icons.refresh),
                  label: const Text('New PIN'),
                ),
                const SizedBox(height: 12),
                Text('Listening on ${pairing.lanIp}',
                    style: TextStyle(color: Colors.grey[500], fontSize: 12)),
                const Text('TLS fingerprint arrives in P1-B4',
                    style: TextStyle(color: Colors.orange, fontSize: 12)),
              ],
            ),
          ),
        );
      },
    );
  }
}
'''

DEVICES_SCREEN = r'''import 'package:flutter/material.dart';

import '../app.dart';

/// Placeholder: device approval, per-device permissions, and kick
/// arrive in P1-B4.
class DevicesScreen extends StatelessWidget {
  const DevicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final net = ReceiverServices.net;
    return ListenableBuilder(
      listenable: net,
      builder: (context, _) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.devices, size: 48, color: Colors.grey[600]),
              const SizedBox(height: 12),
              Text('${net.clientCount} connected client(s)',
                  style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 8),
              const Text(
                'Device approval, per-device permissions,\nand kick arrive in P1-B4.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        );
      },
    );
  }
}
'''

LOG_SCREEN = r'''import 'package:flutter/material.dart';

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
                  ? const Center(child: Text('No events yet.'))
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: lines.length,
                      itemBuilder: (context, i) => SelectableText(
                        lines[i],
                        style: const TextStyle(
                            fontFamily: 'monospace', fontSize: 12),
                      ),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: TextButton.icon(
                onPressed: log.clear,
                icon: const Icon(Icons.delete_outline),
                label: const Text('Clear'),
              ),
            ),
          ],
        );
      },
    );
  }
}
'''

SETTINGS_SCREEN = r'''import 'package:flutter/material.dart';
import 'package:tpad_protocol/tpad_protocol.dart';

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
          padding: const EdgeInsets.all(16),
          children: [
            const ListTile(
              title: Text('TCP port'),
              subtitle: Text('47900 (TLS lands in P1-B4)'),
              leading: Icon(Icons.security),
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
            const ListTile(
              title: Text('Start with Windows'),
              subtitle: Text('Arrives in a later batch (registry entry).'),
              leading: Icon(Icons.power_settings_new),
            ),
          ],
        );
      },
    );
  }
}
'''

FILES = {
    "apps/tpad_receiver/pubspec.yaml": PUBSPEC,
    "apps/tpad_receiver/README.md": APP_README,
    "apps/tpad_receiver/lib/main.dart": MAIN_DART,
    "apps/tpad_receiver/lib/app.dart": APP_DART,
    "apps/tpad_receiver/lib/services/log_service.dart": LOG_SERVICE,
    "apps/tpad_receiver/lib/services/pairing_service.dart": PAIRING_SERVICE,
    "apps/tpad_receiver/lib/services/net_server.dart": NET_SERVER,
    "apps/tpad_receiver/lib/services/tray_service.dart": TRAY_SERVICE,
    "apps/tpad_receiver/lib/screens/pairing_screen.dart": PAIRING_SCREEN,
    "apps/tpad_receiver/lib/screens/devices_screen.dart": DEVICES_SCREEN,
    "apps/tpad_receiver/lib/screens/log_screen.dart": LOG_SCREEN,
    "apps/tpad_receiver/lib/screens/settings_screen.dart": SETTINGS_SCREEN,
}

# (path, anchor that must be present)
ANCHORS = [
    ("apps/tpad_receiver/pubspec.yaml", "tpad_protocol:"),
    ("apps/tpad_receiver/pubspec.yaml", "path: ../../packages/tpad_protocol"),
    ("apps/tpad_receiver/pubspec.yaml", "tray_manager:"),
    ("apps/tpad_receiver/lib/main.dart", "TrayService.init()"),
    ("apps/tpad_receiver/lib/app.dart", "class ReceiverServices"),
    ("apps/tpad_receiver/lib/services/log_service.dart", "class LogService"),
    ("apps/tpad_receiver/lib/services/pairing_service.dart", "qrPayload"),
    ("apps/tpad_receiver/lib/services/pairing_service.dart", "PENDING-P1-B4"),
    ("apps/tpad_receiver/lib/services/net_server.dart", "class NetServer"),
    ("apps/tpad_receiver/lib/services/net_server.dart", "P1-B4"),
    ("apps/tpad_receiver/lib/services/tray_service.dart",
     "onTrayMenuItemClick"),
    ("apps/tpad_receiver/lib/screens/pairing_screen.dart", "QrImageView"),
    ("apps/tpad_receiver/README.md", "P1-B2"),
]

# Batch-table row this script flips to DELIVERED (loud warn if missing).
README_PATCH_ANCHOR = "| P1-B2 | planned | Windows scaffold: tray app, QR pairing screen, listeners |"
README_PATCH_REPLACEMENT = "| P1-B2 | DELIVERED | Windows scaffold: tray app, QR pairing screen, listeners |"


def write_icon_png(path: str, size: int = 64) -> None:
    """Placeholder tray icon: dark tile with a teal dot. Pure stdlib."""

    def px(x: int, y: int):
        cx, cy, r = size // 2, size // 2, size // 4
        if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            return (45, 212, 191, 255)  # teal dot
        return (17, 24, 39, 255)  # dark tile

    raw = b"".join(
        b"\x00" + b"".join(bytes(px(x, y)) for x in range(size))
        for y in range(size)
    )

    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        return (
            struct.pack(">I", len(data))
            + c
            + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)


def run(cmd, cwd, timeout=600):
    print("  $ " + " ".join(cmd))
    try:
        p = subprocess.run(
            cmd, cwd=cwd, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            shell=(sys.platform == "win32"),
        )
    except FileNotFoundError:
        return None, "command not found: " + cmd[0]
    except subprocess.TimeoutExpired:
        return None, "timed out after %ds" % timeout
    return p.returncode, p.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description="P1-B2 builder: receiver scaffold")
    ap.add_argument("--dir", default="tpad", help="project root (from P1-B1)")
    ap.add_argument("--no-flutter", action="store_true",
                    help="only write files; skip flutter create/pub/analyze")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)
    app_dir = os.path.join(root, "apps", "tpad_receiver")

    # --- 0. P1-B1 must have run ---
    codec_pubspec = os.path.join(
        root, "packages", "tpad_protocol", "pubspec.yaml")
    if not os.path.isfile(codec_pubspec):
        print("!! P1-B1 output not found at " + codec_pubspec)
        print("!! Run build_p1b1.py first, then re-run this script.")
        return 1

    # --- 1. flutter create (needs the real toolchain) ---
    if not args.no_flutter:
        rc, out = run(["flutter", "--version"], cwd=root, timeout=120)
        if rc is None or rc != 0:
            print("!! Flutter SDK not found on PATH.")
            print("!! Install: Flutter SDK (stable) + VS2022 'Desktop "
                  "development with C++' + Android SDK, then re-run.")
            if out:
                print(out[-2000:])
            return 1
        if not os.path.isfile(os.path.join(app_dir, "pubspec.yaml")):
            print("== flutter create tpad_receiver ==")
            rc, out = run(
                ["flutter", "create", "--platforms=windows",
                 "--org", "com.tpad", "--project-name", "tpad_receiver",
                 os.path.join("apps", "tpad_receiver")],
                cwd=root, timeout=600,
            )
            print(out[-3000:] if out else "")
            if rc != 0:
                print("!! flutter create failed.")
                return 1
        else:
            print("== flutter project already exists, keeping it ==")

    # --- 2. overlay our files ---
    print("== P1-B2: writing receiver scaffold ==")
    for rel, content in FILES.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("  wrote %-58s %6d bytes" % (rel, len(content.encode("utf-8"))))

    icon_path = os.path.join(app_dir, "assets", "tray_icon.png")
    os.makedirs(os.path.dirname(icon_path), exist_ok=True)
    write_icon_png(icon_path)
    print("  wrote %-58s (generated PNG)" % "apps/tpad_receiver/assets/tray_icon.png")

    # --- 3. flip the batch-table row (loud warn if the anchor moved) ---
    readme = os.path.join(root, "README.md")
    if os.path.isfile(readme):
        with open(readme, "r", encoding="utf-8") as f:
            text = f.read()
        if README_PATCH_ANCHOR in text:
            text = text.replace(README_PATCH_ANCHOR, README_PATCH_REPLACEMENT)
            with open(readme, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            print("  batch table: P1-B2 -> DELIVERED")
        else:
            print("  !! ANCHOR NOT FOUND: P1-B2 batch-table row in README.md")
    else:
        print("  !! ANCHOR NOT FOUND: tpad/README.md missing")

    # --- 4. pub get + analyze (real toolchain only) ---
    if not args.no_flutter:
        print("== flutter pub get ==")
        rc, out = run(["flutter", "pub", "get"], cwd=app_dir, timeout=600)
        print(out[-3000:] if out else "")
        if rc != 0:
            print("!! flutter pub get failed — versions may need a bump; "
                  "send the output back for a patch.")
            return 1
        print("== flutter analyze ==")
        rc, out = run(["flutter", "analyze"], cwd=app_dir, timeout=600)
        tail = out[-4000:] if out else ""
        print(tail)
        if "No issues found!" in (out or ""):
            print("ANALYZE: clean")
        else:
            print("ANALYZE: has findings — review above (batch still "
                  "DELIVERED, not COMPLETE, until clean + tap-tested)")

    # --- 5. VERIFY ---
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
    if not os.path.isfile(icon_path):
        failures.append("MISSING FILE: apps/tpad_receiver/assets/tray_icon.png")
    else:
        with open(icon_path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                failures.append("BAD PNG: tray_icon.png")

    if failures:
        print("VERIFY FAILED:")
        for fl in failures:
            print("  !! " + fl)
        return 1

    print("VERIFY OK — %d files + icon, all anchors present, no redactor damage"
          % len(FILES))
    if not args.no_flutter:
        print("Next: cd %s && flutter run -d windows" % app_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
