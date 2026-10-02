# tpad_receiver (P1-B2 scaffold)

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
