import 'package:flutter/material.dart';
import 'package:tpad_protocol/tpad_protocol.dart';

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
          padding: const EdgeInsets.all(16),
          children: [
            const ListTile(
              title: Text('TCP port'),
              subtitle: Text('47900 (TLS lands in P1-B4)'),
              leading: Icon(Icons.security),
            ),
            ListTile(
              title: const Text('UDP port'),
              subtitle: Text('$kUdpPort'),
              leading: const Icon(Icons.speed),
            ),
            SwitchListTile(
              title: const Text('Listeners running'),
              value: net.running,
              onChanged: (v) => v ? net.start() : net.stop(),
            ),
            const Divider(),
            const ListTile(
              title: Text('Start with Windows'),
              subtitle: Text('Arrives in a later batch (registry entry).'),
              leading: Icon(Icons.power_settings_new),
            ),
          ],
        );
      },
    );
  }
}
