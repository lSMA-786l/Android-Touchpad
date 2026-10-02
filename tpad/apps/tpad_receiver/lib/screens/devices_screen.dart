import 'package:flutter/material.dart';

import '../app.dart';

/// Placeholder: device approval, per-device permissions, and kick
/// arrive in P1-B4.
class DevicesScreen extends StatelessWidget {
  const DevicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final net = ReceiverServices.net;
    return ListenableBuilder(
      listenable: net,
      builder: (context, _) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.devices, size: 48, color: Colors.grey[600]),
              const SizedBox(height: 12),
              Text('${net.clientCount} connected client(s)',
                  style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 8),
              const Text(
                'Device approval, per-device permissions,\nand kick arrive in P1-B4.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        );
      },
    );
  }
}
