import 'dart:async';

import 'package:flutter/material.dart';
import 'package:tpad_theme/tpad_theme.dart';

import 'screens/devices_screen.dart';
import 'screens/log_screen.dart';
import 'screens/pairing_screen.dart';
import 'screens/settings_screen.dart';
import 'services/log_service.dart';
import 'services/net_server.dart';
import 'services/pairing_service.dart';

/// Service singletons for the receiver app.
class ReceiverServices {
  static final log = LogService();
  static final pairing = PairingService();
  static final net = NetServer(log: log);
}

class TPadApp extends StatefulWidget {
  const TPadApp({super.key});

  @override
  State<TPadApp> createState() => _TPadAppState();
}

class _TPadAppState extends State<TPadApp> {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(ReceiverServices.net.start());
      unawaited(ReceiverServices.pairing.refresh());
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TPad Receiver',
      debugShowCheckedModeBanner: false,
      theme: TPadTheme.dark(),
      home: Scaffold(
        appBar: AppBar(title: const Text('TPad Receiver')),
        body: IndexedStack(
          index: _tab,
          children: const [
            PairingScreen(),
            DevicesScreen(),
            LogScreen(),
            SettingsScreen(),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _tab,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.qr_code_2), label: 'Pair'),
            NavigationDestination(icon: Icon(Icons.devices), label: 'Devices'),
            NavigationDestination(icon: Icon(Icons.terminal), label: 'Log'),
            NavigationDestination(
                icon: Icon(Icons.settings), label: 'Settings'),
          ],
        ),
      ),
    );
  }
}
