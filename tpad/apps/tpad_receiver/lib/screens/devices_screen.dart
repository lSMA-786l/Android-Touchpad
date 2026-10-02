import 'package:flutter/material.dart';
import 'package:tpad_theme/tpad_theme.dart';

import '../app.dart';

/// Placeholder: device approval, per-device permissions, and kick
/// arrive in P1-B4.
class DevicesScreen extends StatelessWidget {
  const DevicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final net = ReceiverServices.net;
    final scheme = Theme.of(context).colorScheme;
    return ListenableBuilder(
      listenable: net,
      builder: (context, _) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.devices,
                  size: 48, color: scheme.onSurfaceVariant),
              const SizedBox(height: TPadSpacing.sm),
              Text('${net.clientCount} connected client(s)',
                  style: TPadText.heading),
              const SizedBox(height: TPadSpacing.xs),
              Text(
                'Device approval, per-device permissions,\nand kick arrive in P1-B4.',
                textAlign: TextAlign.center,
                style: TPadText.caption
                    .copyWith(color: scheme.onSurfaceVariant),
              ),
            ],
          ),
        );
      },
    );
  }
}
