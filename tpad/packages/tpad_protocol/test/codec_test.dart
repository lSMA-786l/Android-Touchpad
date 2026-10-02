import 'package:tpad_protocol/tpad_protocol.dart';
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
