import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../app.dart';

class PairingScreen extends StatelessWidget {
  const PairingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final pairing = ReceiverServices.pairing;
    return ListenableBuilder(
      listenable: pairing,
      builder: (context, _) {
        return Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Scan with the TPad phone app',
                    style: TextStyle(fontSize: 16)),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: QrImageView(
                    data: pairing.qrPayload,
                    version: QrVersions.auto,
                    size: 220,
                  ),
                ),
                const SizedBox(height: 16),
                Text('PIN  ${pairing.pin}',
                    style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 4)),
                Text('expires in ${pairing.secondsLeft}s',
                    style: TextStyle(color: Colors.grey[400])),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: pairing.regenerate,
                  icon: const Icon(Icons.refresh),
                  label: const Text('New PIN'),
                ),
                const SizedBox(height: 12),
                Text('Listening on ${pairing.lanIp}',
                    style: TextStyle(color: Colors.grey[500], fontSize: 12)),
                const Text('TLS fingerprint arrives in P1-B4',
                    style: TextStyle(color: Colors.orange, fontSize: 12)),
              ],
            ),
          ),
        );
      },
    );
  }
}
