import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:tpad_theme/tpad_theme.dart';

import '../app.dart';

class PairingScreen extends StatelessWidget {
  const PairingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final pairing = ReceiverServices.pairing;
    final scheme = Theme.of(context).colorScheme;
    return ListenableBuilder(
      listenable: pairing,
      builder: (context, _) {
        return Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(TPadSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Scan with the TPad phone app',
                    style: TPadText.heading),
                const SizedBox(height: TPadSpacing.md),
                // White card behind the QR: scanners need contrast.
                Container(
                  padding: const EdgeInsets.all(TPadSpacing.sm),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius:
                        BorderRadius.circular(TPadRadius.lg),
                  ),
                  child: QrImageView(
                    data: pairing.qrPayload,
                    version: QrVersions.auto,
                    size: 220,
                  ),
                ),
                const SizedBox(height: TPadSpacing.md),
                Text('PIN  ${pairing.pin}',
                    style: TPadText.pin
                        .copyWith(color: scheme.primary)),
                Text('expires in ${pairing.secondsLeft}s',
                    style: TPadText.caption.copyWith(
                        color: scheme.onSurfaceVariant)),
                const SizedBox(height: TPadSpacing.sm),
                TPadButton(
                  label: 'New PIN',
                  icon: Icons.refresh,
                  type: TPadButtonType.secondary,
                  onPressed: pairing.regenerate,
                ),
                const SizedBox(height: TPadSpacing.sm),
                Text('Listening on ${pairing.lanIp}',
                    style: TPadText.caption.copyWith(
                        color: scheme.onSurfaceVariant)),
                Text('TLS fingerprint arrives in P1-B4',
                    style: TPadText.caption
                        .copyWith(color: TPadFunctional.warning)),
              ],
            ),
          ),
        );
      },
    );
  }
}
