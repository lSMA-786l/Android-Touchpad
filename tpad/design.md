# TPad System Design

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
