# TPad — phone-as-touchpad

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
| P1-B2 | DELIVERED | Windows scaffold: tray app, QR pairing screen, listeners |
| P1-B2T | DELIVERED | Shared theme package (tokens + 5 widgets) + receiver retrofit |
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
