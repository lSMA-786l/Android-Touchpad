import 'dart:convert';
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
