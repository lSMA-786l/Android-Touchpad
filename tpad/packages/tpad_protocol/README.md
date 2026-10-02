# tpad_protocol

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
