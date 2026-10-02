# TPad Protocol v1

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
