# TPad Project Rules

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
