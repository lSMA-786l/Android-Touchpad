import 'package:flutter/material.dart';
import 'package:tpad_protocol/tpad_protocol.dart';
import 'package:tpad_theme/tpad_theme.dart';

import '../app.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final net = ReceiverServices.net;
    return ListenableBuilder(
      listenable: net,
      builder: (context, _) {
        return ListView(
          padding: const EdgeInsets.all(TPadSpacing.md),
          children: [
            const TPadSectionHeader('Network'),
            const ListTile(
              title: Text('TCP port'),
              subtitle:
                  Text('$kTcpPort (TLS lands in P1-B4)'),
              leading: Icon(Icons.security),
            ),
            const ListTile(
              title: Text('UDP port'),
              subtitle: Text('$kUdpPort'),
              leading: Icon(Icons.speed),
            ),
            SwitchListTile(
              title: const Text('Listeners running'),
              value: net.running,
              onChanged: (v) => v ? net.start() : net.stop(),
            ),
            const Divider(),
            const TPadSectionHeader('System'),
            const ListTile(
              title: Text('Start with Windows'),
              subtitle:
                  Text('Arrives in a later batch (registry entry).'),
              leading: Icon(Icons.power_settings_new),
            ),
          ],
        );
      },
    );
  }
}
