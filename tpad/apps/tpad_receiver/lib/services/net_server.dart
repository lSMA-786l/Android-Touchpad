import 'dart:io';

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
