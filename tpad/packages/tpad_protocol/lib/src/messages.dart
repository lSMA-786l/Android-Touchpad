import 'dart:convert';
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
